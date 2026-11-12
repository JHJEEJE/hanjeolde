"""logic.py — 한 절 더의 '머리' 부분 (화면은 app.py, 문구는 i18n.py)

참가서류 5번 'AI 기술 활용'과 이 파일의 연결
  ① AI 기반 순례길 추천      : plan_candidates (규칙으로 후보 계산) + agent_choose (Claude가 도구 호출로 고르기)
  ② 날씨 기반 자동 설정      : get_conditions (Open-Meteo, 안 되면 일몰을 직접 계산)
  ③ 코스 유형별 계산         : leg_info (토블러 보행 함수) · rest_near (반경 1km 쉼터)
  ④ AI 스토리텔링 · 음성     : story_for · diff_line · teaser · mission_for · season_for · retell
  ⑤ 순례 일지 · 다음 순례     : journal_lines · recommend (코스 태그 유사도)
  ⑥ 중단 이유 분석 · 보완     : log_event · make_virtual · segment_table · suggestion

모든 함수의 lang 값: "ko" · "en" · "ja" · "zh"
API 키가 없거나 인터넷이 끊겨도 모든 기능이 규칙 기반으로 돌아가요.
"""
from __future__ import annotations

import json
import math
import os
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

import i18n as I

KST = timezone(timedelta(hours=9))
BASE = Path(__file__).parent
DATA = BASE / "data"
LOG_FILE = BASE / "logs" / "pilgrim_log.json"
FIX_FILE = BASE / "logs" / "fixes.json"
GYEONGJU = (35.84, 129.22)

# ---------------------------------------------------------------- 선택지 (값은 한국어, 화면 표시는 i18n.lab)
WHO = ["혼자·친구", "아이와 함께", "어르신과 함께", "외국인 친구와"]
TIMES = {"1시간": 60, "2시간": 120, "반나절": 240}
LEVELS = ["가볍게", "보통", "산길도 좋아요"]
INTERESTS = ["역사", "건축", "사진", "쉼"]
STOP_KEYS = ["시간", "체력", "흥미", "날씨", "동행", "기타"]
WHO_SPEED = {"아이와 함께": 0.75, "어르신과 함께": 0.75}
STAY_MIN = {"museum": 30, "bulguksa": 40, "seokguram": 25}   # 둘러보는 시간(분)
DEFAULT_STAY = 15
MAX_LEG_KM = 3.0           # 직선거리로 이보다 먼 구간은 걷는 순례에서 뺌
PATH_FACTOR = 1.3          # 길 데이터를 못 받을 때: 직선거리 × 1.3


# ---------------------------------------------------------------- 데이터
def data_path(name: str) -> Path:
    """data 폴더 → 앱 폴더 바로 아래 순서로 찾아요. (GitHub에 data 폴더가 안 올라가도 파일만 있으면 동작)"""
    for p in (DATA / name, BASE / name):
        if p.exists():
            return p
    return DATA / name


def _json(name: str, default):
    p = data_path(name)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data
def load_places() -> pd.DataFrame:
    df = pd.read_csv(data_path("places.csv"), encoding="utf-8-sig")
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)
    return df.set_index("id", drop=False)


@st.cache_data
def load_all() -> dict:
    return {
        "courses": _json("courses.json", []),
        "stories": _json("stories.json", {}),
        "pieces": _json("story_pieces.json", {}),
        "tags": {k: v for k, v in _json("course_tags.json", {}).items() if not k.startswith("_")},
        "tr": _json("translations.json", {}),
        "ptags": _json("place_tags.json", {"places": {}}),
    }


def load_rest_spots() -> pd.DataFrame:
    p = data_path("rest_spots.csv")
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, encoding="utf-8-sig", dtype=str).fillna("")
    df = df[df["name"].str.strip() != ""]
    if df.empty:
        return df
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df.dropna(subset=["lat", "lon"])


TOUR_URL = "https://apis.data.go.kr/B551011/KorService2/locationBasedList2"


@st.cache_data(ttl=86400, show_spinner=False)
def _tour(lat: float, lon: float, radius: int, key: str):
    """한국관광공사 TourAPI 위치기반 조회: 반경 안 음식점·카페(contentTypeId 39). 실패하면 None."""
    try:
        r = requests.get(TOUR_URL, timeout=6, params={
            "serviceKey": key, "MobileOS": "ETC", "MobileApp": "HanJeolDeo", "_type": "json",
            "mapX": f"{lon:.6f}", "mapY": f"{lat:.6f}", "radius": radius, "contentTypeId": 39,
            "arrange": "E", "numOfRows": 30, "pageNo": 1})
        body = r.json()["response"]
        if str(body["header"]["resultCode"]) not in ("0000", "00"):
            return None
        items = body["body"]["items"]
        items = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(items, dict):
            items = [items]
        rows = []
        for it in items:
            try:
                rows.append({"id": f"tour_{it.get('contentid')}", "name": it.get("title", ""),
                             "type": "카페" if it.get("cat3") == "A05020900" else "식당",
                             "lat": float(it["mapy"]), "lon": float(it["mapx"]), "open": "", "close": "",
                             "closed_day": "", "indoor": "Y", "near_poi": "", "partner": "", "coupon": "",
                             "source": "TourAPI", "checked_date": "", "addr": it.get("addr1", "")})
            except (KeyError, ValueError, TypeError):
                continue
        return rows
    except Exception:
        return None


def tour_spots(places: pd.DataFrame, stop_ids: list, radius: int = 1000) -> pd.DataFrame | None:
    """순례길 장소마다 반경 1km 음식점·카페. 키가 없거나 실패하면 None."""
    key = tour_key()
    if not key:
        return None
    rows, ok = {}, False
    for sid in dict.fromkeys(stop_ids):
        p = places.loc[sid]
        got = _tour(round(float(p.lat), 5), round(float(p.lon), 5), radius, key)
        if got is None:
            continue
        ok = True
        for r in got:
            rows.setdefault(r["id"], r)
    if not ok:
        return None
    return pd.DataFrame(list(rows.values()))


def example_rest_spots(places: pd.DataFrame, stop_ids: list, lang: str = "ko") -> pd.DataFrame:
    """발표용 '예시 쉼터' (실제 가게 아님). rest_spots.csv가 비어 있을 때만 데모 설정에서 켜요."""
    rows = []
    for i, sid in enumerate(stop_ids):
        p = places.loc[sid]
        rows.append({
            "id": f"ex{i}", "name": I.t("example_spot", lang, x=chr(65 + i)), "type": ["카페", "식당", "공방"][i % 3],
            "lat": p.lat + 0.0012, "lon": p.lon + 0.0010, "open": "09:00", "close": "21:00", "closed_day": "",
            "indoor": "Y", "near_poi": sid, "partner": "후보", "coupon": "", "source": "예시", "checked_date": "",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 번역된 이름 · 소개
def _tr_place(data, pid, lang):
    return data["tr"].get("places", {}).get(pid, {}).get(lang)


def place_name(pid, places, data, lang) -> str:
    if pid not in places.index:
        return pid
    p = places.loc[pid]
    if lang == "en" and str(p.get("name_en", "")).strip() not in ("", "nan"):
        return str(p["name_en"])
    tr = _tr_place(data, pid, lang)
    return tr[0] if tr else str(p["name"])


def place_desc(pid, places, data, lang) -> str:
    p = places.loc[pid]
    if lang == "ko":
        return str(p.story)
    if lang == "en":
        return str(p.desc_en)
    tr = _tr_place(data, pid, lang)
    return tr[1] if tr else str(p.desc_en)


def era_text(era, data, lang) -> str:
    if lang == "ko":
        return str(era)
    return data["tr"].get("eras", {}).get(str(era), {}).get(lang, str(era))


def course_text(course: dict, data, lang) -> tuple[str, str]:
    if lang == "ko":
        return course["title"], course.get("subtitle", "")
    tr = data["tr"].get("courses", {}).get(course["id"], {}).get(lang)
    return tuple(tr) if tr else (course["title"], course.get("subtitle", ""))


def tag_text(tag, data, lang) -> str:
    if lang == "ko":
        return tag
    return data["tr"].get("tags", {}).get(tag, {}).get(lang, tag)


def spot_type(t, lang) -> str:
    d = I.SPOT_TYPE.get(t)
    return (d.get(lang) or d["ko"]) if d else t


# ---------------------------------------------------------------- 거리 · 링크
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def km_between(places, a: str, b: str) -> float:
    pa, pb = places.loc[a], places.loc[b]
    return haversine_km(pa.lat, pa.lon, pb.lat, pb.lon)


def kakao_to(name: str, lat: float, lon: float) -> str:
    return f"https://map.kakao.com/link/to/{quote(str(name))},{lat},{lon}"


def kakao_from_to(a_name, a_lat, a_lon, b_name, b_lat, b_lon) -> str:
    return (f"https://map.kakao.com/link/from/{quote(str(a_name))},{a_lat},{a_lon}"
            f"/to/{quote(str(b_name))},{b_lat},{b_lon}")


@st.cache_data(ttl=86400, show_spinner=False)
def walk_route(lat1, lon1, lat2, lon2):
    """OpenStreetMap 도보 길찾기(FOSSGIS OSRM). 실패하면 None → 직선 × 1.3으로 어림."""
    url = f"https://routing.openstreetmap.de/routed-foot/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    try:
        r = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=6)
        route = r.json()["routes"][0]
        coords = [(c[1], c[0]) for c in route["geometry"]["coordinates"]]
        return float(route["distance"]), coords
    except Exception:
        return None


# ---------------------------------------------------------------- ② 날씨 · 일몰
def sunset_calc(d: date, lat: float = GYEONGJU[0], lon: float = GYEONGJU[1]) -> datetime:
    """인터넷이 없어도 쓰는 일몰 계산 (NOAA 근사식, 오차 수 분)."""
    n = d.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                   - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    cos_ha = math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(decl)) - math.tan(la) * math.tan(decl)
    ha = math.degrees(math.acos(max(-1.0, min(1.0, cos_ha))))
    minutes_utc = 720 - 4 * (lon - ha) - eq
    base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return (base + timedelta(minutes=minutes_utc)).astimezone(KST)


@st.cache_data(ttl=1800, show_spinner=False)
def _open_meteo():
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=6, params={
            "latitude": GYEONGJU[0], "longitude": GYEONGJU[1],
            "current": "temperature_2m,precipitation,weather_code",
            "daily": "sunset", "timezone": "Asia/Seoul", "forecast_days": 1})
        d = r.json()
        cur = d["current"]
        sunset = datetime.fromisoformat(d["daily"]["sunset"][0]).replace(tzinfo=KST)
        code = int(cur.get("weather_code") or 0)
        rain = float(cur.get("precipitation") or 0) > 0.1 or code in range(51, 100)
        return {"temp": float(cur["temperature_2m"]), "rain": rain, "sunset": sunset.isoformat()}
    except Exception:
        return None


# ---- 기상청 단기예보 (공공데이터포털 키: Secrets의 DATA_GO_KR_KEY)
KMA_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
SKY_ICON = {"1": "☀️", "3": "⛅", "4": "☁️"}


def latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    """위경도 → 기상청 5km 격자(nx, ny). 기상청 활용가이드의 LCC 변환식."""
    RE, GRID, SLAT1, SLAT2, OLON, OLAT, XO, YO = 6371.00877, 5.0, 30.0, 60.0, 126.0, 38.0, 43, 136
    D = math.pi / 180.0
    re = RE / GRID
    s1, s2, olon, olat = SLAT1 * D, SLAT2 * D, OLON * D, OLAT * D
    sn = math.log(math.cos(s1) / math.cos(s2)) / math.log(
        math.tan(math.pi * 0.25 + s2 * 0.5) / math.tan(math.pi * 0.25 + s1 * 0.5))
    sf = math.tan(math.pi * 0.25 + s1 * 0.5) ** sn * math.cos(s1) / sn
    ro = re * sf / math.tan(math.pi * 0.25 + olat * 0.5) ** sn
    ra = re * sf / math.tan(math.pi * 0.25 + lat * D * 0.5) ** sn
    theta = lon * D - olon
    if theta > math.pi:
        theta -= 2 * math.pi
    if theta < -math.pi:
        theta += 2 * math.pi
    theta *= sn
    return int(ra * math.sin(theta) + XO + 0.5), int(ro - ra * math.cos(theta) + YO + 0.5)


# 키 이름: 서비스별 키가 있으면 그걸 먼저, 없으면 공통 키(DATA_GO_KR_KEY)를 써요.
KEY_NAMES = {
    "kma": ("KMA_API_KEY", "KMA_KEY", "WEATHER_KEY"),
    "tour": ("TOUR_API_KEY", "TOUR_KEY", "TOURAPI_KEY"),
    "common": ("DATA_GO_KR_KEY", "SERVICE_KEY", "SERVICEKEY", "DATA_KEY", "PUBLIC_DATA_KEY"),
}
SESSION_KEY = {"kma": "kma_key_input", "tour": "tour_key_input"}   # 사이드바 입력칸 (지금 접속에서만)


def _walk_secrets(obj, prefix=""):
    try:
        items = obj.items()
    except Exception:
        return
    for k, v in items:
        if hasattr(v, "items"):
            yield from _walk_secrets(v, f"{prefix}{k}.")
        else:
            yield f"{prefix}{k}", v


def secret_status(service: str = "common") -> tuple[str | None, str]:
    """(키, 어디서 찾았는지). service: 'kma' · 'tour' · 'common'.
    Secrets에 [섹션] 아래 넣었거나 이름을 조금 다르게 써도 찾아요."""
    typed = str(st.session_state.get(SESSION_KEY.get(service, ""), "") or "").strip()
    if typed:
        return typed, "사이드바 입력칸"
    order = (KEY_NAMES[service] + KEY_NAMES["common"]) if service in ("kma", "tour") else KEY_NAMES["common"]
    try:
        pairs = list(_walk_secrets(st.secrets))
    except Exception as e:   # secrets.toml 형식 오류
        pairs, err = [], type(e).__name__
    else:
        err = None
    found = {full.split(".")[-1].upper().replace("-", "_"): (full, str(v).strip()) for full, v in pairs if str(v).strip()}
    for name in order:
        if name in found:
            return found[name][1], f"Secrets의 {found[name][0]}"
        if os.environ.get(name):
            return os.environ[name], f"환경변수 {name}"
    if err or not pairs:
        return None, "Secrets가 비어 있거나 형식 오류 (키 값을 \"따옴표\"로 감쌌는지 확인)"
    return None, "키를 못 찾음 (지금 Secrets에 있는 이름: " + ", ".join(k for k, _ in pairs) + ")"


def data_key() -> str | None:
    return secret_status("common")[0]


def kma_key() -> str | None:
    return secret_status("kma")[0]


def tour_key() -> str | None:
    return secret_status("tour")[0]


def _kma_items(op: str, base: datetime, nx: int, ny: int, key: str) -> list:
    r = requests.get(f"{KMA_URL}/{op}", timeout=6, params={
        "serviceKey": key, "pageNo": 1, "numOfRows": 1000, "dataType": "JSON",
        "base_date": f"{base:%Y%m%d}", "base_time": f"{base:%H%M}", "nx": nx, "ny": ny})
    body = r.json()["response"]
    if body["header"]["resultCode"] != "00":
        raise ValueError(body["header"].get("resultMsg"))
    items = body["body"]["items"]
    return items.get("item", []) if isinstance(items, dict) else []


def kma_bases(now: datetime) -> tuple[datetime, datetime]:
    """(초단기실황 발표시각, 단기예보 발표시각). 실황은 매시 정각(약 40분 뒤 제공), 단기예보는 02·05·…·23시(약 10분 뒤 제공)."""
    ncst = (now - timedelta(minutes=45)).replace(minute=0, second=0, microsecond=0)
    t = now - timedelta(minutes=15)
    hours = [h for h in (2, 5, 8, 11, 14, 17, 20, 23) if h <= t.hour]
    if hours:
        fc = t.replace(hour=hours[-1], minute=0, second=0, microsecond=0)
    else:
        fc = (t - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
    return ncst, fc


@st.cache_data(ttl=1800, show_spinner=False)
def _kma(ncst_iso: str, fc_iso: str, nx: int, ny: int, key: str, now_iso: str):
    """기상청 실황 + 단기예보 → {temp, pty, rain_now, pop_max, sky, tmx, tmn, pcp}. 실패하면 None."""
    try:
        now = datetime.fromisoformat(now_iso)
        nc = {i["category"]: i["obsrValue"] for i in _kma_items("getUltraSrtNcst", datetime.fromisoformat(ncst_iso), nx, ny, key)}
        fc = _kma_items("getVilageFcst", datetime.fromisoformat(fc_iso), nx, ny, key)
        soon, sky, tmx, tmn = [], None, None, None
        today = f"{now:%Y%m%d}"
        for i in fc:
            when = datetime.strptime(i["fcstDate"] + i["fcstTime"], "%Y%m%d%H%M").replace(tzinfo=KST)
            if i["category"] == "TMX" and i["fcstDate"] == today:
                tmx = float(i["fcstValue"])
            if i["category"] == "TMN" and i["fcstDate"] == today:
                tmn = float(i["fcstValue"])
            if now - timedelta(minutes=59) <= when <= now + timedelta(hours=3):
                soon.append(i)
        pops = [int(i["fcstValue"]) for i in soon if i["category"] == "POP"]
        skies = [i["fcstValue"] for i in soon if i["category"] == "SKY"]
        sky = skies[0] if skies else None
        pty = str(nc.get("PTY", "0"))
        temp = float(nc["T1H"]) if "T1H" in nc else next((float(i["fcstValue"]) for i in soon if i["category"] == "TMP"), None)
        return {"temp": temp, "pty": pty, "rain_now": pty not in ("0", ""), "pop_max": max(pops) if pops else None,
                "sky": sky, "tmx": tmx, "tmn": tmn, "pcp": nc.get("RN1")}
    except Exception:
        return None


def kma_now(now: datetime) -> dict | None:
    key = kma_key()
    if not key:
        return None
    nx, ny = latlon_to_grid(*GYEONGJU)
    ncst, fc = kma_bases(now)
    return _kma(ncst.isoformat(), fc.isoformat(), nx, ny, key, now.replace(minute=(now.minute // 30) * 30, second=0,
                                                                            microsecond=0).isoformat())


def season_of(month: int) -> str:
    return {12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄",
            6: "여름", 7: "여름", 8: "여름"}.get(month, "가을")


def get_conditions(demo_weather: str = "실시간", demo_month: int | None = None,
                   now: datetime | None = None) -> dict:
    now = now or datetime.now(KST)
    month = demo_month or now.month
    out = {"now": now, "month": month, "season": season_of(month)}
    if demo_weather != "실시간":
        preset = {"맑음": (16.0, False), "비": (12.0, True), "영하": (-3.0, False), "폭염": (33.0, False)}[demo_weather]
        out.update(temp=preset[0], rain=preset[1], sunset=sunset_calc(now.date()), source="데모 날씨")
    else:
        om = _open_meteo()
        sunset = datetime.fromisoformat(om["sunset"]) if om else sunset_calc(now.date())
        kma = kma_now(now)
        if kma and kma["temp"] is not None:
            pop = kma["pop_max"]
            out.update(temp=kma["temp"], rain=kma["rain_now"] or (pop is not None and pop >= 60), sunset=sunset,
                       source="기상청 단기예보", pop=pop, sky=kma["sky"], pty=kma["pty"], tmx=kma["tmx"], tmn=kma["tmn"])
        elif om:
            out.update(temp=om["temp"], rain=om["rain"], sunset=sunset, source="Open-Meteo")
        else:
            out.update(temp=None, rain=False, sunset=sunset, source="일몰 계산값 (날씨 연결 안 됨)")
    out["cold"] = out["temp"] is not None and out["temp"] <= 0
    return out


def weather_lines(c: dict, lang: str) -> list:
    if c.get("pty") in ("3", "7"):
        icon = "🌨️"
    elif c["rain"]:
        icon = "🌧️"
    elif c["cold"]:
        icon = "🥶"
    else:
        icon = SKY_ICON.get(str(c.get("sky")), "☀️")
    t = f"{icon} {c['temp']:.0f}°" if c["temp"] is not None else f"{icon} {I.t('weather_na', lang)}"
    if c.get("pop") is not None:
        t += f" · ☔{c['pop']}%"
    return [t, I.t("sunset", lang, t=f"{c['sunset']:%H:%M}")]


# ---------------------------------------------------------------- ③ 고도 · 토블러
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_elevations(ids: tuple, lats: tuple, lons: tuple) -> dict:
    try:
        r = requests.get("https://api.open-meteo.com/v1/elevation", timeout=6, params={
            "latitude": ",".join(f"{x:.6f}" for x in lats), "longitude": ",".join(f"{x:.6f}" for x in lons)})
        return dict(zip(ids, [float(v) for v in r.json()["elevation"]]))
    except Exception:
        return {}


def elevations(places: pd.DataFrame) -> dict:
    return fetch_elevations(tuple(places.index), tuple(places.lat), tuple(places.lon))


def hill_pairs(courses: list, tags: dict) -> set:
    """고도를 못 받을 때 쓰는 어림: 산길 코스 안의 구간은 오르막으로 봐요."""
    out = set()
    for c in courses:
        terrain = tags.get(c["id"], {}).get("terrain", "")
        if c.get("difficulty", 1) >= 3 or "산" in terrain or "오르막" in c.get("mode", ""):
            s = c["stops"]
            for a, b in zip(s, s[1:]):
                out.add((a, b))
                out.add((b, a))
    return out


def tobler_kmh(slope: float) -> float:
    """토블러 보행 함수: 평지 약 5km/h, 경사가 급할수록 느려져요."""
    return 6 * math.exp(-3.5 * abs(slope + 0.05))


def grade_label(slope: float) -> str:
    """한국어 키를 돌려줘요. 화면에선 i18n.lab('grade', ...)로 번역."""
    s = abs(slope)
    if s < 0.03:
        return "평지"
    word = "오르막" if slope > 0 else "내리막"
    return f"완만한 {word}" if s < 0.08 else f"가파른 {word}"


def leg_info(places, a, b, who, elev, hills, speed_factor=1.0, dist_m=None) -> dict:
    straight = km_between(places, a, b) * 1000
    dist = dist_m or straight * PATH_FACTOR
    if a in elev and b in elev:
        slope, guessed = (elev[b] - elev[a]) / max(dist, 1), False
    elif (a, b) in hills:
        slope, guessed = 0.08, True
    else:
        slope, guessed = 0.0, True
    kmh = tobler_kmh(slope) * WHO_SPEED.get(who, 1.0) * speed_factor
    return {"from": a, "to": b, "dist_m": dist, "slope": slope, "grade": grade_label(slope),
            "minutes": dist / 1000 / kmh * 60, "kmh": kmh, "guessed": guessed,
            "hill": abs(slope) >= 0.05}


def stay(pid: str) -> int:
    return STAY_MIN.get(pid, DEFAULT_STAY)


# ---------------------------------------------------------------- ① 순례길 후보
def _walkable(places, seq) -> bool:
    return all(km_between(places, a, b) <= MAX_LEG_KM for a, b in zip(seq, seq[1:]))


def candidate_sequences(start: str, places, courses) -> list:
    seqs = []
    for c in courses:
        s = c["stops"]
        if start not in s:   # 버스 구간은 아래 _walkable(3km)에서 걸러져요
            continue
        i = s.index(start)
        for direction in (s[i:], list(reversed(s[: i + 1]))):
            clean = []
            for x in direction:
                if x not in clean:
                    clean.append(x)
            for n in range(2, min(4, len(clean)) + 1):
                seq = clean[:n]
                if _walkable(places, seq):
                    seqs.append((tuple(seq), c["id"]))
    if not seqs:  # 코스에 없는 곳에서 시작하면: 가까운 곳을 차례로 이어 붙여요
        chain, pool = [start], [p for p in places.index if p not in (start, "campus")]
        while len(chain) < 4:
            near = sorted(pool, key=lambda p: km_between(places, chain[-1], p))
            near = [p for p in near if km_between(places, chain[-1], p) <= 2.5 and p not in chain]
            if not near:
                break
            chain.append(near[0])
            seqs.append((tuple(chain), None))
    uniq, seen = [], set()
    for seq, cid in seqs:
        if seq not in seen:
            seen.add(seq)
            uniq.append((seq, cid))
    return uniq


def has_piece(data, pid) -> bool:
    return pid in data["pieces"].get("pieces", {})


def evaluate(seq, places, who, elev, hills, speed_factor=1.0) -> dict:
    legs = [leg_info(places, a, b, who, elev, hills, speed_factor) for a, b in zip(seq, seq[1:])]
    walk = sum(l["minutes"] for l in legs)
    stays = sum(stay(p) for p in seq)
    return {"stops": list(seq), "legs": legs, "walk_min": walk, "stay_min": stays,
            "total_min": walk + stays, "dist_m": sum(l["dist_m"] for l in legs),
            "hill": any(l["hill"] for l in legs), "guessed": any(l["guessed"] for l in legs)}


def time_budget(user: dict, cond: dict, lang: str = "ko") -> tuple[int, list]:
    budget, notes = user["minutes"], []
    left = int((cond["sunset"] - cond["now"]).total_seconds() // 60) - 20
    if left < budget:
        budget = max(0, left)
        notes.append(I.t("n_sunset", lang, t=f"{cond['sunset']:%H:%M}"))
    if cond["rain"] and cond.get("pop") is not None and cond.get("pty") in (None, "0"):
        notes.append(I.t("n_pop", lang, p=cond["pop"]))
    elif cond["rain"]:
        notes.append(I.t("n_rain", lang))
    if cond["cold"]:
        notes.append(I.t("n_cold", lang))
    return budget, notes


def plan_candidates(start: str, user: dict, cond: dict, places, data, elev, hills,
                    lang: str = "ko") -> tuple[list, int, list]:
    budget, notes = time_budget(user, cond, lang)
    out = []
    for seq, cid in candidate_sequences(start, places, data["courses"]):
        if cond["cold"] and len(seq) > 3:
            continue
        ev = evaluate(seq, places, user["who"], elev, hills)
        if ev["total_min"] > budget:
            continue
        if user["level"] == "가볍게" and ev["hill"]:
            continue
        cats = [places.loc[p, "category"] for p in seq]
        diverse = sum(1 for x, y in zip(cats, cats[1:]) if x != y)
        pieces = sum(has_piece(data, p) for p in seq)
        verified = sum(1 for p in seq if data["pieces"].get("pieces", {}).get(p, {}).get("verified"))
        indoor_end = seq[-1] == "museum"
        score = 1.5 * len(seq) + 2 * pieces + 1 * verified + 0.8 * diverse
        if (cond["rain"] or cond["cold"]) and indoor_end:
            score += 3
        if user["level"] == "보통" and ev["hill"]:
            score -= 2
        reasons = [I.t("r_budget", lang, b=budget, t=f"{ev['total_min']:.0f}", km=f"{ev['dist_m'] / 1000:.1f}")]
        if diverse:
            reasons.append(I.t("r_diverse", lang, x=" → ".join(I.lab("category", c, lang) for c in dict.fromkeys(cats))))
        if pieces:
            reasons.append(I.t("r_pieces", lang, i=I.lab("interest", user["interest"], lang), n=pieces))
        if user["level"] == "가볍게":
            reasons.append(I.t("r_light", lang))
        if cond["rain"] and indoor_end:
            reasons.append(I.t("r_rain_end", lang))
        elif cond["cold"] and indoor_end:
            reasons.append(I.t("r_cold_end", lang))
        ev.update(id=f"P{len(out) + 1}", course_id=cid, score=round(score, 1), reasons=reasons)
        out.append(ev)
    out.sort(key=lambda x: -x["score"])
    for i, p in enumerate(out):
        p["id"] = f"P{i + 1}"
    if not out:  # 아무것도 안 맞으면 가장 가까운 한 곳만
        near = sorted([p for p in places.index if p != start], key=lambda p: km_between(places, start, p))[0]
        ev = evaluate((start, near), places, user["who"], elev, hills)
        ev.update(id="P1", course_id=None, score=0, reasons=[I.t("r_nearest", lang)])
        out = [ev]
    return out[:3], budget, notes


# ---------------------------------------------------------------- LLM (선택)
def _secret(name: str, default=None):
    try:
        v = st.secrets.get(name)
        if v:
            return v
    except Exception:
        pass
    return os.environ.get(name, default)


def llm_ready() -> bool:
    return bool(_secret("ANTHROPIC_API_KEY"))


def call_claude(messages, system, model=None, tools=None, max_tokens=600) -> dict | None:
    key = _secret("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = {"model": model or _secret("AGENT_MODEL", "claude-sonnet-5-5"), "max_tokens": max_tokens,
            "system": system, "messages": messages}
    if tools:
        body["tools"] = tools
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=25, json=body, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _text_of(res: dict) -> str:
    return "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text").strip()


AGENT_TOOLS = [
    {"name": "find_routes", "description": "시작 사찰에서 조건(남은 시간·걷기 자신감·날씨)에 맞는 도보 순례길 후보를 돌려준다.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_conditions", "description": "지금 날씨(기온·비), 해 지는 시각, 쓸 수 있는 시간을 돌려준다.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_story_preview", "description": "장소 id와 관심사로 준비된 이야기의 첫 문장을 돌려준다.",
     "input_schema": {"type": "object", "properties": {"place_id": {"type": "string"},
                                                       "interest": {"type": "string", "enum": INTERESTS}},
                      "required": ["place_id", "interest"]}},
]


def agent_choose(cands, budget, cond, user, places, data, lang: str = "ko") -> dict | None:
    """① 에이전트: Claude가 도구를 불러 후보·조건·이야기를 확인하고 하나를 골라 이유를 써요."""
    if not llm_ready() or not cands:
        return None

    def run(name, args):
        if name == "find_routes":
            return [{"plan_id": c["id"], "stops": [place_name(p, places, data, lang) for p in c["stops"]],
                     "stop_ids": c["stops"], "minutes": round(c["total_min"]), "km": round(c["dist_m"] / 1000, 1),
                     "hill": c["hill"], "rule_reasons": c["reasons"]} for c in cands]
        if name == "get_conditions":
            return {"temp": cond["temp"], "rain": cond["rain"], "sunset": f"{cond['sunset']:%H:%M}",
                    "minutes_available": budget, "season": cond["season"]}
        if name == "get_story_preview":
            text, _, _ = story_for(args.get("place_id", ""), args.get("interest", user["interest"]), places, data, lang)
            return {"preview": text[:140]}
        return {"error": "unknown tool"}

    system = ("너는 경주 사찰 도보 순례길을 짜는 AI 에이전트야. 먼저 도구로 후보와 조건을 확인하고, "
              "필요하면 이야기 미리보기를 본 다음 후보 중 하나만 골라. 도구 결과에 없는 사실은 절대 지어내지 마. "
              f'마지막 답은 JSON 한 줄만: {{"plan_id": "P1", "reason": "고른 이유 2문장, {I.LLM_LANG[lang]}로"}}')
    msgs = [{"role": "user", "content": f"일행: {user['who']}, 시간: {user['minutes']}분, 걷기: {user['level']}, "
                                         f"관심사: {user['interest']}, 시작: {places.loc[cands[0]['stops'][0], 'name']}"}]
    for _ in range(5):
        res = call_claude(msgs, system, tools=AGENT_TOOLS, max_tokens=700)
        if not res:
            return None
        if res.get("stop_reason") == "tool_use":
            msgs.append({"role": "assistant", "content": res["content"]})
            results = [{"type": "tool_result", "tool_use_id": b["id"],
                        "content": json.dumps(run(b["name"], b.get("input", {})), ensure_ascii=False)}
                       for b in res["content"] if b.get("type") == "tool_use"]
            msgs.append({"role": "user", "content": results})
            continue
        text = _text_of(res)
        try:
            d = json.loads(text[text.find("{"): text.rfind("}") + 1])
            chosen = next(c for c in cands if c["id"] == d["plan_id"])
            return {"plan": chosen, "reason": str(d.get("reason", ""))[:300]}
        except Exception:
            return None
    return None


def retell(text: str, who: str, lang: str = "ko") -> str:
    """④ 말투 맞춤 (Haiku): 사실은 그대로, 말투만. 키가 없으면 원문."""
    if who in ("혼자·친구", "혼자", "친구") or not llm_ready():
        return text
    res = call_claude([{"role": "user", "content": text}],
                      f"아래 글을 '{who}' 일행에게 들려주듯 말투만 바꿔. 사실·숫자·이름은 그대로 두고 새 사실은 절대 더하지 마. "
                      f"3문장 이내, {I.LLM_LANG[lang]}로. 바꾼 글만 답해.",
                      model=_secret("FAST_MODEL", "claude-haiku-5-5"), max_tokens=300)
    out = _text_of(res) if res else ""
    return out or text


# ---------------------------------------------------------------- ④ 이야기 · 미션 · 계절
def _piece(data, pid):
    return data["pieces"].get("pieces", {}).get(pid)


def _piece_tr(data, pid, lang):
    """이야기 조각의 해당 언어판. 한국어면 원본, 번역이 없으면 None."""
    if lang == "ko":
        return _piece(data, pid)
    return data["tr"].get("pieces", {}).get(pid, {}).get(lang)


def story_for(pid, interest, places, data, lang: str = "ko") -> tuple[str, list, str]:
    """(이야기, 출처, 상태) 상태: 'ok' 출처 확인 / 'review' 검수 중 / 'pending' 출처 확인 중"""
    pc, tr = _piece(data, pid), _piece_tr(data, pid, lang)
    if pc and tr and interest in tr.get("story", {}):
        return tr["story"][interest], pc.get("sources", []), ("ok" if pc.get("verified") else "review")
    st_ = data["stories"].get(pid)
    if lang == "ko" and isinstance(st_, dict) and st_.get("story"):
        return st_["story"], st_.get("sources", []), "ok"
    if pid in places.index:
        return place_desc(pid, places, data, lang), [], "pending"
    return "", [], "pending"


def piece_title(pid, places, data, n: int, lang: str = "ko") -> str:
    tr = _piece_tr(data, pid, lang)
    return tr["title"] if tr and tr.get("title") else I.t("piece_n", lang, n=n, name=place_name(pid, places, data, lang))


def diff_line(prev, cur, places, data, lang: str = "ko") -> str:
    pc, pp, tr = _piece(data, cur), _piece(data, prev), _piece_tr(data, cur, lang)
    if pc and pp and tr and tr.get("diff_from_prev") and pp.get("order", 0) == pc.get("order", 0) - 1:
        return tr["diff_from_prev"]
    a, b = places.loc[prev], places.loc[cur]
    an, bn = place_name(prev, places, data, lang), place_name(cur, places, data, lang)
    if a.category != b.category:
        return I.t("diff_generic", lang, a=an, b=bn, pa=I.lab("phrase", a.category, lang), pb=I.lab("phrase", b.category, lang))
    return I.t("diff_same", lang, a=an, c=I.lab("category", b.category, lang), e=era_text(b.era, data, lang))


def teaser(cur, nxt, places, data, lang: str = "ko") -> str:
    pc, pn, tr = _piece(data, cur), _piece(data, nxt), _piece_tr(data, cur, lang)
    if pc and pn and tr and tr.get("teaser") and pn.get("order", 0) == pc.get("order", 0) + 1:
        return tr["teaser"]
    key = f"{cur}>{nxt}"
    if lang == "ko":
        bridge = data["stories"].get("_bridges", {}).get(key)
    else:
        bridge = data["tr"].get("bridges", {}).get(key, {}).get(lang)
    if bridge:
        return bridge
    return I.t("next_generic", lang, n=place_name(nxt, places, data, lang))


def mission_for(pid, who, places, data, lang: str = "ko") -> str:
    tr = _piece_tr(data, pid, lang)
    if tr and tr.get("mission"):
        m = tr["mission"]
        return m.get(who) or m.get("기본")
    basic, kid = I.GENERIC_MISSION.get(places.loc[pid, "category"], I.GENERIC_MISSION["명소"])
    d = kid if who == "아이와 함께" else basic
    return d.get(lang) or d["ko"]


def season_for(pid, month, data, lang: str = "ko") -> tuple[list, list]:
    """(지금 열린 계절 조각, 다른 계절에 열리는 조각) — 각 항목: {'months', 'label', 'text'}"""
    now, later = [], []
    trs = data["tr"].get("seasons", [])
    for i, s in enumerate(data["pieces"].get("season_pieces", [])):
        if s["poi"] != pid:
            continue
        label, text = s["label"], s["text"]
        if lang != "ko" and i < len(trs) and lang in trs[i]:
            label, text = trs[i][lang]
        item = {"months": s["months"], "label": label, "text": text}
        (now if month in s["months"] else later).append(item)
    return now, later


# ---------------------------------------------------------------- ③ 쉼터
def open_now(spot, now: datetime) -> bool:
    days = "월화수목금토일"
    if spot.get("closed_day") and days[now.weekday()] in str(spot["closed_day"]):
        return False
    try:
        o = datetime.strptime(spot.get("open") or "00:00", "%H:%M").time()
        c = datetime.strptime(spot.get("close") or "23:59", "%H:%M").time()
        return o <= now.time() <= c
    except ValueError:
        return True


def rest_near(spots: pd.DataFrame, places, a, b, cond, limit=2, km=1.0) -> list:
    if spots is None or spots.empty:
        return []
    pa, pb = places.loc[a], places.loc[b]
    rows = []
    for _, s in spots.iterrows():
        d = min(haversine_km(pa.lat, pa.lon, s.lat, s.lon), haversine_km(pb.lat, pb.lon, s.lat, s.lon))
        if d <= km and open_now(s, cond["now"]):
            indoor_first = 0 if (cond["rain"] or cond["cold"]) and str(s.get("indoor")).upper() == "Y" else 1
            rows.append((indoor_first, d, s.to_dict()))
    rows.sort(key=lambda x: (x[0], x[1]))
    return [dict(r[2], dist_km=r[1]) for r in rows[:limit]]


# ---------------------------------------------------------------- ⑤ 일지 · 다음 순례
def _first_sentence(text: str, lang: str) -> str:
    text = str(text).strip()
    if len(text) <= 110:
        return text
    for mark in ("요.", ". ", "。"):
        if mark in text:
            i = text.index(mark) + len(mark.strip())
            return text[:i]
    return text[:80]


def journal_lines(walk: dict, places, data, cond, lang: str = "ko") -> list:
    names = [place_name(p, places, data, lang) for p in walk["arrived"]]
    who = I.lab("who_j", walk["user"]["who"], lang)
    lines = [I.t("j_title", lang, date=I.date_str(cond["now"], lang), season=I.lab("season", cond["season"], lang), who=who),
             " → ".join(names),
             I.t("j_stats", lang, km=f"{walk['walked_m'] / 1000:.1f}", a=len(walk["arrived"]),
                 b=len(walk["plan"]["stops"]), m=len(walk["missions"]))]
    for p in walk["arrived"]:
        text, _, _ = story_for(p, walk["user"]["interest"], places, data, lang)
        lines.append(f"· {place_name(p, places, data, lang)}: {_first_sentence(text, lang)}")
    if walk.get("stopped"):
        lines.append(I.t("j_stopped", lang, r=I.lab("reason", walk["stopped"], lang)))
    elif len(walk["arrived"]) == len(walk["plan"]["stops"]):
        lines.append(I.t("j_done", lang))
    return lines


def polish_journal(lines: list, lang: str = "ko") -> str | None:
    if not llm_ready():
        return None
    res = call_claude([{"role": "user", "content": "\n".join(lines)}],
                      f"아래 기록으로 따뜻한 순례 일지를 4문장으로 써. 기록에 없는 사실은 더하지 마. {I.LLM_LANG[lang]}로.",
                      model=_secret("FAST_MODEL", "claude-haiku-5-5"), max_tokens=350)
    return _text_of(res) if res else None


def course_of(stops: list, courses: list) -> str | None:
    best, score = None, 0
    for c in courses:
        k = len(set(stops) & set(c["stops"]))
        if k > score:
            best, score = c["id"], k
    return best if score >= 2 else None


def recommend(course_id, stops, data, places, lang: str = "ko") -> dict:
    tags, courses = data["tags"], {c["id"]: c for c in data["courses"]}
    cur = course_id or course_of(stops, data["courses"])
    if cur not in tags:   # 정해진 코스가 아닌 AI 길이면, 장소가 가장 많이 겹치는 코스를 기준으로
        ov = [(len(set(c["stops"]) & set(stops)), c["id"]) for c in data["courses"] if c["id"] in tags]
        ov = [x for x in ov if x[0] > 0]
        if not ov:
            return {}
        cur = max(ov)[1]
    me = set(tags[cur]["theme"])
    terrain = tags[cur].get("terrain", "")
    scored = []
    for cid, t in tags.items():
        if cid == cur or cid not in courses:
            continue
        th = set(t["theme"])
        jac = len(me & th) / len(me | th) if me | th else 0
        scored.append((jac, cid, me & th, t.get("terrain", "")))
    out = {}
    tt = lambda xs: I.join_list([tag_text(x, data, lang) for x in xs], lang)
    if scored:
        sim = max(scored, key=lambda x: (x[0], x[3] == terrain))
        if sim[0] > 0:
            out["similar"] = {"course": courses[sim[1]], "reason": I.t("rec_shared", lang, x=tt(sorted(sim[2]))),
                              "score": round(sim[0], 2)}
        new = [s for s in scored if s[0] == 0]
        if new:
            pick = sorted(new, key=lambda x: (("산" in x[3]) != ("산" in terrain), "버스" in x[3]))[0]
            out["new"] = {"course": courses[pick[1]],
                          "reason": I.t("rec_diff", lang, x=tt(tags[pick[1]]["theme"][:3])), "score": 0}
    return out


# ---------------------------------------------------------------- ⑥ 기록 · 가상 기록 · 분석
def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def load_logs() -> list:
    return _load(LOG_FILE, [])


def log_event(sid: str, event: str, **kw):
    recs = load_logs()
    recs.append({"ts": datetime.now(KST).isoformat(timespec="seconds"), "sid": sid, "event": event,
                 "virtual": False, **kw})
    _save(LOG_FILE, recs)


def load_fixes() -> dict:
    return _load(FIX_FILE, {})


def save_fixes(fixes: dict):
    _save(FIX_FILE, fixes)


VIRTUAL_ROUTES = [
    (["bunhwangsa", "hwangnyongsaji", "mitansaji", "museum"], 0.6,
     [(0.06, {"시간": .5, "기타": .5}), (0.30, {"흥미": .65, "시간": .2, "기타": .15}),
      (0.18, {"체력": .45, "날씨": .35, "시간": .2})]),
    (["hwangboksaji", "nangsan_maae", "seondeok", "sacheonwangsaji"], 0.4,
     [(0.12, {"체력": .5, "흥미": .3, "기타": .2}), (0.26, {"체력": .7, "동행": .2, "시간": .1}),
      (0.10, {"시간": .6, "기타": .4})]),
]


def make_virtual(n: int = 80, phase: str = "before", fixes: dict | None = None, seed: int = 7) -> list:
    """발표용 가상 기록. 모든 기록에 virtual=True가 붙어요. fixes가 있으면 보완한 구간의 멈춤 확률을 낮춰요."""
    rnd = random.Random(seed + (100 if phase == "after" else 0))
    fixes = fixes or {}
    out, base = [], datetime.now(KST) - timedelta(days=30)
    for _ in range(n):
        stops, _, legs = rnd.choices(VIRTUAL_ROUTES, weights=[r[1] for r in VIRTUAL_ROUTES])[0]
        sid = "v-" + uuid.uuid4().hex[:8]
        ts = base + timedelta(minutes=rnd.randint(0, 30 * 24 * 60))
        common = {"sid": sid, "virtual": True, "phase": phase, "who": rnd.choice(WHO), "interest": rnd.choice(INTERESTS)}
        out.append({**common, "ts": ts.isoformat(timespec="seconds"), "event": "start", "stops": stops})
        finished = True
        for i, (p, reasons) in enumerate(legs):
            seg = f"{stops[i]}>{stops[i + 1]}"
            if seg in fixes:
                p *= 0.45
            ts += timedelta(minutes=rnd.randint(12, 30))
            if rnd.random() < p:
                why = rnd.choices(list(reasons), weights=list(reasons.values()))[0]
                out.append({**common, "ts": ts.isoformat(timespec="seconds"), "event": "stop", "leg": i,
                            "at": stops[i], "seg": seg, "reason": why})
                finished = False
                break
            out.append({**common, "ts": ts.isoformat(timespec="seconds"), "event": "arrive", "leg": i,
                        "to": stops[i + 1], "seg": seg})
        if finished:
            out.append({**common, "ts": ts.isoformat(timespec="seconds"), "event": "finish"})
    return out


def segment_table(recs: list, places, data=None, lang: str = "ko") -> pd.DataFrame:
    """열 이름은 코드용 한국어 키(구간·진입·도착·완주율·멈춘 수·멈춘 이유 1위). 화면 표시는 app.py에서 번역."""
    entered, arrived, reasons = {}, {}, {}
    by_sid = {}
    for r in recs:
        by_sid.setdefault(r["sid"], []).append(r)
    for evs in by_sid.values():
        start = next((e for e in evs if e["event"] == "start"), None)
        if not start or not start.get("stops"):
            continue
        stops = start["stops"]
        for i in range(len(stops) - 1):
            seg = f"{stops[i]}>{stops[i + 1]}"
            ev = next((e for e in evs if e.get("leg") == i and e["event"] in ("arrive", "stop")), None)
            if ev is None:
                break
            entered[seg] = entered.get(seg, 0) + 1
            if ev["event"] == "arrive":
                arrived[seg] = arrived.get(seg, 0) + 1
            else:
                reasons.setdefault(seg, {})
                reasons[seg][ev["reason"]] = reasons[seg].get(ev["reason"], 0) + 1
                break
    data = data or {"tr": {}}
    rows = []
    for seg, n in entered.items():
        a, b = seg.split(">")
        rs = reasons.get(seg, {})
        top = max(rs, key=rs.get) if rs else "-"
        rows.append({"seg": seg, "구간": f"{place_name(a, places, data, lang)} → {place_name(b, places, data, lang)}",
                     "진입": n, "도착": arrived.get(seg, 0),
                     "완주율": round(arrived.get(seg, 0) / n * 100, 1), "멈춘 수": sum(rs.values()),
                     "멈춘 이유 1위": top, "이유별": rs})
    df = pd.DataFrame(rows)
    return df.sort_values("완주율") if not df.empty else df


def overall(recs: list) -> dict:
    starts = {r["sid"] for r in recs if r["event"] == "start"}
    fins = {r["sid"] for r in recs if r["event"] == "finish"}
    return {"starts": len(starts), "finish": len(fins), "rate": (len(fins) / len(starts) * 100) if starts else 0}


def suggestion(row, lang: str = "ko") -> str:
    key = row["멈춘 이유 1위"] if row["멈춘 이유 1위"] in I.LABELS["fix"] else "기타"
    return I.lab("fix", key, lang)

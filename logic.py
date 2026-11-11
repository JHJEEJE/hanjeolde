"""logic.py — 한 절 더의 '머리' 부분 (화면은 app.py)

참가서류 5번 'AI 기술 활용'과 이 파일의 연결
  ① AI 기반 순례길 추천      : plan_candidates (규칙으로 후보 계산) + agent_choose (Claude가 도구 호출로 고르기)
  ② 날씨 기반 자동 설정      : get_conditions (Open-Meteo, 안 되면 일몰을 직접 계산)
  ③ 코스 유형별 계산         : leg_info (토블러 보행 함수) · rest_near (반경 1km 쉼터)
  ④ AI 스토리텔링 · 음성     : story_for · diff_line · teaser · mission_for · season_for · retell
  ⑤ 순례 일지 · 다음 순례     : journal_lines · recommend (코스 태그 유사도)
  ⑥ 중단 이유 분석 · 보완     : log_event · make_virtual · segment_table · suggestion

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

KST = timezone(timedelta(hours=9))
BASE = Path(__file__).parent
DATA = BASE / "data"
LOG_FILE = BASE / "logs" / "pilgrim_log.json"
FIX_FILE = BASE / "logs" / "fixes.json"
GYEONGJU = (35.84, 129.22)

# ---------------------------------------------------------------- 선택지
WHO = ["혼자·친구", "아이와 함께", "어르신과 함께", "외국인 친구와"]
TIMES = {"1시간": 60, "2시간": 120, "반나절": 240}
LEVELS = ["가볍게", "보통", "산길도 좋아요"]
INTERESTS = ["역사", "건축", "사진", "쉼"]
WHO_SPEED = {"아이와 함께": 0.75, "어르신과 함께": 0.75}
STAY_MIN = {"museum": 30, "bulguksa": 40, "seokguram": 25}   # 둘러보는 시간(분)
DEFAULT_STAY = 15
MAX_LEG_KM = 3.0           # 직선거리로 이보다 먼 구간은 걷는 순례에서 뺌
PATH_FACTOR = 1.3          # 길 데이터를 못 받을 때: 직선거리 × 1.3
STOP_REASONS = {
    "⏱️ 시간이 모자라요": "시간", "😮‍💨 너무 힘들어요": "체력", "😐 볼거리가 없어요": "흥미",
    "🌧️ 날씨·해 질 녘": "날씨", "👨‍👩‍👧 일행이 힘들어해요": "동행", "🤔 다른 이유": "기타",
}
CATEGORY_PHRASE = {
    "현존 사찰": "지금도 스님들이 지내는 절",
    "절터": "건물 없이 터와 주춧돌만 남은 곳",
    "불상·석탑": "돌에 새긴 부처님이나 탑을 가까이 보는 곳",
    "명소": "절 밖에서 신라 이야기를 만나는 곳",
    "출발점": "순례를 시작하는 곳",
}
GENERIC_MISSION = {
    "현존 사찰": ("이 절에서 가장 오래돼 보이는 것 하나 찾아보기", "아이와 함께 절에서 동물 그림이나 조각 찾아보기"),
    "절터": ("터의 끝에서 끝까지 몇 걸음인지 세어 보기", "주춧돌을 아이와 함께 세어 보기"),
    "불상·석탑": ("정면과 옆에서 한 장씩 찍어 모습 비교하기", "부처님 표정을 아이와 따라 해 보기"),
    "명소": ("이곳을 한 문장으로 순례 일지에 남기기", "이곳에서 가장 큰 것 하나 찾아보기"),
    "출발점": ("오늘 걸을 길을 지도에서 한 번 따라가 보기", "오늘 몇 곳을 갈지 아이와 손가락으로 세어 보기"),
}
FIX_TEXT = {
    "흥미": "이 구간에 현장 미션과 이야기 조각을 하나 더 넣어요 (볼거리 보강)",
    "체력": "중간 쉼터를 넣고, 걸음이 느린 일행에겐 이 구간 시간을 넉넉히 잡아요",
    "시간": "기본 추천에서 이 구간을 선택 사항으로 돌려 전체 길이를 줄여요",
    "날씨": "비·추위·해 질 녘엔 이 구간 전에 실내 쉼터를 먼저 추천해요",
    "동행": "아이·어르신 일행이면 이 구간을 건너뛰는 짧은 길을 먼저 보여 줘요",
    "기타": "멈춘 이유를 더 모은 뒤 다시 확인해요",
}


# ---------------------------------------------------------------- 데이터
def _json(name: str, default):
    p = DATA / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data
def load_places() -> pd.DataFrame:
    df = pd.read_csv(DATA / "places.csv", encoding="utf-8-sig")
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
    }


def load_rest_spots() -> pd.DataFrame:
    p = DATA / "rest_spots.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, encoding="utf-8-sig", dtype=str).fillna("")
    df = df[df["name"].str.strip() != ""]
    if df.empty:
        return df
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df.dropna(subset=["lat", "lon"])


def example_rest_spots(places: pd.DataFrame, stop_ids: list) -> pd.DataFrame:
    """발표용 '예시 쉼터' (실제 가게 아님). rest_spots.csv가 비어 있을 때만 데모 설정에서 켜요."""
    rows = []
    for i, sid in enumerate(stop_ids):
        p = places.loc[sid]
        rows.append({
            "id": f"ex{i}", "name": f"예시 쉼터 {chr(65 + i)} (실제 가게 아님)", "type": ["카페", "식당", "공방"][i % 3],
            "lat": p.lat + 0.0012, "lon": p.lon + 0.0010, "open": "09:00", "close": "21:00", "closed_day": "",
            "indoor": "Y", "near_poi": sid, "partner": "후보", "coupon": "", "source": "예시", "checked_date": "",
        })
    return pd.DataFrame(rows)


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


def season_of(month: int) -> str:
    return {12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄",
            6: "여름", 7: "여름", 8: "여름"}.get(month, "가을")


def get_conditions(demo_weather: str = "실시간", demo_month: int | None = None,
                   now: datetime | None = None) -> dict:
    now = now or datetime.now(KST)
    month = demo_month or now.month
    out = {"now": now, "month": month, "season": season_of(month)}
    if demo_weather != "실시간":
        preset = {"맑음": (16.0, False), "비": (12.0, True), "영하": (-3.0, False)}[demo_weather]
        out.update(temp=preset[0], rain=preset[1], sunset=sunset_calc(now.date()), source="데모 날씨")
    else:
        om = _open_meteo()
        if om:
            out.update(temp=om["temp"], rain=om["rain"], sunset=datetime.fromisoformat(om["sunset"]),
                       source="Open-Meteo")
        else:
            out.update(temp=None, rain=False, sunset=sunset_calc(now.date()), source="일몰 계산값 (날씨 연결 안 됨)")
    out["cold"] = out["temp"] is not None and out["temp"] <= 0
    return out


def weather_label(c: dict) -> str:
    icon = "🌧️" if c["rain"] else ("🥶" if c["cold"] else "☀️")
    t = f"{c['temp']:.0f}°" if c["temp"] is not None else "날씨 확인 안 됨"
    return f"{icon} {t} · 일몰 {c['sunset']:%H:%M}"


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


def time_budget(user: dict, cond: dict) -> tuple[int, list]:
    budget, notes = user["minutes"], []
    left = int((cond["sunset"] - cond["now"]).total_seconds() // 60) - 20
    if left < budget:
        budget = max(0, left)
        notes.append(f"🌇 오늘 해 지는 시각이 {cond['sunset']:%H:%M}이라 해 지기 20분 전에 끝나도록 맞췄어요.")
    if cond["rain"]:
        notes.append("☔ 비 소식이 있어서 실내에서 마무리하는 길을 먼저 골랐어요.")
    if cond["cold"]:
        notes.append("🧣 기온이 0도 이하라 1~2곳만 잇는 짧은 순례로 줄이고, 따뜻한 쉼터를 넣었어요.")
    return budget, notes


def plan_candidates(start: str, user: dict, cond: dict, places, data, elev, hills) -> tuple[list, int, list]:
    budget, notes = time_budget(user, cond)
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
        reasons = [f"남은 {budget}분 안에 다녀올 수 있어요 (예상 {ev['total_min']:.0f}분, 걷기 {ev['dist_m'] / 1000:.1f}km)"]
        if diverse:
            reasons.append("앞 장소와 볼거리가 달라요 (" + " → ".join(dict.fromkeys(cats)) + ")")
        if pieces:
            reasons.append(f"'{user['interest']}' 관심사 이야기 조각이 준비된 곳 {pieces}곳")
        if user["level"] == "가볍게":
            reasons.append("'가볍게'라서 오르막 없는 평지 길만 골랐어요")
        if cond["rain"] and indoor_end:
            reasons.append("비가 와도 박물관(실내)에서 마무리해요")
        elif cond["cold"] and indoor_end:
            reasons.append("추운 날이라 따뜻한 박물관(실내)에서 마무리해요")
        ev.update(id=f"P{len(out) + 1}", course_id=cid, score=round(score, 1), reasons=reasons)
        out.append(ev)
    out.sort(key=lambda x: -x["score"])
    for i, p in enumerate(out):
        p["id"] = f"P{i + 1}"
    if not out:  # 아무것도 안 맞으면 가장 가까운 한 곳만
        near = sorted([p for p in places.index if p != start], key=lambda p: km_between(places, start, p))[0]
        ev = evaluate((start, near), places, user["who"], elev, hills)
        ev.update(id="P1", course_id=None, score=0,
                  reasons=["시간이 빠듯해서 가장 가까운 한 곳만 이어요"])
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


def agent_choose(cands, budget, cond, user, places, data) -> dict | None:
    """① 에이전트: Claude가 도구를 불러 후보·조건·이야기를 확인하고 하나를 골라 이유를 써요."""
    if not llm_ready() or not cands:
        return None

    def run(name, args):
        if name == "find_routes":
            return [{"plan_id": c["id"], "stops": [places.loc[p, "name"] for p in c["stops"]],
                     "stop_ids": c["stops"], "minutes": round(c["total_min"]), "km": round(c["dist_m"] / 1000, 1),
                     "hill": c["hill"], "rule_reasons": c["reasons"]} for c in cands]
        if name == "get_conditions":
            return {"temp": cond["temp"], "rain": cond["rain"], "sunset": f"{cond['sunset']:%H:%M}",
                    "minutes_available": budget, "season": cond["season"]}
        if name == "get_story_preview":
            text, _, _ = story_for(args.get("place_id", ""), args.get("interest", user["interest"]), places, data)
            return {"preview": text.split(". ")[0][:120]}
        return {"error": "unknown tool"}

    system = ("너는 경주 사찰 도보 순례길을 짜는 AI 에이전트야. 먼저 도구로 후보와 조건을 확인하고, "
              "필요하면 이야기 미리보기를 본 다음 후보 중 하나만 골라. 도구 결과에 없는 사실은 절대 지어내지 마. "
              '마지막 답은 JSON 한 줄만: {"plan_id": "P1", "reason": "고른 이유 2문장, 해요체"}')
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


def retell(text: str, who: str) -> str:
    """④ 말투 맞춤 (Haiku): 사실은 그대로, 말투만. 키가 없으면 원문."""
    if who == "혼자·친구" or not llm_ready():
        return text
    res = call_claude([{"role": "user", "content": text}],
                      f"아래 글을 '{who}' 일행에게 들려주듯 말투만 바꿔. 사실·숫자·이름은 그대로 두고 새 사실은 절대 더하지 마. "
                      "3문장 이내, 해요체. 바꾼 글만 답해.",
                      model=_secret("FAST_MODEL", "claude-haiku-5-5"), max_tokens=300)
    out = _text_of(res) if res else ""
    return out or text


# ---------------------------------------------------------------- ④ 이야기 · 미션 · 계절
def _piece(data, pid):
    return data["pieces"].get("pieces", {}).get(pid)


def story_for(pid, interest, places, data) -> tuple[str, list, str]:
    """(이야기, 출처, 상태) 상태: '출처 확인' / '검수 중' / '출처 확인 중'"""
    pc = _piece(data, pid)
    if pc and interest in pc.get("story", {}):
        return pc["story"][interest], pc.get("sources", []), ("출처 확인" if pc.get("verified") else "검수 중")
    st_ = data["stories"].get(pid)
    if isinstance(st_, dict) and st_.get("story"):
        return st_["story"], st_.get("sources", []), "출처 확인"
    if pid in places.index:
        return str(places.loc[pid, "story"]), [], "출처 확인 중"
    return "", [], "출처 확인 중"


def piece_title(pid, places, data, n: int) -> str:
    pc = _piece(data, pid)
    return pc["title"] if pc else f"조각 {n} · {places.loc[pid, 'name']}"


def diff_line(prev, cur, places, data) -> str:
    pc = _piece(data, cur)
    pp = _piece(data, prev)
    if pc and pp and pc.get("diff_from_prev") and pp.get("order", 0) == pc.get("order", 0) - 1:
        return pc["diff_from_prev"]
    a, b = places.loc[prev], places.loc[cur]
    if a.category != b.category:
        return f"{a['name']}이 {CATEGORY_PHRASE.get(a.category, a.category)}였다면, {b['name']}은 {CATEGORY_PHRASE.get(b.category, b.category)}예요."
    return f"{a['name']}과 같은 {b.category}지만, 시대와 이야기가 달라요: {b.era}."


def teaser(cur, nxt, places, data) -> str:
    pc, pn = _piece(data, cur), _piece(data, nxt)
    if pc and pn and pc.get("teaser") and pn.get("order", 0) == pc.get("order", 0) + 1:
        return pc["teaser"]
    bridge = data["stories"].get("_bridges", {}).get(f"{cur}>{nxt}")
    if bridge:
        return bridge
    return f"다음 이야기 조각은 {places.loc[nxt, 'name']}에서 열려요."


def mission_for(pid, who, places, data) -> str:
    pc = _piece(data, pid)
    if pc and pc.get("mission"):
        m = pc["mission"]
        return m.get(who) or m.get("기본")
    basic, kid = GENERIC_MISSION.get(places.loc[pid, "category"], GENERIC_MISSION["명소"])
    return kid if who == "아이와 함께" else basic


def season_for(pid, month, data) -> tuple[list, list]:
    """(지금 열린 계절 조각, 다른 계절에 열리는 조각)"""
    now, later = [], []
    for s in data["pieces"].get("season_pieces", []):
        if s["poi"] != pid:
            continue
        (now if month in s["months"] else later).append(s)
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
def journal_lines(walk: dict, places, data, cond) -> list:
    names = [places.loc[p, "name"] for p in walk["arrived"]]
    who = walk["user"]["who"]
    with_whom = who if who.endswith(("함께", "와")) else who + "와"
    lines = [f"{cond['now']:%Y년 %m월 %d일} {cond['season']}, {with_whom} 걸은 순례길",
             " → ".join(names),
             f"걸은 거리 약 {walk['walked_m'] / 1000:.1f}km · 모은 이야기 조각 {len(walk['arrived'])}/{len(walk['plan']['stops'])}개"
             f" · 현장 미션 {len(walk['missions'])}개 완료"]
    for p in walk["arrived"]:
        text, _, _ = story_for(p, walk["user"]["interest"], places, data)
        first = text.split("요.")[0] + "요." if "요." in text else text[:60]
        lines.append(f"· {places.loc[p, 'name']}: {first}")
    if walk.get("stopped"):
        lines.append(f"오늘은 '{walk['stopped']}' 때문에 여기까지 걸었어요. 남은 조각은 다음 순례에서 만나요.")
    elif len(walk["arrived"]) == len(walk["plan"]["stops"]):
        lines.append("모든 조각을 모아 오늘의 이야기를 완성했어요.")
    return lines


def polish_journal(lines: list) -> str | None:
    if not llm_ready():
        return None
    res = call_claude([{"role": "user", "content": "\n".join(lines)}],
                      "아래 기록으로 따뜻한 순례 일지를 4문장으로 써. 기록에 없는 사실은 더하지 마. 해요체.",
                      model=_secret("FAST_MODEL", "claude-haiku-5-5"), max_tokens=350)
    return _text_of(res) if res else None


def course_of(stops: list, courses: list) -> str | None:
    best, score = None, 0
    for c in courses:
        k = len(set(stops) & set(c["stops"]))
        if k > score:
            best, score = c["id"], k
    return best if score >= 2 else None


def recommend(course_id, stops, data, places) -> dict:
    tags, courses = data["tags"], {c["id"]: c for c in data["courses"]}
    cur = course_id or course_of(stops, data["courses"])
    if cur not in tags:
        return {}
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
    if scored:
        sim = max(scored, key=lambda x: (x[0], x[3] == terrain))
        if sim[0] > 0:
            out["similar"] = {"course": courses[sim[1]], "reason": "겹치는 주제: " + "·".join(sorted(sim[2])),
                              "score": round(sim[0], 2)}
        new = [s for s in scored if s[0] == 0]
        if new:
            pick = sorted(new, key=lambda x: (("산" in x[3]) != ("산" in terrain), "버스" in x[3]))[0]
            out["new"] = {"course": courses[pick[1]],
                          "reason": "오늘과 다른 주제: " + "·".join(tags[pick[1]]["theme"][:3]), "score": 0}
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


def segment_table(recs: list, places) -> pd.DataFrame:
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
    rows = []
    for seg, n in entered.items():
        a, b = seg.split(">")
        rs = reasons.get(seg, {})
        top = max(rs, key=rs.get) if rs else "-"
        name = lambda x: places.loc[x, "name"] if x in places.index else x
        rows.append({"seg": seg, "구간": f"{name(a)} → {name(b)}", "진입": n, "도착": arrived.get(seg, 0),
                     "완주율": round(arrived.get(seg, 0) / n * 100, 1), "멈춘 수": sum(rs.values()),
                     "멈춘 이유 1위": top, "이유별": rs})
    df = pd.DataFrame(rows)
    return df.sort_values("완주율") if not df.empty else df


def overall(recs: list) -> dict:
    starts = {r["sid"] for r in recs if r["event"] == "start"}
    fins = {r["sid"] for r in recs if r["event"] == "finish"}
    return {"starts": len(starts), "finish": len(fins), "rate": (len(fins) / len(starts) * 100) if starts else 0}


def suggestion(row) -> str:
    return FIX_TEXT.get(row["멈춘 이유 1위"], FIX_TEXT["기타"])

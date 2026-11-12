"""shops.py — 지역상생 AI 추천 (참가서류 5번 ② ③ ⑤)

1) 모으기  gather()   : 팀 조사(rest_spots.csv) + 한국관광공사 TourAPI(카페·식사·공방·문화공간)
                        + Google Places(평점·리뷰 수, 키가 있을 때)
2) 점수    score()    : 품질(베이지안 평점) · 가까움(가는 길에서 벗어나는 거리) · 상황 맞춤(시간대·날씨·일행·요청) · 제휴
3) 배정    assign()   : 구간마다 중복 없이 최대 2곳, 종류가 겹치지 않게
4) 대체    alternatives(): '볼 게 없어요' → 근처 다른 유적 + 공방·문화공간·카페
"""
from __future__ import annotations

import math

import pandas as pd
import requests
import streamlit as st

import i18n as I
import logic as L
import planner as P

KINDS = ["cafe", "meal", "craft", "culture"]
CSV_KIND = {"카페": "cafe", "찻집": "cafe", "식당": "meal", "공방": "craft", "기념품": "craft", "문화": "culture"}
GOOGLE_URL = "https://places.googleapis.com/v1/places:searchNearby"
TOUR_URL = "https://apis.data.go.kr/B551011/KorService2/locationBasedList2"


def google_key():
    typed = str(st.session_state.get("google_key_input", "") or "").strip()
    if typed:
        return typed, "사이드바 입력칸"
    try:
        pairs = list(L._walk_secrets(st.secrets))
    except Exception:
        pairs = []
    for full, v in pairs:
        if full.split(".")[-1].upper() in ("GOOGLE_PLACES_KEY", "GOOGLE_MAPS_KEY", "GOOGLE_API_KEY") and str(v).strip():
            return str(v).strip(), f"Secrets의 {full}"
    return None, "없음"


NAVER_URL = "https://openapi.naver.com/v1/search/local.json"


def naver_keys():
    """네이버 검색 API (developers.naver.com) Client ID · Secret — 선택"""
    try:
        pairs = dict((k.split(".")[-1].upper(), str(v).strip()) for k, v in L._walk_secrets(st.secrets))
    except Exception:
        pairs = {}
    cid = str(st.session_state.get("naver_id_input", "") or "").strip() or pairs.get("NAVER_CLIENT_ID")
    sec = str(st.session_state.get("naver_secret_input", "") or "").strip() or pairs.get("NAVER_CLIENT_SECRET")
    return (cid, sec) if cid and sec else (None, None)


@st.cache_data(ttl=21600, show_spinner=False)
def _naver(query, cid, sec):
    """네이버 지역 검색: 평점·리뷰 수는 주지 않지만 sort=comment로 '리뷰 많은 순' 상위 5곳을 줘요."""
    try:
        r = requests.get(NAVER_URL, timeout=6, params={"query": query, "display": 5, "sort": "comment"},
                         headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec})
        out = []
        for rank, it in enumerate(r.json().get("items", [])):
            name = _re.sub(r"<[^>]+>", "", it.get("title", ""))
            lon, lat = float(it["mapx"]) / 1e7, float(it["mapy"]) / 1e7
            cat = it.get("category", "")
            kind = classify(name + " " + cat, "cafe" if ("카페" in cat or "디저트" in cat or "베이커리" in cat) else "meal")
            out.append({"id": f"nv_{_norm(name)}_{lat:.4f}", "name": name, "kind": kind, "lat": lat, "lon": lon,
                        "rating": None, "reviews": None, "open_now": None, "url": it.get("link", ""), "img": "",
                        "source": "naver", "partner": "", "coupon": "", "rank": rank, "cat": cat})
        return out
    except Exception:
        return None


# ---------------------------------------------------------------- 1) 모으기
@st.cache_data(ttl=86400, show_spinner=False)
def _tour(lat, lon, radius, ctype, key):
    try:
        r = requests.get(TOUR_URL, timeout=6, params={
            "serviceKey": key, "MobileOS": "ETC", "MobileApp": "HanJeolDeo", "_type": "json",
            "mapX": f"{lon:.6f}", "mapY": f"{lat:.6f}", "radius": radius, "contentTypeId": ctype,
            "arrange": "E", "numOfRows": 40, "pageNo": 1})
        body = r.json()["response"]
        if str(body["header"]["resultCode"]) not in ("0000", "00"):
            return None
        items = body["body"]["items"]
        items = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(items, dict):
            items = [items]
        out = []
        for it in items:
            try:
                kind = classify(it.get("title", ""), {39: "meal", 38: "craft", 14: "culture"}[ctype], it.get("cat3", ""),
                                it.get("lclsSystm2", ""))
                out.append({"id": f"tour_{it.get('contentid')}", "name": it.get("title", ""), "kind": kind,
                            "lat": float(it["mapy"]), "lon": float(it["mapx"]), "rating": None, "reviews": None,
                            "open_now": None, "url": "", "img": it.get("firstimage", ""), "source": "tour",
                            "partner": "", "coupon": ""})
            except (KeyError, ValueError, TypeError):
                continue
        return out
    except Exception:
        return None


def _google(lat, lon, radius, key, lang):
    """카페와 식당을 따로 물어요 (한 번에 물으면 식당만 잔뜩 와요)"""
    out = []
    for types in (("cafe", "coffee_shop", "bakery", "tea_house"), ("restaurant",)):
        out += _google_q(lat, lon, radius, key, lang, types) or []
    return out


@st.cache_data(ttl=21600, show_spinner=False)
def _google_q(lat, lon, radius, key, lang, types):
    try:
        r = requests.post(GOOGLE_URL, timeout=8, json={
            "includedTypes": list(types), "maxResultCount": 12, "rankPreference": "POPULARITY",
            "languageCode": {"ko": "ko", "en": "en", "ja": "ja", "zh": "zh-CN"}[lang],
            "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": float(radius)}}},
            headers={"X-Goog-Api-Key": key, "Content-Type": "application/json",
                     "X-Goog-FieldMask": "places.id,places.displayName,places.location,places.rating,"
                                         "places.userRatingCount,places.primaryType,places.types,places.googleMapsUri,"
                                         "places.currentOpeningHours.openNow"})
        if r.status_code != 200:
            return None
        out = []
        for p in r.json().get("places", []):
            types = set(p.get("types", [])) | {p.get("primaryType", "")}
            kind = "cafe" if types & {"cafe", "coffee_shop", "tea_house", "bakery", "dessert_shop"} else "meal"
            kind = classify(p.get("displayName", {}).get("text", ""), kind)
            out.append({"id": f"g_{p.get('id')}", "name": p.get("displayName", {}).get("text", ""), "kind": kind,
                        "lat": p["location"]["latitude"], "lon": p["location"]["longitude"],
                        "rating": p.get("rating"), "reviews": p.get("userRatingCount"),
                        "open_now": p.get("currentOpeningHours", {}).get("openNow"), "url": p.get("googleMapsUri", ""),
                        "img": "", "source": "google", "partner": "", "coupon": ""})
        return out
    except Exception:
        return None


import re as _re
CAFE_RE = _re.compile(r"카페|커피|cafe|coffee|다방|찻집|다원|티하우스|티룸|tea|베이커리|bakery|빵|디저트|dessert|로스터|roaster|브루|젤라또|한옥카페|스타벅스|starbucks|투썸|이디야|메가커피|빽다방|폴바셋|할리스|엔제리너스|파스쿠찌|커피빈|블루보틀|tea house|茶|咖啡", _re.I)


def classify(name, kind, cat3="", lcls2=""):
    """이름·분류 코드로 카페/식사 다시 가르기 (TourAPI 음식점 안에 카페가 섞여 와요)"""
    if kind in ("craft", "culture"):
        return kind
    if cat3 == "A05020900" or str(lcls2).startswith("FD05") or CAFE_RE.search(str(name or "")):
        return "cafe"
    return kind


def _norm(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def gather(places, stop_ids, lang, use_tour=True, use_google=True, example=False, csv=None, use_naver=True) -> tuple[list, dict]:
    """(가게 목록, 출처별 개수)"""
    shops, stat = [], {"csv": 0, "tour": 0, "google": 0, "example": 0, "naver": 0}
    if csv is not None and not csv.empty:
        for _, s in csv.iterrows():
            shops.append({"id": f"csv_{s.get('id')}", "name": s["name"], "kind": classify(s["name"], CSV_KIND.get(s.get("type", ""), "meal")),
                          "lat": float(s["lat"]), "lon": float(s["lon"]), "rating": None, "reviews": None,
                          "open_now": L.open_now(s, L.datetime.now(L.KST)) if s.get("open") else None, "url": "",
                          "img": "", "source": "csv", "partner": s.get("partner", ""), "coupon": s.get("coupon", "")})
        stat["csv"] = len(shops)
    gkey = google_key()[0] if use_google else None
    tkey = L.tour_key() if use_tour else None
    for sid in dict.fromkeys(stop_ids):
        p = places.loc[sid]
        lat, lon = round(float(p.lat), 5), round(float(p.lon), 5)
        if gkey:
            got = _google(lat, lon, 800, gkey, lang) or []
            stat["google"] += len(got)
            shops += got
        ncid, nsec = naver_keys() if use_naver else (None, None)
        if ncid:
            for word in ("카페", "맛집"):
                got = _naver(f"경주 {p['name'].split(' ')[0]} {word}", ncid, nsec) or []
                stat["naver"] += len(got)
                shops += got
        if tkey:
            for ctype in (39, 38, 14):
                got = _tour(lat, lon, 800, ctype, tkey) or []
                stat["tour"] += len(got)
                shops += got
    # 같은 가게 합치기 (이름이 같고 60m 안이면 하나로, 평점 있는 쪽 우선)
    merged = []
    for s in sorted(shops, key=lambda x: (x["rating"] is None, x["source"] != "csv")):
        dup = next((m for m in merged if _norm(m["name"]) == _norm(s["name"])
                    and L.haversine_km(m["lat"], m["lon"], s["lat"], s["lon"]) < 0.06), None)
        if dup:
            for k in ("partner", "coupon", "img"):
                dup[k] = dup.get(k) or s.get(k)
        elif s["name"]:
            merged.append(s)
    if not merged and example:
        for i, sid in enumerate(dict.fromkeys(stop_ids)):
            p = places.loc[sid]
            for j, kind in enumerate(KINDS):
                merged.append({"id": f"ex{i}{j}", "name": I.t("example_spot", lang, x=f"{chr(65 + i)}{j + 1}"),
                               "kind": kind, "lat": p.lat + 0.0009 * (j + 1), "lon": p.lon + 0.0007 * (2 - j),
                               "rating": None, "reviews": None, "open_now": None, "url": "", "img": "",
                               "source": "example", "partner": "후보", "coupon": ""})
        stat["example"] = len(merged)
    return merged, stat


# ---------------------------------------------------------------- 2) 점수
def seg_dist_m(lat, lon, a, b) -> float:
    """점에서 선분 a→b까지 거리(m). 가는 길에서 얼마나 벗어나는지."""
    k = 111320.0
    cx = math.cos(math.radians((a[0] + b[0]) / 2))
    ax, ay, bx, by = a[1] * k * cx, a[0] * k, b[1] * k * cx, b[0] * k
    px, py = lon * k * cx, lat * k
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def bayes(rating, n, m=30, c=4.0) -> float:
    """평점과 리뷰 수를 함께 반영하는 베이지안 평균 (리뷰가 적으면 평균 쪽으로 당겨요)."""
    return (n / (n + m)) * rating + (m / (n + m)) * c


def score(s, a, b, ctx, lang) -> tuple[float, list]:
    d = seg_dist_m(s["lat"], s["lon"], a, b)
    prox = max(0.0, 1 - d / 700)
    why = [I.t("s_near", lang, m=f"{d:.0f}")]
    if s.get("rating") is not None and s.get("reviews"):
        bq = bayes(float(s["rating"]), int(s["reviews"]))
        q = 0.7 * max(0, min(1, (bq - 3.5) / 1.5)) + 0.3 * min(1, math.log10(int(s["reviews"]) + 1) / 3)
        why.append(I.t("s_rating", lang, r=f"{s['rating']:.1f}", n=f"{int(s['reviews']):,}"))
    elif s.get("source") == "naver" and s.get("rank") is not None:
        q = 0.8 - 0.07 * s["rank"]   # 네이버 '리뷰 많은 순' 순위
        why.append({"ko": f"네이버 리뷰 많은 순 {s['rank'] + 1}위", "en": f"#{s['rank'] + 1} by Naver review count",
                    "ja": f"NAVERレビュー数{s['rank'] + 1}位", "zh": f"NAVER评论数第{s['rank'] + 1}"}.get(lang, ""))
    else:
        q = 0.45 + (0.1 if s.get("img") else 0)
    hour = ctx["now"].hour
    kind = s["kind"]
    if 11 <= hour < 14 or 17 <= hour < 20:
        fit = {"meal": 0.85, "cafe": 0.5, "craft": 0.4, "culture": 0.4}[kind]
        if kind == "meal":
            why.append(I.t("s_mealtime", lang))
    elif 14 <= hour < 17:
        fit = {"meal": 0.3, "cafe": 0.9, "craft": 0.5, "culture": 0.5}[kind]
        if kind == "cafe":
            why.append(I.t("s_cafetime", lang))
    else:
        fit = {"meal": 0.5, "cafe": 0.65, "craft": 0.45, "culture": 0.45}[kind]
    if ctx.get("want_cafe") and kind == "cafe":
        fit += 0.35
        why.append(I.t("s_asked_cafe", lang))
    if ctx.get("want_meal") and kind == "meal":
        fit += 0.35
        why.append(I.t("s_asked_meal", lang))
    if ctx.get("kids") and kind in ("craft", "culture"):
        fit += 0.3
        why.append(I.t("s_kids", lang))
    if (ctx.get("rain") or ctx.get("cold")) and kind in ("cafe", "culture"):
        fit += 0.2
        why.append(I.t("s_warm", lang))
    if ctx.get("tired") and kind == "cafe":
        fit += 0.4
    partner = {"제휴": 0.2, "후보": 0.08}.get(s.get("partner", ""), 0)
    total = 0.4 * q + 0.3 * prox + 0.25 * min(fit, 1.2) + partner
    return total, why


# ---------------------------------------------------------------- 3) 배정
def assign(shops, places, stops, ctx, lang, per_leg=2, max_m=700) -> dict:
    """구간마다 중복 없이 최대 2곳 (첫째는 점수 1등, 둘째는 다른 종류 중 1등)."""
    used, out = set(), {}
    for i, (a, b) in enumerate(zip(stops, stops[1:])):
        pa, pb = places.loc[a], places.loc[b]
        A, B = (pa.lat, pa.lon), (pb.lat, pb.lon)
        cands = []
        for s in shops:
            if s["id"] in used or s.get("open_now") is False:
                continue
            if seg_dist_m(s["lat"], s["lon"], A, B) > max_m:
                continue
            sc, why = score(s, A, B, ctx, lang)
            cands.append(dict(s, score=sc, why=why, dist_m=seg_dist_m(s["lat"], s["lon"], A, B)))
        cands.sort(key=lambda x: -x["score"])
        pick = []
        cafe = next((c for c in cands if c["kind"] == "cafe"), None)   # 쉬어 갈 카페·찻집은 꼭 하나
        if cafe:
            pick.append(cafe)
        for c in cands:
            if len(pick) >= per_leg:
                break
            if c not in pick and all(c["kind"] != q["kind"] for q in pick):
                pick.append(c)
        for p in pick:
            used.add(p["id"])
        out[i] = pick
    return out


def around(shops, places, pid, ctx, lang, exclude=(), limit=3, kinds=None, radius_km=0.8, min_rating=3.5) -> list:
    """한 장소 둘레(radius_km) 안의 가게. 평점을 아는 가게는 min_rating 미만이면 빼요."""
    p = places.loc[pid]
    A = (p.lat, p.lon)
    cands = []
    for s in shops:
        if s["id"] in exclude or s.get("open_now") is False or (kinds and s["kind"] not in kinds):
            continue
        if s.get("rating") is not None and s.get("reviews") and int(s["reviews"]) >= 5 and float(s["rating"]) < min_rating:
            continue
        if L.haversine_km(p.lat, p.lon, s["lat"], s["lon"]) > radius_km:
            continue
        sc, why = score(s, A, A, ctx, lang)
        cands.append(dict(s, score=sc, why=why, dist_m=L.haversine_km(p.lat, p.lon, s["lat"], s["lon"]) * 1000))
    cands.sort(key=lambda x: -x["score"])
    cafe = next((c for c in cands if c["kind"] == "cafe"), None)
    if cafe:   # 카페를 맨 앞에
        cands.remove(cafe)
        cands.insert(0, cafe)
    out, seen_kind = [], set()
    for c in cands:   # 종류가 다양하게
        if c["kind"] in seen_kind and len(cands) > limit:
            continue
        out.append(c)
        seen_kind.add(c["kind"])
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- 4) '볼 게 없어요' 대체 추천
def alternatives(cur, plan_stops, prefs, cond, places, data, lang, limit=3) -> list:
    to_sunset = int((cond["sunset"] - cond["now"]).total_seconds() // 60)
    out = []
    for pid in places.index:
        if pid in plan_stops or pid == "campus":
            continue
        km = L.km_between(places, cur, pid)
        if km > 1.6:
            continue
        if prefs.get("avoid_hill") and P.tags_of(data, pid).get("hill"):
            continue
        u, parts = P.place_utility(pid, prefs, cond, data, to_sunset)
        u -= 0.4 * km
        out.append({"pid": pid, "score": u, "km": km, "top": parts.get("top")})
    out.sort(key=lambda x: -x["score"])
    return out[:limit]

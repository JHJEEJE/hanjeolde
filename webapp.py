"""webapp.py — HTML 앱(web/index.html)과 파이썬 AI 엔진을 잇는 다리

화면은 web/index.html(HTML·CSS·JS)이 그리고, 계산은 여기서 해요.
  화면 → 파이썬 : 요청 {id, kind, payload}  (Streamlit 컴포넌트 값으로 전달)
  파이썬 → 화면 : args = {bundle(문구·장소), cond(날씨), resp(마지막 요청의 답)}
kind: plan · route · alts · finish · compare · lang · demo
"""
from __future__ import annotations

import math
from urllib.parse import quote
from datetime import datetime
from pathlib import Path

import streamlit as st

import i18n as I
import journal as J
import logic as L
import pins as PN
import planner as P
import shops as SH

WEB = Path(__file__).parent / "web"
CMP_TIMES = ["09:30", "13:00", "15:30", "16:30"]
CMP_WEATHER = ["맑음", "비", "영하", "폭염"]


# ---------------------------------------------------------------- 데이터 묶음 (언어별, 바뀌지 않는 것)
def _kind(places, pid):
    return PN.icon_of(pid, places.loc[pid, "category"], places.loc[pid, "name"])


@st.cache_data(show_spinner=False)
def bundle(lang: str, _v: int = 3) -> dict:
    places, data = L.load_places(), L.load_all()
    S = {k: (v.get(lang) or v["ko"]) for k, v in I.S.items()}
    labels = {g: {k: (v.get(lang) or v.get("ko", k)) for k, v in d.items()} for g, d in I.LABELS.items()}
    pl = []
    for pid in places.index:
        p = places.loc[pid]
        tg = P.tags_of(data, pid)
        desc = L.place_desc(pid, places, data, lang)
        kind = _kind(places, pid)
        pl.append({"id": pid, "name": L.place_name(pid, places, data, lang), "cat": p.category,
                   "catLabel": I.lab("category", p.category, lang), "era": L.era_text(p.era, data, lang),
                   "lat": float(p.lat), "lon": float(p.lon), "desc": desc, "short": L._first_sentence(desc, lang),
                   "kind": kind, "hill": bool(tg.get("hill")), "indoor": bool(tg.get("indoor")),
                   "kakao": L.kakao_to(p["name"], p.lat, p.lon)})
    return {"lang": lang, "S": S, "L": labels, "places": pl,
            "langs": [{"id": x, "name": I.LANG_NAMES[x]} for x in I.LANGS], "tts": I.TTS_LANG[lang],
            "opts": {"who": P.WHO_OPTS, "level": P.LEVEL_OPTS, "interest": P.INTEREST_OPTS, "mood": J.MOODS,
                     "stop": L.STOP_KEYS, "cmpTimes": CMP_TIMES, "cmpWeather": CMP_WEATHER},
            "pins": {"svg": {k: PN.svg_icon(k, 40) for k in PN.ICON_SVG}, "inner": PN.ICON_SVG, "color": PN.ICON_COLOR, "legend": PN.LEGEND_ORDER},
            "badgeEmoji": I.BADGE_EMOJI, "examples": EXAMPLES[lang], "analysis": analysis(lang)}


EXAMPLES = {
    "ko": ["선덕여왕 이야기가 궁금해요", "오르막은 싫어요", "카페에서 쉬고 싶어요", "조용한 곳이 좋아요", "사진 예쁘게 나오는 곳"],
    "en": ["Tell me about Queen Seondeok", "No hills, please", "I'd like a café break", "Somewhere quiet", "Great photo spots"],
    "ja": ["善徳女王の話が聞きたい", "坂は苦手です", "カフェで休みたい", "静かな場所がいい", "写真映えする場所"],
    "zh": ["想听善德女王的故事", "不想爬坡", "想在咖啡馆休息", "喜欢安静的地方", "适合拍照的地方"],
}


def analysis(lang):
    """⑥ 중단 이유 분석 (가상 기록 80건) — 보완 전 · 후"""
    places, data = L.load_places(), L.load_all()
    before = L.make_virtual(80, "before")
    seg = L.segment_table(before, places, data, lang)
    if seg.empty:
        return None
    worst = seg.iloc[0]
    fixes = {worst["seg"]: worst["멈춘 이유 1위"]}
    after = L.make_virtual(80, "after", fixes)
    seg2 = L.segment_table(after, places, data, lang)

    def rows(df):
        return [{"seg": r["seg"], "name": r["구간"], "in": int(r["진입"]), "arr": int(r["도착"]), "rate": float(r["완주율"]),
                 "stops": int(r["멈춘 수"]), "why": I.lab("reason", r["멈춘 이유 1위"], lang) if r["멈춘 수"] else ""}
                for _, r in df.iterrows()]
    row2 = seg2[seg2["seg"] == worst["seg"]]
    return {"before": rows(seg), "after": rows(seg2), "overallBefore": L.overall(before), "overallAfter": L.overall(after),
            "worst": {"seg": worst["seg"], "name": worst["구간"], "rate": float(worst["완주율"]),
                      "why": I.lab("reason", worst["멈춘 이유 1위"], lang), "sugg": L.suggestion(worst, lang),
                      "after": float(row2["완주율"].iloc[0]) if not row2.empty else None}}


# ---------------------------------------------------------------- 날씨
def conditions(demo: dict):
    now = datetime.now(L.KST)
    t = (demo or {}).get("time") or "지금"
    if t != "지금":
        hh, mm = map(int, t.split(":"))
        now = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    month = (demo or {}).get("month") or None
    return L.get_conditions((demo or {}).get("weather") or "실시간", month, now)


def cond_json(cond, lang):
    lines = L.weather_lines(cond, lang)
    return {"now": cond["now"].isoformat(), "month": cond["month"], "season": cond["season"],
            "seasonLabel": I.lab("season", cond["season"], lang), "temp": cond.get("temp"), "rain": bool(cond["rain"]),
            "cold": bool(cond["cold"]), "hot": (cond.get("temp") or 0) >= 28, "pop": cond.get("pop"),
            "sunset": cond["sunset"].strftime("%H:%M"), "source": cond["source"], "line1": lines[0], "line2": lines[1]}


@st.cache_data(ttl=86400, show_spinner=False)
def _walk_route(lat1, lon1, lat2, lon2):
    return L.walk_route(lat1, lon1, lat2, lon2)


# ---------------------------------------------------------------- 길 하나의 내용 (지도·구간·이야기·가게)
def _shops(places, stops, lang, keys, points=()):
    key = (tuple(stops), lang, keys, tuple(points))
    cache = st.session_state.setdefault("shop_cache", {})
    if key not in cache:
        tour_ok, google_ok = keys
        cache[key] = SH.gather(places, list(stops), lang, tour_ok, google_ok, not (tour_ok or google_ok or L.data_key()),
                               L.load_rest_spots(), points=points)[0]
    return cache[key]


def _shop_json(s, lang, origin=None):
    src = {"google": "src_google", "tour": "src_tour", "csv": "src_csv", "example": "src_example", "naver": "src_naver", "gj": "src_gj"}[s["source"]]
    return {"id": s.get("id"), "name": s["name"], "kind": s["kind"], "kindLabel": I.lab("shop_kind", s["kind"], lang),
            "lat": s["lat"], "lon": s["lon"], "why": s.get("why", []), "src": I.t(src, lang), "rating": s.get("rating"),
            "reviews": s.get("reviews"), "partner": s.get("partner"), "coupon": s.get("coupon"),
            "url": (L.kakao_walk(origin["name"], origin["lat"], origin["lon"], s["name"], s["lat"], s["lon"]) if origin
                    else s.get("url") or L.kakao_to(s["name"], s["lat"], s["lon"])),
            "from": origin["label"] if origin else None, "gmap": s.get("url") or "",
            "naver": "https://map.naver.com/p/search/" + quote("경주 " + str(s["name"])),
            "walkMin": round(L.haversine_km(origin["lat"], origin["lon"], s["lat"], s["lon"]) * 1000 * L.PATH_FACTOR / 75) if origin else None,
            "distM": round(L.haversine_km(origin["lat"], origin["lon"], s["lat"], s["lon"]) * 1000) if origin else None}


def shop_ctx(cond, prefs, who, extra=None):
    c = {"now": cond["now"], "want_cafe": prefs.get("want_cafe"), "want_meal": prefs.get("want_meal"),
         "kids": who == "아이와 함께", "rain": cond["rain"], "cold": cond["cold"]}
    c.update(extra or {})
    return c


def route_json(stops, who, story_interest, prefs, cond, lang, keys, with_paths=True):
    places, data = L.load_places(), L.load_all()
    elev = L.elevations(places)
    hills = L.hill_pairs(data["courses"], data["tags"])
    legs = []
    for a, b in zip(stops, stops[1:]):
        pa, pb = places.loc[a], places.loc[b]
        r = _walk_route(float(pa.lat), float(pa.lon), float(pb.lat), float(pb.lon)) if with_paths else None
        lg = L.leg_info(places, a, b, who, elev, hills, prefs.get("speed", 1.0), dist_m=r[0] if r else None)
        if lg["guessed"]:
            lg["hill"] = bool(P.tags_of(data, a).get("hill") or P.tags_of(data, b).get("hill"))
        steps = L.directions(r[2] if r and len(r) > 2 else None, (float(pa.lat), float(pa.lon)), (float(pb.lat), float(pb.lon)),
                             L.place_name(b, places, data, lang), lang)
        legs.append({"from": a, "to": b, "dist": round(lg["dist_m"]), "min": round(lg["minutes"], 1), "hill": lg["hill"],
                     "steps": steps, "detailed": bool(r and len(r) > 2 and r[2]),
                     "grade": I.lab("grade", lg["grade"], lang), "guessed": lg["guessed"],
                     "coords": [[round(x, 6), round(y, 6)] for x, y in r[1]] if r else None})
    shop_list = []
    ctx = shop_ctx(cond, prefs, who)

    def origin(pid):   # 가게 길찾기 출발점 = 지금 서 있는(도착한) 장소
        pp = places.loc[pid]
        return {"name": pp["name"], "lat": float(pp.lat), "lon": float(pp.lon), "label": L.place_name(pid, places, data, lang)}
    assigned = {}   # 걷는 동안에는 가게를 권하지 않아요 (끝났거나 그만둘 때 둘레 가게를 보여 줘요)
    used = set()
    st_json = []
    for i, p in enumerate(stops):
        text, sources, status = L.story_for(p, story_interest, places, data, lang)
        now_s, later_s = L.season_for(p, cond["month"], data, lang)
        near = []
        st_json.append({"id": p, "title": L.piece_title(p, places, data, i + 1, lang), "story": text,
                        "sources": [{"title": (s["title"] if lang == "ko" else s["title"].replace("한국민족문화대백과사전", I.t("encyk", lang)) + I.t("in_korean", lang)),
                                     "url": s["url"]} for s in sources],
                        "status": status, "mission": L.mission_for(p, who, places, data, lang),
                        "seasonNow": now_s, "seasonLater": [{"label": s["label"], "months": I.join_list([I.month_name(m, lang) for m in s["months"]], lang)} for s in later_s],
                        "diff": L.diff_line(stops[i - 1], p, places, data, lang) if i else "",
                        "teaser": L.teaser(p, stops[i + 1], places, data, lang) if i < len(stops) - 1 else "",
                        "near": [_shop_json(s, lang, origin(p)) for s in near]})
    walk_min = sum(l["min"] for l in legs)
    total = walk_min + sum(P.stay_min(data, p, who) for p in stops)
    return {"stops": st_json, "legs": legs, "dist": sum(l["dist"] for l in legs), "walkMin": round(walk_min),
            "totalMin": round(total), "legShops": [[_shop_json(s, lang, origin(stops[i])) for s in assigned.get(i, [])] for i in range(len(legs))],
            "kakaoLegs": [L.kakao_walk(places.loc[a, "name"], places.loc[a, "lat"], places.loc[a, "lon"],
                                          places.loc[b, "name"], places.loc[b, "lat"], places.loc[b, "lon"]) for a, b in zip(stops, stops[1:])]}


# ---------------------------------------------------------------- 요청 처리
def keys_status():
    tour_val, _ = L.secret_status("tour")
    g_val, _ = SH.google_key()
    return bool(tour_val), bool(g_val)


def _choice(c):
    return {"who": c.get("who") or "혼자", "minutes": int(c.get("minutes") or 120), "level": c.get("level") or "가볍게",
            "interests": [x for x in (c.get("interests") or []) if x in P.INTEREST_OPTS], "free": (c.get("free") or "").strip()[:300]}


def do_plan(payload, cond, lang):
    places, data = L.load_places(), L.load_all()
    choice = _choice(payload.get("choice", {}))
    start = payload.get("start") if payload.get("start") in places.index else None
    elev = L.elevations(places)
    hills = L.hill_pairs(data["courses"], data["tags"])
    res = P.plan(start, choice, cond, places, data, elev, hills, lang)
    prefs = res["prefs"]
    st.session_state.prefs = prefs
    st.session_state.choice = choice
    si = P.interest_to_story(prefs)
    keys = keys_status()
    cands = []
    for c in res["cands"]:
        r = route_json(c["stops"], choice["who"], si, prefs, cond, lang, keys)
        r.update(id=c["id"], reasons=c["reasons"], picked=(c is res["chosen"]))
        cands.append(r)
    name = lambda p: L.place_name(p, places, data, lang)
    w = prefs["weights"]
    proc = res["process"]
    return {"cands": cands, "planner": res["planner"], "aiReason": res["ai_reason"], "notes": res["notes"], "budget": res["budget"],
            "storyInterest": si, "speed": prefs["speed"], "autoStart": res.get("auto_start", False),
            "prefs": {"tops": [I.lab("theme", k, lang) for k in P.top_themes(prefs)], "by": prefs.get("parsed_by"),
                      "effects": [[q, I.lab("effect", e, lang)] for q, e in prefs["effects"][:5]],
                      "weights": [[I.lab("theme", k, lang), round(v, 3)] for k, v in sorted(w.items(), key=lambda kv: -kv[1]) if v > 0.02],
                      "avoidHill": prefs["avoid_hill"], "cafe": prefs["want_cafe"]},
            "process": {"evaluated": proc["evaluated"], "feasible": proc["feasible"], "radius": proc["radius"],
                        "starts": [[name(p), u, pt] for p, u, pt in proc.get("starts", [])],
                        "pool": [[p, name(p), u, I.lab("theme", tp, lang) if tp else ""] for p, u, tp in proc["pool"][:8]]}}


def do_route(payload, cond, lang):
    prefs = st.session_state.get("prefs") or P.understand(_choice({}), L.load_places(), L.load_all(), False)
    return route_json(payload["stops"], payload.get("who") or "혼자", payload.get("storyInterest") or "역사", prefs, cond, lang,
                      keys_status())


def do_alts(payload, cond, lang):
    places, data = L.load_places(), L.load_all()
    prefs = st.session_state.get("prefs") or P.understand(_choice({}), places, data, False)
    cur, stops = payload["cur"], payload["stops"]
    alts = SH.alternatives(cur, stops, prefs, cond, places, data, lang)
    keys = keys_status()
    near = []
    return {"alts": [{"id": a["pid"], "km": round(a["km"], 2), "theme": I.lab("theme", a["top"], lang) if a["top"] else ""} for a in alts],
            "near": [_shop_json(s, lang, {"name": places.loc[cur, "name"], "lat": float(places.loc[cur, "lat"]),
                                          "lon": float(places.loc[cur, "lon"]), "label": L.place_name(cur, places, data, lang)}) for s in near]}


def do_finish(payload, cond, lang):
    places, data = L.load_places(), L.load_all()
    w = payload["walk"]
    walk = {"plan": {"stops": w["stops"], "legs": [{"to": l["to"], "minutes": l["min"], "hill": l["hill"]} for l in w.get("legs", [])],
                     "total_min": w.get("totalMin", 60), "course_id": None},
            "arrived": w["arrived"], "user": {"who": w.get("who", "혼자"), "story_interest": w.get("storyInterest", "역사")},
            "missions": w.get("missions", []), "walked_m": w.get("walkedM", 0), "start_ts": w.get("startTs", ""),
            "end_ts": w.get("endTs", ""), "memos": w.get("memos", {}), "moods": w.get("moods", {}),
            "photos": {p: True for p in w.get("photos", [])}, "events": w.get("events", []), "stopped": w.get("stopped"),
            "used_tired": w.get("usedTired", False), "bored": w.get("bored", 0)}
    story = J.story(walk, places, data, cond, lang)
    polished = J.polish(story, lang)
    s = J.stats(walk)
    bs = J.badges(walk, cond, data, lang)
    rec = L.recommend(L.course_of(w["stops"], data["courses"]), w["stops"], data, places, lang)
    recs = []
    for k in ("similar", "new"):
        if k in (rec or {}):
            c = rec[k]["course"]
            title, sub = L.course_text(c, data, lang)
            recs.append({"kind": k, "title": title, "sub": sub, "stops": c["stops"], "reason": rec[k]["reason"]})
    prefs = st.session_state.get("prefs") or {}
    end = w["arrived"][-1]
    pool = _shops(places, [end], lang, keys_status())
    ctx_ = shop_ctx(cond, prefs, walk["user"]["who"])
    near = SH.around(pool, places, end, ctx_, lang, limit=8, radius_km=0.5)
    radius = 500
    if len(near) < 3:   # 500m 안에 가게가 적으면 1km까지 넓혀요
        near = SH.around(pool, places, end, ctx_, lang, limit=8, radius_km=1.0)
        radius = 1000
    try:
        L.log_event(st.session_state.get("sid", "web"), "finish" if not w.get("stopped") else "stop",
                    stops=w["stops"], arrived=w["arrived"], reason=w.get("stopped"), lang=lang)
    except Exception:
        pass
    return {"story": polished or story, "byClaude": bool(polished), "stats": s,
            "badges": [{"key": b, "label": I.lab("badge", b, lang), "emoji": I.BADGE_EMOJI.get(b, "")} for b in bs],
            "end": {"id": end, "lat": float(places.loc[end, "lat"]), "lon": float(places.loc[end, "lon"]), "radius": radius},
            "recs": recs, "near": [_shop_json(x, lang, {"name": places.loc[w["arrived"][-1], "name"], "lat": float(places.loc[w["arrived"][-1], "lat"]),
                                                  "lon": float(places.loc[w["arrived"][-1], "lon"]),
                                                  "label": L.place_name(w["arrived"][-1], places, data, lang)}) for x in near]}


CMP_QR = ["bunhwangsa", "hwangnyongsaji", "mitansaji", "museum", "seondeok", "heungnyunsa",
          "muyeol", "kimyusin", "geumjangdae", "samneung", "bulguksa", "girimsa"]


def do_compare_qr(payload, cond, lang):
    """같은 취향·같은 날씨에서 QR을 찍은 사찰만 바꿔 보기"""
    places, data = L.load_places(), L.load_all()
    choice = _choice(payload.get("choice", {}))
    elev = L.elevations(places)
    hills = L.hill_pairs(data["courses"], data["tags"])
    rows = []
    for st_id in CMP_QR:
        res = P.plan(st_id, choice, cond, places, data, elev, hills, lang, use_llm=False)
        c = res["chosen"]
        rows.append({"qr": st_id, "stops": c["stops"], "totalMin": round(c["total_min"]), "dist": round(c["dist_m"]),
                     "why": c["reasons"][0] if c.get("reasons") else "", "fallback": bool(c.get("fallback"))})
    used = sorted({p for r in rows for p in r["stops"]})
    return {"mode": "qr", "rows": rows, "used": len(used), "budget": res["budget"], "notes": res["notes"]}


def do_compare(payload, lang):
    places, data = L.load_places(), L.load_all()
    choice = _choice(payload.get("choice", {}))
    start = payload.get("start") if payload.get("start") in places.index else "bunhwangsa"
    elev = L.elevations(places)
    hills = L.hill_pairs(data["courses"], data["tags"])
    month = payload.get("month")
    out = []
    base = datetime.now(L.KST)
    for t in CMP_TIMES:
        row = []
        hh, mm = map(int, t.split(":"))
        for wth in CMP_WEATHER:
            cond = L.get_conditions(wth, month, base.replace(hour=hh, minute=mm, second=0, microsecond=0))
            res = P.plan(start, choice, cond, places, data, elev, hills, lang, use_llm=False)
            c = res["chosen"]
            notes = [n for n in res["notes"]]
            tags = ["nearest"] if c.get("fallback") else []
            if c["stops"][-1] and P.tags_of(data, c["stops"][-1]).get("indoor") and (cond["rain"] or cond["cold"]):
                tags.append("indoor_end")
            if any(P.tags_of(data, p).get("shade") for p in c["stops"]) and (cond.get("temp") or 0) >= 28:
                tags.append("shade")
            row.append({"weather": wth, "stops": c["stops"], "totalMin": round(c["total_min"]), "dist": round(c["dist_m"]),
                        "budget": res["budget"], "notes": notes, "tags": tags, "sunset": cond["sunset"].strftime("%H:%M")})
        out.append({"time": t, "cells": row})
    return {"mode": "time", "start": start, "grid": out}


def do_nearby(payload, cond, lang):
    """걷는 중 '근처 쉬어 갈 곳'을 눌렀을 때만: 지금 내 위치(GPS) 둘레 600m + 지금 걷는 길 300m 안쪽"""
    places, data = L.load_places(), L.load_all()
    pid = payload.get("pid")
    if pid not in places.index:
        return {"near": []}
    nxt = payload.get("next") if payload.get("next") in places.index else None
    a = (float(places.loc[pid, "lat"]), float(places.loc[pid, "lon"]))
    b = (float(places.loc[nxt, "lat"]), float(places.loc[nxt, "lon"])) if nxt else a
    pos = payload.get("pos")
    me = (float(pos[0]), float(pos[1])) if pos else a
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    pts = [(round(me[0], 3), round(me[1], 3))] + ([(round(mid[0], 3), round(mid[1], 3))] if nxt else [])
    stops = [pid] + ([nxt] if nxt else [])
    prefs = st.session_state.get("prefs") or {}
    pool = _shops(places, stops, lang, keys_status(), points=tuple(pts))
    near = SH.around_point(pool, me[0], me[1], shop_ctx(cond, prefs, payload.get("who")), lang, leg=(a, b) if nxt else None)
    here = "내 위치" if pos else L.place_name(pid, places, data, lang)
    here = {"ko": "내 위치", "en": "my location", "ja": "現在地", "zh": "我的位置"}[lang] if pos else here
    o = {"name": here if pos else places.loc[pid, "name"], "lat": me[0], "lon": me[1], "label": here}
    return {"pid": pid, "pos": list(me), "near": [_shop_json(x, lang, o) for x in near],
            "search": "https://map.naver.com/p/search/" + quote("경주 " + L.place_name(pid, places, data, "ko") + " 카페")}


HANDLERS = {"plan", "route", "alts", "finish", "compare", "nearby"}


def _plain(obj):
    """numpy 숫자 등을 JSON으로 보낼 수 있는 기본형으로"""
    import json
    return json.loads(json.dumps(obj, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


def handle(req: dict, cond, lang) -> dict | None:
    out = _handle(req, cond, lang)
    return _plain(out) if out is not None else None


def _handle(req: dict, cond, lang) -> dict | None:
    kind, payload = req.get("kind"), req.get("payload") or {}
    try:
        if kind == "plan":
            return do_plan(payload, cond, lang)
        if kind == "route":
            return do_route(payload, cond, lang)
        if kind == "alts":
            return do_alts(payload, cond, lang)
        if kind == "finish":
            return do_finish(payload, cond, lang)
        if kind == "nearby":
            return do_nearby(payload, cond, lang)
        if kind == "compare":
            return do_compare_qr(payload, cond, lang) if payload.get("mode") == "qr" else do_compare(payload, lang)
    except Exception as e:  # 화면이 멈추지 않게 에러도 답으로 보내요
        import traceback
        traceback.print_exc()
        return {"error": f"{type(e).__name__}: {e}"}
    return None

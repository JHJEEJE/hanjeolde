"""planner.py — AI 순례길 엔진 (참가서류 5번 ① ② ③)

흐름
  1) 취향 이해   understand()   : 고른 선택지 + 자유 입력(규칙 해석, 키가 있으면 Claude가 해석) → 테마 가중치·조건
  2) 장소 점수   place_utility(): 35곳마다 취향 일치 + 이야기 조각 + 계절 + 날씨 + 노을 점수
  3) 경로 최적화 search()       : 출발지 주변 후보로 1~3곳 조합·순서를 모두 따져
                                  시간·거리·경사·일몰 조건을 지키면서 점수가 가장 높은 길을 찾음 (오리엔티어링 문제)
  4) 다양한 후보 diverse_top()  : 서로 겹치지 않는 후보 3개
  5) 설명       explain()      : 왜 이 길인지 (어떤 취향·조건이 반영됐는지)
  6) 에이전트   agent_pick()   : Claude가 도구로 후보·조건·이야기를 확인하고 하나를 골라 이유를 씀 (키 있을 때)
"""
from __future__ import annotations

import itertools
import json
import math
import re

import i18n as I
import logic as L

THEMES = ["history", "architecture", "buddha_art", "photo", "nature", "rest", "people", "kids", "temple_life"]

WHO_OPTS = ["혼자", "친구", "연인", "아이와 함께", "어르신과 함께", "외국인 친구와", "단체"]
LEVEL_OPTS = ["아주 가볍게", "가볍게", "보통", "산길도 좋아요"]
LEVELS = {
    "아주 가볍게": {"max_km": 2.0, "hill": False, "leg": 1.5},
    "가볍게": {"max_km": 4.0, "hill": False, "leg": 2.5},
    "보통": {"max_km": 6.0, "hill": True, "leg": 3.0},
    "산길도 좋아요": {"max_km": 9.0, "hill": True, "leg": 3.5},
}
INTEREST_OPTS = ["역사 이야기", "건축·석탑", "불상·불교미술", "사진 명소", "자연·숲길", "쉼·힐링",
                 "신라 인물", "아이 체험", "사찰 체험", "카페·맛집"]
INTEREST_W = {
    "역사 이야기": {"history": 1.0}, "건축·석탑": {"architecture": 1.0}, "불상·불교미술": {"buddha_art": 1.0},
    "사진 명소": {"photo": 1.0}, "자연·숲길": {"nature": 1.0}, "쉼·힐링": {"rest": 0.7, "nature": 0.3},
    "신라 인물": {"people": 1.0}, "아이 체험": {"kids": 1.0}, "사찰 체험": {"temple_life": 1.0},
    "카페·맛집": {"rest": 0.3},
}
# 이야기 조각(story_pieces.json)의 관심사 4개와 연결
STORY_INTEREST = {"history": "역사", "people": "역사", "temple_life": "역사", "architecture": "건축", "buddha_art": "건축",
                  "photo": "사진", "nature": "사진", "rest": "쉼", "kids": "쉼"}
WHO_ADJ = {
    "아이와 함께": {"w": {"kids": 0.6}, "speed": 0.75, "km": 0.7},
    "어르신과 함께": {"w": {"rest": 0.3}, "speed": 0.75, "km": 0.7, "no_hill": True},
    "연인": {"w": {"photo": 0.4, "nature": 0.2}},
    "외국인 친구와": {"w": {"history": 0.2, "architecture": 0.3}},
    "단체": {"speed": 0.85},
}

# ---------------------------------------------------------------- 1) 취향 이해
FREE_RULES = [  # (정규식, 효과 키) — 한국어·영어·일본어·중국어 키워드
    (r"사진|인생샷|예쁜|포토|노을|photo|picture|instagram|写真|映え|拍照|照片", "photo"),
    (r"카페|커피|디저트|빵|찻집|차 한잔|cafe|coffee|dessert|tea|カフェ|コーヒー|咖啡|甜点|茶", "cafe"),
    (r"밥|점심|저녁|맛집|식사|배고|먹|lunch|dinner|food|eat|restaurant|ご飯|ランチ|食事|午饭|吃饭|美食", "meal"),
    (r"오르막|계단|산길 싫|힘들|무릎|다리 아|uphill|stairs|no hill|knee|坂|階段|上り坂|台阶|爬山|上坡", "no_hill"),
    (r"조용|한적|사람 없|붐비지|quiet|calm|peaceful|静か|安静|人少", "quiet"),
    (r"아이|애기|아기|아들|딸|어린이|kid|child|children|子ども|子供|孩子|小孩", "kids"),
    (r"선덕|여왕|김유신|원효|최치원|이차돈|queen|king|seondeok|女王|王", "people"),
    (r"탑|석탑|건축|pagoda|architecture|塔|建築|建筑", "architecture"),
    (r"불상|부처|마애|불교 미술|buddha|statue|仏像|仏|佛像|佛", "buddha_art"),
    (r"숲|자연|풍경|산책|소나무|nature|forest|walk|scenery|森|自然|景色|散歩|森林|风景|散步", "nature"),
    (r"실내|비 와|비와|박물관|indoor|museum|rain|屋内|博物館|雨|室内|博物馆|下雨", "indoor"),
    (r"짧게|빨리|금방|잠깐|가볍게|short|quick|briefly|短く|少し|短一点|快一点", "short"),
    (r"역사|이야기|옛날|history|story|歴史|物語|历史|故事", "history"),
    (r"템플|스님|절 체험|사찰 체험|temple stay|monk|お寺体験|寺院体验|僧", "temple_life"),
    (r"쉬고|쉼|힐링|여유|휴식|relax|rest|healing|休み|癒し|休息|放松", "rest"),
]
EFFECT_W = {"photo": {"photo": 0.8}, "kids": {"kids": 0.8}, "people": {"people": 0.8}, "architecture": {"architecture": 0.8},
            "buddha_art": {"buddha_art": 0.8}, "nature": {"nature": 0.8}, "history": {"history": 0.6},
            "temple_life": {"temple_life": 0.8}, "rest": {"rest": 0.6}, "quiet": {"nature": 0.2}}


def _aliases(pid, places, data):
    names = set()
    for lang in I.LANGS:
        n = L.place_name(pid, places, data, lang)
        names.add(n)
        names.add(n.split(" ")[0].split("·")[0])
    out = set()
    for n in names:
        n = n.strip()
        if len(n) >= 2:
            out.add(n)
            if n.endswith("사지") and len(n) >= 4:
                out.add(n[:-1])          # 황룡사지 → 황룡사
    return out


# 인물 이름을 말하면 그 인물과 이어진 곳에 가산점 (꼭 넣지는 않음)
PERSON_PLACES = [
    (r"선덕|seondeok|善徳|善德", ["seondeok", "bunhwangsa", "hwangnyongsaji"]),
    (r"김유신|kim yu-?sin|金庾信", ["kimyusin"]),
    (r"무열|김춘추|muyeol|武烈", ["muyeol"]),
]


def parse_free_text(text: str, places, data) -> dict:
    """자유 입력을 규칙으로 해석. 결과: {effects: [(구절, 효과)], must: [장소 id]}"""
    text = (text or "").strip()
    out = {"effects": [], "must": [], "boost": []}
    if not text:
        return out
    low = text.lower()
    for pat, pids in PERSON_PLACES:
        if re.search(pat, low):
            out["boost"] += [p for p in pids if p in places.index and p not in out["boost"]]
    for pat, eff in FREE_RULES:
        m = re.search(pat, low)
        if m and eff not in [e for _, e in out["effects"]]:
            out["effects"].append((m.group(0), eff))
    for pid in places.index:
        if pid == "campus":
            continue
        if any(a.lower() in low for a in _aliases(pid, places, data)):
            out["must"].append(pid)
    return out


def parse_free_text_llm(text: str) -> dict | None:
    """키가 있으면 Claude(Haiku)가 자유 입력을 해석해요. 실패하면 None → 규칙 해석만 사용."""
    if not text or not L.llm_ready():
        return None
    effects = sorted({e for _, e in FREE_RULES})
    res = L.call_claude([{"role": "user", "content": text}],
                        "사용자가 경주 사찰 도보 순례에 대해 자유롭게 쓴 요청이야. 아래 효과 목록에서 해당하는 것만 골라 "
                        f"JSON 한 줄로만 답해: {{\"effects\": [[\"근거가 된 구절\", \"효과\"], ...]}}. 효과 목록: {effects}",
                        model=L._secret("FAST_MODEL", "claude-haiku-5-5"), max_tokens=250)
    if not res:
        return None
    t = L._text_of(res)
    try:
        d = json.loads(t[t.find("{"): t.rfind("}") + 1])
        return {"effects": [(str(q)[:30], e) for q, e in d.get("effects", []) if e in effects]}
    except Exception:
        return None


def understand(choice: dict, places, data, use_llm: bool = True) -> dict:
    """선택지 + 자유 입력 → 취향(prefs). choice: {who, minutes, level, interests[list], free}"""
    w = {t: 0.0 for t in THEMES}
    for it in choice.get("interests") or []:
        for k, v in INTEREST_W.get(it, {}).items():
            w[k] += v
    if not any(w.values()):   # 관심사를 안 골랐으면 고르게
        for k, v in {"history": 0.35, "architecture": 0.2, "photo": 0.2, "nature": 0.15, "buddha_art": 0.1}.items():
            w[k] = v
    adj = WHO_ADJ.get(choice.get("who"), {})
    for k, v in adj.get("w", {}).items():
        w[k] += v
    level = LEVELS.get(choice.get("level"), LEVELS["가볍게"])
    prefs = {"weights": w, "avoid_hill": (not level["hill"]) or adj.get("no_hill", False),
             "want_cafe": "카페·맛집" in (choice.get("interests") or []), "want_meal": False,
             "quiet": 0.0, "indoor": False, "short": False, "must": [], "effects": [],
             "speed": adj.get("speed", 1.0), "max_km": level["max_km"] * adj.get("km", 1.0), "leg_km": level["leg"],
             "parsed_by": "rule"}
    ft = parse_free_text(choice.get("free", ""), places, data)
    llm = parse_free_text_llm(choice.get("free", "")) if use_llm else None
    effects = ft["effects"]
    if llm and llm["effects"]:
        effects = llm["effects"] + [e for e in effects if e[1] not in {x for _, x in llm["effects"]}]
        prefs["parsed_by"] = "claude"
    for q, eff in effects:
        for k, v in EFFECT_W.get(eff, {}).items():
            w[k] += v
        if eff == "cafe":
            prefs["want_cafe"] = True
        elif eff == "meal":
            prefs["want_meal"] = True
        elif eff == "no_hill":
            prefs["avoid_hill"] = True
        elif eff == "quiet":
            prefs["quiet"] = 1.0
        elif eff == "indoor":
            prefs["indoor"] = True
        elif eff == "short":
            prefs["short"] = True
    prefs["effects"] = effects
    prefs["must"] = ft["must"][:2]
    prefs["boost"] = ft.get("boost", [])
    total = sum(w.values()) or 1.0
    prefs["weights"] = {k: v / total for k, v in w.items()}
    return prefs


# ---------------------------------------------------------------- 2) 장소 점수
EXTRA_TAGS = {"t": {"temple_life": 0.8, "rest": 0.6, "nature": 0.35, "history": 0.2, "architecture": 0.3, "photo": 0.3,
                   "buddha_art": 0.3, "kids": 0.15, "people": 0.05}, "quiet": 1, "stay": 15}


def tags_of(data, pid) -> dict:
    got = data.get("ptags", {}).get("places", {}).get(pid)
    if got:
        return got
    if L.is_extra(pid):   # 종교시설 현황에서 더한 절: 조용한 절집으로 보고, 주소가 '산 ○○'이면 산길로 봐요
        try:
            addr = str(L.load_places().loc[pid, "address"])
        except Exception:
            addr = ""
        hill = bool(re.search(r"산\d|산길|골길|계곡", addr))
        t = dict(EXTRA_TAGS["t"], nature=0.6 if hill else 0.35)
        try:
            if "심인당" in str(L.load_places().loc[pid, "name"]):   # 도심 법당(진각종)
                t.update(temple_life=0.4, nature=0.1, rest=0.4)
        except Exception:
            pass
        return dict(EXTRA_TAGS, t=t, hill=hill, shade=hill)
    return {"t": {}, "stay": 15}


def stay_min(data, pid, who) -> int:
    s = tags_of(data, pid).get("stay", 15)
    if pid == "museum" and who == "아이와 함께":
        s += 15
    return s


MUSEUM_OPEN = (10 * 60, 17 * 60 + 30)   # 국립경주박물관 10:00 개관 · 늦어도 17:30 전 도착


def daypart(cond, minutes_to_sunset=None) -> str:
    """morning(~11시) · noon(11~14시) · afternoon · golden(해 지기 90분 전부터)"""
    h = cond["now"].hour + cond["now"].minute / 60
    if minutes_to_sunset is not None and minutes_to_sunset <= 90:
        return "golden"
    return "morning" if h < 11 else "noon" if h < 14 else "afternoon"


def site_kind(pid) -> str:
    """covered: 법당·처마가 있는 절 / indoor: 박물관 / open: 그늘 없는 들판의 절터·탑·왕릉"""
    try:
        cat = L.load_places().loc[pid, "category"]
    except Exception:
        cat = ""
    if cat == "현존 사찰":
        return "covered"
    return "open" if cat in ("절터", "불상·석탑", "명소") else "other"


def place_utility(pid, prefs, cond, data, minutes_to_sunset=None) -> tuple[float, dict]:
    tg = tags_of(data, pid)
    t = tg.get("t", {})
    w = prefs["weights"]
    contrib = {k: w.get(k, 0) * t.get(k, 0) for k in THEMES}
    match = sum(contrib.values())
    parts = {"match": match, "top": max(contrib, key=contrib.get) if any(contrib.values()) else None}
    u = 0.15 + 1.6 * match
    # 내가 가장 원하는 테마가 그곳의 대표 테마면 가산점 (두루두루 무난한 곳보다 '딱 맞는 곳'을 먼저)
    if t:
        mine = max(w, key=w.get)
        if max(t, key=t.get) == mine or t.get(mine, 0) >= 0.9:
            u += 0.25 * w[mine] / max(max(w.values()), 1e-6)
            parts["fit"] = True
    if prefs.get("quiet"):
        q = 0.4 * tg.get("quiet", 0)
        u += q
        parts["quiet"] = q
    if L.has_piece(data, pid):
        u += 0.06
        parts["story"] = True
    now_s, _ = L.season_for(pid, cond["month"], data, "ko")
    if now_s:
        u += 0.2
        parts["season"] = True
    if cond.get("rain") or prefs.get("indoor"):
        if tg.get("indoor"):
            u += 0.6
            parts["indoor"] = True
        if tg.get("hill"):
            u -= 0.35
    if cond.get("cold") and tg.get("indoor"):
        u += 0.35
        parts["indoor"] = True
    if (cond.get("temp") or 0) >= 28:
        if tg.get("shade"):
            u += 0.25
            parts["shade"] = True
        if tg.get("hill"):
            u -= 0.2
    if L.is_extra(pid):   # 이야기 조각이 아직 없는 절은 이야기가 있는 유적 다음 순서로
        u -= 0.3
        parts["extra"] = True
    # ---- 시간대 · 날씨에 따라 '지금 가기 좋은 곳'이 달라져요
    dp = daypart(cond, minutes_to_sunset)
    sk = "indoor" if tg.get("indoor") else ("other" if tg.get("shade") else site_kind(pid))
    hot = (cond.get("temp") or 0) >= 28
    if cond.get("rain"):
        if sk == "covered":
            u += 0.35
            parts["covered"] = True
        elif sk == "open":
            u -= 0.45
    if cond.get("cold") and sk == "open":
        u -= 0.3
    if hot and sk == "open":
        u -= 0.45 if dp in ("noon", "afternoon") else 0.25
        parts["hot_open"] = True
    if dp == "noon" and not (cond.get("rain") or cond.get("cold")):
        if tg.get("shade") or sk == "indoor":
            u += 0.25   # 해가 머리 위에 있는 한낮엔 그늘·실내가 편해요
            parts["noon_shade"] = True
        elif sk == "open":
            u -= 0.15
    if dp == "morning" and sk == "covered" and not cond.get("rain"):
        u += 0.3 + 0.2 * tg.get("quiet", 0)
        parts["morning"] = True
    if dp == "afternoon" and sk == "open" and not (cond.get("rain") or cond.get("cold") or hot):
        u += 0.25 * t.get("photo", 0) + 0.1
        parts["light"] = True
    if dp == "golden" and tg.get("sunset"):
        u += 0.7
        parts["sunset"] = True
    elif minutes_to_sunset is not None and minutes_to_sunset <= 120 and tg.get("sunset"):
        u += 0.3
        parts["sunset"] = True
    if pid in prefs.get("boost", []):
        u += 0.9
        parts["boost"] = True
    if pid in prefs.get("must", []):
        u += 2.5
        parts["must"] = True
    return u, parts


# ---------------------------------------------------------------- 3) 경로 최적화
def _story_link(a, b, data) -> float:
    pa, pb = L._piece(data, a), L._piece(data, b)
    if pa and pb and pb.get("order", 0) == pa.get("order", 0) + 1:
        return 0.1
    if f"{a}>{b}" in data["stories"].get("_bridges", {}):
        return 0.12
    return 0.0


def search(start: str, choice: dict, prefs: dict, cond: dict, places, data, elev, hills, budget: int,
           start_util: float = 0.0) -> dict:
    """출발지에서 1~3곳을 더 잇는 모든 조합·순서를 평가해요. start_util: AI가 출발지까지 고를 때 출발지 자체 점수"""
    who = choice.get("who")
    to_sunset = int((cond["sunset"] - cond["now"]).total_seconds() // 60)
    radius = min(3.5, max(1.2, prefs["max_km"] * 0.75))
    util = {}
    for pid in places.index:
        if pid in (start, "campus"):
            continue
        km = L.km_between(places, start, pid)
        if km <= radius or (pid in prefs["must"] and km <= 6):
            util[pid] = place_utility(pid, prefs, cond, data, to_sunset)
    ranked = sorted(util, key=lambda p: -util[p][0])
    pool = ranked[:12] + [p for p in prefs["must"] if p in util and p not in ranked[:12]]
    leg_cache = {}

    def leg(a, b):
        if (a, b) not in leg_cache:
            lg = L.leg_info(places, a, b, who, elev, hills, prefs["speed"])
            if lg["guessed"]:   # 고도를 못 받았을 때는 장소 태그(산길 여부)로 오르막을 어림해요
                lg["hill"] = bool(tags_of(data, a).get("hill") or tags_of(data, b).get("hill"))
            leg_cache[(a, b)] = lg
        return leg_cache[(a, b)]

    max_extra = 2 if (cond.get("cold") or prefs.get("short")) else 3
    now_min = cond["now"].hour * 60 + cond["now"].minute
    dp_now = daypart(cond, to_sunset)
    evaluated, feasible = 0, []
    start_stay = stay_min(data, start, who)
    for k in range(0 if start_util else 1, max_extra + 1):   # AI 출발지 모드에서는 '한 곳만 깊게'도 후보
        for combo in itertools.combinations(pool, k):
            if sum(1 for p in combo if L.is_extra(p)) > 2:   # 이야기 없는 절은 한 길에 2곳까지
                continue
            for perm in itertools.permutations(combo):
                evaluated += 1
                seq = (start,) + perm
                ok, legs = True, []
                for a, b in zip(seq, seq[1:]):
                    if L.km_between(places, a, b) > prefs["leg_km"]:
                        ok = False
                        break
                    lg = leg(a, b)
                    if (prefs["avoid_hill"] or cond.get("rain")) and (lg["hill"] or tags_of(data, b).get("hill")):
                        ok = False
                        break
                    legs.append(lg)
                if not ok:
                    continue
                dist = sum(l["dist_m"] for l in legs)
                if dist / 1000 > prefs["max_km"]:
                    continue
                total = sum(l["minutes"] for l in legs) + start_stay + sum(stay_min(data, p, who) for p in perm)
                if total > budget:
                    continue
                if "museum" in seq:   # 박물관 여는 시간 안에 도착하는지 (도착 시각 = 지금 + 앞 구간·관람 시간)
                    i = seq.index("museum")
                    arr = now_min + (start_stay if i else 0) + sum(l["minutes"] for l in legs[:i]) + sum(stay_min(data, p, who) for p in seq[1:i])
                    if not (MUSEUM_OPEN[0] <= arr <= MUSEUM_OPEN[1]):
                        continue
                us = [util[p][0] for p in perm] + ([start_util] if start_util else [])
                # 많이 들르는 것보다 '나에게 맞는 곳'을 우선: 평균 점수 × 들르는 수 보정(체감)
                score = sum(us) / len(us) * (1 + 0.22 * (len(us) - 1))
                cats = {places.loc[p, "category"] for p in seq}
                score += 0.05 * len(cats)
                score += sum(_story_link(a, b, data) for a, b in zip(seq, seq[1:]))
                if (cond.get("rain") or cond.get("cold") or prefs.get("indoor")) and tags_of(data, seq[-1]).get("indoor"):
                    score += 0.4
                hill_legs = sum(1 for l in legs if l["hill"])
                score -= 0.15 * hill_legs
                score -= 0.2 * (dist / 1000) / max(prefs["max_km"], 1)
                score += 0.15 * min(1.0, total / max(budget, 1))
                score -= 1.2 * max(0.0, 0.6 - total / max(budget, 1))   # 쓸 수 있는 시간을 너무 남기면 감점
                if dp_now == "golden" and tags_of(data, seq[-1]).get("sunset"):
                    score += 0.4   # 노을 보며 끝나기
                if prefs.get("must") and not set(prefs["must"]) & set(perm):
                    score -= 1.5
                feasible.append({"stops": list(seq), "legs": legs, "dist_m": dist, "total_min": total,
                                 "walk_min": sum(l["minutes"] for l in legs), "hill": hill_legs > 0,
                                 "guessed": any(l["guessed"] for l in legs), "score": round(score, 3),
                                 "course_id": L.course_of(list(seq), data["courses"])})
    feasible.sort(key=lambda r: -r["score"])
    return {"routes": feasible, "evaluated": evaluated, "feasible": len(feasible), "util": util,
            "pool": pool, "radius": radius, "to_sunset": to_sunset}


def diverse_top(routes: list, n: int = 3, by_start: bool = False) -> list:
    """점수 높은 길을 고르되, 앞에서 고른 길과 장소가 많이 겹치면 감점 (서로 다른 후보 3개)."""
    picked = []
    for _ in range(n):
        best, best_s = None, -1e9
        for r in routes[:400]:
            if r in picked or any(set(r["stops"]) == set(p["stops"]) for p in picked):
                continue   # 같은 장소를 순서만 바꾼 길은 빼요
            k = 0 if by_start else 1
            overlap = max((len(set(r["stops"][k:]) & set(p["stops"][k:])) for p in picked), default=0)
            s = r["score"] - 0.6 * overlap
            if s > best_s:
                best, best_s = r, s
        if best is None:
            break
        picked.append(best)
    for i, r in enumerate(picked):
        r["id"] = f"P{i + 1}"
    return picked


def nearest_fallback(start, places, data, elev, hills, choice, prefs, cond=None):
    """조건에 맞는 길이 없을 때: 걸어서 닿는 평지의 가장 가까운 곳 하나, 그것도 없으면 QR 사찰 한 곳을 깊게"""
    who = choice.get("who")
    no_hill = prefs["avoid_hill"] or bool(cond and cond.get("rain"))
    near = sorted([p for p in places.index if p not in (start, "campus")], key=lambda p: L.km_between(places, start, p))
    for p in near[:6]:
        if L.km_between(places, start, p) > prefs["leg_km"]:
            break
        lg = L.leg_info(places, start, p, who, elev, hills, prefs["speed"])
        if lg["guessed"]:
            lg["hill"] = bool(tags_of(data, start).get("hill") or tags_of(data, p).get("hill"))
        if no_hill and (lg["hill"] or tags_of(data, p).get("hill")):
            continue
        return {"id": "P1", "stops": [start, p], "legs": [lg], "dist_m": lg["dist_m"], "walk_min": lg["minutes"],
                "total_min": lg["minutes"] + stay_min(data, start, who) + stay_min(data, p, who),
                "hill": lg["hill"], "guessed": lg["guessed"], "score": 0, "course_id": None, "fallback": True}
    return {"id": "P1", "stops": [start], "legs": [], "dist_m": 0, "walk_min": 0, "total_min": stay_min(data, start, who),
            "hill": False, "guessed": False, "score": 0, "course_id": None, "fallback": True, "alone": True,
            "skipped": near[0] if near else None}


# ---------------------------------------------------------------- 5) 설명
def top_themes(prefs, n=3):
    w = prefs["weights"]
    return [k for k in sorted(w, key=lambda k: -w[k]) if w[k] > 0.05][:n]


def explain(route: dict, prefs: dict, cond: dict, result: dict, places, data, budget: int, lang: str) -> list:
    T = lambda k, **kw: I.t(k, lang, **kw)
    th = lambda k: I.lab("theme", k, lang)
    name = lambda p: L.place_name(p, places, data, lang)
    out = []
    if route.get("alone"):
        sk = route.get("skipped")
        return [T("r_alone", n=name(route["stops"][0]), m=name(sk) if sk else "-")]
    if route.get("fallback"):
        return [T("r_nearest")]
    picks = []
    for p in route["stops"][1:]:
        u, parts = result["util"].get(p, (0, {}))
        if parts.get("must"):
            picks.append(T("why_must", n=name(p)))
        elif parts.get("top"):
            picks.append(f"{name(p)}({th(parts['top'])})")
        else:
            picks.append(name(p))
    tops = I.join_list([th(k) for k in top_themes(prefs)], lang)
    out.append(T("r_fit", t=tops, x=I.join_list(picks, lang)))
    out.append(I.t("r_budget", lang, b=budget, t=f"{route['total_min']:.0f}", km=f"{route['dist_m'] / 1000:.1f}"))
    if prefs["avoid_hill"]:
        out.append(T("r_nohill"))
    elif route["hill"]:
        out.append(T("r_hill_ok"))
    links = sum(1 for a, b in zip(route["stops"], route["stops"][1:]) if _story_link(a, b, data) > 0)
    if links:
        out.append(T("r_story", n=links))
    flags = {k for p in route["stops"][1:] for k, v in result["util"].get(p, (0, {}))[1].items() if v is True}
    if "indoor" in flags and (cond.get("rain") or cond.get("cold") or prefs.get("indoor")):
        out.append(T("r_indoor"))
    if "sunset" in flags:
        out.append(T("r_sunset"))
    if "covered" in flags and cond.get("rain"):
        out.append(T("r_covered"))
    if "morning" in flags:
        out.append(T("r_morning"))
    if "light" in flags:
        out.append(T("r_light"))
    if "noon_shade" in flags:
        out.append(T("r_noon"))
    if "season" in flags:
        out.append(T("r_season", s=I.lab("season", cond["season"], lang)))
    if "shade" in flags:
        out.append(T("r_shade"))
    for q, eff in prefs["effects"][:4]:
        out.append(T("r_free", q=q, e=I.lab("effect", eff, lang)))
    return out


# ---------------------------------------------------------------- 6) Claude 에이전트 (선택)
def agent_pick(cands, prefs, cond, choice, places, data, budget, lang) -> dict | None:
    if not L.llm_ready() or not cands:
        return None
    tools = [
        {"name": "find_routes", "description": "AI 엔진이 최적화한 도보 순례길 후보(점수·시간·거리·장소 특성)를 돌려준다.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "get_conditions", "description": "날씨(기온·비·강수확률), 해 지는 시각, 쓸 수 있는 시간, 사용자 취향 가중치를 돌려준다.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "get_story_preview", "description": "장소 id의 이야기 첫 문장을 돌려준다.",
         "input_schema": {"type": "object", "properties": {"place_id": {"type": "string"}}, "required": ["place_id"]}},
    ]

    def run(nm, args):
        if nm == "find_routes":
            return [{"plan_id": c["id"], "stops": [L.place_name(p, places, data, lang) for p in c["stops"]],
                     "stop_ids": c["stops"], "minutes": round(c["total_min"]), "km": round(c["dist_m"] / 1000, 1),
                     "hill": c["hill"], "score": c["score"],
                     "place_themes": {p: tags_of(data, p).get("t", {}) for p in c["stops"]}} for c in cands]
        if nm == "get_conditions":
            return {"temp": cond.get("temp"), "rain": cond.get("rain"), "pop": cond.get("pop"),
                    "sunset": f"{cond['sunset']:%H:%M}", "minutes_available": budget, "season": cond["season"],
                    "who": choice.get("who"), "free_request": choice.get("free", ""),
                    "weights": {k: round(v, 2) for k, v in prefs["weights"].items() if v > 0.02}}
        if nm == "get_story_preview":
            text, _, _ = L.story_for(args.get("place_id", ""), "역사", places, data, lang)
            return {"preview": text[:140]}
        return {"error": "unknown tool"}

    system = ("너는 경주 사찰 도보 순례길을 고르는 AI 에이전트야. 도구로 후보와 조건을 확인하고 사용자에게 가장 맞는 후보 하나를 골라. "
              "도구 결과에 없는 사실은 지어내지 마. 마지막 답은 JSON 한 줄만: "
              f'{{"plan_id": "P1", "reason": "고른 이유 2문장, {I.LLM_LANG[lang]}로"}}')
    msgs = [{"role": "user", "content": f"일행 {choice.get('who')}, {choice.get('minutes')}분, 걷기 {choice.get('level')}, "
                                         f"관심사 {choice.get('interests')}, 요청: {choice.get('free') or '없음'}"}]
    for _ in range(5):
        res = L.call_claude(msgs, system, tools=tools, max_tokens=700)
        if not res:
            return None
        if res.get("stop_reason") == "tool_use":
            msgs.append({"role": "assistant", "content": res["content"]})
            msgs.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": b["id"],
                 "content": json.dumps(run(b["name"], b.get("input", {})), ensure_ascii=False)}
                for b in res["content"] if b.get("type") == "tool_use"]})
            continue
        t = L._text_of(res)
        try:
            d = json.loads(t[t.find("{"): t.rfind("}") + 1])
            chosen = next(c for c in cands if c["id"] == d["plan_id"])
            return {"plan": chosen, "reason": str(d.get("reason", ""))[:300]}
        except Exception:
            return None
    return None


# ---------------------------------------------------------------- 한 번에
def pick_starts(prefs, cond, places, data, n=6) -> list:
    """AI가 출발지를 고를 때: 장소 자체 점수 + 걸어서 닿는 주변(1.5km)의 좋은 곳 2개 점수로 출발 후보 n곳"""
    to_sunset = int((cond["sunset"] - cond["now"]).total_seconds() // 60)
    util = {p: place_utility(p, prefs, cond, data, to_sunset)[0] for p in places.index if p != "campus"}
    if prefs["avoid_hill"]:
        util = {p: u for p, u in util.items() if not tags_of(data, p).get("hill")}
    pot = {}
    for p, u in util.items():
        near = sorted((util[q] for q in util if q != p and L.km_between(places, p, q) <= 1.5), reverse=True)[:2]
        pot[p] = u + sum(near) * 0.8
    out = []
    for p in sorted(pot, key=lambda p: -pot[p]):
        if all(L.km_between(places, p, q) > 0.35 for q in out):   # 너무 붙은 출발지는 하나만
            out.append(p)
        if len(out) >= n:
            break
    for p in prefs.get("must", []):
        if p in util and p not in out:
            out.append(p)
    return [(p, util[p], pot[p]) for p in out]


def situation_budget(budget, notes, cond, lang):
    """날씨·시간대에 따라 쓸 시간과 안내 문장을 바꿔요"""
    notes = list(notes)
    to_sunset = int((cond["sunset"] - cond["now"]).total_seconds() // 60)
    dp = daypart(cond, to_sunset)
    hot = (cond.get("temp") or 0) >= 28
    if cond.get("rain"):
        budget = int(budget * 0.85)
        notes.append(I.t("n_rain_short", lang))
    if cond.get("cold") and budget > 75:
        budget = 75
        notes.append(I.t("n_cold_cap", lang))
    if hot:
        budget = int(budget * (0.85 if dp in ("noon", "afternoon") else 0.92))
        notes.append(I.t("n_hot", lang))
    if dp == "noon" and not (cond.get("rain") or cond.get("cold") or hot):
        notes.append(I.t("n_noon", lang))
    if dp == "morning" and not cond.get("rain"):
        notes.append(I.t("n_morning", lang))
    elif dp == "afternoon" and not (cond.get("rain") or cond.get("cold") or hot):
        notes.append(I.t("n_afternoon", lang))
    elif dp == "golden":
        notes.append(I.t("n_golden", lang))
    h = cond["now"].hour * 60 + cond["now"].minute
    if h < MUSEUM_OPEN[0]:
        notes.append(I.t("n_museum", lang))
    return budget, notes


def plan(start, choice: dict, cond: dict, places, data, elev, hills, lang: str, use_llm: bool = True) -> dict:
    """start=None 이면 출발지까지 AI가 골라요. use_llm=False면 Claude 없이 규칙 AI만 (비교 화면용)."""
    prefs = understand(choice, places, data, use_llm)
    budget, notes = L.time_budget({"minutes": choice["minutes"]}, cond, lang)
    if prefs["short"]:
        budget = int(budget * 0.7)
    budget, notes = situation_budget(budget, notes, cond, lang)
    if start:
        res = search(start, choice, prefs, cond, places, data, elev, hills, budget)
        routes, starts = res["routes"], []
    else:
        starts = pick_starts(prefs, cond, places, data)
        routes, res = [], None
        agg = {"evaluated": 0, "feasible": 0, "util": {}, "pool": []}
        for sp, su, _ in starts:
            r = search(sp, choice, prefs, cond, places, data, elev, hills, budget, start_util=su)
            routes += r["routes"]
            agg["evaluated"] += r["evaluated"]
            agg["feasible"] += r["feasible"]
            for k, v in r["util"].items():
                agg["util"].setdefault(k, v)
            if res is None:
                res = r
        routes.sort(key=lambda r: -r["score"])
        to_sunset = int((cond["sunset"] - cond["now"]).total_seconds() // 60)
        for sp, _, _ in starts:
            agg["util"].setdefault(sp, place_utility(sp, prefs, cond, data, to_sunset))
        res = dict(res, evaluated=agg["evaluated"], feasible=agg["feasible"], util=agg["util"],
                   pool=sorted(agg["util"], key=lambda p: -agg["util"][p][0])[:12])
        start = routes[0]["stops"][0] if routes else starts[0][0]
    cands = diverse_top(routes, 3, by_start=bool(starts)) or [
        nearest_fallback(start, places, data, elev, hills, choice, prefs, cond)]
    for c in cands:
        c["reasons"] = explain(c, prefs, cond, res, places, data, budget, lang)
    agent = agent_pick(cands, prefs, cond, choice, places, data, budget, lang) if use_llm else None
    chosen = agent["plan"] if agent else cands[0]
    return {"prefs": prefs, "budget": budget, "notes": notes, "cands": cands, "chosen": chosen,
            "planner": "agent" if agent else "rule", "ai_reason": agent["reason"] if agent else "",
            "process": {"evaluated": res["evaluated"], "feasible": res["feasible"], "radius": res["radius"],
                        "starts": [(p, round(u, 2), round(pt, 2)) for p, u, pt in starts],
                        "pool": [(p, round(res["util"][p][0], 2), res["util"][p][1].get("top")) for p in res["pool"]]},
            "util": res["util"], "auto_start": bool(starts)}


def interest_to_story(prefs: dict) -> str:
    """이야기 조각의 관심사(역사·건축·사진·쉼) 중 취향에 가장 맞는 것"""
    score = {"역사": 0.0, "건축": 0.0, "사진": 0.0, "쉼": 0.0}
    for k, v in prefs["weights"].items():
        score[STORY_INTEREST.get(k, "역사")] += v
    return max(score, key=score.get)

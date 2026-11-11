"""app.py — 한 절 더 (화면)

실행:  streamlit run app.py
QR:    주소 뒤에 ?temple=bunhwangsa 처럼 사찰 id를 붙이면 그 사찰에서 시작해요.
언어:  ?lang=en (English) · ja (日本語) · zh (中文) · ko (한국어, 기본)
"""
import html
import io
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import folium
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

import importlib

import i18n as I
import logic as L


def _fresh(mod):
    """Streamlit Cloud는 GitHub가 업데이트돼도 예전 logic.py · i18n.py를 기억하고 있을 때가 있어요.
    파일이 바뀌었으면(수정 시각이 달라졌으면) 새로 불러와요."""
    try:
        mtime = Path(mod.__file__).stat().st_mtime
    except OSError:
        return mod
    if getattr(mod, "_loaded_mtime", None) != mtime:
        mod = importlib.reload(mod)
        mod._loaded_mtime = mtime
    return mod


I = _fresh(I)
L = _fresh(L)

st.set_page_config(page_title="한 절 더 · Han Jeol Deo", page_icon="🪷", layout="centered",
                   initial_sidebar_state="collapsed")
st.markdown(f"<style>{(Path(__file__).parent / 'style.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)

SS = st.session_state
E = html.escape
places = L.load_places()
data = L.load_all()

PIN = {"현존 사찰": ("#F7B193", "#FFFFFF"), "절터": ("#9FD0AE", "#FFFFFF"), "불상·석탑": ("#9DC4E8", "#FFFFFF"),
       "명소": ("#F5D06F", "#6E5510"), "출발점": ("#C7B3E6", "#FFFFFF")}
CAT_CHIP = {"현존 사찰": "peach", "절터": "", "불상·석탑": "sky", "명소": "butter", "출발점": "lav"}

# ---------------------------------------------------------------- 상태
if "sid" not in SS:
    SS.sid = uuid.uuid4().hex[:10]
    SS.step = "setup"
    qp = st.query_params.get("temple") or st.query_params.get("start")
    SS.start = qp if qp in places.index else "bunhwangsa"
    SS.from_qr = qp in places.index if qp else False
    ql = st.query_params.get("lang")
    SS.lang_pick = ql if ql in I.LANGS else "ko"
    SS.retold = {}
    SS.virtual = {}


def md(s: str):
    """HTML 카드 출력. 줄바꿈·들여쓰기를 지워서 마크다운이 코드 블록으로 착각하지 않게 해요."""
    st.markdown(re.sub(r"\n[ \t]*", "", s), unsafe_allow_html=True)


def pills(label, options, default, key, fmt, multi=False):
    if hasattr(st, "pills"):
        v = st.pills(label, options, default=default, key=key, format_func=fmt, label_visibility="collapsed",
                     selection_mode="multi" if multi else "single")
    elif multi:
        v = st.multiselect(label, options, default=default, key=key, format_func=fmt, label_visibility="collapsed")
    else:
        v = st.radio(label, options, index=options.index(default), key=key, horizontal=True, format_func=fmt,
                     label_visibility="collapsed")
    return v if v else default


def chip(text, kind=""):
    return f"<span class='chip {kind}'>{E(str(text))}</span>"


# ---------------------------------------------------------------- 언어
lang = SS.get("lang_pick") or SS.get("lang_last") or "ko"   # 언어 버튼을 다시 눌러 선택이 풀려도 원래 언어 유지
SS.lang_last = lang
T = lambda key, **kw: I.t(key, lang, **kw)
LB = lambda group, value: I.lab(group, value, lang)
name = lambda pid: L.place_name(pid, places, data, lang)


# ---------------------------------------------------------------- 사이드바 (발표·테스트 설정, 한국어)
with st.sidebar:
    st.markdown("### 🎛️ 발표·테스트 설정")
    st.caption("화면에는 안 보여요. 발표 때 상황을 바꿔 보는 곳이에요.")
    ids = list(places.index)
    pick = st.selectbox("QR 찍은 것처럼 시작하기", ids, index=ids.index(SS.start),
                        format_func=lambda p: L.place_name(p, places, data, "ko"))
    if pick != SS.start:
        SS.start, SS.step = pick, "setup"
    demo_weather = st.radio("날씨", ["실시간", "맑음", "비", "영하"], horizontal=True)
    m = st.selectbox("계절(월)", ["지금"] + [f"{i}월" for i in range(1, 13)])
    demo_month = None if m == "지금" else int(m[:-1])
    t_opts = ["지금", "10:00", "13:00", "15:30"]
    t_q = st.query_params.get("t")
    t = st.selectbox("시각", t_opts, index=t_opts.index(t_q) if t_q in t_opts else 0,
                     help="발표가 늦은 오후면 해 질 녘 규칙 때문에 길이 짧아져요. 그럴 땐 10:00으로 바꿔 보세요.")
    real_spots = L.load_rest_spots()
    has_key = bool(L.data_key())
    use_tour = st.toggle("주변 가게: TourAPI 실데이터", value=has_key, disabled=not has_key,
                         help="Secrets에 DATA_GO_KR_KEY가 있으면 한국관광공사 TourAPI로 반경 1km 음식점·카페를 불러와요.")
    show_example = False
    if real_spots.empty:
        show_example = st.toggle("예시 쉼터 보기 (실제 가게 아님)", value=not has_key,
                                 help="rest_spots.csv나 TourAPI 데이터가 없을 때만 예시가 나와요.")
    st.markdown("---")
    st.markdown("**🔌 연결 상태**")
    st.caption("🤖 Claude: " + ("연결됨 ✅" if L.llm_ready() else "키 없음 → 규칙 기반"))
    st.caption("🔑 공공데이터포털 키: " + ("있음 ✅" if has_key else "없음 → Open-Meteo·예시 쉼터"))
    st.markdown("---")
    st.markdown("**🖨️ QR 만들기**")
    url = st.text_input("앱 주소", placeholder="https://○○○.streamlit.app")
    qr_place = st.selectbox("QR 붙일 곳", ids, index=ids.index("bunhwangsa"),
                            format_func=lambda p: L.place_name(p, places, data, "ko"), key="qr_place")
    qr_lang = st.selectbox("QR 언어", I.LANGS, format_func=lambda x: I.LANG_NAMES[x], key="qr_lang")
    if url:
        import qrcode
        link = f"{url.rstrip('/')}/?temple={qr_place}" + (f"&lang={qr_lang}" if qr_lang != "ko" else "")
        img = qrcode.make(link)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=160)
        st.caption(link)
        st.download_button("QR 내려받기", buf.getvalue(), file_name=f"qr_{qr_place}_{qr_lang}.png", mime="image/png")

now = datetime.now(L.KST)
if t != "지금":
    hh, mm = map(int, t.split(":"))
    now = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
cond = L.get_conditions(demo_weather, demo_month, now)
with st.sidebar:
    st.caption(f"🌤️ 날씨 출처: {cond['source']}")


def spots_for(stop_ids):
    """쉼터 순서: 팀이 직접 확인한 rest_spots.csv → TourAPI 주변 가게 → (둘 다 없으면) 예시 쉼터"""
    frames = [real_spots] if not real_spots.empty else []
    if use_tour:
        tour = L.tour_spots(places, stop_ids)
        if tour is not None and not tour.empty:
            if frames:
                tour = tour[~tour["name"].isin(set(real_spots["name"]))]
            frames.append(tour)
    if frames:
        import pandas as pd
        return pd.concat(frames, ignore_index=True)
    return L.example_rest_spots(places, stop_ids, lang) if show_example else real_spots


# ---------------------------------------------------------------- 공통 조각
def speak(text: str, label: str):
    components.html(f"""
      <button id="b" style="border:none;border-radius:999px;padding:10px 18px;font-weight:700;font-size:15px;
        color:#fff;cursor:pointer;background:linear-gradient(135deg,#9FD0AE,#7DBB92);
        box-shadow:0 6px 16px rgba(125,187,146,.35);font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif">
        {html.escape(label)}</button>
      <script>
        const t = {json.dumps(text)};
        document.getElementById('b').onclick = () => {{
          speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(t); u.lang = '{I.TTS_LANG[lang]}'; u.rate = 0.95;
          speechSynthesis.speak(u);
        }};
      </script>""", height=56)


def pin(pid, number=None, size=30, grey=False):
    bg, fg = PIN.get(places.loc[pid, "category"], ("#F7B193", "#fff"))
    if grey:
        bg, fg = "#E9E1DC", "#9C8F88"
    label = number if number is not None else ""
    return folium.DivIcon(html=f"""<div style="width:{size}px;height:{size}px;border-radius:50%;background:{bg};
        color:{fg};border:3px solid #fff;box-shadow:0 3px 10px rgba(120,80,60,.25);display:flex;align-items:center;
        justify-content:center;font-weight:800;font-size:13px;font-family:sans-serif">{label}</div>""",
                          icon_size=(size, size), icon_anchor=(size // 2, size // 2))


SOFT_TILES = "<style>.leaflet-tile-pane{filter:saturate(.5) brightness(1.06) sepia(.08);} .leaflet-container{background:#FFF9F1;}</style>"


def base_map(center, zoom=15):
    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap", control_scale=False, zoom_control=False)
    m.get_root().header.add_child(folium.Element(SOFT_TILES))   # 지도 색을 부드럽게
    return m


def route_map(plan, height=300, done=None):
    stops = plan["stops"]
    lat = sum(places.loc[p, "lat"] for p in stops) / len(stops)
    lon = sum(places.loc[p, "lon"] for p in stops) / len(stops)
    m = base_map((lat, lon), 15)
    for leg in plan["legs"]:
        a, b = places.loc[leg["from"]], places.loc[leg["to"]]
        pts = leg.get("coords") or [(a.lat, a.lon), (b.lat, b.lon)]
        folium.PolyLine(pts, color="#F2896B", weight=6, opacity=0.85,
                        dash_array=None if leg.get("coords") else "8 10").add_to(m)
    for i, p in enumerate(stops):
        folium.Marker([places.loc[p, "lat"], places.loc[p, "lon"]], tooltip=name(p),
                      icon=pin(p, i + 1, grey=bool(done) and p not in done)).add_to(m)
    m.fit_bounds([[places.loc[p, "lat"], places.loc[p, "lon"]] for p in stops], padding=(30, 30))
    st_folium(m, height=height, use_container_width=True, returned_objects=[],
              key=f"map_{'_'.join(stops)}_{len(done or [])}_{lang}")


def route_chips(stops):
    parts = []
    for i, p in enumerate(stops):
        if i:
            parts.append("<span class='arrow'>›</span>")
        parts.append(f"<span class='stop'>{E(name(p))}</span>")
    return f"<div class='route'>{''.join(parts)}</div>"


def rest_html(spots):
    out = []
    for s in spots:
        badge = f" · <b>{T('rest_soon')}</b>" if s.get("partner") == "후보" else \
            (f" · <b>{T('rest_partner')}</b>" if s.get("partner") == "제휴" else "")
        coupon = f" · 🎟️ {E(s['coupon'])}" if s.get("coupon") else ""
        if s.get("source") == "TourAPI":
            badge += f" · {T('tour_badge')}"
        link = L.kakao_to(s["name"], s["lat"], s["lon"])
        out.append(f"<span class='rest'>☕ {E(s['name'])} <span class='muted'>({E(L.spot_type(s.get('type', ''), lang))}, "
                   f"{s['dist_km'] * 1000:.0f}m{badge}{coupon})</span> <a href='{link}' target='_blank'>{T('rest_dir')}</a></span>")
    return "".join(out)


def sources_html(sources):
    if not sources:
        return ""
    def title(s):
        tt = s["title"]
        if lang != "ko":   # 출처는 한국어 자료라서 사전 이름만 번역하고 '(한국어)' 표시
            tt = tt.replace("한국민족문화대백과사전", T("encyk")) + T("in_korean")
        return tt
    links = " · ".join(f"<a href='{E(s['url'])}' target='_blank'>{E(title(s))}</a>" for s in sources)
    return f"<div class='src'>{T('sources')}: {links}</div>"


def stats_html(items):
    cells = "".join(f"<div class='stat'><div class='v'>{E(v)}</div><div class='l'>{E(l)}</div></div>" for v, l in items)
    return f"<div class='stats'>{cells}</div>"


def dots(n_on, total):
    d = "".join(f"<span class='dot {'on' if i < n_on else ''}'></span>" for i in range(total))
    return f"<div class='dots'>{d}<span class='label'>{T('dots', a=n_on, b=total)}</span></div>"


def leg_text(leg):
    return T("leg_line", km=f"{leg['dist_m'] / 1000:.1f}", m=f"{leg['minutes']:.0f}", grade=LB("grade", leg["grade"]))


# ---------------------------------------------------------------- 머리 · 언어 선택
wx = "<br>".join(E(x) for x in L.weather_lines(cond, lang))
md(f"""<div class="brand"><div class="logo">🪷</div>
  <div><div class="name">한 절 더</div><div class="tag">{E(T('tag'))}</div></div>
  <div class="wx">{wx}</div></div>""")
if hasattr(st, "pills"):
    st.pills("🌐", I.LANGS, key="lang_pick", format_func=lambda x: "🌐 " + I.LANG_NAMES[x] if x == lang else I.LANG_NAMES[x],
             label_visibility="collapsed")
else:
    st.radio("🌐", I.LANGS, key="lang_pick", horizontal=True, format_func=lambda x: I.LANG_NAMES[x])

tab_walk, tab_map, tab_log = st.tabs([T("tab_walk"), T("tab_map"), T("tab_log")])


# ---------------------------------------------------------------- 순례: 1) 고르기
def make_plan():
    user = {"who": SS.get("q_who") or L.WHO[0], "minutes": L.TIMES[SS.get("q_time") or "2시간"],
            "time_label": SS.get("q_time") or "2시간", "level": SS.get("q_level") or "가볍게",
            "interest": SS.get("q_int") or "역사"}
    elev = L.elevations(places)
    hills = L.hill_pairs(data["courses"], data["tags"])
    cands, budget, notes = L.plan_candidates(SS.start, user, cond, places, data, elev, hills, lang)
    agent = L.agent_choose(cands, budget, cond, user, places, data, lang)
    chosen = agent["plan"] if agent else cands[0]
    SS.plan_ctx = {"user": user, "cands": cands, "budget": budget, "notes": notes, "elev": elev,
                   "hills": list(hills), "planner": "agent" if agent else "rule", "lang": lang,
                   "ai_reason": agent["reason"] if agent else ""}
    SS.plan = attach_routes(chosen, user, elev, hills)
    SS.step = "plan"


def attach_routes(plan, user, elev, hills, speed_factor=1.0):
    plan = dict(plan)
    legs = []
    for a, b in zip(plan["stops"], plan["stops"][1:]):
        pa, pb = places.loc[a], places.loc[b]
        r = L.walk_route(pa.lat, pa.lon, pb.lat, pb.lon)
        leg = L.leg_info(places, a, b, user["who"], elev, hills, speed_factor, dist_m=r[0] if r else None)
        leg["coords"] = r[1] if r else None
        legs.append(leg)
    plan["legs"] = legs
    plan["walk_min"] = sum(l["minutes"] for l in legs)
    plan["dist_m"] = sum(l["dist_m"] for l in legs)
    plan["total_min"] = plan["walk_min"] + sum(L.stay(p) for p in plan["stops"])
    return plan


def relocalize_plan():
    """추천을 받은 뒤 언어를 바꾸면, 추천 이유·날씨 안내도 그 언어로 다시 만들어요."""
    ctx = SS.plan_ctx
    if ctx.get("lang") == lang:
        return
    hills = set(map(tuple, ctx["hills"]))
    cands, _, notes = L.plan_candidates(SS.start, ctx["user"], cond, places, data, ctx["elev"], hills, lang)
    by_stops = {tuple(c["stops"]): c["reasons"] for c in cands}
    for c in ctx["cands"]:
        c["reasons"] = by_stops.get(tuple(c["stops"]), c["reasons"])
    SS.plan["reasons"] = by_stops.get(tuple(SS.plan["stops"]), SS.plan["reasons"])
    ctx.update(notes=notes, lang=lang)


def setup_view():
    p = places.loc[SS.start]
    desc = L.place_desc(SS.start, places, data, lang)
    first = L._first_sentence(desc, lang)
    where = T("where_qr") if SS.from_qr else T("where_here")
    hanja = f" <span class='muted small'>{E(str(p.hanja))}</span>" if lang in ("ko", "en") else ""
    md(f"""<div class="card soft">
      <div class="eyebrow">{E(where)}</div>
      <h3>{E(name(SS.start))}{hanja}</h3>
      {chip(LB('category', p.category), CAT_CHIP.get(p.category, ''))}{chip(L.era_text(p.era, data, lang), 'line')}
      <p class="small">{E(first)}</p></div>""")
    md(f"<div class='eyebrow' style='margin-top:6px'>{E(T('ask4'))}</div>")
    for qkey, label_key, options, default, group in (
            ("q_who", "q_who", L.WHO, L.WHO[0], "who"),
            ("q_time", "q_time", list(L.TIMES), "2시간", "time"),
            ("q_level", "q_level", L.LEVELS, "가볍게", "level"),
            ("q_int", "q_int", L.INTERESTS, "역사", "interest")):
        md(f"<div class='q'>{E(T(label_key))}</div>")
        pills(T(label_key), options, default, qkey, lambda v, g=group: LB(g, v))
    st.write("")
    if st.button(T("btn_plan"), type="primary", width="stretch"):
        with st.spinner(T("spinner")):
            make_plan()
        st.rerun()


# ---------------------------------------------------------------- 순례: 2) 추천 보기
def plan_view():
    relocalize_plan()
    plan, ctx = SS.plan, SS.plan_ctx
    user = ctx["user"]
    planner_chip = chip(T("chip_agent"), "lav") if ctx["planner"] == "agent" else chip(T("chip_rule"), "line")
    ai = f"<div class='ai-quote'>💬 {E(ctx['ai_reason'])}</div>" if ctx["ai_reason"] else ""
    reasons = "".join(f"<div class='reason'>✔️ {E(r)}</div>" for r in plan["reasons"])
    notes = "".join(f"<div class='reason'>{E(n)}</div>" for n in ctx["notes"])
    md(f"""<div class="card">
      <div class="eyebrow">{E(T('plan_title'))}</div>
      {route_chips(plan['stops'])}
      {stats_html([(f"{plan['dist_m'] / 1000:.1f}km", T('stat_dist')), (T('min', n=f"{plan['total_min']:.0f}"), T('stat_total')),
                   (T('count', n=len(plan['stops'])), T('stat_pieces'))])}
      <div style="margin-top:8px">{planner_chip}{chip(LB('who', user['who']), 'peach')}{chip(LB('level', user['level']), 'sky')}{chip(LB('interest', user['interest']), 'butter')}</div>
      {ai}<div style="margin-top:8px">{reasons}{notes}</div></div>""")
    route_map(plan)
    spots = spots_for(plan["stops"])
    legs_html = []
    for i, leg in enumerate(plan["legs"]):
        guess = f" <span class='muted'>{E(T('guess'))}</span>" if leg["guessed"] else ""
        rests = L.rest_near(spots, places, leg["from"], leg["to"], cond)
        legs_html.append(f"""<div class="leg"><div class="n">{i + 1}</div><div>
          <b>{E(name(leg['from']))} → {E(name(leg['to']))}</b><br>
          <span class="muted">{E(leg_text(leg))}{guess}</span>
          {('<div>' + rest_html(rests) + '</div>') if rests else ''}</div></div>""")
    md(f"<div class='card'><div class='eyebrow'>{E(T('legs_title'))}</div>{''.join(legs_html)}</div>")
    others = [c for c in ctx["cands"] if c["stops"] != plan["stops"]]
    if others:
        with st.expander(T("other_routes")):
            for c in others:
                alt = T("alt_line", m=f"{c['total_min']:.0f}", km=f"{c['dist_m'] / 1000:.1f}")
                md(route_chips(c["stops"]) + f"<span class='muted'>{E(alt)}</span>")
                if st.button(T("switch"), key=f"sw_{c['id']}"):
                    SS.plan = attach_routes(c, user, ctx["elev"], set(map(tuple, ctx["hills"])))
                    SS.plan_ctx["ai_reason"] = ""
                    st.rerun()
    c1, c2 = st.columns([2, 1])
    if c1.button(T("btn_start"), type="primary", width="stretch"):
        SS.walk = {"plan": plan, "user": user, "idx": 0, "arrived": [plan["stops"][0]], "missions": [],
                   "walked_m": 0.0, "speed": 1.0, "stopped": None}
        L.log_event(SS.sid, "start", stops=plan["stops"], who=user["who"], level=user["level"],
                    interest=user["interest"], planner=ctx["planner"], rain=cond["rain"], cold=cond["cold"], lang=lang)
        SS.step = "walk"
        st.rerun()
    if c2.button(T("btn_back"), width="stretch"):
        SS.step = "setup"
        st.rerun()


# ---------------------------------------------------------------- 순례: 3) 걷기
def story_text(pid, user):
    text, sources, status = L.story_for(pid, user["interest"], places, data, lang)
    k = (pid, user["who"], user["interest"], lang)
    if k not in SS.retold:
        SS.retold[k] = L.retell(text, user["who"], lang)
    return SS.retold[k], sources, status


def shorten():
    w = SS.walk
    stops, i = w["plan"]["stops"], w["idx"]
    ctx = SS.plan_ctx
    hills = set(map(tuple, ctx["hills"]))
    if len(stops) - i - 1 >= 2:
        skipped = stops[i + 1]
        new = stops[: i + 1] + stops[i + 2:]
        w["plan"] = attach_routes(dict(w["plan"], stops=new), w["user"], ctx["elev"], hills, 0.8)
        L.log_event(SS.sid, "shorten", leg=i, at=stops[i], skipped=[skipped])
        SS.toast = T("toast_skip", a=name(skipped), b=name(new[i + 1]))
    else:
        w["speed"] = 0.8
        w["plan"] = attach_routes(w["plan"], w["user"], ctx["elev"], hills, 0.8)
        SS.toast = T("toast_slow")


def walk_view():
    w = SS.walk
    plan, user, i = w["plan"], w["user"], w["idx"]
    stops = plan["stops"]
    pid = stops[i]
    p = places.loc[pid]
    fixes = L.load_fixes()
    if SS.get("toast"):
        st.toast(SS.pop("toast"), icon="🧭")
    md(dots(len(w["arrived"]), len(stops)))

    text, sources, status = story_text(pid, user)
    badge = {"ok": chip(T("st_ok"), ""), "review": chip(T("st_review"), "butter"),
             "pending": chip(T("st_pending"), "line")}[status]
    diff = f"<div class='diff'>{E(T('diff'))} · {E(L.diff_line(stops[i - 1], pid, places, data, lang))}</div>" if i > 0 else ""
    en = f"<p class='muted small'><i>{E(str(p.desc_en))}</i></p>" if (user["who"] == "외국인 친구와" and lang == "ko") else ""
    md(f"""<div class="card">
      <div class="eyebrow">{E(T('here'))} · {E(L.piece_title(pid, places, data, i + 1, lang))}</div>
      <h3>{E(name(pid))}</h3>{diff}
      {chip(T('interest_story', i=LB('interest', user['interest'])), 'butter')}{badge}
      <p>{E(text)}</p>{en}{sources_html(sources)}</div>""")
    speak(text, T("speak"))

    mission = L.mission_for(pid, user["who"], places, data, lang)
    md(f"<div class='card sage'><div class='eyebrow' style='color:#3F7A55'>{E(T('mission'))}</div><p>{E(mission)}</p></div>")
    if st.checkbox(T("mission_done"), key=f"m_{pid}_{i}"):
        if pid not in w["missions"]:
            w["missions"].append(pid)
    now_s, later_s = L.season_for(pid, cond["month"], data, lang)
    for s in now_s:
        md(f"<div class='card butter'><div class='eyebrow' style='color:#8A6A12'>{E(T('season_open', label=s['label']))}</div>"
           f"<p>{E(s['text'])}</p></div>")
    for s in later_s:
        months = I.join_list([I.month_name(x, lang) for x in s["months"]], lang)
        md(f"<p class='muted'>{E(T('season_later', months=months, label=s['label']))}</p>")

    if i < len(stops) - 1:
        nxt = stops[i + 1]
        leg = plan["legs"][i]
        seg = f"{pid}>{nxt}"
        boost = ""
        if fixes.get(seg) == "흥미":
            boost = f"<div class='reason'>{E(T('boost_interest'))}</div>"
        elif fixes.get(seg) in ("체력", "날씨", "동행"):
            boost = f"<div class='reason'>{E(T('boost_rest'))}</div>"
        rests = L.rest_near(spots_for(stops), places, pid, nxt, cond)
        a, b = places.loc[pid], places.loc[nxt]
        link = L.kakao_from_to(a["name"], a.lat, a.lon, b["name"], b.lat, b.lon)
        md(f"""<div class="card sky">
          <div class="eyebrow" style="color:#3C6E95">{E(T('next'))}</div>
          <h3>{E(name(nxt))}</h3>
          <span class="muted">{E(leg_text(leg))}</span>
          <div class="teaser">📖 {E(L.teaser(pid, nxt, places, data, lang))}</div>{boost}
          {('<div>' + rest_html(rests) + '</div>') if rests else ''}
          <div class="src" style="margin-top:6px"><a href="{link}" target="_blank">{E(T('kakao_walk'))}</a></div>
        </div>""")
        route_map(plan, height=240, done=w["arrived"])
        if st.button(T("arrive", n=name(nxt)), type="primary", width="stretch"):
            w["idx"] += 1
            w["arrived"].append(nxt)
            w["walked_m"] += leg["dist_m"]
            L.log_event(SS.sid, "arrive", leg=i, to=nxt, seg=seg, stops=stops)
            st.rerun()
        c1, c2 = st.columns(2)
        if c1.button(T("tired"), width="stretch"):
            shorten()
            st.rerun()
        with c2.popover(T("quit"), width="stretch"):
            why = st.radio(T("quit_q"), L.STOP_KEYS, key="why", format_func=lambda k: LB("stop", k))
            if st.button(T("quit_ok"), key="quit"):
                w["stopped"] = why
                L.log_event(SS.sid, "stop", leg=i, at=pid, seg=seg, reason=why, stops=stops)
                SS.step = "done"
                st.rerun()
    else:
        md(f"<div class='card butter'><h3>{E(T('last_title'))}</h3><p>{E(T('last_body'))}</p></div>")
        if st.button(T("finish"), type="primary", width="stretch"):
            L.log_event(SS.sid, "finish", stops=stops)
            SS.step = "done"
            st.rerun()


# ---------------------------------------------------------------- 순례: 4) 일지 · 다음 순례
def done_view():
    w = SS.walk
    lines = L.journal_lines(w, places, data, cond, lang)
    key = ("journal", tuple(w["arrived"]), lang)
    if key not in SS.retold:
        SS.retold[key] = L.polish_journal(lines, lang)
    polished = SS.retold[key]
    pieces = "".join(chip(("✔ " if p in w["arrived"] else "○ ") + name(p), "" if p in w["arrived"] else "line")
                     for p in w["plan"]["stops"])
    body = f"<p>{E(polished)}</p>" if polished else ""
    rest_lines = "".join(f"<div class='reason'>{E(l)}</div>" for l in lines[3:])
    md(f"""<div class="card soft">
      <div class="eyebrow">{E(T('journal'))}</div><h3>{E(lines[0])}</h3>
      {route_chips(w['arrived'])}<p class="muted">{E(lines[2])}</p>{pieces}{body}{rest_lines}</div>""")
    speak(polished or " ".join(lines[3:]), T("speak_journal"))

    rec = L.recommend(w["plan"].get("course_id"), w["plan"]["stops"], data, places, lang)
    if rec:
        md(f"<div class='eyebrow' style='margin-top:8px'>{E(T('rec_title'))}</div>")
        for k, label, kind in (("similar", T("rec_similar"), "peach"), ("new", T("rec_new"), "sky")):
            if k not in rec:
                continue
            c = rec[k]["course"]
            title, sub = L.course_text(c, data, lang)
            md(f"""<div class="card {'sky' if k == 'new' else ''}">{chip(label, kind)}
              <h3>{E(title)}</h3><p class="muted small">{E(sub)}</p>
              {route_chips(c['stops'])}<div class="reason">💡 {E(rec[k]['reason'])}</div></div>""")
            if st.button(T("rec_go", t=title), key=f"next_{k}"):
                SS.start, SS.step = c["stops"][0], "setup"
                st.rerun()
    last = w["arrived"][-1]
    rests = L.rest_near(spots_for([last]), places, last, last, cond, limit=3)
    if rests:
        md(f"<div class='card sage'><div class='eyebrow' style='color:#3F7A55'>{E(T('rest_after'))}</div>{rest_html(rests)}</div>")
    if st.button(T("home"), width="stretch"):
        SS.step = "setup"
        st.rerun()


with tab_walk:
    {"setup": setup_view, "plan": plan_view, "walk": walk_view, "done": done_view}[SS.step]()


# ---------------------------------------------------------------- 사찰 지도
with tab_map:
    cats = list(PIN)
    pick_c = pills("category", cats, cats, "map_cats", lambda c: LB("category", c), multi=True)
    shown = places[places["category"].isin(pick_c or cats)]
    m = base_map((35.83, 129.23), 12)
    for pid, p in shown.iterrows():
        desc = L.place_desc(pid, places, data, lang)
        pop = f"""<div style="font-family:sans-serif;width:220px"><b>{E(name(pid))}</b><br>
          <span style="color:#8F827B;font-size:12px">{E(L.era_text(p.era, data, lang))} · {E(LB('category', p.category))}</span>
          <p style="font-size:12px;line-height:1.5">{E(desc[:120])}{'…' if len(desc) > 120 else ''}</p>
          <a href="{L.kakao_to(p['name'], p.lat, p.lon)}" target="_blank">{E(T('kakao_dir'))}</a></div>"""
        folium.Marker([p.lat, p.lon], tooltip=name(pid), popup=folium.Popup(pop, max_width=240),
                      icon=pin(pid, size=22)).add_to(m)
    st_folium(m, height=440, use_container_width=True, returned_objects=[], key=f"overview_{lang}")
    legend = "".join(f"<span class='chip line'><span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
                     f"background:{PIN[c][0]};margin-right:5px'></span>{E(LB('category', c))}</span>" for c in cats)
    md(f"<div>{legend}</div><p class='muted'>{E(T('map_caption', n=len(places)))}</p>")


# ---------------------------------------------------------------- 순례 기록 (⑥)
def show_analysis(recs):
    o = L.overall(recs)
    seg = L.segment_table(recs, places, data, lang)
    stopped = int(seg["멈춘 수"].sum()) if not seg.empty else 0
    md(stats_html([(T("times", n=o["starts"]), T("s_starts")), (f"{o['rate']:.0f}%", T("s_rate")),
                   (T("times", n=stopped), T("s_stops"))]))
    if seg.empty:
        st.caption(T("no_seg"))
        return seg
    rows = []
    for k, (_, r) in enumerate(seg.iterrows()):
        color = "linear-gradient(90deg,#F8A985,#F2896B)" if k == 0 else "linear-gradient(90deg,#BFE0C8,#9CC9A8)"
        why = T("seg_why", r=LB("reason", r["멈춘 이유 1위"])) if r["멈춘 수"] else ""
        rows.append(f"""<div style="margin:10px 0">
          <div style="display:flex;justify-content:space-between;gap:8px;font-size:.86rem;font-weight:700">
            <span>{E(r['구간'])}</span><span style="color:{'#DD6E4E' if k == 0 else '#3F7A55'}">{r['완주율']:.0f}%</span></div>
          <div style="background:#F6ECE6;border-radius:999px;height:12px;margin:5px 0 3px">
            <div style="width:{r['완주율']:.0f}%;height:12px;border-radius:999px;background:{color}"></div></div>
          <div class="muted small">{E(T('seg_line', a=r['진입'], b=r['도착']) + why)}</div></div>""")
    md(f"<div class='card'><div class='eyebrow'>{E(T('seg_title'))}</div>{''.join(rows)}</div>")
    with st.expander(T("table")):
        view = seg[["구간", "진입", "도착", "완주율", "멈춘 이유 1위"]].copy()
        view["멈춘 이유 1위"] = view["멈춘 이유 1위"].map(lambda x: LB("reason", x))
        view.columns = [T("col_leg"), T("col_in"), T("col_arr"), T("col_rate"), T("col_why")]
        st.dataframe(view, hide_index=True, width="stretch")
    return seg


with tab_log:
    view = st.radio("view", ["virtual", "real"], horizontal=True, label_visibility="collapsed",
                    format_func=lambda v: T("v_virtual") if v == "virtual" else T("v_real"))
    if view == "real":
        recs = [r for r in L.load_logs() if not r.get("virtual")]
        st.caption(T("real_caption"))
        if recs:
            show_analysis(recs)
        else:
            md(f"<div class='card'><p class='muted'>{E(T('real_empty'))}</p></div>")
    else:
        md(f"<div class='virtual-banner'>{E(T('v_banner'))}</div>")
        fixes = L.load_fixes()
        if st.button(T("btn_virtual"), width="stretch") or "before" not in SS.virtual:
            SS.virtual = {"before": L.make_virtual(80, "before")}
        seg = show_analysis(SS.virtual["before"])
        if not seg.empty:
            worst = seg.iloc[0]
            md(f"""<div class="card butter">
              <div class="eyebrow" style="color:#8A6A12">{E(T('worst'))}</div>
              <h3>{E(worst['구간'])}</h3>
              <p>{T('worst_line', r=f"{worst['완주율']:.0f}", w=E(LB('reason', worst['멈춘 이유 1위'])))}</p>
              <div class="reason">{E(T('fix_sugg', t=L.suggestion(worst, lang)))}</div></div>""")
            c1, c2 = st.columns(2)
            if c1.button(T("btn_fix"), type="primary", width="stretch"):
                fixes[worst["seg"]] = worst["멈춘 이유 1위"]
                L.save_fixes(fixes)
                SS.virtual["after"] = L.make_virtual(80, "after", fixes)
                st.rerun()
            if c2.button(T("btn_unfix"), width="stretch"):
                L.save_fixes({})
                SS.virtual.pop("after", None)
                st.rerun()
            if "after" in SS.virtual:
                after = L.segment_table(SS.virtual["after"], places, data, lang)
                row = after[after["seg"] == worst["seg"]]
                before_rate, after_rate = worst["완주율"], (row["완주율"].iloc[0] if not row.empty else 0)
                ob, oa = L.overall(SS.virtual["before"]), L.overall(SS.virtual["after"])
                md(f"<div class='eyebrow'>{E(T('cmp_title'))}</div>")
                md(stats_html([(f"{before_rate:.0f}% → {after_rate:.0f}%", T("cmp_seg", d=f"{after_rate - before_rate:+.0f}")),
                               (f"{ob['rate']:.0f}% → {oa['rate']:.0f}%", T("cmp_all", d=f"{oa['rate'] - ob['rate']:+.0f}"))]))
                st.caption(T("fixed_note"))

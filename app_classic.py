"""app.py — 한 절 더 (화면)

실행:  streamlit run app.py
QR:    주소 뒤에 ?temple=bunhwangsa 처럼 사찰 id를 붙이면 그 사찰에서 시작해요.
언어:  ?lang=en (English) · ja (日本語) · zh (中文) · ko (한국어, 기본)
"""
import html
import importlib
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

import i18n as I
import logic as L
import planner as P
import shops as SH
import journal as J
import pins as PN


def _fresh(mod):
    """Streamlit Cloud는 GitHub가 업데이트돼도 예전 모듈을 기억할 때가 있어요. 파일이 바뀌었으면 새로 불러와요."""
    try:
        mtime = Path(mod.__file__).stat().st_mtime
    except OSError:
        return mod
    if getattr(mod, "_loaded_mtime", None) != mtime:
        mod = importlib.reload(mod)
        mod._loaded_mtime = mtime
    return mod


I, L, P, SH, J, PN = _fresh(I), _fresh(L), _fresh(P), _fresh(SH), _fresh(J), _fresh(PN)

st.set_page_config(page_title="한 절 더 · Han Jeol Deo", page_icon="🪷", layout="centered",
                   initial_sidebar_state="collapsed")
st.markdown(f"<style>{(Path(__file__).parent / 'style.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)

SS = st.session_state
E = html.escape
places = L.load_places()
data = L.load_all()
CAT_COLOR = {"현존 사찰": PN.ICON_COLOR["temple"], "절터": PN.ICON_COLOR["ruins"], "불상·석탑": PN.ICON_COLOR["pagoda"],
             "명소": PN.ICON_COLOR["landmark"], "출발점": PN.ICON_COLOR["start"]}
KIND_ICON = {"cafe": "☕", "meal": "🍚", "craft": "🎨", "culture": "🏛️"}

# ---------------------------------------------------------------- 상태
if "sid" not in SS:
    SS.sid = uuid.uuid4().hex[:10]
    SS.step = "setup"
    qp = st.query_params.get("temple") or st.query_params.get("start")
    SS.start = qp if qp in places.index else "bunhwangsa"
    SS.from_qr = bool(qp in places.index) if qp else False
    ql = st.query_params.get("lang")
    SS.lang_pick = ql if ql in I.LANGS else "ko"
    SS.retold, SS.virtual, SS.shop_cache = {}, {}, {}


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
    if multi:
        return list(v or [])
    return v if v else default


def chip(text, kind=""):
    return f"<span class='chip {kind}'>{E(str(text))}</span>"


lang = SS.get("lang_pick") or "ko"
T = lambda key, **kw: I.t(key, lang, **kw)
LB = lambda group, value: I.lab(group, value, lang)
name = lambda pid: L.place_name(pid, places, data, lang)
icon_kind = lambda pid: PN.icon_of(pid, places.loc[pid, "category"], places.loc[pid, "name"])


def fmt_minutes(m):
    h, mm = divmod(int(m), 60)
    if h and mm:
        return T("hm", h=h, m=mm)
    return T("h", h=h) if h else T("m", m=mm)


# ---------------------------------------------------------------- 사이드바 (발표·테스트 설정, 한국어)
with st.sidebar:
    st.markdown("### 🎛️ 발표·테스트 설정")
    st.caption("화면에는 안 보여요. 발표 때 상황을 바꿔 보는 곳이에요.")
    ids = list(places.index)
    demo_weather = st.radio("날씨", ["실시간", "맑음", "비", "영하"], horizontal=True)
    m = st.selectbox("계절(월)", ["지금"] + [f"{i}월" for i in range(1, 13)])
    demo_month = None if m == "지금" else int(m[:-1])
    t_opts = ["지금", "10:00", "13:00", "15:30"]
    t_q = st.query_params.get("t")
    t = st.selectbox("시각", t_opts, index=t_opts.index(t_q) if t_q in t_opts else 0,
                     help="발표가 늦은 오후면 해 질 녘 규칙 때문에 길이 짧아져요. 그럴 땐 10:00으로 바꿔 보세요.")
    real_spots = L.load_rest_spots()
    st.markdown("---")
    st.markdown("**🔑 API 키**")
    st.caption("보통은 Streamlit Secrets에 넣어요. 여기 칸에 붙여 넣으면 지금 접속에서만 쓰고 저장되지 않아요.")
    st.text_input("기상청 단기예보 키", key="kma_key_input", type="password", placeholder="비워 두면 Secrets 값 사용")
    st.text_input("TourAPI(국문 관광정보 GW) 키", key="tour_key_input", type="password", placeholder="비워 두면 Secrets 값 사용")
    st.text_input("Google Places 키 (평점·리뷰, 선택)", key="google_key_input", type="password", placeholder="GOOGLE_PLACES_KEY")
    kma_val, kma_note = L.secret_status("kma")
    tour_val, tour_note = L.secret_status("tour")
    g_val, g_note = SH.google_key()
    use_tour = st.toggle("주변 가게: TourAPI", value=bool(tour_val), disabled=not tour_val)
    use_google = st.toggle("주변 가게: Google 평점", value=bool(g_val), disabled=not g_val)
    show_example = st.toggle("가게 데이터가 없으면 예시 보여 주기", value=not (tour_val or g_val))
    st.markdown("---")
    st.markdown("**🔌 연결 상태**")
    st.caption("🤖 Claude: " + ("연결됨 ✅ (자유 입력 해석·경로 선택·일지 문장)" if L.llm_ready() else "키 없음 → 규칙 기반 AI로 동작"))
    st.caption("🌦️ 기상청 키: " + (f"있음 ✅ ({kma_note}, {len(kma_val)}자)" if kma_val else f"없음 → Open-Meteo · {kma_note}"))
    st.caption("🏪 TourAPI 키: " + (f"있음 ✅ ({tour_note}, {len(tour_val)}자)" if tour_val else f"없음 · {tour_note}"))
    st.caption("⭐ Google Places 키: " + (f"있음 ✅ ({g_note})" if g_val else "없음 → 평점 없이 거리·상황으로 추천"))
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


def clock_now():
    """도착·완료 시각. 데모 시각을 쓰면 계획 시간표 기준으로 계산해요."""
    return datetime.now(L.KST) if t == "지금" else None


# ---------------------------------------------------------------- 공통 조각
def speak(text: str, label: str):
    js_text = json.dumps(text).replace("</", "<\\/")
    page = f"""
      <button id="b" style="border:none;border-radius:999px;padding:10px 18px;font-weight:700;font-size:15px;
        color:#fff;cursor:pointer;background:linear-gradient(135deg,#9FD0AE,#7DBB92);
        box-shadow:0 6px 16px rgba(125,187,146,.35);font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif">
        {html.escape(label)}</button>
      <script>
        const t = {js_text};
        document.getElementById('b').onclick = () => {{
          speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(t); u.lang = '{I.TTS_LANG[lang]}'; u.rate = 0.95;
          speechSynthesis.speak(u);
        }};
      </script>"""
    if hasattr(st, "iframe"):
        st.iframe(page, height=56)
    else:
        components.html(page, height=56)


SOFT_TILES = "<style>.leaflet-tile-pane{filter:saturate(.5) brightness(1.06) sepia(.08);} .leaflet-container{background:#FFF9F1;}</style>"


def base_map(center, zoom=15):
    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap", control_scale=False, zoom_control=False)
    m.get_root().header.add_child(folium.Element(SOFT_TILES))   # 지도 색을 부드럽게
    return m


def marker(pid, number=None, grey=False, size=1.0):
    w, h = int(36 * size), int(46 * size)
    return folium.DivIcon(html=PN.marker_html(icon_kind(pid), number, grey, size), icon_size=(w, h),
                          icon_anchor=(w // 2, h - 1))


def route_map(plan, height=300, done=None, shops=None):
    stops = plan["stops"]
    lat = sum(places.loc[p, "lat"] for p in stops) / len(stops)
    lon = sum(places.loc[p, "lon"] for p in stops) / len(stops)
    m = base_map((lat, lon), 15)
    for leg in plan["legs"]:
        a, b = places.loc[leg["from"]], places.loc[leg["to"]]
        pts = leg.get("coords") or [(a.lat, a.lon), (b.lat, b.lon)]
        folium.PolyLine(pts, color="#F2896B", weight=6, opacity=0.85,
                        dash_array=None if leg.get("coords") else "8 10").add_to(m)
    for s in shops or []:
        folium.Marker([s["lat"], s["lon"]], tooltip=f"{KIND_ICON[s['kind']]} {s['name']}",
                      icon=folium.DivIcon(html=f"<div style='font-size:18px;filter:drop-shadow(0 1px 2px rgba(0,0,0,.25))'>"
                                               f"{KIND_ICON[s['kind']]}</div>", icon_size=(22, 22), icon_anchor=(11, 11))).add_to(m)
    for i, p in enumerate(stops):
        folium.Marker([places.loc[p, "lat"], places.loc[p, "lon"]], tooltip=name(p),
                      icon=marker(p, i + 1, grey=bool(done) and p not in done)).add_to(m)
    m.fit_bounds([[places.loc[p, "lat"], places.loc[p, "lon"]] for p in stops], padding=(36, 36))
    st_folium(m, height=height, use_container_width=True, returned_objects=[],
              key=f"map_{'_'.join(stops)}_{len(done or [])}_{lang}")


def route_chips(stops):
    parts = []
    for i, p in enumerate(stops):
        if i:
            parts.append("<span class='arrow'>›</span>")
        parts.append(f"<span class='stop'>{PN.svg_icon(icon_kind(p), 16)} {E(name(p))}</span>")
    return f"<div class='route'>{''.join(parts)}</div>"


def shop_html(s):
    src = {"google": T("src_google"), "tour": T("src_tour"), "csv": T("src_csv"), "example": T("src_example")}[s["source"]]
    badge = f" · <b>{T('rest_soon')}</b>" if s.get("partner") == "후보" else \
        (f" · <b>{T('rest_partner')}</b>" if s.get("partner") == "제휴" else "")
    coupon = f" · 🎟️ {E(s['coupon'])}" if s.get("coupon") else ""
    link = s.get("url") or L.kakao_to(s["name"], s["lat"], s["lon"])
    why = " · ".join(E(w) for w in s.get("why", []))
    return (f"<div class='shop'><div class='k'>{KIND_ICON[s['kind']]}</div><div>"
            f"<div class='nm'>{E(s['name'])} <span class='muted small'>{E(LB('shop_kind', s['kind']))} · {E(src)}{badge}{coupon}</span></div>"
            f"<div class='why'>{why}</div><a href='{E(link)}' target='_blank'>{T('rest_dir')} ›</a></div></div>")


def sources_html(sources):
    if not sources:
        return ""

    def title(s):
        tt = s["title"]
        if lang != "ko":
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


# ---------------------------------------------------------------- 머리 · 언어
wx_lines = L.weather_lines(cond, lang)
md(f"""<div class="brand"><div class="logo">🪷</div>
  <div><div class="name">한 절 더</div><div class="tag">{E(T('tag'))}</div></div>
  <div class="wx"><span class="big">{E(wx_lines[0])}</span><br>{E(wx_lines[1])}</div></div>""")
c_l, c_r = st.columns([1.7, 1])
with c_r:
    st.selectbox(T("lang_label"), I.LANGS, key="lang_pick", format_func=lambda x: "🌐 " + I.LANG_NAMES[x],
                 label_visibility="collapsed")

tab_walk, tab_map, tab_log = st.tabs([T("tab_walk"), T("tab_map"), T("tab_log")])


# ---------------------------------------------------------------- 가게 (AI 추천)
def shop_ctx(extra=None):
    ctx = SS.get("plan_ctx", {})
    prefs = ctx.get("prefs", {})
    c = {"now": cond["now"], "want_cafe": prefs.get("want_cafe"), "want_meal": prefs.get("want_meal"),
         "kids": ctx.get("choice", {}).get("who") == "아이와 함께", "rain": cond["rain"], "cold": cond["cold"]}
    c.update(extra or {})
    return c


def shops_for(stop_ids):
    key = (tuple(stop_ids), lang, use_tour, use_google, show_example, len(real_spots))
    if key not in SS.shop_cache:
        SS.shop_cache[key] = SH.gather(places, list(stop_ids), lang, use_tour, use_google, show_example, real_spots)[0]
    return SS.shop_cache[key]


# ---------------------------------------------------------------- 순례: 1) 고르기
def attach_routes(plan, who, elev, hills, speed=1.0):
    plan = dict(plan)
    legs = []
    for a, b in zip(plan["stops"], plan["stops"][1:]):
        pa, pb = places.loc[a], places.loc[b]
        r = L.walk_route(pa.lat, pa.lon, pb.lat, pb.lon)
        leg = L.leg_info(places, a, b, who, elev, hills, speed, dist_m=r[0] if r else None)
        leg["coords"] = r[1] if r else None
        legs.append(leg)
    plan["legs"] = legs
    plan["walk_min"] = sum(l["minutes"] for l in legs)
    plan["dist_m"] = sum(l["dist_m"] for l in legs)
    plan["total_min"] = plan["walk_min"] + sum(P.stay_min(data, p, who) for p in plan["stops"])
    return plan


def make_plan():
    choice = {"who": SS.get("q_who") or "혼자", "minutes": int(SS.get("q_time") or 120),
              "level": SS.get("q_level") or "가볍게", "interests": list(SS.get("q_int") or []),
              "free": (SS.get("q_free") or "").strip()[:300]}
    elev = L.elevations(places)
    hills = L.hill_pairs(data["courses"], data["tags"])
    res = P.plan(SS.start, choice, cond, places, data, elev, hills, lang)
    prefs = res["prefs"]
    SS.plan_ctx = {"choice": choice, "prefs": prefs, "cands": res["cands"], "budget": res["budget"], "notes": res["notes"],
                   "elev": elev, "hills": list(hills), "planner": res["planner"], "ai_reason": res["ai_reason"],
                   "process": res["process"], "util": res["util"], "lang": lang,
                   "story_interest": P.interest_to_story(prefs)}
    chosen = attach_routes(res["chosen"], choice["who"], elev, hills, prefs["speed"])
    chosen["reasons"] = res["chosen"]["reasons"]
    SS.plan = chosen
    SS.step = "plan"


def relocalize_plan():
    ctx = SS.plan_ctx
    if ctx.get("lang") == lang:
        return
    result = {"util": ctx["util"]}
    for c in ctx["cands"] + [SS.plan]:
        c["reasons"] = P.explain(c, ctx["prefs"], cond, result, places, data, ctx["budget"], lang)
    ctx["notes"] = L.time_budget({"minutes": ctx["choice"]["minutes"]}, cond, lang)[1]
    ctx["lang"] = lang


def setup_view():
    p = places.loc[SS.start]
    where = T("where_qr") if SS.from_qr else T("where_here")
    desc = L._first_sentence(L.place_desc(SS.start, places, data, lang), lang)
    md(f"""<div class="card soft">
      <div class="eyebrow">{E(where)}</div>
      <h3>{PN.svg_icon(icon_kind(SS.start), 22)} {E(name(SS.start))}</h3>
      {chip(LB('icon', icon_kind(SS.start)), '')}{chip(L.era_text(p.era, data, lang), 'line')}
      <p class="small">{E(desc)}</p></div>""")
    ids = list(places.index)
    pick = st.selectbox(T("start_change"), ids, index=ids.index(SS.start), format_func=name, key="start_pick")
    if pick != SS.start:
        SS.start, SS.from_qr = pick, False
        st.rerun()
    md(f"<div class='q'>{E(T('q_who'))}</div>")
    pills(T("q_who"), P.WHO_OPTS, "혼자", "q_who", lambda v: LB("who2", v))
    md(f"<div class='q'>{E(T('q_time'))}</div>")
    v = st.slider(T("q_time"), 30, 300, 120, 15, key="q_time", label_visibility="collapsed")
    st.caption(T("time_val", v=fmt_minutes(v)))
    md(f"<div class='q'>{E(T('q_level'))}</div>")
    pills(T("q_level"), P.LEVEL_OPTS, "가볍게", "q_level", lambda v: LB("level2", v))
    md(f"<div class='q'>{E(T('q_int2'))}</div>")
    pills(T("q_int2"), P.INTEREST_OPTS, [], "q_int", lambda v: LB("interest2", v), multi=True)
    md(f"<div class='q'>{E(T('q_free'))}</div>")
    st.text_area(T("q_free"), key="q_free", placeholder=T("free_ph"), height=80, label_visibility="collapsed")
    st.write("")
    if st.button(T("btn_plan"), type="primary", width="stretch"):
        with st.spinner(T("spinner")):
            make_plan()
        st.rerun()


# ---------------------------------------------------------------- 순례: 2) 추천 보기
def process_html(ctx):
    prefs, proc = ctx["prefs"], ctx["process"]
    tops = I.join_list([LB("theme", k) for k in P.top_themes(prefs)], lang)
    by = T("by_claude") if prefs.get("parsed_by") == "claude" else T("by_rule")
    w = prefs["weights"]
    bars = "".join(f"<div class='wbar'><span class='lab'>{E(LB('theme', k))}</span><div class='bg'>"
                   f"<div class='fg' style='width:{min(100, v * 250):.0f}%'></div></div><span>{v * 100:.0f}%</span></div>"
                   for k, v in sorted(w.items(), key=lambda kv: -kv[1]) if v > 0.02)
    rows = "".join(f"<tr><td>{PN.svg_icon(icon_kind(p), 14)} {E(name(p))}</td><td style='text-align:right'>{u:.2f}</td>"
                   f"<td>&nbsp;{E(LB('theme', tp)) if tp else '-'}</td></tr>" for p, u, tp in proc["pool"][:8])
    radius = f"{proc['radius']:.1f}"
    p2 = T("proc_2", r=radius, k=len(proc["pool"]))
    p3 = T("proc_3", e=f"{proc['evaluated']:,}", f=f"{proc['feasible']:,}")
    return f"""<div class="proc">{E(T('proc_1', t=tops))}<br><span class="muted">{E(T('proc_1b', by=by))}</span></div>{bars}
      <div class="proc" style="margin-top:8px">{E(p2)}</div>
      <table style="width:100%;font-size:.8rem;border-collapse:collapse"><tr style="color:#8F827B"><td>{E(T('col_place'))}</td>
      <td style="text-align:right">{E(T('col_score'))}</td><td>&nbsp;{E(T('col_theme'))}</td></tr>{rows}</table>
      <div class="proc" style="margin-top:8px">{E(p3)}<br>{E(T('proc_4'))}</div>"""


def plan_view():
    relocalize_plan()
    plan, ctx = SS.plan, SS.plan_ctx
    choice, prefs = ctx["choice"], ctx["prefs"]
    planner_chip = chip(T("chip_agent"), "lav") if ctx["planner"] == "agent" else chip(T("chip_rule"), "line")
    ints = "".join(chip(LB("interest2", x), "butter") for x in choice["interests"][:3])
    ai = f"<div class='ai-quote'>💬 {E(ctx['ai_reason'])}</div>" if ctx["ai_reason"] else ""
    reasons = "".join(f"<div class='reason'>✔️ {E(r)}</div>" for r in plan["reasons"])
    notes = "".join(f"<div class='reason'>{E(n)}</div>" for n in ctx["notes"])
    level_short = LB("level2", choice["level"]).split("·")[0].strip()
    md(f"""<div class="card">
      <div class="eyebrow">{E(T('plan_title'))}</div>
      {route_chips(plan['stops'])}
      {stats_html([(f"{plan['dist_m'] / 1000:.1f}km", T('stat_dist')), (T('min', n=f"{plan['total_min']:.0f}"), T('stat_total')),
                   (T('count', n=len(plan['stops'])), T('stat_pieces'))])}
      <div style="margin-top:8px">{planner_chip}{chip(LB('who2', choice['who']), 'peach')}{chip(level_short, 'sky')}{ints}</div>
      {ai}<div style="margin-top:8px">{reasons}{notes}</div></div>""")
    with st.expander(T("ai_process")):
        md(process_html(ctx))
    shop_list = shops_for(plan["stops"])
    assigned = SH.assign(shop_list, places, plan["stops"], shop_ctx(), lang)
    route_map(plan, shops=[s for v in assigned.values() for s in v])
    legs_html = []
    for i, leg in enumerate(plan["legs"]):
        guess = f" <span class='muted'>{E(T('guess'))}</span>" if leg["guessed"] else ""
        sh = "".join(shop_html(s) for s in assigned.get(i, []))
        legs_html.append(f"""<div class="leg"><div class="n">{i + 1}</div><div style="flex:1">
          <b>{E(name(leg['from']))} → {E(name(leg['to']))}</b><br>
          <span class="muted">{E(leg_text(leg))}{guess}</span>{sh}</div></div>""")
    shop_note = f"<div class='muted small' style='margin-top:6px'>{E(T('shops_title'))}</div>" if any(assigned.values()) else ""
    md(f"<div class='card'><div class='eyebrow'>{E(T('legs_title'))}</div>{''.join(legs_html)}{shop_note}</div>")
    others = [c for c in ctx["cands"] if c["stops"] != plan["stops"]]
    if others:
        with st.expander(T("other_routes")):
            for c in others:
                alt = T("alt_line", m=f"{c['total_min']:.0f}", km=f"{c['dist_m'] / 1000:.1f}")
                md(route_chips(c["stops"]) + f"<span class='muted'>{E(alt)}</span>")
                if st.button(T("switch"), key=f"sw_{c['id']}"):
                    newp = attach_routes(c, choice["who"], ctx["elev"], set(map(tuple, ctx["hills"])), prefs["speed"])
                    newp["reasons"] = c["reasons"]
                    SS.plan = newp
                    SS.plan_ctx["ai_reason"] = ""
                    st.rerun()
    c1, c2 = st.columns([2, 1])
    if c1.button(T("btn_start"), type="primary", width="stretch"):
        SS.walk = {"plan": plan, "user": {"who": choice["who"], "story_interest": ctx["story_interest"], "interest": ctx["story_interest"]},
                   "idx": 0, "arrived": [plan["stops"][0]], "missions": [], "walked_m": 0.0, "speed": prefs["speed"],
                   "stopped": None, "start_ts": cond["now"].isoformat(),
                   "arrived_at": {plan["stops"][0]: cond["now"].isoformat()},
                   "memos": {}, "moods": {}, "photos": {}, "bored": 0, "used_tired": False}
        L.log_event(SS.sid, "start", stops=plan["stops"], who=choice["who"], level=choice["level"],
                    interests=choice["interests"], free=bool(choice["free"]), planner=ctx["planner"],
                    rain=cond["rain"], cold=cond["cold"], lang=lang)
        SS.step = "walk"
        st.rerun()
    if c2.button(T("btn_back"), width="stretch"):
        SS.step = "setup"
        st.rerun()


# ---------------------------------------------------------------- 순례: 3) 걷기
def story_text(pid, user):
    text, sources, status = L.story_for(pid, user["story_interest"], places, data, lang)
    k = (pid, user["who"], user["story_interest"], lang)
    if k not in SS.retold:
        SS.retold[k] = L.retell(text, user["who"], lang)
    return SS.retold[k], sources, status


def replan_walk(new_stops):
    w, ctx = SS.walk, SS.plan_ctx
    w["plan"] = attach_routes(dict(w["plan"], stops=new_stops), w["user"]["who"], ctx["elev"],
                              set(map(tuple, ctx["hills"])), w["speed"])


def shorten():
    w = SS.walk
    stops, i = w["plan"]["stops"], w["idx"]
    w["used_tired"] = True
    w["speed"] = w["speed"] * 0.8
    if len(stops) - i - 1 >= 2:
        skipped = stops[i + 1]
        new = stops[: i + 1] + stops[i + 2:]
        replan_walk(new)
        L.log_event(SS.sid, "shorten", leg=i, at=stops[i], skipped=[skipped])
        SS.toast = T("toast_skip", a=name(skipped), b=name(new[i + 1]))
    else:
        replan_walk(stops)
        SS.toast = T("toast_slow")
    SS.tired_now = True


def save_photo(pid, up):
    try:
        from PIL import Image
        im = Image.open(up).convert("RGB")
        im.thumbnail((900, 900))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=82)
        SS.walk["photos"][pid] = buf.getvalue()
    except Exception:
        pass


def planned_clock(idx_arrived):
    """데모 시각일 때 도착 시각 = 출발 시각 + 계획상 걷기·관람 시간"""
    w = SS.walk
    stops, legs = w["plan"]["stops"], w["plan"]["legs"]
    mins = sum(l["minutes"] for l in legs[:idx_arrived]) + sum(P.stay_min(data, x, w["user"]["who"]) for x in stops[:idx_arrived])
    return datetime.fromisoformat(w["start_ts"]) + L.timedelta(minutes=mins)


def bored_panel(pid, i):
    w, ctx = SS.walk, SS.plan_ctx
    stops = w["plan"]["stops"]
    alts = SH.alternatives(pid, stops, ctx["prefs"], cond, places, data, lang)
    md(f"<div class='card butter'><div class='eyebrow' style='color:#8A6A12'>{E(T('bored_title'))}</div></div>")
    for a in alts:
        km = f"{a['km']:.1f}"
        theme = LB("theme", a["top"]) if a["top"] else ""
        md(f"<div class='shop'><div class='k'>{PN.svg_icon(icon_kind(a['pid']), 24)}</div><div>"
           f"<div class='nm'>{E(name(a['pid']))}</div><div class='why'>{E(T('alt_near', km=km, t=theme))}</div></div></div>")
        if i < len(stops) - 1 and st.button(T("alt_swap", n=name(a["pid"])), key=f"swap_{a['pid']}_{i}"):
            new = stops[: i + 1] + [a["pid"]] + stops[i + 2:]
            replan_walk(new)
            w["bored"] += 1
            L.log_event(SS.sid, "swap", leg=i, at=pid, to=a["pid"], reason="흥미")
            SS.toast = T("toast_swap", n=name(a["pid"]))
            SS.bored_open = False
            st.rerun()
    near = SH.around(shops_for(stops), places, pid, shop_ctx(), lang, limit=3, kinds=("craft", "culture", "cafe"))
    if near:
        md(f"<div class='eyebrow' style='margin-top:6px'>{E(T('alt_shops'))}</div>" + "".join(shop_html(s) for s in near))


def walk_view():
    w = SS.walk
    plan, user, i = w["plan"], w["user"], w["idx"]
    stops = plan["stops"]
    pid = stops[i]
    fixes = L.load_fixes()
    if SS.get("toast"):
        st.toast(SS.pop("toast"), icon="🧭")
    md(dots(len(w["arrived"]), len(stops)))
    text, sources, status = story_text(pid, user)
    badge = {"ok": chip(T("st_ok"), ""), "review": chip(T("st_review"), "butter"),
             "pending": chip(T("st_pending"), "line")}[status]
    diff = f"<div class='diff'>{E(T('diff'))} · {E(L.diff_line(stops[i - 1], pid, places, data, lang))}</div>" if i > 0 else ""
    md(f"""<div class="card">
      <div class="eyebrow">{E(T('here'))} · {E(L.piece_title(pid, places, data, i + 1, lang))}</div>
      <h3>{PN.svg_icon(icon_kind(pid), 22)} {E(name(pid))}</h3>{diff}
      {chip(T('interest_story', i=LB('interest', user['story_interest'])), 'butter')}{badge}
      <p>{E(text)}</p>{sources_html(sources)}</div>""")
    speak(text, T("speak"))

    mission = L.mission_for(pid, user["who"], places, data, lang)
    md(f"<div class='card sage'><div class='eyebrow' style='color:#3F7A55'>{E(T('mission'))}</div><p>{E(mission)}</p></div>")
    if st.checkbox(T("mission_done"), key=f"m_{pid}_{i}"):
        if pid not in w["missions"]:
            w["missions"].append(pid)
    elif pid in w["missions"]:
        w["missions"].remove(pid)
    w["memos"][pid] = st.text_input(T("memo_ph"), key=f"memo_{pid}", label_visibility="collapsed", placeholder=T("memo_ph"))
    md(f"<div class='muted small'>{E(T('mood_q'))}</div>")
    mood = pills(T("mood_q"), J.MOODS, None, f"mood_{pid}", lambda v: v)
    if mood:
        w["moods"][pid] = mood
    up = st.file_uploader(T("photo_up"), type=["jpg", "jpeg", "png", "webp"], key=f"ph_{pid}")
    if up is not None and pid not in w["photos"]:
        save_photo(pid, up)
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
        assigned = SH.assign(shops_for(stops), places, stops, shop_ctx({"tired": SS.get("tired_now", False)}), lang)
        here_shops = assigned.get(i, [])
        a, b = places.loc[pid], places.loc[nxt]
        link = L.kakao_from_to(a["name"], a.lat, a.lon, b["name"], b.lat, b.lon)
        md(f"""<div class="card sky">
          <div class="eyebrow" style="color:#3C6E95">{E(T('next'))}</div>
          <h3>{PN.svg_icon(icon_kind(nxt), 22)} {E(name(nxt))}</h3>
          <span class="muted">{E(leg_text(leg))}</span>
          <div class="teaser">📖 {E(L.teaser(pid, nxt, places, data, lang))}</div>{boost}
          {''.join(shop_html(s) for s in here_shops)}
          <div class="src" style="margin-top:6px"><a href="{link}" target="_blank">{E(T('kakao_walk'))}</a></div>
        </div>""")
        route_map(plan, height=240, done=w["arrived"], shops=here_shops)
        if st.button(T("arrive", n=name(nxt)), type="primary", width="stretch"):
            w["idx"] += 1
            w["arrived"].append(nxt)
            w["arrived_at"][nxt] = (clock_now() or planned_clock(i + 1)).isoformat()
            w["walked_m"] += leg["dist_m"]
            SS.bored_open, SS.tired_now = False, False
            L.log_event(SS.sid, "arrive", leg=i, to=nxt, seg=seg, stops=stops)
            st.rerun()
        c1, c2, c3 = st.columns(3)
        if c1.button(T("tired"), width="stretch"):
            shorten()
            st.rerun()
        if c2.button(T("bored"), width="stretch"):
            SS.bored_open = not SS.get("bored_open", False)
            L.log_event(SS.sid, "bored", leg=i, at=pid, seg=seg)
        with c3.popover(T("quit"), width="stretch"):
            why = st.radio(T("quit_q"), L.STOP_KEYS, key="why", format_func=lambda k: LB("stop", k))
            if st.button(T("quit_ok"), key="quit"):
                w["stopped"] = why
                w["end_ts"] = (clock_now() or planned_clock(i)).isoformat()
                L.log_event(SS.sid, "stop", leg=i, at=pid, seg=seg, reason=why, stops=stops)
                SS.step = "done"
                st.rerun()
        if SS.get("bored_open"):
            bored_panel(pid, i)
    else:
        md(f"<div class='card butter'><h3>{E(T('last_title'))}</h3><p>{E(T('last_body'))}</p></div>")
        if st.button(T("finish"), type="primary", width="stretch"):
            end = clock_now() or (planned_clock(i) + L.timedelta(minutes=P.stay_min(data, pid, user["who"])))
            w["end_ts"] = end.isoformat()
            L.log_event(SS.sid, "finish", stops=stops)
            SS.step = "done"
            st.rerun()


# ---------------------------------------------------------------- 순례: 4) 나만의 순례 일지
def done_view():
    w = SS.walk
    lines = L.journal_lines(w, places, data, cond, lang)
    s = J.stats(w)
    bs = J.badges(w, cond, data, lang)
    badge_html = "".join(f"<span class='badge'>{I.BADGE_EMOJI.get(b, '')} {E(LB('badge', b))}</span>" for b in bs)
    badge_block = f"<div class='eyebrow' style='margin-top:10px'>{E(T('jr_badges'))}</div>{badge_html}" if bs else ""
    md(f"""<div class="card soft">
      <div class="eyebrow">{E(T('journal'))}</div><h3>{E(lines[0])}</h3>
      {route_chips(w['arrived'])}
      {stats_html([(f"{s['km']:.1f}km", T('pc_dist')), (fmt_minutes(s['minutes']), T('pc_time')),
                   (f"{s['steps']:,}", T('pc_steps')), (f"{s['pieces']}/{s['total']}", T('stat_pieces'))])}
      {badge_block}</div>""")

    key = ("story", tuple(w["arrived"]), lang, tuple(sorted((k, v) for k, v in w["memos"].items() if v)),
           tuple(sorted(w["moods"].items())), tuple(w["missions"]))
    if key not in SS.retold:
        base = J.story(w, places, data, cond, lang)
        SS.retold[key] = J.polish(base, lang) or base
    paras = SS.retold[key]
    md(f"<div class='card story'><div class='eyebrow'>📖 {E(T('jr_story'))}</div>" +
       "".join(f"<p>{E(x)}</p>" for x in paras) + "</div>")
    speak(" ".join(paras), T("speak_journal"))

    md(f"<div class='eyebrow' style='margin-top:6px'>🕰️ {E(T('jr_timeline'))}</div>")
    for i, p in enumerate(w["arrived"]):
        at = w["arrived_at"].get(p, "")
        tm = at[11:16] if at else ""
        memo = (w["memos"].get(p) or "").strip()
        mood = w["moods"].get(p, "")
        mission = "🎯 " + E(L.mission_for(p, w["user"]["who"], places, data, lang)) if p in w["missions"] else ""
        memo_html = f"<div class='memo'>“{E(memo)}”</div>" if memo else ""
        mission_html = f"<div class='muted small' style='margin-top:4px'>{mission}</div>" if mission else ""
        item = f"""<div class="tl"><div class="tm">{E(tm)}</div><div>
              <b>{PN.svg_icon(icon_kind(p), 16)} {E(name(p))}</b> {mood}<br>
              <span class="muted small">{E(L.piece_title(p, places, data, i + 1, lang))}</span>
              {memo_html}{mission_html}</div></div>"""
        if p in w["photos"]:
            c1, c2 = st.columns([3, 1])
            with c1:
                md(item)
            c2.image(w["photos"][p], width="stretch")
        else:
            md(item)

    try:
        card = J.postcard(w, places, data, cond, lang, CAT_COLOR)
        st.download_button(T("dl_card"), card, file_name=f"hanjeolde_{cond['now']:%Y%m%d}.png", mime="image/png",
                           width="stretch")
        with st.expander("🖼️ " + T("dl_card").split("(")[0].replace("📮", "").strip()):
            st.image(card, width="stretch")
    except Exception as e:
        st.caption(f"postcard: {type(e).__name__}")

    rec = L.recommend(w["plan"].get("course_id"), w["plan"]["stops"], data, places, lang)
    if rec:
        md(f"<div class='eyebrow' style='margin-top:12px'>{E(T('rec_title'))}</div>")
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
    near = SH.around(shops_for(w["plan"]["stops"]), places, last, shop_ctx(), lang, limit=3)
    if near:
        md(f"<div class='card sage'><div class='eyebrow' style='color:#3F7A55'>{E(T('rest_after'))}</div>"
           + "".join(shop_html(x) for x in near) + "</div>")
    if st.button(T("home"), width="stretch"):
        SS.step = "setup"
        st.rerun()


with tab_walk:
    {"setup": setup_view, "plan": plan_view, "walk": walk_view, "done": done_view}[SS.step]()


# ---------------------------------------------------------------- 사찰 지도
with tab_map:
    kinds = PN.LEGEND_ORDER
    pick_k = pills("icon", kinds, kinds, "map_kinds", lambda k: LB("icon", k), multi=True)
    shown = [pid for pid in places.index if icon_kind(pid) in (pick_k or kinds)]
    m = base_map((35.83, 129.23), 12)
    for pid in shown:
        p = places.loc[pid]
        desc = L.place_desc(pid, places, data, lang)
        pop = f"""<div style="font-family:sans-serif;width:220px"><b>{E(name(pid))}</b><br>
          <span style="color:#8F827B;font-size:12px">{E(L.era_text(p.era, data, lang))} · {E(LB('icon', icon_kind(pid)))}</span>
          <p style="font-size:12px;line-height:1.5">{E(desc[:120])}{'…' if len(desc) > 120 else ''}</p>
          <a href="{L.kakao_to(p['name'], p.lat, p.lon)}" target="_blank">{E(T('kakao_dir'))}</a></div>"""
        folium.Marker([p.lat, p.lon], tooltip=name(pid), popup=folium.Popup(pop, max_width=240),
                      icon=marker(pid, size=0.8)).add_to(m)
    st_folium(m, height=460, use_container_width=True, returned_objects=[], key=f"overview_{lang}")
    legend = "".join(f"<span>{PN.svg_icon(k, 18)} {E(LB('icon', k))}</span>" for k in kinds)
    md(f"<div class='legend'>{legend}</div><p class='muted'>{E(T('map_caption', n=len(places)))}</p>")


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

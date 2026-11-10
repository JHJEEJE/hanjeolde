"""app.py — 한 절 더 (화면)

실행:  streamlit run app.py
QR:    주소 뒤에 ?temple=bunhwangsa 처럼 사찰 id를 붙이면 그 사찰에서 시작해요.
"""
import html
import re
import io
import json
import uuid
from datetime import datetime, time
from pathlib import Path

import folium
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

import logic as L

st.set_page_config(page_title="한 절 더 · 경주 사찰 순례길", page_icon="🪷", layout="centered",
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
    SS.retold = {}
    SS.virtual = {}


def md(s: str):
    """HTML 카드 출력. 줄바꿈·들여쓰기를 지워서 마크다운이 코드 블록으로 착각하지 않게 해요."""
    st.markdown(re.sub(r"\n[ \t]*", "", s), unsafe_allow_html=True)


def choice(label, options, default, key):
    md(f"<div class='q'>{label}</div>")
    if hasattr(st, "pills"):
        v = st.pills(label, options, default=default, key=key, label_visibility="collapsed")
    else:
        v = st.radio(label, options, index=options.index(default), key=key, horizontal=True,
                     label_visibility="collapsed")
    return v or default


def chip(text, kind=""):
    return f"<span class='chip {kind}'>{E(str(text))}</span>"


def name(pid):
    return places.loc[pid, "name"]


# ---------------------------------------------------------------- 사이드바 (발표·테스트 설정)
with st.sidebar:
    md("### 🎛️ 발표·테스트 설정")
    st.caption("화면에는 안 보여요. 발표 때 상황을 바꿔 보는 곳이에요.")
    ids = list(places.index)
    pick = st.selectbox("QR 찍은 것처럼 시작하기", ids, index=ids.index(SS.start), format_func=name)
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
    show_example = False
    if real_spots.empty:
        show_example = st.toggle("예시 쉼터 보기 (실제 가게 아님)", value=True,
                                 help="rest_spots.csv를 채우면 이 설정은 사라지고 실제 쉼터가 나와요.")
    md("---")
    md("**🤖 AI 연결**")
    st.caption("Claude 연결됨 ✅" if L.llm_ready() else "API 키 없음 → 규칙 기반으로 동작 중")
    md("---")
    md("**🖨️ QR 만들기**")
    url = st.text_input("앱 주소", placeholder="https://○○○.streamlit.app")
    qr_place = st.selectbox("QR 붙일 곳", ids, index=ids.index("bunhwangsa"), format_func=name, key="qr_place")
    if url:
        import qrcode
        img = qrcode.make(f"{url.rstrip('/')}/?temple={qr_place}")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=160)
        st.download_button("QR 내려받기", buf.getvalue(), file_name=f"qr_{qr_place}.png", mime="image/png")

now = datetime.now(L.KST)
if t != "지금":
    hh, mm = map(int, t.split(":"))
    now = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
cond = L.get_conditions(demo_weather, demo_month, now)


def spots_for(stop_ids):
    if not real_spots.empty:
        return real_spots
    return L.example_rest_spots(places, stop_ids) if show_example else real_spots


# ---------------------------------------------------------------- 공통 조각
def speak(text: str, label="🔊 들려주기"):
    components.html(f"""
      <button id="b" style="border:none;border-radius:999px;padding:10px 18px;font-weight:700;font-size:15px;
        color:#fff;cursor:pointer;background:linear-gradient(135deg,#9FD0AE,#7DBB92);
        box-shadow:0 6px 16px rgba(125,187,146,.35);font-family:-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif">
        {label}</button>
      <script>
        const t = {json.dumps(text)};
        document.getElementById('b').onclick = () => {{
          speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(t); u.lang = 'ko-KR'; u.rate = 0.95;
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
    st_folium(m, height=height, use_container_width=True, returned_objects=[], key=f"map_{'_'.join(stops)}_{len(done or [])}")


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
        badge = " · <b>제휴 예정</b>" if s.get("partner") == "후보" else (" · <b>제휴</b>" if s.get("partner") == "제휴" else "")
        coupon = f" · 🎟️ {E(s['coupon'])}" if s.get("coupon") else ""
        link = L.kakao_to(s["name"], s["lat"], s["lon"])
        out.append(f"<span class='rest'>☕ {E(s['name'])} <span class='muted'>({E(s.get('type', ''))}, "
                   f"{s['dist_km'] * 1000:.0f}m{badge}{coupon})</span> <a href='{link}' target='_blank'>길찾기</a></span>")
    return "".join(out)


def sources_html(sources):
    if not sources:
        return ""
    links = " · ".join(f"<a href='{E(s['url'])}' target='_blank'>{E(s['title'])}</a>" for s in sources)
    return f"<div class='src'>📚 출처: {links}</div>"


def stats_html(items):
    cells = "".join(f"<div class='stat'><div class='v'>{E(v)}</div><div class='l'>{E(l)}</div></div>" for v, l in items)
    return f"<div class='stats'>{cells}</div>"


def dots(n_on, total):
    d = "".join(f"<span class='dot {'on' if i < n_on else ''}'></span>" for i in range(total))
    return f"<div class='dots'>{d}<span class='label'>이야기 조각 {n_on}/{total}</span></div>"


# ---------------------------------------------------------------- 머리
md(f"""<div class="brand"><div class="logo">🪷</div>
  <div><div class="name">한 절 더</div><div class="tag">AI가 짜 주는 경주 사찰 순례길</div></div>
  <div class="wx">{"<br>".join(E(x) for x in L.weather_label(cond).split(" · "))}</div></div>""")

tab_walk, tab_map, tab_log = st.tabs(["🚶 순례", "🗺️ 사찰 지도", "📊 순례 기록"])


# ---------------------------------------------------------------- 순례: 1) 고르기
def make_plan():
    user = {"who": SS.q_who or L.WHO[0], "minutes": L.TIMES[SS.q_time or "2시간"],
            "time_label": SS.q_time or "2시간", "level": SS.q_level or "가볍게", "interest": SS.q_int or "역사"}
    elev = L.elevations(places)
    hills = L.hill_pairs(data["courses"], data["tags"])
    cands, budget, notes = L.plan_candidates(SS.start, user, cond, places, data, elev, hills)
    agent = L.agent_choose(cands, budget, cond, user, places, data)
    chosen = agent["plan"] if agent else cands[0]
    SS.plan_ctx = {"user": user, "cands": cands, "budget": budget, "notes": notes, "elev": elev,
                   "hills": list(hills), "planner": "Claude 에이전트" if agent else "규칙 기반",
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


def setup_view():
    p = places.loc[SS.start]
    first = str(p.story).split("요.")[0] + "요." if "요." in str(p.story) else str(p.story)[:80]
    where = "QR로 찾아오셨어요" if SS.from_qr else "여기서 시작해요"
    md(f"""<div class="card soft">
      <div class="eyebrow">📍 {where}</div>
      <h3>{E(p['name'])} <span class="muted small">{E(str(p.hanja))}</span></h3>
      {chip(p.category, CAT_CHIP.get(p.category, ''))}{chip(p.era, 'line')}
      <p class="small">{E(first)}</p></div>""")
    md("<div class='eyebrow' style='margin-top:6px'>네 가지만 골라 주세요 · 기본값이 골라져 있어서 바로 눌러도 돼요</div>")
    choice("누구랑 걸어요?", L.WHO, L.WHO[0], "q_who")
    choice("시간은 얼마나 있어요?", list(L.TIMES), "2시간", "q_time")
    choice("얼마나 걸을까요?", L.LEVELS, "가볍게", "q_level")
    choice("무엇이 궁금해요?", L.INTERESTS, "역사", "q_int")
    st.write("")
    if st.button("✨ AI에게 순례길 부탁하기", type="primary", width="stretch"):
        with st.spinner("날씨와 해 지는 시각, 길을 살펴보는 중이에요…"):
            make_plan()
        st.rerun()


# ---------------------------------------------------------------- 순례: 2) 추천 보기
def plan_view():
    plan, ctx = SS.plan, SS.plan_ctx
    user = ctx["user"]
    n_pieces = len(plan["stops"])
    planner_chip = chip("🤖 Claude 에이전트가 골랐어요", "lav") if ctx["planner"] == "Claude 에이전트" \
        else chip("🧭 규칙 기반 추천", "line")
    md(f"""<div class="card">
      <div class="eyebrow">오늘의 순례길</div>
      {route_chips(plan['stops'])}
      <div class="stats">
        <div class="stat"><div class="v">{plan['dist_m'] / 1000:.1f}km</div><div class="l">걷는 거리</div></div>
        <div class="stat"><div class="v">{plan['total_min']:.0f}분</div><div class="l">둘러보기 포함</div></div>
        <div class="stat"><div class="v">{n_pieces}개</div><div class="l">이야기 조각</div></div>
      </div>
      <div style="margin-top:8px">{planner_chip}{chip(user['who'], 'peach')}{chip(user['level'], 'sky')}{chip(user['interest'], 'butter')}</div>
      {f"<div class='ai-quote'>💬 {E(ctx['ai_reason'])}</div>" if ctx['ai_reason'] else ""}
      <div style="margin-top:8px">{''.join(f"<div class='reason'>✔️ {E(r)}</div>" for r in plan['reasons'])}
      {''.join(f"<div class='reason'>{E(n)}</div>" for n in ctx['notes'])}</div>
    </div>""")
    route_map(plan)
    spots = spots_for(plan["stops"])
    legs_html = []
    for i, leg in enumerate(plan["legs"]):
        guess = " <span class='muted'>(경사는 어림값)</span>" if leg["guessed"] else ""
        rests = L.rest_near(spots, places, leg["from"], leg["to"], cond)
        legs_html.append(f"""<div class="leg"><div class="n">{i + 1}</div><div>
          <b>{E(name(leg['from']))} → {E(name(leg['to']))}</b><br>
          <span class="muted">{leg['dist_m'] / 1000:.1f}km · 약 {leg['minutes']:.0f}분 · {leg['grade']}{guess}</span>
          {('<div>' + rest_html(rests) + '</div>') if rests else ''}</div></div>""")
    md(f"<div class='card'><div class='eyebrow'>구간별 걷는 시간 (토블러 보행 함수)</div>{''.join(legs_html)}</div>")
    others = [c for c in ctx["cands"] if c["stops"] != plan["stops"]]
    if others:
        with st.expander("다른 길도 있어요"):
            for c in others:
                md(route_chips(c["stops"]) + f"<span class='muted'>약 {c['total_min']:.0f}분 · "
                            f"{c['dist_m'] / 1000:.1f}km</span>")
                if st.button("이 길로 바꾸기", key=f"sw_{c['id']}"):
                    SS.plan = attach_routes(c, user, ctx["elev"], set(map(tuple, ctx["hills"])))
                    SS.plan_ctx["ai_reason"] = ""
                    st.rerun()
    c1, c2 = st.columns([2, 1])
    if c1.button("🚶 이 길로 걷기 시작", type="primary", width="stretch"):
        SS.walk = {"plan": plan, "user": user, "idx": 0, "arrived": [plan["stops"][0]], "missions": [],
                   "walked_m": 0.0, "speed": 1.0, "stopped": None}
        L.log_event(SS.sid, "start", stops=plan["stops"], who=user["who"], level=user["level"],
                    interest=user["interest"], planner=ctx["planner"], rain=cond["rain"], cold=cond["cold"])
        SS.step = "walk"
        st.rerun()
    if c2.button("다시 고르기", width="stretch"):
        SS.step = "setup"
        st.rerun()


# ---------------------------------------------------------------- 순례: 3) 걷기
def story_text(pid, user):
    text, sources, status = L.story_for(pid, user["interest"], places, data)
    k = (pid, user["who"], user["interest"])
    if k not in SS.retold:
        SS.retold[k] = L.retell(text, user["who"])
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
        SS.toast = f"{name(skipped)}을(를) 건너뛰고 {name(new[i + 1])}(으)로 바로 가는 길로 다시 짰어요. 걸음도 천천히 잡았어요."
    else:
        w["speed"] = 0.8
        w["plan"] = attach_routes(w["plan"], w["user"], ctx["elev"], hills, 0.8)
        SS.toast = "마지막 구간이에요. 걸음을 천천히 잡아 시간을 넉넉하게 다시 계산했어요."


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
    badge = {"출처 확인": chip("✔ 출처 확인", ""), "검수 중": chip("검수 중", "butter"),
             "출처 확인 중": chip("출처 확인 중", "line")}[status]
    diff = f"<div class='diff'>🔍 차이 한 줄 · {E(L.diff_line(stops[i - 1], pid, places, data))}</div>" if i > 0 else ""
    en = f"<p class='muted small'><i>{E(str(p.desc_en))}</i></p>" if user["who"] == "외국인 친구와" else ""
    md(f"""<div class="card">
      <div class="eyebrow">지금 여기 · {E(L.piece_title(pid, places, data, i + 1))}</div>
      <h3>{E(p['name'])}</h3>{diff}
      {chip(user['interest'] + ' 이야기', 'butter')}{badge}
      <p>{E(text)}</p>{en}{sources_html(sources)}</div>""")
    speak(text)

    mission = L.mission_for(pid, user["who"], places, data)
    md(f"<div class='card sage'><div class='eyebrow' style='color:#3F7A55'>🎯 현장 미션</div><p>{E(mission)}</p></div>")
    if st.checkbox("미션 완료!", key=f"m_{pid}_{i}"):
        if pid not in w["missions"]:
            w["missions"].append(pid)
    now_s, later_s = L.season_for(pid, cond["month"], data)
    for s in now_s:
        md(f"<div class='card butter'><div class='eyebrow' style='color:#8A6A12'>🌸 {E(s['label'])}이 열렸어요</div>"
                    f"<p>{E(s['text'])}</p></div>")
    for s in later_s:
        months = "·".join(f"{x}월" for x in s["months"])
        md(f"<p class='muted'>🔒 {months}에 다시 오면 여기서 '{E(s['label'])}'이 열려요.</p>")

    if i < len(stops) - 1:
        nxt = stops[i + 1]
        leg = plan["legs"][i]
        seg = f"{pid}>{nxt}"
        boost = ""
        if fixes.get(seg) == "흥미":
            boost = "<div class='reason'>🛠 보완된 구간: 가는 길에 오늘 본 곳과 다른 점 하나를 찾아 말해 보세요.</div>"
        elif fixes.get(seg) in ("체력", "날씨", "동행"):
            boost = "<div class='reason'>🛠 보완된 구간: 아래 쉼터에서 한 번 쉬어 가는 걸 추천해요.</div>"
        rests = L.rest_near(spots_for(stops), places, pid, nxt, cond)
        a, b = places.loc[pid], places.loc[nxt]
        link = L.kakao_from_to(a["name"], a.lat, a.lon, b["name"], b.lat, b.lon)
        md(f"""<div class="card sky">
          <div class="eyebrow" style="color:#3C6E95">다음 장소</div>
          <h3>{E(b['name'])}</h3>
          <span class="muted">{leg['dist_m'] / 1000:.1f}km · 약 {leg['minutes']:.0f}분 · {leg['grade']}</span>
          <div class="teaser">📖 {E(L.teaser(pid, nxt, places, data))}</div>{boost}
          {('<div>' + rest_html(rests) + '</div>') if rests else ''}
          <div class="src" style="margin-top:6px"><a href="{link}" target="_blank">🧭 카카오맵으로 걷는 길 보기</a></div>
        </div>""")
        route_map(plan, height=240, done=w["arrived"])
        if st.button(f"📍 {b['name']}에 도착했어요", type="primary", width="stretch"):
            w["idx"] += 1
            w["arrived"].append(nxt)
            w["walked_m"] += leg["dist_m"]
            L.log_event(SS.sid, "arrive", leg=i, to=nxt, seg=seg, stops=stops)
            st.rerun()
        c1, c2 = st.columns(2)
        if c1.button("😮‍💨 힘들어요, 줄여 주세요", width="stretch"):
            shorten()
            st.rerun()
        with c2.popover("그만둘래요", width="stretch"):
            why = st.radio("왜 멈추셨어요? (코스를 고치는 데 써요)", list(L.STOP_REASONS), key="why")
            if st.button("여기서 마칠게요", key="quit"):
                w["stopped"] = L.STOP_REASONS[why]
                L.log_event(SS.sid, "stop", leg=i, at=pid, seg=seg, reason=w["stopped"], stops=stops)
                SS.step = "done"
                st.rerun()
    else:
        md("<div class='card butter'><h3>🎉 마지막 조각까지 모았어요</h3>"
                    "<p>오늘의 이야기를 순례 일지로 정리해 드릴게요.</p></div>")
        if st.button("📔 순례 마치고 일지 보기", type="primary", width="stretch"):
            L.log_event(SS.sid, "finish", stops=stops)
            SS.step = "done"
            st.rerun()


# ---------------------------------------------------------------- 순례: 4) 일지 · 다음 순례
def done_view():
    w = SS.walk
    lines = L.journal_lines(w, places, data, cond)
    key = ("journal", tuple(w["arrived"]))
    if key not in SS.retold:
        SS.retold[key] = L.polish_journal(lines)
    polished = SS.retold[key]
    pieces = "".join(chip(("✔ " if p in w["arrived"] else "○ ") + name(p), "" if p in w["arrived"] else "line")
                     for p in w["plan"]["stops"])
    body = f"<p>{E(polished)}</p>" if polished else ""
    md(f"""<div class="card soft">
      <div class="eyebrow">📔 나의 순례 일지</div><h3>{E(lines[0])}</h3>
      {route_chips(w['arrived'])}<p class="muted">{E(lines[2])}</p>{pieces}{body}
      {''.join(f"<div class='reason'>{E(l)}</div>" for l in lines[3:])}</div>""")
    full = " ".join(lines[3:])
    speak(polished or full, "🔊 일지 들려주기")

    rec = L.recommend(w["plan"].get("course_id"), w["plan"]["stops"], data, places)
    if rec:
        md("<div class='eyebrow' style='margin-top:8px'>다음 순례 추천 (코스 태그 유사도)</div>")
        for k, label, kind in (("similar", "비슷한 코스", "peach"), ("new", "새로운 코스", "sky")):
            if k not in rec:
                continue
            c = rec[k]["course"]
            md(f"""<div class="card {'sky' if k == 'new' else ''}">{chip(label, kind)}
              <h3>{E(c['title'])}</h3><p class="muted small">{E(c.get('subtitle', ''))}</p>
              {route_chips(c['stops'])}<div class="reason">💡 {E(rec[k]['reason'])}</div></div>""")
            if st.button(f"다음엔 '{c['title']}' 걸어보기", key=f"next_{k}"):
                SS.start, SS.step = c["stops"][0], "setup"
                st.rerun()
    last = w["arrived"][-1]
    rests = L.rest_near(spots_for([last]), places, last, last, cond, limit=3)
    if rests:
        md(f"<div class='card sage'><div class='eyebrow' style='color:#3F7A55'>☕ 순례 끝난 곳 주변 쉼터</div>"
                    f"{rest_html(rests)}</div>")
    if st.button("처음으로", width="stretch"):
        SS.step = "setup"
        st.rerun()


with tab_walk:
    {"setup": setup_view, "plan": plan_view, "walk": walk_view, "done": done_view}[SS.step]()


# ---------------------------------------------------------------- 사찰 지도
with tab_map:
    cats = list(PIN)
    pick_c = st.pills("종류", cats, selection_mode="multi", default=cats, label_visibility="collapsed") \
        if hasattr(st, "pills") else st.multiselect("종류", cats, default=cats)
    shown = places[places["category"].isin(pick_c or cats)]
    m = base_map((35.83, 129.23), 12)
    for pid, p in shown.iterrows():
        pop = f"""<div style="font-family:sans-serif;width:220px"><b>{E(p['name'])}</b><br>
          <span style="color:#8F827B;font-size:12px">{E(str(p.era))} · {E(str(p.category))}</span>
          <p style="font-size:12px;line-height:1.5">{E(str(p.story)[:120])}…</p>
          <a href="{L.kakao_to(p['name'], p.lat, p.lon)}" target="_blank">카카오맵 길찾기</a></div>"""
        folium.Marker([p.lat, p.lon], tooltip=p["name"], popup=folium.Popup(pop, max_width=240),
                      icon=pin(pid, size=22)).add_to(m)
    st_folium(m, height=440, use_container_width=True, returned_objects=[], key="overview")
    legend = "".join(f"<span class='chip line'><span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
                     f"background:{PIN[c][0]};margin-right:5px'></span>{c}</span>" for c in cats)
    md(f"<div>{legend}</div><p class='muted'>사찰·유적 {len(places)}곳 · 좌표: 국가유산청 OpenAPI</p>")


# ---------------------------------------------------------------- 순례 기록 (⑥)
def show_analysis(recs, label):
    o = L.overall(recs)
    seg = L.segment_table(recs, places)
    stopped = int(seg["멈춘 수"].sum()) if not seg.empty else 0
    md(stats_html([(f"{o['starts']}번", "순례 시작"), (f"{o['rate']:.0f}%", "완주율"), (f"{stopped}번", "중간에 멈춤")]))
    if seg.empty:
        st.caption("아직 구간 기록이 없어요.")
        return seg
    rows = []
    for k, (_, r) in enumerate(seg.iterrows()):
        color = "linear-gradient(90deg,#F8A985,#F2896B)" if k == 0 else "linear-gradient(90deg,#BFE0C8,#9CC9A8)"
        why = f" · 멈춘 이유 1위 {E(r['멈춘 이유 1위'])}" if r["멈춘 수"] else ""
        rows.append(f"""<div style="margin:10px 0">
          <div style="display:flex;justify-content:space-between;font-size:.86rem;font-weight:700">
            <span>{E(r['구간'])}</span><span style="color:{'#DD6E4E' if k == 0 else '#3F7A55'}">{r['완주율']:.0f}%</span></div>
          <div style="background:#F6ECE6;border-radius:999px;height:12px;margin:5px 0 3px">
            <div style="width:{r['완주율']:.0f}%;height:12px;border-radius:999px;background:{color}"></div></div>
          <div class="muted small">{r['진입']}명 진입 · {r['도착']}명 도착{why}</div></div>""")
    md(f"<div class='card'><div class='eyebrow'>구간별 완주율 · 낮은 순</div>{''.join(rows)}</div>")
    with st.expander("표로 보기"):
        st.dataframe(seg[["구간", "진입", "도착", "완주율", "멈춘 이유 1위"]], hide_index=True, width="stretch")
    return seg


with tab_log:
    view = st.radio("보기", ["가상 기록 (발표용)", "실제 기록"], horizontal=True, label_visibility="collapsed")
    if view == "실제 기록":
        recs = [r for r in L.load_logs() if not r.get("virtual")]
        st.caption("이 앱에서 실제로 시작·도착·멈춘 기록이에요. (Streamlit Cloud는 앱이 다시 켜지면 기록이 지워져요)")
        if recs:
            show_analysis(recs, "실제")
        else:
            md("<div class='card'><p class='muted'>아직 실제 기록이 없어요. 순례를 시작하고 도착·멈춤을 누르면 여기에 모여요.</p></div>")
    else:
        md("<div class='virtual-banner'>🧪 가상 데이터예요 · 분석과 자동 보완이 어떻게 돌아가는지 보여 주는 시연용</div>")
        fixes = L.load_fixes()
        if st.button("가상 기록 80건 만들기", width="stretch") or "before" not in SS.virtual:
            SS.virtual = {"before": L.make_virtual(80, "before")}
        seg = show_analysis(SS.virtual["before"], "가상")
        if not seg.empty:
            worst = seg.iloc[0]
            md(f"""<div class="card butter">
              <div class="eyebrow" style="color:#8A6A12">🔎 가장 많이 멈춘 구간</div>
              <h3>{E(worst['구간'])}</h3>
              <p>완주율 <b>{worst['완주율']:.0f}%</b> · 멈춘 이유 1위 <b>{E(worst['멈춘 이유 1위'])}</b></p>
              <div class="reason">🛠 자동 보완 제안: {E(L.suggestion(worst))}</div></div>""")
            c1, c2 = st.columns(2)
            if c1.button("🛠 보완 적용하기", type="primary", width="stretch"):
                fixes[worst["seg"]] = worst["멈춘 이유 1위"]
                L.save_fixes(fixes)
                SS.virtual["after"] = L.make_virtual(80, "after", fixes)
                st.rerun()
            if c2.button("보완 되돌리기", width="stretch"):
                L.save_fixes({})
                SS.virtual.pop("after", None)
                st.rerun()
            if "after" in SS.virtual:
                after = L.segment_table(SS.virtual["after"], places)
                row = after[after["seg"] == worst["seg"]]
                before_rate, after_rate = worst["완주율"], (row["완주율"].iloc[0] if not row.empty else 0)
                ob, oa = L.overall(SS.virtual["before"]), L.overall(SS.virtual["after"])
                md("<div class='eyebrow'>보완 전후 비교 (가상)</div>")
                md(stats_html([(f"{before_rate:.0f}% → {after_rate:.0f}%", f"이 구간 완주율 ({after_rate - before_rate:+.0f}%p)"),
                               (f"{ob['rate']:.0f}% → {oa['rate']:.0f}%", f"전체 완주율 ({oa['rate'] - ob['rate']:+.0f}%p)")]))
                st.caption("보완된 구간은 순례 화면에서도 '🛠 보완된 구간' 안내가 붙어요.")

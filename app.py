"""app.py — 한 절 더 (HTML 앱)

화면은 web/index.html, AI 계산은 webapp.py · planner.py · shops.py · journal.py 가 해요.
실행:  streamlit run app.py
QR:    주소 뒤에 ?temple=bunhwangsa 처럼 사찰 id를 붙이면 그 사찰에서 시작해요.
언어:  ?lang=en · ja · zh (기본 한국어)
예전 Streamlit 화면은 app_classic.py 에 있어요.
"""
import importlib
import uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


def _fresh(mod):
    """Streamlit Cloud가 예전 모듈을 기억할 때가 있어서, 파일이 바뀌었으면 새로 불러와요."""
    try:
        mtime = Path(mod.__file__).stat().st_mtime
    except OSError:
        return mod
    if getattr(mod, "_loaded_mtime", None) != mtime:
        mod = importlib.reload(mod)
        mod._loaded_mtime = mtime
    return mod


import i18n as I
import logic as L
import planner as P
import shops as SH
import journal as J
import pins as PN
import webapp as W

I, L, P, SH, J, PN = _fresh(I), _fresh(L), _fresh(P), _fresh(SH), _fresh(J), _fresh(PN)
W = _fresh(W)

st.set_page_config(page_title="한 절 더 · Han Jeol Deo", page_icon="🪷", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
  header[data-testid="stHeader"]{background:transparent;height:0;pointer-events:none}
  header[data-testid="stHeader"] button{pointer-events:auto}
  [data-testid="stSidebarCollapsedControl"],[data-testid="stExpandSidebarButton"]{position:fixed!important;top:6px;left:6px;z-index:1000000!important;
    background:#fff;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.2);opacity:.85}
  [data-testid="stToolbarActions"],[data-testid="stMainMenu"],[data-testid="stAppDeployButton"],[data-testid="stStatusWidget"],[data-testid="stDecoration"],footer{display:none!important}
  [data-testid="stToolbar"]{background:transparent!important;pointer-events:none}
  [data-testid="stToolbar"] button{pointer-events:auto}
  .block-container{padding:0!important;max-width:100%!important}
  [data-testid="stMainBlockContainer"]{padding:0!important}
  [data-testid="stVerticalBlock"]{gap:0!important}
  iframe[title="app.hanjeolde"],iframe[title="hanjeolde"],[data-testid="stCustomComponentV1"]{height:100vh!important;height:100dvh!important;width:100%!important;border:0;display:block}
  .stApp{background:#EEF0EA}
</style>""", unsafe_allow_html=True)

SS = st.session_state
if "sid" not in SS:
    SS.sid = uuid.uuid4().hex[:10]
    ql = st.query_params.get("lang")
    SS.lang = ql if ql in I.LANGS else "ko"
    qp = st.query_params.get("temple") or st.query_params.get("start")
    SS.qr = qp if qp in L.load_places().index else None
    SS.demo = {"weather": "실시간", "time": st.query_params.get("t") or "지금", "month": None}
    SS.done_ids = set()
    SS.resp = None

_app = components.declare_component("hanjeolde", path=str(W.WEB))

# ---- 관리 화면: 키 · 공공데이터 · 사찰 좌표 · QR (사이드바, 또는 주소 끝에 ?admin=1)
def admin_panel():
    st.markdown("### 🔑 API 키 (선택)")
    st.caption("보통은 Streamlit Secrets에 넣어요. 여기 넣으면 지금 접속에서만 써요.")
    st.text_input("기상청 단기예보 키", key="kma_key_input", type="password")
    st.text_input("TourAPI(국문 관광정보 GW) 키", key="tour_key_input", type="password")
    st.text_input("Google Places 키 (평점·리뷰)", key="google_key_input", type="password")
    st.text_input("네이버 API HUB Client ID", key="naver_id_input", type="password")
    st.text_input("네이버 API HUB Client Secret", key="naver_secret_input", type="password")
    kv, kn = L.secret_status("kma")
    tv, tn = L.secret_status("tour")
    gv, gn = SH.google_key()
    st.caption("🤖 Claude: " + ("연결됨 ✅" if L.llm_ready() else "키 없음 → 규칙 AI"))
    st.caption("🌦️ 기상청: " + ("있음 ✅" if kv else f"없음 · {kn}"))
    st.caption("🏪 TourAPI: " + ("있음 ✅" if tv else f"없음 · {tn}"))
    st.caption("⭐ Google Places: " + ("있음 ✅" if gv else "없음"))
    st.caption("🟢 네이버 검색: " + ("있음 · 아래 '연결 확인'으로 테스트" if SH.naver_keys()[0] else "없음"))
    if SH.naver_keys()[0] and st.button("네이버 연결 확인"):
        st.caption("🟢 네이버: " + SH.naver_check())
    st.markdown("---")
    st.markdown("**📡 경주시 공공데이터 (가게 추천)**")
    st.caption("키는 TourAPI 키와 같은 공공데이터포털 키를 자동으로 써요. 요청주소는 비워 두면 기본값을 써요.")
    with st.expander("요청주소 직접 넣기 (선택)"):
        st.text_input("전망 좋은 카페 요청주소", key="gj_view_cafe_url_input", placeholder=SH.GJ_SOURCES["view_cafe"][1])
        st.text_input("디저트점 현황 요청주소", key="gj_dessert_url_input", placeholder="https://apis.data.go.kr/5050000/…")
        st.text_input("이색체험 정보 요청주소", key="gj_experience_url_input", placeholder="https://apis.data.go.kr/5050000/…")
    if st.button("불러오기 확인"):
        for name, msg in SH.gj_check():
            st.caption(f"{name}: {msg}")
    st.caption("좌표가 없는 가게는 주소로 위치를 찾아야 지도에 나와요. (카카오 키가 있으면 빨라요)")
    if st.button("가게 주소 → 좌표 만들기"):
        bar = st.progress(0.0, text="준비 중…")
        ok, n, total = SH.gj_build_geo(lambda f, nm: bar.progress(min(1.0, f), text=f"{nm} 찾는 중…"))
        st.success(f"새로 찾은 곳 {ok}/{n} · 저장된 좌표 {total}곳")
        if SH.GJ_GEO_FILE.exists():
            st.download_button("gj_geo.json 받기 (GitHub data 폴더에 올리면 계속 유지돼요)", SH.GJ_GEO_FILE.read_bytes(), "gj_geo.json", "application/json")
    st.markdown("---")
    st.markdown("**🛕 사찰 좌표 만들기 (종교시설 현황)**")
    n_extra = int(L.load_places().index.str.startswith("tp").sum())
    st.caption(f"지금 앱에 들어 있는 곳: {len(L.load_places())}곳 (종교시설 현황에서 더한 절 {n_extra}곳)")
    st.text_input("카카오 REST API 키 (없으면 OpenStreetMap으로 5~6분)", key="kakao_rest_input", type="password")
    if st.button("주소 → 좌표 변환 시작"):
        import geocode
        bar = st.progress(0.0, text="시작해요")
        ok, total = geocode.run(st.session_state.get("kakao_rest_input") or None,
                                lambda i, n, nm, hit: bar.progress(i / n, text=f"{i}/{n} {'✓' if hit else '✗'} {nm}"))
        st.cache_data.clear()
        st.success(f"{ok}/{total}곳 좌표를 찾았어요. 아래 파일을 GitHub의 data 폴더에 올리면 계속 써요.")
        st.download_button("temples_geo.csv 내려받기", (W.WEB.parent / "data" / "temples_geo.csv").read_bytes(), file_name="temples_geo.csv")
    st.markdown("---")
    st.markdown("**🖨️ QR 만들기**")
    url = st.text_input("앱 주소", placeholder="https://○○○.streamlit.app")
    places = L.load_places()
    ids = [p for p in places.index if p != "campus"]
    qr_place = st.selectbox("QR 붙일 곳", ids, index=ids.index("bunhwangsa"), format_func=lambda p: places.loc[p, "name"])
    qr_lang = st.selectbox("QR 언어", I.LANGS, format_func=lambda x: I.LANG_NAMES[x])
    if url:
        import io
        import qrcode
        link = f"{url.rstrip('/')}/?temple={qr_place}" + (f"&lang={qr_lang}" if qr_lang != "ko" else "")
        buf = io.BytesIO()
        qrcode.make(link).save(buf, format="PNG")
        st.image(buf.getvalue(), width=160)
        st.caption(link)
        st.download_button("QR 내려받기", buf.getvalue(), file_name=f"qr_{qr_place}_{qr_lang}.png", mime="image/png")



ADMIN = st.query_params.get("admin") in ("1", "true", "yes")
if ADMIN:
    st.markdown("<style>.block-container{padding:2rem 1.2rem!important;max-width:760px!important}</style>", unsafe_allow_html=True)
    st.title("🛠️ 한 절 더 · 관리 화면")
    st.caption("앱 화면으로 돌아가려면 주소 끝의 ?admin=1 을 지우세요.")
    admin_panel()
    st.stop()
with st.sidebar:
    admin_panel()

# ---- 화면에서 온 요청 처리
req = SS.get("hj")
if isinstance(req, dict) and req.get("id") and req["id"] not in SS.done_ids:
    SS.done_ids.add(req["id"])
    kind = req.get("kind")
    if kind == "lang" and req.get("payload", {}).get("lang") in I.LANGS:
        SS.lang = req["payload"]["lang"]
        SS.shop_cache = {}
        SS.resp = {"id": req["id"], "kind": kind, "data": {"ok": True}}
    elif kind == "demo":
        SS.demo.update({k: v for k, v in (req.get("payload") or {}).items() if k in ("weather", "time", "month")})
        SS.shop_cache = {}
        SS.resp = {"id": req["id"], "kind": kind, "data": {"ok": True}}
    else:
        cond = W.conditions(SS.demo)
        SS.resp = {"id": req["id"], "kind": kind, "data": W.handle(req, cond, SS.lang)}

cond = W.conditions(SS.demo)
_app(bundle=W._plain(W.bundle(SS.lang)), cond=W._plain(W.cond_json(cond, SS.lang)), resp=SS.resp, qr=SS.qr, demo=SS.demo,
     llm=L.llm_ready(), key="hj", default=None)

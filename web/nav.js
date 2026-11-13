/* 실시간 길 안내 — 지도 앱처럼 내 위치(GPS)를 따라가며 다음 사찰까지 안내하고, 도착하면 이야기를 들려줘요. */
"use strict";
const NAV_TX = {
  ko: { start: "🧭 지도로 길 안내 시작", to: "{n}까지", left: "남은 거리 {d} · 약 {m}분", eta: "{t} 도착 예정", me: "내 위치", sim: "▶ 시연: 따라 걷기",
        simstop: "⏸ 시연 멈춤", gps_wait: "내 위치를 찾고 있어요… (위치 권한을 허용해 주세요)", gps_no: "위치를 쓸 수 없어요. 휴대폰 설정에서 위치 권한을 켜거나, 시연으로 따라 걸어 보세요.",
        off: "길에서 벗어났어요. 새 길을 찾는 중…", rerouted: "새 길로 안내할게요", arrived: "📍 {n}에 도착했어요!", then: "그다음", near_t: "☕ 근처 쉬어 갈 곳", close: "안내 끝내기",
        arrive_btn: "도착했어요", near_none: "걸어갈 만한 가게를 아직 못 찾았어요.", near_more: "네이버 지도에서 근처 카페 더 보기", acc: "GPS 정확도 ±{m}m", follow: "따라가기" },
  en: { start: "🧭 Start live navigation", to: "to {n}", left: "{d} left · about {m} min", eta: "Arrive around {t}", me: "My location", sim: "▶ Demo: walk the route",
        simstop: "⏸ Stop demo", gps_wait: "Finding your location… (please allow location access)", gps_no: "Location unavailable. Turn on location permission, or try the demo walk.",
        off: "You're off the route. Finding a new one…", rerouted: "New route ready", arrived: "📍 You've arrived at {n}!", then: "Then", near_t: "☕ Places to rest nearby", close: "End navigation",
        arrive_btn: "I'm here", near_none: "No shops found within walking distance yet.", near_more: "More cafés nearby on Naver Map", acc: "GPS accuracy ±{m} m", follow: "Follow" },
  ja: { start: "🧭 地図で道案内を開始", to: "{n}まで", left: "残り{d} · 約{m}分", eta: "{t}到着予定", me: "現在地", sim: "▶ デモ：ルートを歩く",
        simstop: "⏸ デモ停止", gps_wait: "現在地を探しています…（位置情報を許可してください）", gps_no: "位置情報が使えません。位置情報の許可をオンにするか、デモで歩いてみてください。",
        off: "ルートから外れました。新しい道を探しています…", rerouted: "新しい道で案内します", arrived: "📍 {n}に到着しました！", then: "その次", near_t: "☕ 近くの休憩スポット", close: "案内を終了",
        arrive_btn: "着きました", near_none: "歩いて行ける店がまだ見つかりません。", near_more: "NAVER地図で近くのカフェをもっと見る", acc: "GPS精度 ±{m}m", follow: "追従" },
  zh: { start: "🧭 开始地图导航", to: "前往{n}", left: "剩余{d} · 约{m}分钟", eta: "预计{t}到达", me: "我的位置", sim: "▶ 演示：沿路线走",
        simstop: "⏸ 停止演示", gps_wait: "正在定位…（请允许位置权限）", gps_no: "无法使用位置。请开启定位权限，或试试演示。",
        off: "已偏离路线，正在重新规划…", rerouted: "已为您规划新路线", arrived: "📍 已到达{n}！", then: "然后", near_t: "☕ 附近可休息的地方", close: "结束导航",
        arrive_btn: "我到了", near_none: "附近暂未找到步行可达的店。", near_more: "在NAVER地图查看更多附近咖啡馆", acc: "GPS精度 ±{m}米", follow: "跟随" },
};
const Nav = (() => {
  let map = null, me = null, meRing = null, line = null, doneLine = null, watchId = null, simTimer = null, follow = true, wake = null;
  let pts = [], cum = [], total = 0, man = [], dest = null, destName = "", offCount = 0, rerouting = false, lastProg = 0, arrivedFlag = false;
  const T = (k, kw) => { const d = NAV_TX[lang()] || NAV_TX.ko; let s = d[k] || NAV_TX.ko[k] || k; if (kw) for (const q in kw) s = s.split("{" + q + "}").join(kw[q]); return s; };
  const R = 6371000;
  function xy(lat, lon, lat0) { return [(lon * Math.PI / 180) * R * Math.cos(lat0 * Math.PI / 180), (lat * Math.PI / 180) * R]; }
  function dist(a, b) { const p = xy(a[0], a[1], a[0]), q = xy(b[0], b[1], a[0]); return Math.hypot(p[0] - q[0], p[1] - q[1]); }
  function setLine(coords) {
    pts = coords.map((c) => [c[0], c[1]]);
    cum = [0];
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + dist(pts[i - 1], pts[i]));
    total = cum[cum.length - 1] || 1;
  }
  function project(p) {   // 선 위에서 가장 가까운 점까지 거리와, 출발점에서 그 점까지 거리(진행도)
    let best = { d: Infinity, prog: 0, pt: pts[0] };
    const lat0 = p[0];
    const P0 = xy(p[0], p[1], lat0);
    for (let i = 1; i < pts.length; i++) {
      const A = xy(pts[i - 1][0], pts[i - 1][1], lat0), Bq = xy(pts[i][0], pts[i][1], lat0);
      const dx = Bq[0] - A[0], dy = Bq[1] - A[1], L2 = dx * dx + dy * dy;
      let t = L2 ? ((P0[0] - A[0]) * dx + (P0[1] - A[1]) * dy) / L2 : 0;
      t = Math.max(0, Math.min(1, t));
      const X = A[0] + t * dx, Y = A[1] + t * dy, d = Math.hypot(P0[0] - X, P0[1] - Y);
      if (d < best.d) best = { d, prog: cum[i - 1] + t * (cum[i] - cum[i - 1]), pt: [pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])] };
    }
    return best;
  }
  function pointAt(prog) {
    for (let i = 1; i < pts.length; i++) if (cum[i] >= prog) { const t = (prog - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]); return [pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])]; }
    return pts[pts.length - 1];
  }
  const fmtD = (m) => (m >= 1000 ? (m / 1000).toFixed(1) + "km" : Math.max(0, Math.round(m / 10) * 10) + "m");

  function open() {
    const w = S.walk, i = w.idx, lg = w.route.legs[i];
    if (!lg) return;
    const a = P(lg.from), b = P(lg.to);
    dest = [b.lat, b.lon]; destName = b.name; arrivedFlag = false; offCount = 0; follow = true; lastProg = 0;
    setLine(lg.coords && lg.coords.length > 1 ? lg.coords : [[a.lat, a.lon], [b.lat, b.lon]]);
    man = (lg.steps || []).filter((s) => s && s.lat != null).map((s) => Object.assign({}, s, { prog: project([s.lat, s.lon]).prog }));
    const ov = document.createElement("div");
    ov.className = "nav"; ov.id = "nav";
    ov.innerHTML = `<div class="navtop"><button class="navx" data-nav="close" aria-label="${esc(T("close"))}">✕</button>
        <div class="navdest">${icon(b.kind, 26)}<div><b>${esc(T("to", { n: b.name }))}</b><span id="navacc"></span></div></div></div>
      <div id="navmap"></div>
      <div class="navpanel"><div class="navnext"><span class="navarrow" id="navarrow">↑</span><div><div class="navin" id="navin">${esc(T("gps_wait"))}</div><div class="navthen" id="navthen"></div></div></div>
        <div class="navleft" id="navleft"></div>
        <div class="navbtns"><button class="mini" data-nav="me">◎ ${esc(T("me"))}</button><button class="mini" data-nav="sim" id="navsim">${esc(T("sim"))}</button>
          <button class="mini" data-nav="near">${esc(T("near_t"))}</button><button class="mini coral" data-nav="arrive">${esc(T("arrive_btn"))}</button></div></div>`;
    $("#frame").appendChild(ov);
    map = L.map("navmap", { zoomControl: false, attributionControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
    L.control.zoom({ position: "topright" }).addTo(map);
    line = L.polyline(pts, { color: "#2F7BD8", weight: 8, opacity: 0.85 }).addTo(map);
    doneLine = L.polyline([], { color: "#A9B8C8", weight: 8, opacity: 0.9 }).addTo(map);
    L.marker(dest, { icon: L.divIcon({ html: pinHtml(b.kind, i + 2, false), className: "", iconSize: [34, 44], iconAnchor: [17, 43] }) }).addTo(map);
    L.marker([a.lat, a.lon], { icon: L.divIcon({ html: pinHtml(a.kind, i + 1, true), className: "", iconSize: [34, 44], iconAnchor: [17, 43] }) }).addTo(map);
    map.fitBounds(pts, { padding: [40, 40] });
    map.on("dragstart", () => { follow = false; });
    updatePanel(0, null);
    startGps();
    try { if (navigator.wakeLock) navigator.wakeLock.request("screen").then((l) => { wake = l; }).catch(() => {}); } catch (e) { /* */ }
  }
  function startGps() {
    if (!navigator.geolocation) { $("#navin").textContent = T("gps_no"); return; }
    watchId = navigator.geolocation.watchPosition(
      (p) => { if (!simTimer) onPos(p.coords.latitude, p.coords.longitude, p.coords.accuracy, p.coords.heading); },
      () => { if (!simTimer) $("#navin").textContent = T("gps_no"); },
      { enableHighAccuracy: true, maximumAge: 2000, timeout: 15000 });
  }
  function onPos(lat, lon, acc, heading) {
    if (!map || arrivedFlag) return;
    const p = [lat, lon];
    if (!me) {
      meRing = L.circle(p, { radius: Math.max(5, acc || 10), color: "#2F7BD8", weight: 1, fillOpacity: 0.12 }).addTo(map);
      me = L.marker(p, { icon: L.divIcon({ html: `<div class="medot"><i></i></div>`, className: "", iconSize: [26, 26], iconAnchor: [13, 13] }), zIndexOffset: 1000 }).addTo(map);
    } else { me.setLatLng(p); meRing.setLatLng(p).setRadius(Math.max(5, acc || 10)); }
    if (heading != null && !isNaN(heading)) { const el = me.getElement(); if (el) el.querySelector(".medot").style.setProperty("--h", heading + "deg"); }
    $("#navacc").textContent = acc ? T("acc", { m: Math.round(acc) }) : "";
    const pr = project(p);
    const prog = Math.max(lastProg - 30, pr.prog);   // 뒤로 크게 튀지 않게
    lastProg = prog;
    doneLine.setLatLngs(pts.filter((_, k) => cum[k] <= prog).concat([pr.pt]));
    if (follow) map.setView(p, Math.max(map.getZoom(), 17), { animate: true });
    if (dist(p, dest) < 35 || total - prog < 20) { arrivedAuto(); return; }
    if (pr.d > 45 && (!acc || acc < 60)) { offCount++; if (offCount >= 3) reroute(p); } else offCount = 0;
    updatePanel(prog, p);
  }
  function arrowFor(text) {
    if (/왼쪽|left|左/.test(text)) return /살짝|Bear|やや|稍/.test(text) ? "↖" : "↰";
    if (/오른쪽|right|右/.test(text)) return /살짝|Bear|やや|稍/.test(text) ? "↗" : "↱";
    if (/도착|Arrive|到着|到达/.test(text)) return "📍";
    if (/되돌아|U-turn|引き返|掉头/.test(text)) return "↶";
    return "↑";
  }
  function updatePanel(prog, p) {
    const left = Math.max(0, total - prog);
    const mins = Math.max(1, Math.round(left / 70));   // 시속 약 4.2km
    const eta = new Date(Date.now() + mins * 60000);
    $("#navleft").innerHTML = `<b>${esc(T("left", { d: fmtD(left), m: mins }))}</b><span>${esc(T("eta", { t: hhmm(eta) }))}</span>`;
    if (!p && !simTimer) return;
    const nx = man.find((s) => s.prog > prog + 8) || man[man.length - 1];
    if (nx) {
      const dd = Math.max(0, nx.prog - prog);
      $("#navin").innerHTML = `${dd > 15 ? `<b>${fmtD(dd)}</b> ` : ""}${esc(nx.text)}`;
      $("#navarrow").textContent = arrowFor(nx.text);
      const k = man.indexOf(nx), th = man[k + 1];
      $("#navthen").textContent = th ? `${T("then")}: ${th.text}` : "";
    }
  }
  async function reroute(p) {
    if (rerouting) return;
    rerouting = true; offCount = 0;
    $("#navthen").textContent = T("off");
    try {
      const url = `https://routing.openstreetmap.de/routed-foot/route/v1/driving/${p[1]},${p[0]};${dest[1]},${dest[0]}?overview=full&geometries=geojson`;
      const r = await fetch(url).then((res) => res.json());
      const c = r.routes[0].geometry.coordinates.map((q) => [q[1], q[0]]);
      setLine(c);
    } catch (e) { setLine([p, dest]); }
    man = [{ text: x("walked_to", { n: destName }) || destName, lat: dest[0], lon: dest[1], prog: total }];
    line.setLatLngs(pts); doneLine.setLatLngs([]); lastProg = 0;
    toast(T("rerouted"));
    rerouting = false;
  }
  function arrivedAuto() {
    if (arrivedFlag) return;
    arrivedFlag = true;
    try { if (navigator.vibrate) navigator.vibrate([120, 60, 120]); } catch (e) { /* */ }
    toast(T("arrived", { n: destName }));
    close();
    arrive();
    render();
    setTimeout(() => { const s = S.walk && S.walk.route.stops[S.walk.idx]; if (s) speak(s.story); }, 600);   // 도착하면 이야기 이어 듣기 (지오펜스)
  }
  function simulate() {
    const btn = $("#navsim");
    if (simTimer) { clearInterval(simTimer); simTimer = null; btn.textContent = T("sim"); return; }
    btn.textContent = T("simstop");
    let prog = lastProg;
    simTimer = setInterval(() => {
      prog += 14;
      const q = pointAt(prog);
      onPos(q[0] + (Math.random() - 0.5) * 0.00003, q[1] + (Math.random() - 0.5) * 0.00003, 8, null);
      if (arrivedFlag || prog > total + 30) { clearInterval(simTimer); simTimer = null; }
    }, 500);
  }
  let shopLayer = null;
  function clearShops() { if (shopLayer && map) { map.removeLayer(shopLayer); } shopLayer = null; }
  function showNearby(d) {
    if (!map) return false;
    clearShops();
    shopLayer = L.layerGroup().addTo(map);
    (d.near || []).forEach((s) => L.marker([s.lat, s.lon], { icon: L.divIcon({ html: `<div class="shopdot">${KIND_EMOJI[s.kind] || "📍"}</div>`, className: "", iconSize: [24, 24], iconAnchor: [12, 12] }) }).bindTooltip(s.name).addTo(shopLayer));
    let sh = $("#navnear");
    if (!sh) { sh = document.createElement("div"); sh.id = "navnear"; sh.className = "navnear"; $("#nav").appendChild(sh); }
    sh.innerHTML = `<div class="between"><b>${esc(T("near_t"))}</b><button class="mini" data-nav="nearclose">✕</button></div>
      ${d.near && d.near.length ? d.near.map(shopCard).join("") : `<p class="sub">${esc(T("near_none"))}</p>`}
      ${d.search ? `<a class="mini" href="${esc(d.search)}" target="_blank" rel="noopener">N ${esc(T("near_more"))} ›</a>` : ""}`;
    return true;
  }
  function isOpen() { return !!map; }
  function close() {
    if (watchId != null) { try { navigator.geolocation.clearWatch(watchId); } catch (e) { /* */ } watchId = null; }
    if (simTimer) { clearInterval(simTimer); simTimer = null; }
    try { if (wake) wake.release(); } catch (e) { /* */ }
    wake = null;
    if (map) { try { map.remove(); } catch (e) { /* */ } }
    map = null; me = null; meRing = null;
    const ov = $("#nav"); if (ov) ov.remove();
  }
  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-nav]");
    if (!el) return;
    const a = el.dataset.nav;
    if (a === "close") close();
    else if (a === "me") { follow = true; if (me) map.setView(me.getLatLng(), 17); }
    else if (a === "sim") simulate();
    else if (a === "arrive") arrivedAuto();
    else if (a === "near") {   // 길 안내는 그대로 두고, 지금 위치 둘레 가게를 아래에 띄워요
      const w = S.walk;
      const pos = me ? [me.getLatLng().lat, me.getLatLng().lng] : null;
      ask("nearby", { pid: w.stops[w.idx], next: w.stops[w.idx + 1] || null, pos, who: w.who });
    }
    else if (a === "nearclose") { const sh = $("#navnear"); if (sh) sh.remove(); clearShops(); }
  });
  return { open, close, T, showNearby, isOpen };
})();

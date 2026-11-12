/* 순례 엽서 — 앞면은 사진(없으면 그림), 오른쪽은 우표·소인·손글씨 편지 */
"use strict";
const Postcard = (() => {
  const W = 1600, H = 1000;
  const HAND = { ko: "Nanum Pen Script", en: "Gaegu", ja: "Klee One", zh: "Ma Shan Zheng" };
  const SANS = '"Pretendard Variable",Pretendard,"Apple SD Gothic Neo","Noto Sans KR","Hiragino Sans","PingFang SC",sans-serif';

  async function fonts(lang) {
    const fam = HAND[lang] || HAND.ko;
    try {
      await Promise.race([Promise.all([document.fonts.load(`60px "${fam}"`), document.fonts.load(`700 40px ${SANS}`)]),
        new Promise((r) => setTimeout(r, 1500))]);
    } catch (e) { /* 글꼴을 못 받아도 기본 글꼴로 그려요 */ }
    return `"${fam}", cursive`;
  }
  function loadImg(src) {
    return new Promise((res) => { if (!src) return res(null); const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
  }
  function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function wrap(ctx, text, width) {
    const out = []; let cur = "";
    const words = /[぀-ヿ一-鿿]/.test(text) ? Array.from(text) : text.split(/(\s+)/);
    for (const w of words) {
      if (ctx.measureText(cur + w).width > width && cur.trim()) { out.push(cur.trim()); cur = w.trimStart(); } else cur += w;
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  }

  /* 사진이 없을 때 그리는 경주 풍경 */
  function scene(ctx, x, y, w, h, o) {
    const hr = o.date.getHours();
    const g = ctx.createLinearGradient(0, y, 0, y + h);
    const sky = o.rain ? ["#AEB9C2", "#E2E5E3"] : o.cold ? ["#C9DFEE", "#F3F6F8"] : hr >= 16 ? ["#F3A77D", "#FCE4C6"] : ["#A9D6EE", "#FFF2DE"];
    g.addColorStop(0, sky[0]); g.addColorStop(1, sky[1]);
    ctx.fillStyle = g; ctx.fillRect(x, y, w, h);
    if (!o.rain) { ctx.fillStyle = hr >= 16 ? "rgba(255,230,170,.95)" : "rgba(255,248,215,.95)"; ctx.beginPath(); ctx.arc(x + w * 0.74, y + h * 0.27, h * 0.1, 0, Math.PI * 2); ctx.fill(); }
    const hills = [["rgba(120,140,150,.35)", 0.52, 0.06], ["rgba(95,125,110,.45)", 0.6, 0.05], ["rgba(80,110,90,.65)", 0.7, 0.04]];
    hills.forEach(([c, base, amp], k) => {
      ctx.fillStyle = c; ctx.beginPath(); ctx.moveTo(x, y + h);
      for (let i = 0; i <= 40; i++) { const px = x + (w * i) / 40; ctx.lineTo(px, y + h * (base - amp * Math.sin(i / 6 + k * 1.7) - amp * 0.6 * Math.sin(i / 2.3 + k))); }
      ctx.lineTo(x + w, y + h); ctx.closePath(); ctx.fill();
    });
    const field = { 봄: "#B9D9A0", 여름: "#9CC98A", 가을: "#E3C58B", 겨울: "#E9E4DA" }[o.season] || "#C9D9A8";
    ctx.fillStyle = field; ctx.fillRect(x, y + h * 0.78, w, h * 0.22);
    const cx = x + w * 0.42, gy = y + h * 0.8, s = h / 900;
    ctx.fillStyle = "rgba(70,56,50,.88)";
    const k = o.kind;
    if (k === "temple") {
      ctx.beginPath(); ctx.moveTo(cx - 260 * s, gy - 190 * s); ctx.quadraticCurveTo(cx, gy - 300 * s, cx + 260 * s, gy - 190 * s);
      ctx.lineTo(cx + 210 * s, gy - 160 * s); ctx.lineTo(cx - 210 * s, gy - 160 * s); ctx.closePath(); ctx.fill();
      ctx.fillRect(cx - 170 * s, gy - 160 * s, 340 * s, 160 * s);
      ctx.fillStyle = field; ctx.fillRect(cx - 40 * s, gy - 110 * s, 80 * s, 110 * s);
    } else if (k === "tomb") {
      ctx.beginPath(); ctx.ellipse(cx, gy, 260 * s, 150 * s, 0, Math.PI, 0); ctx.fill();
      [-360, 340].forEach((dx) => { ctx.fillRect(cx + dx * s, gy - 160 * s, 14 * s, 160 * s); ctx.beginPath(); ctx.arc(cx + (dx + 7) * s, gy - 180 * s, 50 * s, 0, Math.PI * 2); ctx.fill(); });
    } else if (k === "buddha") {
      ctx.beginPath(); ctx.arc(cx, gy - 330 * s, 70 * s, 0, Math.PI * 2); ctx.globalAlpha = 0.35; ctx.fill(); ctx.globalAlpha = 1;
      ctx.beginPath(); ctx.arc(cx, gy - 330 * s, 42 * s, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.moveTo(cx - 140 * s, gy); ctx.quadraticCurveTo(cx - 130 * s, gy - 270 * s, cx, gy - 280 * s); ctx.quadraticCurveTo(cx + 130 * s, gy - 270 * s, cx + 140 * s, gy); ctx.fill();
    } else if (k === "museum") {
      ctx.beginPath(); ctx.moveTo(cx - 250 * s, gy - 230 * s); ctx.lineTo(cx, gy - 330 * s); ctx.lineTo(cx + 250 * s, gy - 230 * s); ctx.fill();
      for (let i = 0; i < 5; i++) ctx.fillRect(cx - 220 * s + i * 105 * s, gy - 215 * s, 28 * s, 200 * s);
      ctx.fillRect(cx - 250 * s, gy - 20 * s, 500 * s, 20 * s);
    } else {
      const tiers = [[230, 46], [150, 70], [190, 38], [120, 60], [160, 34], [96, 54], [130, 30]];
      let yy = gy;
      ctx.fillRect(cx - 160 * s, yy - 50 * s, 320 * s, 50 * s); yy -= 50 * s;
      tiers.forEach(([tw, th]) => { ctx.fillRect(cx - (tw / 2) * s, yy - th * s, tw * s, th * s); yy -= th * s; });
      ctx.fillRect(cx - 8 * s, yy - 90 * s, 16 * s, 90 * s);
    }
    if (o.rain) { ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.lineWidth = 3; for (let i = 0; i < 90; i++) { const rx = x + ((i * 97) % w), ry = y + ((i * 53) % (h * 0.8)); ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx - 12, ry + 34); ctx.stroke(); } }
    if (o.cold) { ctx.fillStyle = "rgba(255,255,255,.85)"; for (let i = 0; i < 80; i++) { ctx.beginPath(); ctx.arc(x + ((i * 131) % w), y + ((i * 71) % h), 4 + (i % 4), 0, Math.PI * 2); ctx.fill(); } }
  }

  function stamp(ctx, x, y, w, h, o) {
    ctx.save();
    ctx.fillStyle = "#fff"; ctx.shadowColor = "rgba(0,0,0,.18)"; ctx.shadowBlur = 10; ctx.fillRect(x, y, w, h); ctx.shadowBlur = 0;
    ctx.fillStyle = "#FBF6EE";
    const r = 9;
    for (let i = 0; i <= w; i += 26) { ctx.beginPath(); ctx.arc(x + i, y, r, 0, Math.PI * 2); ctx.arc(x + i, y + h, r, 0, Math.PI * 2); ctx.fill(); }
    for (let i = 0; i <= h; i += 26) { ctx.beginPath(); ctx.arc(x, y + i, r, 0, Math.PI * 2); ctx.arc(x + w, y + i, r, 0, Math.PI * 2); ctx.fill(); }
    ctx.fillStyle = o.stampColor || "#E8795A"; ctx.fillRect(x + 18, y + 18, w - 36, h - 36);
    ctx.restore();
    return new Promise((res) => {
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 20 20">${o.stampSvg || ""}</svg>`;
      const img = new Image();
      img.onload = () => { const s = w - 90; ctx.drawImage(img, x + 45, y + 36, s, s); fin(); res(); };
      img.onerror = () => { fin(); res(); };
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
      function fin() {
        ctx.fillStyle = "#fff"; ctx.textAlign = "center";
        ctx.font = `800 26px ${SANS}`; ctx.fillText("한 절 더", x + w / 2, y + h - 58);
        ctx.font = `800 18px ${SANS}`; ctx.fillText("KOREA · GYEONGJU", x + w / 2, y + h - 32);
        ctx.textAlign = "left";
      }
    });
  }

  function postmark(ctx, cx, cy, date) {
    ctx.save(); ctx.strokeStyle = "rgba(90,80,90,.55)"; ctx.fillStyle = "rgba(90,80,90,.6)"; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.arc(cx, cy, 86, 0, Math.PI * 2); ctx.stroke();
    ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx, cy, 70, 0, Math.PI * 2); ctx.stroke();
    ctx.textAlign = "center"; ctx.font = `800 21px ${SANS}`; ctx.fillText("GYEONGJU", cx, cy - 20);
    const d = `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, "0")}.${String(date.getDate()).padStart(2, "0")}`;
    ctx.font = `800 25px ${SANS}`; ctx.fillText(d, cx, cy + 12); ctx.font = `700 17px ${SANS}`; ctx.fillText("HAN JEOL DEO", cx, cy + 40);
    ctx.lineWidth = 4;
    for (let k = 0; k < 4; k++) { ctx.beginPath(); const yy = cy - 36 + k * 24; ctx.moveTo(cx - 100, yy); for (let i = 0; i <= 10; i++) ctx.lineTo(cx - 100 - i * 22, yy + (i % 2 ? 7 : -7)); ctx.stroke(); }
    ctx.restore();
  }

  async function draw(cv, o) {
    cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");
    const hand = await fonts(o.lang);
    ctx.fillStyle = "#FBF6EE"; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "#EADFD2"; ctx.lineWidth = 4; ctx.strokeRect(12, 12, W - 24, H - 24);
    // 앞면 (사진)
    const px = 44, py = 44, pw = 960, ph = H - 88;
    ctx.save(); rr(ctx, px, py, pw, ph, 18); ctx.clip();
    const img = await loadImg(o.photo);
    if (img) {
      const s = Math.max(pw / img.width, ph / img.height);
      const iw = img.width * s, ih = img.height * s;
      ctx.drawImage(img, px + (pw - iw) / 2, py + (ph - ih) / 2, iw, ih);
    } else scene(ctx, px, py, pw, ph, o);
    const g = ctx.createLinearGradient(0, py + ph * 0.55, 0, py + ph);
    g.addColorStop(0, "rgba(0,0,0,0)"); g.addColorStop(1, "rgba(30,20,15,.62)");
    ctx.fillStyle = g; ctx.fillRect(px, py, pw, ph);
    ctx.restore();
    ctx.fillStyle = "#fff"; ctx.shadowColor = "rgba(0,0,0,.35)"; ctx.shadowBlur = 12;
    ctx.font = `76px ${hand}`; ctx.fillText(o.greet, px + 46, py + ph - 128);
    ctx.font = `900 60px ${SANS}`;
    const nm = o.place.length > 16 ? o.place.slice(0, 16) + "…" : o.place;
    ctx.fillText(nm, px + 46, py + ph - 52);
    ctx.shadowBlur = 0;
    ctx.font = `800 22px ${SANS}`; ctx.fillStyle = "rgba(255,255,255,.9)"; ctx.fillText("🪷 HAN JEOL DEO", px + 46, py + 64);
    // 뒷면 (편지)
    ctx.strokeStyle = "#E2D5C7"; ctx.lineWidth = 3; ctx.setLineDash([10, 10]);
    ctx.beginPath(); ctx.moveTo(1050, 80); ctx.lineTo(1050, H - 80); ctx.stroke(); ctx.setLineDash([]);
    await stamp(ctx, 1352, 66, 190, 230, o);
    postmark(ctx, 1238, 190, o.date);
    ctx.fillStyle = "#4B3F3A"; ctx.font = `54px ${hand}`;
    ctx.fillText(o.to, 1090, 380);
    ctx.font = `46px ${hand}`;
    let y = 452;
    const lines = [];
    o.lines.forEach((l) => wrap(ctx, l, 450).forEach((w) => lines.push(w)));
    lines.slice(0, 7).forEach((l) => {
      ctx.fillStyle = "#5B4C46"; ctx.fillText(l, 1094, y);
      ctx.strokeStyle = "#E6DACB"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(1090, y + 14); ctx.lineTo(1560, y + 14); ctx.stroke();
      y += 62;
    });
    ctx.fillStyle = "#4B3F3A"; ctx.font = `46px ${hand}`; ctx.textAlign = "right"; ctx.fillText(o.from, 1556, H - 70); ctx.textAlign = "left";
  }

  function toImg(cv, imgEl) { const url = cv.toDataURL("image/png"); if (imgEl) { imgEl.src = url; imgEl.style.display = "block"; } return url; }
  function download(cv, name, imgEl) {
    const url = toImg(cv, imgEl);
    try { const a = document.createElement("a"); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove(); } catch (e) { /* 이미지로 보여 줘요 */ }
  }
  async function share(cv, imgEl) {
    try {
      const blob = await new Promise((r) => cv.toBlob(r, "image/png"));
      const file = new File([blob], "hanjeolde_postcard.png", { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) { await navigator.share({ files: [file], title: "한 절 더" }); return; }
    } catch (e) { /* */ }
    toImg(cv, imgEl);
  }
  return { draw, download, share };
})();

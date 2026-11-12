"""journal.py — 나만의 순례 일지 (참가서류 5번 ⑤)

걷는 동안 남긴 것(도착 시각 · 한 줄 · 기분 · 사진 · 미션)과 날씨 · 일행 · 모은 이야기 조각을 엮어
'오늘의 이야기'를 만들고, 배지를 주고, 순례 엽서(PNG)를 만들어요.
"""
from __future__ import annotations

import io
import os
from datetime import datetime

import i18n as I
import logic as L
import planner as P

MOODS = ["😊", "😌", "🤩", "🥹", "😮‍💨"]
QUEEN = {"bunhwangsa", "hwangnyongsaji", "seondeok"}


def _dt(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def stats(walk: dict) -> dict:
    st, en = _dt(walk.get("start_ts", "")), _dt(walk.get("end_ts", ""))
    minutes = int((en - st).total_seconds() // 60) if st and en else int(walk["plan"]["total_min"])
    km = walk["walked_m"] / 1000
    steps = int(walk["walked_m"] / 0.7)
    return {"minutes": max(minutes, 1), "km": km, "steps": steps, "kcal": int(steps * 0.04),
            "pieces": len(walk["arrived"]), "total": len(walk["plan"]["stops"]),
            "missions": len(walk["missions"]), "memos": sum(1 for v in walk.get("memos", {}).values() if v),
            "photos": len(walk.get("photos", {}))}


def badges(walk: dict, cond: dict, data, lang) -> list:
    out = []
    done = not walk.get("stopped") and len(walk["arrived"]) == len(walk["plan"]["stops"])
    if done:
        out.append("done")
    if cond.get("rain"):
        out.append("rain")
    if cond.get("cold"):
        out.append("cold")
    en = _dt(walk.get("end_ts", ""))
    if en and 0 <= (cond["sunset"] - en).total_seconds() / 60 <= 60:
        out.append("sunset")
    if len(QUEEN & set(walk["arrived"])) >= 2:
        out.append("queen")
    tg = lambda p, k: P.tags_of(data, p).get("t", {}).get(k, 0)
    if sum(1 for p in walk["arrived"] if tg(p, "architecture") >= 0.8) >= 2:
        out.append("pagoda")
    if sum(1 for p in walk["arrived"] if tg(p, "buddha_art") >= 0.9) >= 2:
        out.append("buddha")
    if walk["missions"] and len(walk["missions"]) >= len(walk["arrived"]):
        out.append("mission")
    if walk.get("used_tired"):
        out.append("slow")
    if sum(1 for v in walk.get("memos", {}).values() if v) >= 2:
        out.append("writer")
    if len(walk.get("photos", {})) >= 2:
        out.append("photo")
    return out


def weather_word(cond, lang):
    if cond.get("rain"):
        return I.t("w_rain", lang)
    if cond.get("cold"):
        return I.t("w_cold", lang)
    if (cond.get("temp") or 0) >= 28:
        return I.t("w_hot", lang)
    return I.t("w_clear", lang)


def story(walk: dict, places, data, cond, lang) -> list:
    """오늘의 이야기 (문단 목록). 키가 있으면 Claude가 다듬어요 (기록에 없는 사실은 금지)."""
    T = lambda _key, **kw: I.t(_key, lang, **kw)
    name = lambda p: L.place_name(p, places, data, lang)
    user = walk["user"]
    stops, arrived = walk["plan"]["stops"], walk["arrived"]
    paras = [T("jn_intro", date=I.date_str(cond["now"], lang), w=weather_word(cond, lang),
               s=I.lab("season", cond["season"], lang), who=I.lab("who_j2", user["who"], lang), start=name(stops[0]))]
    for i, p in enumerate(arrived):
        text, _, _ = L.story_for(p, user["story_interest"], places, data, lang)
        key = L._first_sentence(text, lang)
        at = _dt(walk.get("arrived_at", {}).get(p, ""))
        when = f"{at:%H:%M}" if at else ""
        title = L.piece_title(p, places, data, i + 1, lang)
        if i == 0:
            line = T("jn_first", t=title, n=name(p), k=key)
        else:
            line = T("jn_next", time=when, n=name(p), d=L.diff_line(arrived[i - 1], p, places, data, lang))
        memo = (walk.get("memos", {}).get(p) or "").strip()
        if memo:
            line += " " + T("jn_memo", m=memo)
        mood = walk.get("moods", {}).get(p)
        if mood:
            line += " " + mood
        if p in walk["missions"]:
            line += " " + T("jn_mission", m=L.mission_for(p, user["who"], places, data, lang))
        paras.append(line)
    if walk.get("bored"):
        paras.append(T("jn_swap", n=walk["bored"]))
    if walk.get("stopped"):
        paras.append(I.t("j_stopped", lang, r=I.lab("reason", walk["stopped"], lang)))
    else:
        titles = I.join_list([L.piece_title(p, places, data, i + 1, lang).split("·")[-1].strip()
                              for i, p in enumerate(arrived)], lang)
        paras.append(T("jn_end", n=len(arrived), x=titles))
    locked = []
    for p in stops:
        _, later = L.season_for(p, cond["month"], data, lang)
        locked += [(p, s) for s in later]
    if locked:
        p, s = locked[0]
        months = I.join_list([I.month_name(m, lang) for m in s["months"]], lang)
        paras.append(T("jn_locked", m=months, n=name(p), l=s["label"]))
    return paras


def polish(paras: list, lang) -> list | None:
    if not L.llm_ready():
        return None
    res = L.call_claude([{"role": "user", "content": "\n".join(paras)}],
                        "아래는 사용자가 오늘 걸은 순례 기록이야. 사용자가 남긴 말(따옴표)은 그대로 살리고, 기록에 없는 사실은 절대 더하지 말고 "
                        f"따뜻한 일기처럼 4~6문장으로 다시 써. {I.LLM_LANG[lang]}로. 문단은 줄바꿈으로 나눠.",
                        model=L._secret("FAST_MODEL", "claude-haiku-5-5"), max_tokens=600)
    t = L._text_of(res) if res else ""
    return [x.strip() for x in t.split("\n") if x.strip()] or None


# ---------------------------------------------------------------- 엽서 PNG
FONT_PATHS = {
    "bold": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
             "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf"],
    "regular": ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"],
}
TTC_INDEX = {"ja": 0, "ko": 1, "en": 1, "zh": 2}   # Noto Sans CJK .ttc: JP, KR, SC, TC, HK


def _font(kind, size, lang):
    from PIL import ImageFont
    for p in FONT_PATHS[kind]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=TTC_INDEX.get(lang, 1) if p.endswith(".ttc") else 0)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap(draw, text, font, width):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) > width and cur:
            lines.append(cur)
            cur = ch.lstrip()
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def postcard(walk: dict, places, data, cond, lang, pin_colors: dict) -> bytes:
    from PIL import Image, ImageDraw
    W, H = 1080, 1500
    img = Image.new("RGB", (W, H), (255, 249, 241))
    d = ImageDraw.Draw(img)
    T = lambda _key, **kw: I.t(_key, lang, **kw)
    name = lambda p: L.place_name(p, places, data, lang)
    coral, ink, muted = (242, 137, 107), (75, 63, 58), (143, 130, 123)
    d.rectangle([0, 0, W, 210], fill=(255, 230, 216))
    d.ellipse([W - 260, -120, W + 80, 220], fill=(255, 243, 199))
    d.text((70, 52), "한 절 더", font=_font("bold", 64, "ko"), fill=ink)
    d.text((72, 132), T("pc_sub", date=I.date_str(cond["now"], lang)), font=_font("regular", 30, lang), fill=muted)
    # 경로 그림
    box = (70, 250, W - 70, 760)
    d.rounded_rectangle(box, radius=36, fill=(255, 255, 255), outline=(246, 228, 217), width=3)
    pts = [(places.loc[p, "lat"], places.loc[p, "lon"]) for p in walk["plan"]["stops"]]
    lat0, lat1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lon0, lon1 = min(p[1] for p in pts), max(p[1] for p in pts)
    span = max(lat1 - lat0, (lon1 - lon0) * 0.82, 1e-4)
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    sc = min(box[2] - box[0] - 260, box[3] - box[1] - 140) / span

    def xy(lat, lon):
        return cx + ((lon - (lon0 + lon1) / 2) * 0.82) * sc, cy - (lat - (lat0 + lat1) / 2) * sc
    xys = [xy(*p) for p in pts]
    for (x1, y1), (x2, y2) in zip(xys, xys[1:]):
        d.line([x1, y1, x2, y2], fill=coral, width=10)
    fsmall = _font("bold", 26, lang)
    for i, ((x, y), pid) in enumerate(zip(xys, walk["plan"]["stops"])):
        col = pin_colors.get(places.loc[pid, "category"], "#F7B193").lstrip("#")
        rgb = tuple(int(col[j:j + 2], 16) for j in (0, 2, 4))
        on = pid in walk["arrived"]
        d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=rgb if on else (233, 225, 220), outline=(255, 255, 255), width=6)
        d.text((x, y), str(i + 1), font=_font("bold", 26, "en"), fill=(255, 255, 255), anchor="mm")
        label = name(pid)
        tx = x + 38 if x < cx + 120 else x - 38
        d.text((tx, y), label[:14], font=fsmall, fill=ink, anchor="lm" if x < cx + 120 else "rm")
    # 숫자
    s = stats(walk)
    cells = [(f"{s['km']:.1f}km", T("pc_dist")), (T("min", n=s["minutes"]), T("pc_time")),
             (f"{s['steps']:,}", T("pc_steps")), (f"{s['pieces']}/{s['total']}", T("stat_pieces"))]
    cw = (W - 140) / 4
    for i, (v, l) in enumerate(cells):
        x0 = 70 + i * cw
        d.rounded_rectangle([x0 + 8, 800, x0 + cw - 8, 950], radius=28, fill=(255, 240, 230))
        d.text((x0 + cw / 2, 855), v, font=_font("bold", 40, lang), fill=(221, 110, 78), anchor="mm")
        d.text((x0 + cw / 2, 912), l, font=_font("regular", 24, lang), fill=muted, anchor="mm")
    # 배지
    y = 990
    bs = badges(walk, cond, data, lang)
    if bs:
        bx = 70
        fb = _font("bold", 26, lang)
        for b in bs[:6]:
            txt = I.lab("badge", b, lang)
            w = d.textlength(txt, font=fb) + 44
            if bx + w > W - 70:
                bx, y = 70, y + 62
            d.rounded_rectangle([bx, y, bx + w, y + 50], radius=25, fill=(231, 244, 234))
            d.text((bx + 22, y + 25), txt, font=fb, fill=(63, 122, 85), anchor="lm")
            bx += w + 12
        y += 80
    # 한 줄
    memo = next((walk["memos"][p] for p in walk["arrived"] if walk.get("memos", {}).get(p)), "")
    quote = memo or L.diff_line(walk["arrived"][0], walk["arrived"][-1], places, data, lang) if len(walk["arrived"]) > 1 else memo
    if quote:
        fq = _font("regular", 34, lang)
        for line in _wrap(d, f"“{quote}”", fq, W - 160)[:3]:
            d.text((80, y), line, font=fq, fill=ink)
            y += 50
        y += 10
    # 사진
    photos = [walk["photos"][p] for p in walk["arrived"] if p in walk.get("photos", {})][:3]
    if photos:
        tw = int((W - 140 - 2 * 16) / 3)
        for i, b in enumerate(photos):
            try:
                ph = Image.open(io.BytesIO(b)).convert("RGB")
                ph.thumbnail((tw * 2, tw * 2))
                side = min(ph.size)
                ph = ph.crop(((ph.width - side) // 2, (ph.height - side) // 2, (ph.width + side) // 2, (ph.height + side) // 2))
                ph = ph.resize((tw, tw))
                img.paste(ph, (70 + i * (tw + 16), min(y, H - tw - 90)))
            except Exception:
                continue
    d.text((W / 2, H - 50), T("pc_footer"), font=_font("regular", 24, lang), fill=muted, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

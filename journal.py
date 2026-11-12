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


# ---------------------------------------------------------------- 오늘의 이야기 (동화책 같은 한 편의 일기)
MOOD_WORD = {
    "ko": {"😊": "마음이 환해졌어요", "😌": "마음이 차분히 가라앉았어요", "🤩": "가슴이 두근거렸어요",
           "🥹": "괜히 마음이 뭉클해졌어요", "😮‍💨": "조금 지쳤지만 뿌듯했어요"},
    "en": {"😊": "my heart felt light", "😌": "everything inside me went quiet", "🤩": "my heart was racing",
           "🥹": "I felt strangely moved", "😮‍💨": "I was a little tired, but proud"},
    "ja": {"😊": "心がぱっと明るくなりました", "😌": "心がすっと静かになりました", "🤩": "胸がどきどきしました",
           "🥹": "なぜか胸がじんとしました", "😮‍💨": "少し疲れたけれど、うれしかったです"},
    "zh": {"😊": "心里一下子亮了起来", "😌": "心慢慢静了下来", "🤩": "心怦怦直跳",
           "🥹": "不知为何有些感动", "😮‍💨": "有点累，但很满足"},
}
WHO_PHRASE = {
    "ko": {"혼자": "나는 혼자", "친구": "나는 친구와 함께", "연인": "우리 둘은", "아이와 함께": "나는 아이의 손을 꼭 잡고",
           "어르신과 함께": "나는 어르신과 발을 맞추며", "외국인 친구와": "나는 외국인 친구에게 경주를 보여 주려고", "단체": "우리 일행은"},
    "en": {"혼자": "I set out alone", "친구": "My friend and I set out", "연인": "The two of us set out",
           "아이와 함께": "Holding my child's hand, I set out", "어르신과 함께": "Walking at an elder's pace, we set out",
           "외국인 친구와": "Wanting to show a friend from abroad around, I set out", "단체": "Our group set out"},
    "ja": {"혼자": "わたしはひとりで", "친구": "わたしは友だちと", "연인": "わたしたちふたりは", "아이와 함께": "わたしは子どもの手をぎゅっと握って",
           "어르신과 함께": "わたしはお年寄りと歩幅を合わせながら", "외국인 친구와": "わたしは海外の友だちに慶州を見せたくて", "단체": "わたしたち一行は"},
    "zh": {"혼자": "我一个人", "친구": "我和朋友一起", "연인": "我们两个人", "아이와 함께": "我紧紧牵着孩子的手",
           "어르신과 함께": "我陪着长辈慢慢地", "외국인 친구와": "为了带外国朋友看看庆州，我", "단체": "我们一行人"},
}
STOP_PHRASE = {
    "ko": {"시간": "시간이 빠듯해서", "체력": "다리가 무거워져서", "흥미": "마음이 다른 데로 향해서", "날씨": "날씨가 궂어져서",
           "동행": "함께 온 사람의 사정으로", "기타": "사정이 생겨서"},
    "en": {"시간": "because time ran short", "체력": "because my legs grew heavy", "흥미": "because my mind wandered elsewhere",
           "날씨": "because the weather turned", "동행": "for my companion's sake", "기타": "for my own reasons"},
    "ja": {"시간": "時間が足りなくなって", "체력": "足が重くなって", "흥미": "気持ちがほかへ向いて", "날씨": "天気がくずれて",
           "동행": "連れの都合で", "기타": "事情があって"},
    "zh": {"시간": "因为时间不够了", "체력": "因为腿越来越沉", "흥미": "因为心思飘到了别处", "날씨": "因为天气变了",
           "동행": "因为同伴的情况", "기타": "因为一些原因"},
}


def _sentences(text):
    import re
    return [x.strip() for x in re.split(r"(?<=[.!?。！？])\s*", text or "") if x.strip()]


def _hook(teaser_text, nxt_name):
    """다음 장소 예고에서 '궁금하게 만드는 문장'만 (…에서 이어져요 같은 안내 문장은 뺌)"""
    keep = [s for s in _sentences(teaser_text) if nxt_name not in s and "다음" not in s and "next" not in s.lower()
            and "次の" not in s and "下一" not in s]
    return keep[0] if keep else ""


def _mission_ko(m):
    m = m.strip().rstrip(".")
    return (m[:-1] + "는") if m.endswith("기") else m


def _daypart(dt, lang):
    h = dt.hour if dt else 12
    k = "morning" if h < 11 else "noon" if h < 14 else "afternoon" if h < 17 else "evening"
    return {"ko": {"morning": "아침", "noon": "한낮", "afternoon": "오후", "evening": "해 질 녘"},
            "en": {"morning": "morning", "noon": "midday", "afternoon": "afternoon", "evening": "evening"},
            "ja": {"morning": "朝", "noon": "昼さがり", "afternoon": "午後", "evening": "夕暮れどき"},
            "zh": {"morning": "早晨", "noon": "正午", "afternoon": "午后", "evening": "傍晚"}}[lang][k]


def _scene(cond, lang):
    s = cond["season"]
    if cond.get("rain"):
        k = "rain"
    elif cond.get("cold"):
        k = "cold"
    elif (cond.get("temp") or 0) >= 28:
        k = "hot"
    else:
        k = s
    return {"ko": {"rain": "보슬비가 기와 끝마다 맺히는", "cold": "입김이 하얗게 피어오르는", "hot": "햇볕이 뜨겁게 내리쬐는",
                   "봄": "꽃바람이 살랑이는", "여름": "초록이 짙게 우거진", "가을": "바람이 선선하게 부는", "겨울": "공기가 맑고 차가운"},
            "en": {"rain": "a drizzly", "cold": "a frosty", "hot": "a blazing", "봄": "a breezy spring", "여름": "a green summer",
                   "가을": "a cool autumn", "겨울": "a crisp winter"},
            "ja": {"rain": "小雨が瓦の先にしずくを結ぶ", "cold": "息が白くなる", "hot": "日差しが照りつける", "봄": "花風がそよぐ春の",
                   "여름": "緑の濃い夏の", "가을": "風が涼しい秋の", "겨울": "空気の澄んだ冬の"},
            "zh": {"rain": "细雨挂在瓦檐上的", "cold": "呵气成霜的", "hot": "烈日当空的", "봄": "春风轻拂的", "여름": "绿意正浓的夏日",
                   "가을": "秋风送爽的", "겨울": "空气清冷的冬日"}}[lang].get(k, "")


def story(walk: dict, places, data, cond, lang) -> dict:
    """한 편의 이야기: {"title", "paras"}. 기록(도착·메모·기분·사진·미션·길 바꿈)과 장소 이야기를 엮어 동화처럼 이어 써요."""
    name = lambda p: L.place_name(p, places, data, lang)
    J_ = I.josa
    user = walk["user"]
    stops, arrived = walk["plan"]["stops"], walk["arrived"]
    legs = walk["plan"].get("legs", [])
    events = walk.get("events", [])
    st_dt = _dt(walk.get("start_ts", "")) or cond["now"]
    en_dt = _dt(walk.get("end_ts", ""))
    who = user.get("who", "혼자")
    season = I.lab("season", cond["season"], lang)
    paras = []
    # ---- 여는 문단
    scene = _scene(cond, lang)
    if lang == "ko":
        paras.append(f"{I.date_str(st_dt, lang)}, {scene} {season}날 {_daypart(st_dt, lang)}이었어요. "
                     f"{WHO_PHRASE['ko'].get(who, '나는')} 천 년 전 신라 사람들이 걷던 길을 따라가 보기로 했어요. "
                     + J_(f"첫걸음은 {name(stops[0])}[에서/에서] 시작됐어요.").replace("[에서/에서]", "에서"))
    elif lang == "en":
        paras.append(f"It was {scene} {_daypart(st_dt, lang)} on {I.date_str(st_dt, lang)}. "
                     f"{WHO_PHRASE['en'].get(who, 'I set out')} to follow the paths people of Silla walked a thousand years ago. "
                     f"The first step began at {name(stops[0])}.")
    elif lang == "ja":
        paras.append(f"{I.date_str(st_dt, lang)}、{scene}{'' if season in scene else season + 'の'}{_daypart(st_dt, lang)}でした。"
                     f"{WHO_PHRASE['ja'].get(who, 'わたしは')}、千年前の新羅の人びとが歩いた道をたどってみることにしました。"
                     f"最初の一歩は{name(stops[0])}から始まりました。")
    else:
        paras.append(f"{I.date_str(st_dt, lang)}，一个{scene}{_daypart(st_dt, lang)}。"
                     f"{WHO_PHRASE['zh'].get(who, '我')}决定沿着一千年前新罗人走过的路走一走。第一步，从{name(stops[0])}开始。")
    # ---- 장소마다
    for i, p in enumerate(arrived):
        text, _, _ = L.story_for(p, user.get("story_interest", "역사"), places, data, lang)
        bits = []
        if i == 0:
            bits.append({"ko": f"{name(p)}에서 들은 첫 이야기는 이랬어요. {text}",
                         "en": f"The first story I heard at {name(p)} went like this: {text}",
                         "ja": f"{name(p)}で聞いた最初の物語は、こんなお話でした。{text}",
                         "zh": f"在{name(p)}听到的第一个故事是这样的：{text}"}[lang])
        else:
            prev = arrived[i - 1]
            swap = next((e for e in events if e.get("type") == "swap" and e.get("to") == p), None)
            tired = next((e for e in events if e.get("type") == "tired" and e.get("at") == prev and e.get("skipped")), None)
            leg = legs[i - 1] if i - 1 < len(legs) and legs[i - 1].get("to") == p else None
            mins = int(round(leg["minutes"])) if leg else None
            hill = bool(leg and leg.get("hill"))
            hook = _hook(L.teaser(prev, p, places, data, lang), name(p))
            if lang == "ko":
                if swap:
                    lead = J_(f"원래는 {name(swap['from'])}에 가려고 했지만, 마음이 끌리는 쪽으로 길을 바꿔 {name(p)}[으로/로] 향했어요.")
                elif hook:
                    lead = f"‘{hook}’ {name(prev)}에서 들은 이 말이 자꾸 마음에 남았어요. 그 뒷이야기가 궁금해서 발걸음이 빨라졌어요."
                else:
                    lead = ["발길을 돌려 다음 길로 들어섰어요.", "조금 더 걸어 보기로 했어요.", "길은 천천히 다음 이야기로 이어졌어요."][i % 3]
                if tired:
                    lead = J_(f"다리가 조금 무거워져서 {name(tired['skipped'])}[은/는] 다음으로 미루고, 천천히 걸었어요. ") + lead
                walk_s = (("숨이 조금 차오르는 오르막을 지나 " if hill else "") + (f"{mins}분쯤 걸어 " if mins else "")
                          + f"{name(p)}에 닿았어요.")
                bits += [lead, walk_s, L.diff_line(prev, p, places, data, lang), text]
            elif lang == "en":
                if swap:
                    lead = f"I had meant to go to {name(swap['from'])}, but I followed my heart to {name(p)} instead."
                elif hook:
                    lead = f"“{hook}” Those words from {name(prev)} stayed with me, and I walked faster to hear the rest."
                else:
                    lead = ["I turned onto the next path.", "I decided to walk a little farther.", "The road slowly led on to the next story."][i % 3]
                if tired:
                    lead = f"My legs felt heavy, so I saved {name(tired['skipped'])} for another day and slowed down. " + lead
                walk_s = ("After a short climb, " if hill else "") + (f"about {mins} minutes later " if mins else "") + f"I reached {name(p)}."
                bits += [lead, walk_s[0].upper() + walk_s[1:], L.diff_line(prev, p, places, data, lang), text]
            elif lang == "ja":
                if swap:
                    lead = f"本当は{name(swap['from'])}へ行くつもりでしたが、心のひかれるほうへ道を変えて{name(p)}へ向かいました。"
                elif hook:
                    lead = f"「{hook}」{name(prev)}で聞いたこの言葉がずっと心に残っていました。続きが知りたくて、足が速くなりました。"
                else:
                    lead = ["次の道へと足を向けました。", "もう少し歩いてみることにしました。", "道はゆっくりと次の物語へつながっていきました。"][i % 3]
                if tired:
                    lead = f"足が少し重くなったので、{name(tired['skipped'])}は次の楽しみにとっておき、ゆっくり歩きました。" + lead
                walk_s = ("少し息の上がる坂をこえて、" if hill else "") + (f"{mins}分ほど歩くと" if mins else "") + f"{name(p)}に着きました。"
                bits += [lead, walk_s, L.diff_line(prev, p, places, data, lang), text]
            else:
                if swap:
                    lead = f"本来打算去{name(swap['from'])}，但我顺着心意改道去了{name(p)}。"
                elif hook:
                    lead = f"“{hook}”在{name(prev)}听到的这句话一直留在心里。想知道后来的故事，我加快了脚步。"
                else:
                    lead = ["我转身走上下一段路。", "我决定再往前走一走。", "小路慢慢通向了下一个故事。"][i % 3]
                if tired:
                    lead = f"腿有些沉了，于是把{name(tired['skipped'])}留到下次，放慢了脚步。" + lead
                walk_s = ("爬过一段让人微微喘气的坡，" if hill else "") + (f"走了大约{mins}分钟，" if mins else "") + f"来到了{name(p)}。"
                bits += [lead, walk_s, L.diff_line(prev, p, places, data, lang), text]
        memo = (walk.get("memos", {}).get(p) or "").strip()
        mood = walk.get("moods", {}).get(p)
        if memo:
            bits.append({"ko": f"나는 수첩에 ‘{memo}’라고 적어 두었어요.", "en": f"In my notebook I wrote, “{memo}”.",
                         "ja": f"わたしは手帳に「{memo}」と書きとめました。", "zh": f"我在本子上写下：“{memo}”。"}[lang])
        if mood and mood in MOOD_WORD[lang]:
            bits.append({"ko": f"그 순간 {MOOD_WORD['ko'][mood]}.", "en": f"In that moment, {MOOD_WORD['en'][mood]}.",
                         "ja": f"その瞬間、{MOOD_WORD['ja'][mood]}。", "zh": f"那一刻，{MOOD_WORD['zh'][mood]}。"}[lang])
        if p in walk.get("missions", []):
            m = L.mission_for(p, who, places, data, lang)
            bits.append({"ko": f"‘{_mission_ko(m)}’ 미션도 해냈어요.", "en": f"I even completed the mission: {m[0].lower() + m[1:]}.",
                         "ja": f"「{m}」のミッションもやりとげました。", "zh": f"还完成了任务：{m}。"}[lang])
        if walk.get("photos", {}).get(p):
            bits.append({"ko": "그 장면은 사진 한 장으로 남겼어요.", "en": "I kept that scene in a photo.",
                         "ja": "その場面は一枚の写真に残しました。", "zh": "我把那一幕拍成了一张照片。"}[lang])
        sep = "" if lang in ("ja", "zh") else " "
        paras.append(sep.join(b.strip() for b in bits if b))
    # ---- 닫는 문단
    last = arrived[-1]
    km = walk.get("walked_m", 0) / 1000
    n = len(arrived)
    tt = lambda i, p: L.piece_title(p, places, data, i + 1, lang).split("·")[-1].strip()
    if walk.get("stopped"):
        nxt = stops[len(arrived)] if len(arrived) < len(stops) else None
        why = STOP_PHRASE[lang].get(walk["stopped"], "")
        end = {"ko": J_(f"오늘의 순례는 {name(last)}에서 여기까지 하기로 했어요. {why} 조금 아쉬웠지만, ")
                     + (J_(f"{name(nxt)}의 이야기는 다음에 꼭 듣기로 나 자신과 약속했어요.") if nxt else "괜찮았어요."),
               "en": f"I decided to end today's walk at {name(last)}, {why}. A little sad, but "
                     + (f"I promised myself to hear the story of {name(nxt)} next time." if nxt else "it was fine."),
               "ja": f"今日の巡礼は{name(last)}までにしました。{why}、少し名残惜しかったけれど、"
                     + (f"{name(nxt)}の物語はまた今度きっと聞こうと自分に約束しました。" if nxt else "それでよかったと思います。"),
               "zh": f"今天的巡礼就在{name(last)}画上句号。{why}，有点遗憾，"
                     + (f"但我和自己约好，下次一定要来听{name(nxt)}的故事。" if nxt else "但也很好。")}[lang]
    else:
        first_t, last_t = tt(0, arrived[0]), tt(n - 1, last)
        end = {"ko": f"{_daypart(en_dt, lang) if en_dt else '그날'}, {name(last)}에서 순례를 마쳤어요. 오늘 걸은 길은 {km:.1f}km, "
                     f"모은 이야기 조각은 {n}개. ‘{first_t}’에서 시작한 이야기가 ‘{last_t}’까지 한 줄로 이어졌어요.",
               "en": f"{({'morning': 'In the morning', 'midday': 'At midday', 'afternoon': 'In the afternoon', 'evening': 'In the evening'}[_daypart(en_dt, 'en')]) if en_dt else 'In the end'}, I finished at {name(last)}. {km:.1f} km walked, {n} story pieces gathered — "
                     f"from “{first_t}” to “{last_t}”, they became one story.",
               "ja": f"{_daypart(en_dt, lang) if en_dt else 'その日'}、{name(last)}で巡礼を終えました。歩いた道は{km:.1f}km、集めたかけらは{n}つ。"
                     f"「{first_t}」から始まった物語が「{last_t}」まで一本につながりました。",
               "zh": f"{_daypart(en_dt, lang) if en_dt else '那天'}，我在{name(last)}结束了巡礼。走了{km:.1f}公里，收集了{n}个故事碎片——"
                     f"从“{first_t}”开始的故事，一直连到了“{last_t}”。"}[lang]
    locked = []
    for p in stops:
        _, later = L.season_for(p, cond["month"], data, lang)
        locked += [(p, s) for s in later]
    if locked:
        p, s = locked[0]
        months = I.join_list([I.month_name(m, lang) for m in s["months"]], lang)
        end += ("" if lang in ("ja", "zh") else " ") + {"ko": I.josa(f"{months}[이/가] 되면 {name(p)}에서 ‘{s['label']}’[이/가] 열린대요. 그때 다시 와야겠어요."),
                      "en": f"In {months}, a “{s['label']}” opens at {name(p)}. I'll have to come back then.",
                      "ja": f"{months}になると{name(p)}で「{s['label']}」が開くそうです。そのころ、また来なくちゃ。",
                      "zh": f"听说到了{months}，{name(p)}会开启“{s['label']}”。到时候还要再来。"}[lang]
    end += ("" if lang in ("ja", "zh") else " ") + {"ko": "그러니까 다음엔, 한 절 더.", "en": "So next time — one more temple.",
                  "ja": "だから次は、もう一寺。", "zh": "所以下一次，再多走一寺。"}[lang]
    paras.append(end)
    title = {"ko": f"{season}의 경주, {name(stops[0])}에서 {name(last)}까지", "en": f"{season.capitalize()} in Gyeongju: from {name(stops[0])} to {name(last)}",
             "ja": f"{season}の慶州、{name(stops[0])}から{name(last)}まで", "zh": f"{season}的庆州，从{name(stops[0])}到{name(last)}"}[lang]
    if len(arrived) == 1:
        title = {"ko": f"{season}의 경주, {name(last)}에서", "en": f"{season.capitalize()} in Gyeongju, at {name(last)}",
                 "ja": f"{season}の慶州、{name(last)}にて", "zh": f"{season}的庆州，在{name(last)}"}[lang]
    return {"title": title, "paras": paras}


def polish(st: dict, lang) -> dict | None:
    """Claude(Haiku)가 같은 사실로 동화책처럼 다듬어요. 기록에 없는 사실은 금지."""
    if not L.llm_ready():
        return None
    res = L.call_claude([{"role": "user", "content": st["title"] + "\n\n" + "\n\n".join(st["paras"])}],
                        "아래는 사용자가 오늘 걸은 경주 순례를 엮은 이야기야. 동화책처럼 자연스럽게 이어지는 한 편의 일기로 다듬어 줘. "
                        "규칙: 사용자가 남긴 말(따옴표)은 그대로, 장소 이야기에 나온 사실만 쓰고 새 사실은 절대 더하지 마. "
                        "문단 수는 원문과 같게, 각 문단은 2~5문장. 첫 줄은 제목. "
                        f"{I.LLM_LANG[lang]}로 써.",
                        model=L._secret("FAST_MODEL", "claude-haiku-5-5"), max_tokens=1400)
    t = L._text_of(res) if res else ""
    lines = [x.strip() for x in t.split("\n") if x.strip()]
    if len(lines) < 3:
        return None
    return {"title": lines[0].strip("# "), "paras": lines[1:]}


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

"""romanize.py — 한글 이름을 국어의 로마자 표기법(간단판)으로 바꿔요. 예: 월정사 → Woljeongsa"""

INI = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
MED = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
FIN = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"]
# 받침 뒤에 'ㅇ'으로 시작하는 글자가 오면 소리가 넘어가요 (석암 → Seogam)
LINK = {1: "g", 2: "kk", 4: "n", 7: "d", 8: "r", 16: "m", 17: "b", 19: "s", 20: "ss", 22: "j", 23: "ch", 24: "k", 25: "t", 26: "p", 27: "h"}


def romanize(word: str) -> str:
    out = []
    syl = [ch for ch in str(word)]
    for i, ch in enumerate(syl):
        c = ord(ch) - 0xAC00
        if not 0 <= c < 11172:
            out.append(ch)
            continue
        ini, med, fin = c // 588, (c % 588) // 28, c % 28
        nxt = ord(syl[i + 1]) - 0xAC00 if i + 1 < len(syl) else -1
        nxt_ini = nxt // 588 if 0 <= nxt < 11172 else -1
        head = INI[ini]
        if ini == 5:   # ㄹ: 앞 글자 받침이 ㄹ이면 l, 첫소리면 r
            prev = ord(syl[i - 1]) - 0xAC00 if i > 0 else -1
            head = "l" if 0 <= prev < 11172 and prev % 28 == 8 else "r"
        if ini == 11 and i > 0 and out and out[-1].startswith("§"):   # 넘어온 받침 소리
            head = out.pop()[1:]
        if out and out[-1].startswith("¤"):
            head = out.pop()[1:]
        tail = FIN[fin]
        force = None   # 다음 글자 첫소리를 바꿀 때
        if fin and nxt_ini in (2, 6, 5):   # 콧소리되기·흐름소리되기: 극락→Geungnak, 신라→Silla, 백률→Baengnyul
            if tail == "k":
                tail = "ng"; force = "n" if nxt_ini == 5 else None
            elif tail == "p":
                tail = "m"; force = "n" if nxt_ini == 5 else None
            elif tail == "t":
                tail = "n"; force = "n" if nxt_ini == 5 else None
            elif tail == "n" and nxt_ini == 5:
                tail = "l"; force = "l"
            elif tail == "ng" and nxt_ini == 5 or tail == "m" and nxt_ini == 5:
                force = "n"
        if fin and nxt_ini == 11 and fin in LINK:
            tail = ""
            out.append(head + MED[med])
            out.append("§" + LINK[fin])
            continue
        if fin == 8 and nxt_ini == 5:
            tail = "l"
        out.append(head + MED[med] + tail)
        if force:
            out.append("¤" + force)
    s = "".join(x[1:] if x[:1] in ("§", "¤") else x for x in out)
    return s[:1].upper() + s[1:]


def temple_name(name: str, lang: str) -> str:
    r = romanize(name)
    return f"{r} Temple" if lang == "en" else r


def town_name(town: str) -> str:
    """감포읍 → Gampo-eup, 구황동 → Guhwang-dong"""
    t = str(town or "")
    for suf, r in (("읍", "eup"), ("면", "myeon"), ("동", "dong"), ("리", "ri")):
        if t.endswith(suf) and len(t) > 1:
            return f"{romanize(t[:-1])}-{r}"
    return romanize(t)

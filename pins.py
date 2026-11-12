"""pins.py — 지도 핀 아이콘 (사찰 · 절터 · 석탑 · 불상 · 박물관 · 왕릉 · 명소 · 출발점)"""

ICON_COLOR = {
    "temple": "#F29A76", "ruins": "#8DC49F", "pagoda": "#8DB8E3", "buddha": "#B9A2E0",
    "museum": "#E9B949", "tomb": "#7FB5A8", "landmark": "#F2C14E", "start": "#C7B3E6",
}
W = 'fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
F = 'fill="#fff"'
ICON_SVG = {
    # 기와지붕 절
    "temple": f'<path d="M1.5 8.5 Q10 2.5 18.5 8.5" {W}/><path d="M4 8.5 h12 v1.6 h-12z" {F}/>'
              f'<rect x="5.2" y="10.5" width="2" height="5.5" {F}/><rect x="12.8" y="10.5" width="2" height="5.5" {F}/>'
              f'<rect x="2.5" y="16" width="15" height="2" rx="0.6" {F}/>',
    # 주춧돌만 남은 절터
    "ruins": f'<rect x="3" y="5" width="3" height="9" rx="0.6" {F}/><path d="M6 5 l0.8 -1.6" {W}/>'
             f'<ellipse cx="11" cy="15" rx="2.6" ry="1.4" {F}/><ellipse cx="16" cy="15" rx="2.2" ry="1.3" {F}/>'
             f'<path d="M1.5 17.5 h17" {W}/>',
    # 삼층석탑
    "pagoda": f'<path d="M10 1.5 v3" {W}/><rect x="6.8" y="4.5" width="6.4" height="1.6" rx="0.4" {F}/>'
              f'<rect x="8.2" y="6.1" width="3.6" height="2.4" {F}/><rect x="5.6" y="8.5" width="8.8" height="1.6" rx="0.4" {F}/>'
              f'<rect x="7.6" y="10.1" width="4.8" height="2.6" {F}/><rect x="4.3" y="12.7" width="11.4" height="1.7" rx="0.4" {F}/>'
              f'<rect x="3" y="15.6" width="14" height="2.4" rx="0.6" {F}/>',
    # 앉은 부처님
    "buddha": f'<circle cx="10" cy="5" r="2.6" {F}/><path d="M10 1.4 v-0.6" {W}/>'
              f'<path d="M5 15.5 Q5 8.4 10 8.4 Q15 8.4 15 15.5 z" {F}/>'
              f'<path d="M2.5 17.6 Q10 13.6 17.5 17.6" {W}/>',
    # 박물관
    "museum": f'<path d="M10 2 L18 6.5 H2 Z" {F}/><rect x="3.6" y="7.6" width="1.8" height="7.6" {F}/>'
              f'<rect x="7.4" y="7.6" width="1.8" height="7.6" {F}/><rect x="10.8" y="7.6" width="1.8" height="7.6" {F}/>'
              f'<rect x="14.6" y="7.6" width="1.8" height="7.6" {F}/><rect x="2" y="15.8" width="16" height="2.2" rx="0.5" {F}/>',
    # 왕릉 (봉분)
    "tomb": f'<path d="M2 15.5 Q10 3 18 15.5 z" {F}/><path d="M1 17.6 h18" {W}/>'
            f'<path d="M4.5 12 l-1 -1.6 M15.5 12 l1 -1.6" {W}/>',
    # 정자·명소
    "landmark": f'<path d="M2 8 Q10 3.4 18 8" {W}/><path d="M4.5 8 h11 v1.4 h-11z" {F}/>'
                f'<path d="M6 9.4 v6.4 M14 9.4 v6.4" {W}/><path d="M3 16.4 h14" {W}/>'
                f'<path d="M8 12.6 q2 -1.6 4 0" {W}/>',
    # 출발 깃발
    "start": f'<path d="M5 18 V2.5" {W}/><path d="M5.6 3 h9.4 l-2.6 3.4 2.6 3.4 h-9.4z" {F}/>',
}
LEGEND_ORDER = ["temple", "ruins", "pagoda", "buddha", "museum", "tomb", "landmark", "start"]


def icon_of(pid: str, category: str, name_ko: str) -> str:
    if category == "현존 사찰":
        return "temple"
    if category == "절터":
        return "ruins"
    if category == "불상·석탑":
        if "당간" in name_ko:
            return "ruins"
        return "pagoda" if "탑" in name_ko else "buddha"
    if category == "출발점":
        return "start"
    if pid == "museum" or "박물관" in name_ko:
        return "museum"
    if "릉" in name_ko or "묘" in name_ko:
        return "tomb"
    return "landmark"


def svg_icon(kind: str, size: int = 18, color: str | None = None) -> str:
    """범례·카드에 넣는 작은 원형 아이콘"""
    c = color or ICON_COLOR[kind]
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" style="vertical-align:-4px">'
            f'<circle cx="12" cy="12" r="12" fill="{c}"/><g transform="translate(2,2)">{ICON_SVG[kind]}</g></svg>')


def marker_html(kind: str, number=None, grey=False, size=1.0) -> str:
    """지도 핀 (물방울 모양 + 흰색 아이콘 + 순서 번호)"""
    c = "#D9CFC9" if grey else ICON_COLOR[kind]
    w, h = int(36 * size), int(46 * size)
    badge = ""
    if number is not None:
        badge = (f'<div style="position:absolute;top:-9px;right:-11px;min-width:15px;height:15px;border-radius:8px;'
                 f'background:#4B3F3A;color:#fff;font:700 10px/15px sans-serif;text-align:center;'
                 f'border:1.5px solid #fff;padding:0 1px">{number}</div>')
    return (f'<div style="position:relative;width:{w}px;height:{h}px;filter:drop-shadow(0 3px 4px rgba(90,60,40,.3))">'
            f'<svg width="{w}" height="{h}" viewBox="0 0 36 46">'
            f'<path d="M18 45 C18 45 3 28.5 3 17 A15 15 0 1 1 33 17 C33 28.5 18 45 18 45 Z" fill="{c}" stroke="#fff" stroke-width="2.5"/>'
            f'<g transform="translate(8,7)">{ICON_SVG[kind]}</g></svg>{badge}</div>')

"""areas.py — 절이 경주시 어디에 있는지 권역으로 묶어요 (QR 고르기 화면용).

주소에 읍·면이 있으면 그 읍·면으로, 동 지역(시내)은 좌표가 가장 가까운 권역으로 나눠요.
"""
from __future__ import annotations

import math
import re

# 권역: (key, 4개 언어 이름, 이모지)
AREAS = [
    ("downtown", {"ko": "경주 시내 · 대릉원·황리단길", "en": "Downtown · Daereungwon", "ja": "市内・大陵苑", "zh": "市区·大陵苑"}, "🏙️"),
    ("hwangnyong", {"ko": "황룡사·분황사 · 낭산", "en": "Hwangnyongsa · Bunhwangsa", "ja": "皇龍寺・芬皇寺", "zh": "皇龙寺·芬皇寺"}, "🛕"),
    ("namsan", {"ko": "경주 남산", "en": "Namsan Mountain", "ja": "慶州南山", "zh": "庆州南山"}, "⛰️"),
    ("bulguk", {"ko": "불국사·토함산", "en": "Bulguksa · Tohamsan", "ja": "仏国寺・吐含山", "zh": "佛国寺·吐含山"}, "🏯"),
    ("bomun", {"ko": "보문관광단지", "en": "Bomun Resort", "ja": "普門観光団地", "zh": "普门旅游区"}, "🌸"),
    ("west_city", {"ko": "서악·선도산 · 서천 서쪽", "en": "Seoak · Seondosan", "ja": "西岳・仙桃山", "zh": "西岳·仙桃山"}, "🌄"),
    ("north_city", {"ko": "동천·용강·황성 (시내 북쪽)", "en": "North downtown", "ja": "市内北部", "zh": "市区北部"}, "🏘️"),
    ("east_coast", {"ko": "동해안 · 감포·문무대왕면·양남", "en": "East coast", "ja": "東海岸", "zh": "东海岸"}, "🌊"),
    ("north", {"ko": "북부 · 안강·강동·현곡·천북", "en": "North (Angang etc.)", "ja": "北部（安康など）", "zh": "北部（安康等）"}, "🌾"),
    ("west", {"ko": "서부 · 건천·서면·산내", "en": "West (Geoncheon etc.)", "ja": "西部（乾川など）", "zh": "西部（乾川等）"}, "🏞️"),
    ("south", {"ko": "남부 · 내남·외동", "en": "South (Naenam · Oedong)", "ja": "南部（内南・外東）", "zh": "南部（内南·外东）"}, "🛤️"),
]
AREA_ORDER = [a[0] for a in AREAS]
AREA_LABEL = {a[0]: a[1] for a in AREAS}
AREA_EMOJI = {a[0]: a[2] for a in AREAS}

# 읍·면 → 권역
TOWN_AREA = {
    "감포읍": "east_coast", "문무대왕면": "east_coast", "양북면": "east_coast", "양남면": "east_coast",
    "안강읍": "north", "강동면": "north", "현곡면": "north", "천북면": "north",
    "건천읍": "west", "서면": "west", "산내면": "west",
    "내남면": "south", "외동읍": "south",
}
# 동 지역 권역의 대표 좌표
CITY_CENTERS = {
    "downtown": (35.8350, 129.2120),
    "hwangnyong": (35.8330, 129.2330),
    "namsan": (35.7880, 129.2280),
    "bulguk": (35.7900, 129.3300),
    "bomun": (35.8450, 129.2850),
    "west_city": (35.8420, 129.1880),
    "north_city": (35.8700, 129.2250),
}
# 이름이 분명한 동은 바로 정해요 (좌표가 경계에 걸려도 헷갈리지 않게)
DONG_AREA = {
    "황남동": "downtown", "황오동": "downtown", "인왕동": "downtown", "교동": "downtown", "노동동": "downtown", "노서동": "downtown",
    "사정동": "downtown", "성건동": "downtown", "성동동": "downtown", "동부동": "downtown", "서부동": "downtown", "북부동": "downtown",
    "구황동": "hwangnyong", "보문동": "hwangnyong", "배반동": "namsan", "배동": "namsan", "남산동": "namsan", "탑동": "namsan",
    "진현동": "bulguk", "구정동": "bulguk", "마동": "bulguk", "시래동": "bulguk", "조양동": "bulguk", "하동": "bulguk", "덕동": "bomun",
    "신평동": "bomun", "북군동": "bomun", "천군동": "bomun", "암곡동": "bomun", "서악동": "west_city", "충효동": "west_city",
    "효현동": "west_city", "석장동": "west_city", "동천동": "north_city", "용강동": "north_city", "황성동": "north_city",
}


def _town(address: str) -> str:
    a = str(address or "")
    m = re.search(r"경주시\s+(\S+?(?:읍|면))(?=\s|$)", a)
    if m:
        return "문무대왕면" if m.group(1) == "양북면" else m.group(1)
    m = re.search(r"(?:경주시\s+|\()(\S+?동)(?=[\s)\d]|$)", a)
    return m.group(1) if m else ""


def area_of(address: str, lat: float, lon: float) -> tuple[str, str]:
    """(권역 key, 읍·면·동 이름)"""
    town = _town(address)
    if "용장" in str(address):   # 내남면 용장리 = 남산 용장골
        return "namsan", town
    if town in TOWN_AREA:
        return TOWN_AREA[town], town
    if town in DONG_AREA:
        return DONG_AREA[town], town
    best = min(CITY_CENTERS, key=lambda k: math.hypot((lat - CITY_CENTERS[k][0]) * 1.11, (lon - CITY_CENTERS[k][1]) * 0.9))
    far = math.hypot((lat - CITY_CENTERS[best][0]) * 111, (lon - CITY_CENTERS[best][1]) * 90)
    if far > 7:   # 시내 권역에서 너무 멀면 가장 가까운 읍·면 권역으로
        outer = {"east_coast": (35.78, 129.45), "north": (35.98, 129.24), "west": (35.85, 129.07), "south": (35.70, 129.27)}
        best = min(outer, key=lambda k: math.hypot(lat - outer[k][0], lon - outer[k][1]))
    return best, town

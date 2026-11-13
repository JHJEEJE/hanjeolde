"""geocode.py — 경주시 종교시설 현황(불교 334곳) 주소 → 좌표

data/religion_raw.csv (구분, 시설명, 소재지) 를 읽어 data/temples_geo.csv 를 만들어요.
만든 파일을 GitHub의 data 폴더에 올리면, 앱이 35곳 + 이 사찰들을 모두 QR 출발지·순례 후보로 써요.

1) 카카오 로컬 API (권장, 빠르고 정확): developers.kakao.com → 내 애플리케이션 → REST API 키
2) 키가 없으면 OpenStreetMap Nominatim (무료, 1초에 1건이라 5~6분, 못 찾는 곳이 더 많아요)

앱 사이드바 '🛕 사찰 좌표 만들기'에서 누르거나, 내 컴퓨터에서:
    python geocode.py 카카오REST키
"""
from __future__ import annotations

import csv
import re
import sys
import time
from pathlib import Path

import requests

DATA = Path(__file__).parent / "data"
RAW = DATA / "religion_raw.csv"
OUT = DATA / "temples_geo.csv"
BBOX = (35.60, 36.10, 128.95, 129.55)   # 경주시 둘레 (위도 최소, 최대, 경도 최소, 최대)
COLS = ["id", "name", "hanja", "name_en", "category", "era", "address", "lat", "lon", "coord_source", "heritage", "story", "tip", "desc_en"]


def clean_addr(a: str) -> str:
    a = re.sub(r"\(.*?\)|>.*$", "", str(a)).strip()
    a = re.sub(r"^경북\s*", "", a)
    a = a.replace("경주시 경주시", "경주시")
    if not a.startswith("경주시"):
        a = "경주시 " + a
    return "경상북도 " + a


def in_bbox(lat, lon):
    return BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lon <= BBOX[3]


def kakao(addr: str, name: str, key: str):
    h = {"Authorization": f"KakaoAK {key}"}
    try:
        r = requests.get("https://dapi.kakao.com/v2/local/search/address.json", headers=h, params={"query": addr}, timeout=6).json()
        if r.get("documents"):
            d = r["documents"][0]
            return float(d["y"]), float(d["x"]), "카카오 주소검색"
        q = f"경주 {name}"
        r = requests.get("https://dapi.kakao.com/v2/local/search/keyword.json", headers=h, params={"query": q}, timeout=6).json()
        for d in r.get("documents", []):
            if "경주" in d.get("address_name", "") and name.replace(" ", "")[:2] in d.get("place_name", "").replace(" ", ""):
                return float(d["y"]), float(d["x"]), "카카오 장소검색"
    except Exception:
        pass
    return None


def nominatim(addr: str, name: str):
    h = {"User-Agent": "HanJeolDeo-prototype/1.0 (student project)"}
    for q in (addr.replace("경상북도 ", ""), f"{name}, 경주시"):
        try:
            r = requests.get("https://nominatim.openstreetmap.org/search", headers=h,
                             params={"q": q, "format": "json", "limit": 1, "countrycodes": "kr"}, timeout=8).json()
            time.sleep(1.05)
            if r:
                return float(r[0]["lat"]), float(r[0]["lon"]), "OpenStreetMap Nominatim"
        except Exception:
            time.sleep(1.05)
    return None


def run(kakao_key: str | None = None, progress=None) -> tuple[int, int]:
    rows = list(csv.DictReader(RAW.open(encoding="utf-8-sig")))
    out, ok = [], 0
    for i, r in enumerate(rows):
        name = re.sub(r"\s+", " ", r["시설명"]).strip()
        addr = clean_addr(r["소재지"])
        got = kakao(addr, name, kakao_key) if kakao_key else nominatim(addr, name)
        if got and in_bbox(got[0], got[1]):
            ok += 1
            dong = re.findall(r"경주시\s+(\S+)", addr)
            where = dong[0] if dong else "경주"
            out.append({"id": f"tp{i:03d}", "name": name, "hanja": "", "name_en": name, "category": "현존 사찰", "era": "-",
                        "address": addr.replace("경상북도 ", ""), "lat": f"{got[0]:.6f}", "lon": f"{got[1]:.6f}",
                        "coord_source": got[2], "heritage": "", "tip": "",
                        "story": f"{name}은(는) 경주시 {where}에 있는 절이에요. 이 절의 이야기 조각은 아직 준비 중이에요. 법당 앞에서 잠시 숨을 고르고 가요.",
                        "desc_en": f"{name} is a Buddhist temple in {where}, Gyeongju. Its story pieces are still being prepared."})
        if progress:
            progress(i + 1, len(rows), name, bool(got))
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    return ok, len(rows)


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else None
    done, total = run(key, lambda i, n, nm, hit: print(f"{i}/{n} {'✓' if hit else '✗'} {nm}"))
    print(f"좌표를 찾은 곳 {done}/{total} → {OUT}")

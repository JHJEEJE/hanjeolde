# 🪷 한 절 더 — AI가 짜 주는 경주 사찰 순례길 (새 시제품)

사찰 QR을 찍고 **누구랑 · 시간 · 얼마나 걸을까 · 관심사** 네 가지를 고르면, AI가 사찰 1~3곳을 잇는 도보 순례길을 짜 줘요.
걷는 동안 이야기 조각을 모으고, 다음 이야기는 다음 사찰에서 이어져요.
기본값이 미리 골라져 있어서 **QR → 부탁하기 → 걷기 시작**, 터치 3번이면 시작해요.

## 폴더
```
hanjeolde/
├─ app.py              # 화면 (순례 · 사찰 지도 · 순례 기록)
├─ logic.py            # 순례길 설계 · 날씨 · 토블러 · 이야기 · 추천 · 기록 분석
├─ i18n.py             # 화면 문구 사전 (한국어 · English · 日本語 · 中文)
├─ style.css           # 밝고 부드러운 디자인 (크림 · 살구 · 세이지)
├─ .streamlit/config.toml   # 테마 색
├─ requirements.txt
└─ data/
   ├─ places.csv        # 사찰·유적 35곳 (국가유산청 좌표)
   ├─ courses.json      # 코스 9개
   ├─ stories.json      # 출처 확인된 이야기 4곳 + 구간 연결 이야기
   ├─ story_pieces.json # 이야기 조각 (관심사 4개별 이야기 · 차이 한 줄 · 예고 · 미션 · 계절 조각)
   ├─ course_tags.json  # 다음 순례 추천용 코스 태그
   ├─ rest_spots.csv    # 쉼터 목록 (비어 있으면 '예시 쉼터'로 시연)
   └─ translations.json # 사찰·코스·이야기 조각의 영어·일본어·중국어 번역
```

## 1. 내 컴퓨터에서 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```
- 분황사에서 시작: `http://localhost:8501/?temple=bunhwangsa`
- 발표용 (오전 10시처럼 보이게): `http://localhost:8501/?temple=bunhwangsa&t=10:00`

## 2. 인터넷에 올리기 (Streamlit Community Cloud, 무료)
1. 이 폴더를 **새 GitHub 저장소**에 올리기
2. share.streamlit.io → New app → 저장소 선택 → Main file: `app.py` → Deploy
3. 생긴 주소(`https://○○○.streamlit.app`)를 왼쪽 사이드바 **🖨️ QR 만들기**에 넣으면 사찰별 QR PNG가 나와요

## 3. 발표 · 테스트 설정 (왼쪽 사이드바, 화면 왼쪽 위 `>` 버튼)
| 설정 | 쓰는 때 |
|---|---|
| QR 찍은 것처럼 시작하기 | 실제 QR 없이 시작 사찰 바꾸기 |
| 날씨 (실시간/맑음/비/영하) | ② 날씨 규칙 시연: 비 → 박물관 마무리, 영하 → 짧은 길 |
| 계절(월) | 계절 조각 시연: 4월 → 분황사 '봄 조각' 열림 |
| 시각 | **발표가 오후 늦게면 꼭 10:00으로.** 해 지기 20분 전에 끝나도록 길을 줄이는 규칙이 있어요 |
| 예시 쉼터 보기 | rest_spots.csv가 비어 있을 때만 보여요. '실제 가게 아님'이 붙은 예시 |

## 4. 다국어 (한국어 · English · 日本語 · 中文)
- 화면 위 언어 버튼으로 바꾸거나, 주소 뒤에 `&lang=en` / `ja` / `zh`를 붙이면 그 언어로 열려요.
  예: `https://○○○.streamlit.app/?temple=bunhwangsa&lang=en`
- 사이드바 **QR 만들기**에서 'QR 언어'를 고르면 외국어 안내판용 QR이 나와요.
- 바뀌는 것: 버튼·안내 문구, 사찰 이름·소개, 시대, 코스 이름, 이야기 조각·차이 한 줄·미션·계절 조각, 추천 이유, 일지, 기록 분석, 🔊 음성(언어별 발음).
- 출처(한국민족문화대백과사전)는 한국어 자료라서 사전 이름만 번역하고 '(in Korean)'을 붙여요.
- 사이드바(발표 설정)는 팀용이라 한국어 그대로예요.
- 한국어 원문을 고치면 `data/translations.json`의 번역도 같이 고쳐 주세요. 화면 문구는 `i18n.py`에 있어요.

## 5. AI(Claude) 연결 — 선택
키가 없어도 모든 기능이 **규칙 기반**으로 돌아가요 (발표 중 인터넷이 끊겨도 안전).
키를 넣으면 ① 순례길 고르기(도구 호출 에이전트) ④ 일행 맞춤 말투 ⑤ 일지 문장을 Claude가 맡아요. 고른 언어로 답해요.
Streamlit Cloud → Manage app → Settings → Secrets:
```
ANTHROPIC_API_KEY = "sk-ant-..."
AGENT_MODEL = "claude-sonnet-5-5"   # 순례길 에이전트 (생략 가능)
FAST_MODEL = "claude-haiku-5-5"     # 말투·일지 (생략 가능)
```

## 6. 참가서류 5번과 연결
| 5번 | 화면 | 코드 (logic.py) |
|---|---|---|
| ① AI 순례길 추천 | 부탁하기 → 추천 카드 + 고른 이유 | `plan_candidates`, `agent_choose` |
| ② 날씨 자동 설정 | 추천 이유의 날씨·일몰 줄, 실내 마무리 | `get_conditions`, `time_budget` |
| ③ 코스 유형별 계산 | 구간별 시간(토블러), 1km 안 쉼터 | `leg_info`, `tobler_kmh`, `rest_near` |
| ④ 스토리텔링·음성 | 차이 한 줄 · 관심사별 이야기 · 출처 · 🔊 · 미션 · 계절 조각 | `story_for`, `diff_line`, `teaser`, `mission_for`, `season_for` |
| ⑤ 일지·다음 순례 | 순례 일지 · 비슷한/새로운 코스 | `journal_lines`, `recommend` |
| ⑥ 중단 분석·보완 | 순례 기록 탭: 구간 완주율 → 보완 제안 → 전후 비교 | `segment_table`, `make_virtual`, `suggestion` |

- 실제 기록은 `logs/pilgrim_log.json`에 쌓여요 (Streamlit Cloud는 앱이 다시 켜지면 지워져요).
- 가상 기록은 화면에서만 만들어지고 실제 기록과 섞이지 않아요. 화면에 '가상 데이터' 표시가 붙어요.

## 7. 팀이 채울 데이터
1. **story_pieces.json**: 문장을 출처와 대조한 뒤 `"verified": true`로 바꾸면 화면의 '검수 중'이 '✔ 출처 확인'으로 바뀌어요.
2. **rest_spots.csv**: 분황사 일대 쉼터 5~6곳. 칸: `id,name,type,lat,lon,open,close,closed_day,indoor,near_poi,partner,coupon,source,checked_date`
   (예: `cafe01,가게이름,카페,35.84,129.23,10:00,21:00,월,Y,bunhwangsa,후보,,카카오맵,2026-11-12`)
   `partner`가 `후보`면 '제휴 예정' 배지가 붙어요.
3. 이야기 조각을 다른 코스로 늘리려면 story_pieces.json의 `pieces`에 같은 형식으로 추가하세요.

## 8. 자주 고칠 곳
| 하고 싶은 것 | 고칠 곳 |
|---|---|
| 색 바꾸기 | `style.css` 맨 위 `:root`의 색 값, `.streamlit/config.toml` |
| 둘러보는 시간 | `logic.py`의 `STAY_MIN`, `DEFAULT_STAY` |
| 아이·어르신 걸음 속도 | `logic.py`의 `WHO_SPEED` |
| 날씨 규칙 (영하 기준 등) | `logic.py`의 `get_conditions`(cold), `time_budget` |
| 보완 제안 문구 | `i18n.py`의 `LABELS["fix"]` |
| 화면 문구 (4개 언어) | `i18n.py`의 `S` |

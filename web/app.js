/* 한 절 더 — HTML 앱 (화면·상태). AI 계산은 파이썬(webapp.py)이 하고, 여기서는 그리기만 해요. */
"use strict";

/* ------------------------------------------------------------------ 새 화면 문구 (4개 언어) */
const TX = {
  ko: {
    how: "이렇게 이용해요",
    dir_t: "🧭 자세한 길 안내", dir_rough: "지도 데이터로 어림한 방향이에요. 정확한 길은 카카오맵 도보 길찾기로 확인해요.", from_here: "{n}에서 길찾기",
    map_big: "크게 보기", map_close: "닫기",
    how1: "QR 찍기",
    how1s: "사찰 입구에서",
    how2: "취향 고르기",
    how2s: "일행·시간·걷기",
    how3: "AI 순례길",
    how3s: "이야기·일지·엽서",
    hero_q: "{n}에서\n한 절 더 걸어 볼까요?",
    qr_t: "사찰 입구의 QR을 찍어 주세요",
    qr_s: "QR을 찍은 사찰에서 시작하는 순례길을 AI가 짜 드려요.",
    qr_cam: "📷 카메라로 QR 찍기",
    qr_demo: "🧭 시연: QR 찍은 사찰 고르기",
    qr_here: "📍 QR을 찍은 곳",
    qr_from: "여기서 시작해 사찰 1~3곳을 더 잇는 순례길을 짜 드려요.",
    qr_other: "다른 사찰 QR",
    qr_need: "먼저 사찰 QR을 찍어 주세요",
    qr_nocam: "이 브라우저는 앱 안에서 QR을 못 읽어요. 휴대폰 기본 카메라로 사찰 QR을 찍으면 이 앱이 그 사찰로 바로 열려요.",
    qr_scanning: "QR을 네모 안에 맞춰 주세요",
    qr_bad: "한 절 더 QR이 아니에요",
    qr_list: "QR 찍은 사찰 고르기 (시연)",
    cmp_m1: "⏰ 시간·날씨별",
    cmp_m2: "📍 QR 사찰별",
    cmp_qr_s: "같은 취향·지금 날씨에서, QR을 찍은 사찰만 바꿔 봤어요.",
    cmp_used: "QR {n}곳에서 시작한 길이 서로 다른 장소 {m}곳을 지나요",
    cmp_go2: "QR 사찰별로 비교해 보기",
    cmp_from: "QR: {n}",

    hero_ey: "TODAY IN GYEONGJU", hero_t: "한 절 더,\n걸어 볼까요?", hero_s: "고른 취향과 오늘 날씨·해 지는 시각으로\nAI가 순례길을 새로 짜 드려요.",
    tip_rain: "☔ 비 오는 날이라 실내에서 마무리하는 길을 먼저 찾아요", tip_cold: "🧣 추운 날이라 짧고 따뜻한 길로 맞춰요", tip_hot: "🥵 더운 날이라 그늘·숲길에 가산점을 줘요", tip_clear: "☀️ 걷기 좋은 날이에요",
    make: "AI 순례길 만들기", make_s: "고를수록 AI가 짜는 길이 달라져요",
    q_start: "어디서 시작해요?", st_ai: "🤖 AI가 정해요", st_ai_s: "35곳 중 취향에 맞게", st_qr: "📍 {n}", st_qr_s: "QR 찍은 곳", st_pick: "🧭 직접 고르기", st_pick_s: "출발지 선택",
    st_ai_note: "출발지까지 AI가 골라요. 취향 점수가 높은 곳이 모인 동네에서 시작해요.",
    q_time: "시간은 얼마나 있어요?", end_at: "{t}쯤 끝나요 · 해 지기 전까지 맞춰 드려요", minus: "−5분", plus: "+5분",
    q_who: "누구랑 걸어요?", q_level: "얼마나 걸을까요?", q_int: "무엇이 궁금해요?", q_int_s: "여러 개 골라도 돼요", q_free: "AI에게 하고 싶은 말", q_free_s: "선택",
    free_ph: "예: 사진 예쁜 곳 위주로, 중간에 카페에서 쉬고 싶어요. 오르막은 싫어요.", ex: "이렇게 말해도 돼요",
    go: "✨ AI에게 순례길 부탁하기",
    ld: ["취향을 이해하는 중", "35곳에 점수를 매기는 중", "가능한 길 수천 개를 비교하는 중", "고른 이유를 정리하는 중"], ld_t: "AI가 순례길을 짜고 있어요",
    ld_other: "잠시만요…",
    back: "← 다시 고르기", cand: "추천 {n}", ai_pick: "⭐ AI 추천", why: "AI가 이 길을 고른 이유", course: "코스 한눈에",
    stay: "둘러보기 약 {m}분", walk_leg: "도보 {m}분 · {km}km · {g}", starts: "출발지 후보 (AI가 고른 곳)", start_btn: "🚶 이 길로 걷기 시작",
    one_place: "한 곳을 깊게 둘러보는 길이에요", listen: "🔊 이야기 듣기", stop: "✋ 그만할래요", tired: "😮‍💨 힘들어요",
    bored: "😐 볼 게 없어요", photo: "📷 사진 남기기", photo2: "📷 다른 사진", memo: "한 줄 남기기 (일지에 들어가요)",
    nearby: "근처 들를 곳", swap_to: "다음 목적지를 여기로 바꾸기", no_alt: "가까운 다른 곳이 없어요.",
    pc: "📮 순례 엽서", pc_s: "사진을 골라 엽서로 만들어요", pc_pick: "엽서에 넣을 사진", pc_none: "사진이 없으면 그림 엽서로 만들어 드려요", pc_dl: "📥 엽서 저장하기", pc_share: "공유하기",
    pc_to: "To. 다음의 나에게", pc_from: "From. 한 절 더 순례자", pc_greet: "경주에서,", pc_msg1: "오늘은 {n}곳, {km}km를 걸었어.", pc_msg2: "다음엔, 한 절 더.",
    pc_hold: "저장이 안 되면 이미지를 길게 눌러 저장하세요",
    story_by_ai: "Claude가 다듬은 이야기", story_rule: "오늘 남긴 기록으로 엮은 이야기",
    cmp: "상황별 AI 추천 비교", cmp_s: "같은 취향이라도 시각·날씨에 따라 AI가 고르는 길이 달라져요.", cmp_go: "지금 취향으로 비교해 보기",
    cmp_base: "기준", cmp_left: "쓸 수 있는 시간 {m}분 · 일몰 {s}", cmp_changed: "맑음과 달라요", cmp_rules: "AI가 지키는 규칙",
    rule_rain: "☔ 비 → 실내 마무리 가산, 오르막 감점", rule_cold: "🥶 영하 → 1~2곳만, 따뜻한 실내", rule_hot: "🥵 폭염 → 그늘·숲길 가산, 오르막 감점", rule_sun: "🌇 해 질 녘 → 일몰 20분 전에 끝나게",
    w_맑음: "☀️ 맑음", w_비: "☔ 비", w_영하: "🥶 영하", w_폭염: "🥵 폭염", t_indoor_end: "실내 마무리", t_shade: "그늘길", t_nearest: "시간이 빠듯해 가장 가까운 곳만", cmp_need: "먼저 ‘순례’ 탭에서 취향을 고르면 그 취향으로 비교해요. 지금은 기본값으로 비교해요.",
    map_t: "사찰 지도", map_s: "아이콘으로 종류를 구분해요", start_here: "여기서 시작하기", kakao: "카카오맵 길찾기",
    log_t: "순례 기록 분석", log_s: "구간별 완주율과 멈춘 이유로 코스를 자동 보완해요", apply: "🛠 보완 적용해 보기", undo: "되돌리기", my_log: "내 기록 (이 기기)",
    set_t: "발표 설정", set_w: "날씨", set_time: "시각", set_m: "계절(월)", now: "지금", live: "실시간", close: "닫기", apply_btn: "적용",
    tab1: "순례", tab2: "지도", tab3: "AI 비교", tab4: "기록", err: "앗, 잠시 문제가 생겼어요", retry: "다시 시도", rerouted: "길을 다시 짰어요",
    walked_to: "{n}에 도착", done_t: "순례 완료", home: "처음으로", rec: "다음 순례 추천", near_end: "☕ 끝난 곳 주변 쉼터", photos: "오늘의 사진",
    new_story: "다시 쓰기", stop_q: "왜 멈추셨어요? (코스를 고치는 데 써요)", stop_ok: "여기서 마칠게요", lang: "언어",
  },
  en: {
    how: "How it works",
    dir_t: "🧭 Step-by-step directions", dir_rough: "Rough direction only — check Kakao Map walking directions for the exact path.", from_here: "Directions from {n}",
    map_big: "Full screen", map_close: "Close",
    how1: "Scan the QR",
    how1s: "at the temple gate",
    how2: "Pick your taste",
    how2s: "who · time · walking",
    how3: "AI route",
    how3s: "story · journal · postcard",
    hero_q: "From {n},\none more temple?",
    qr_t: "Scan the QR at the temple gate",
    qr_s: "AI plans a walk that starts from the temple where you scanned.",
    qr_cam: "📷 Scan with camera",
    qr_demo: "🧭 Demo: pick the scanned temple",
    qr_here: "📍 Where you scanned",
    qr_from: "Starts here and links 1–3 more temples on foot.",
    qr_other: "Other temple QR",
    qr_need: "Please scan a temple QR first",
    qr_nocam: "This browser can't read QR inside the app. Scan the temple QR with your phone camera and the app opens at that temple.",
    qr_scanning: "Fit the QR inside the square",
    qr_bad: "Not a Han Jeol Deo QR",
    qr_list: "Pick the scanned temple (demo)",
    cmp_m1: "⏰ By time & weather",
    cmp_m2: "📍 By QR temple",
    cmp_qr_s: "Same taste, current weather — only the scanned temple changes.",
    cmp_used: "Routes from {n} QR temples pass through {m} different places",
    cmp_go2: "Compare by QR temple",
    cmp_from: "QR: {n}",

    hero_ey: "TODAY IN GYEONGJU", hero_t: "One more temple,\nshall we walk?", hero_s: "Using your taste, today's weather and sunset,\nAI builds a fresh temple walk for you.",
    tip_rain: "☔ Rainy day — routes that end indoors come first", tip_cold: "🧣 Cold day — short and warm routes", tip_hot: "🥵 Hot day — shady forest paths get a bonus", tip_clear: "☀️ A great day for walking",
    make: "Build an AI route", make_s: "Every choice changes the route",
    q_start: "Where do you start?", st_ai: "🤖 Let AI choose", st_ai_s: "best of 35 for you", st_qr: "📍 {n}", st_qr_s: "QR spot", st_pick: "🧭 I'll pick", st_pick_s: "choose a start",
    st_ai_note: "AI picks the start too — a neighborhood full of places that match your taste.",
    q_time: "How much time do you have?", end_at: "Ends around {t} · fitted before sunset", minus: "−5 min", plus: "+5 min",
    q_who: "Who are you walking with?", q_level: "How much walking?", q_int: "What are you curious about?", q_int_s: "pick as many as you like", q_free: "Tell the AI anything", q_free_s: "optional",
    free_ph: "e.g. Photo spots please, with a café break. No hills.", ex: "You can say things like",
    go: "✨ Ask AI for a route",
    ld: ["Understanding your taste", "Scoring 35 places", "Comparing thousands of routes", "Writing down the reasons"], ld_t: "AI is planning your walk",
    ld_other: "Just a moment…",
    back: "← Change choices", cand: "Option {n}", ai_pick: "⭐ AI pick", why: "Why AI chose this route", course: "Route at a glance",
    stay: "about {m} min to look around", walk_leg: "{m} min walk · {km} km · {g}", starts: "Start candidates (chosen by AI)", start_btn: "🚶 Start this walk",
    one_place: "A route to explore one place deeply", listen: "🔊 Listen", stop: "✋ Stop here", tired: "😮‍💨 I'm tired",
    bored: "😐 Not interesting", photo: "📷 Add a photo", photo2: "📷 Change photo", memo: "Leave a line (goes in your journal)",
    nearby: "Nearby spots", swap_to: "Make this my next stop", no_alt: "No other places nearby.",
    pc: "📮 Pilgrimage postcard", pc_s: "Pick a photo and turn it into a postcard", pc_pick: "Photo for the postcard", pc_none: "No photo? We'll paint an illustrated card", pc_dl: "📥 Save postcard", pc_share: "Share",
    pc_to: "To. my future self", pc_from: "From. a Han Jeol Deo walker", pc_greet: "From Gyeongju,", pc_msg1: "Today I walked {km} km through {n} places.", pc_msg2: "Next time, one more temple.",
    pc_hold: "If saving fails, long-press the image to save it",
    story_by_ai: "Polished by Claude", story_rule: "Woven from what you left today",
    cmp: "AI routes by situation", cmp_s: "Same taste, different time and weather — AI picks different routes.", cmp_go: "Compare with my choices",
    cmp_base: "Based on", cmp_left: "{m} min available · sunset {s}", cmp_changed: "differs from sunny", cmp_rules: "Rules AI follows",
    rule_rain: "☔ Rain → indoor ending bonus, climbs penalized", rule_cold: "🥶 Below zero → only 1–2 stops, warm indoors", rule_hot: "🥵 Heatwave → shade bonus, climbs penalized", rule_sun: "🌇 Late day → finish 20 min before sunset",
    w_맑음: "☀️ Sunny", w_비: "☔ Rain", w_영하: "🥶 Freezing", w_폭염: "🥵 Heatwave", t_indoor_end: "ends indoors", t_shade: "shady path", t_nearest: "tight on time: nearest stop only", cmp_need: "Pick your taste in the Walk tab first. For now, defaults are used.",
    map_t: "Temple map", map_s: "Icons show each type", start_here: "Start here", kakao: "Directions (Kakao Map)",
    log_t: "Walk log analysis", log_s: "Completion and stop reasons per leg auto-improve the course", apply: "🛠 Try the fix", undo: "Undo", my_log: "My log (this device)",
    set_t: "Demo settings", set_w: "Weather", set_time: "Time", set_m: "Season (month)", now: "Now", live: "Live", close: "Close", apply_btn: "Apply",
    tab1: "Walk", tab2: "Map", tab3: "AI compare", tab4: "Log", err: "Oops, something went wrong", retry: "Try again", rerouted: "Route updated",
    walked_to: "Arrived at {n}", done_t: "Walk complete", home: "Home", rec: "Next walk", near_end: "☕ Rest spots near the end", photos: "Today's photos",
    new_story: "Rewrite", stop_q: "Why did you stop? (helps us fix the course)", stop_ok: "End here", lang: "Language",
  },
  ja: {
    how: "使い方",
    dir_t: "🧭 詳しい道案内", dir_rough: "おおよその方向です。正確な道はカカオマップの徒歩ルートで確認してください。", from_here: "{n}から道案内",
    map_big: "大きく見る", map_close: "閉じる",
    how1: "QRを読む",
    how1s: "寺の入口で",
    how2: "好みを選ぶ",
    how2s: "同行・時間・歩く量",
    how3: "AI巡礼ルート",
    how3s: "物語・日記・はがき",
    hero_q: "{n}から\nもう一寺、歩きませんか？",
    qr_t: "寺の入口のQRを読み取ってください",
    qr_s: "QRを読んだ寺から始まる巡礼ルートをAIが組みます。",
    qr_cam: "📷 カメラでQRを読む",
    qr_demo: "🧭 デモ：QRを読んだ寺を選ぶ",
    qr_here: "📍 QRを読んだ場所",
    qr_from: "ここから始めて、さらに1〜3か所の寺を歩いてつなぎます。",
    qr_other: "別の寺のQR",
    qr_need: "まず寺のQRを読み取ってください",
    qr_nocam: "このブラウザはアプリ内でQRを読めません。スマホのカメラで寺のQRを読むと、その寺でアプリが開きます。",
    qr_scanning: "QRを枠の中に合わせてください",
    qr_bad: "ハン・ジョル・ドのQRではありません",
    qr_list: "QRを読んだ寺を選ぶ（デモ）",
    cmp_m1: "⏰ 時刻・天気別",
    cmp_m2: "📍 QRの寺別",
    cmp_qr_s: "同じ好み・今の天気で、QRを読んだ寺だけを変えてみました。",
    cmp_used: "QR {n}か所から始まる道が、{m}か所の異なる場所を通ります",
    cmp_go2: "QRの寺別に比べる",
    cmp_from: "QR：{n}",

    hero_ey: "TODAY IN GYEONGJU", hero_t: "もう一寺、\n歩いてみませんか？", hero_s: "好みと今日の天気・日の入りから\nAIが巡礼ルートを組み立てます。",
    tip_rain: "☔ 雨の日なので屋内で締めくくる道を優先します", tip_cold: "🧣 寒い日なので短く暖かい道に", tip_hot: "🥵 暑い日なので木陰・森の道を優先", tip_clear: "☀️ 歩くのにいい日です",
    make: "AI巡礼ルートを作る", make_s: "選ぶほどAIのルートが変わります",
    q_start: "どこから始めますか？", st_ai: "🤖 AIにおまかせ", st_ai_s: "35か所から好みに合わせて", st_qr: "📍 {n}", st_qr_s: "QRの場所", st_pick: "🧭 自分で選ぶ", st_pick_s: "出発地を選択",
    st_ai_note: "出発地もAIが選びます。好みに合う場所が集まるエリアから始めます。",
    q_time: "時間はどれくらいありますか？", end_at: "{t}ごろ終わります · 日の入り前に合わせます", minus: "−5分", plus: "+5分",
    q_who: "誰と歩きますか？", q_level: "どれくらい歩きますか？", q_int: "何に興味がありますか？", q_int_s: "いくつ選んでもOK", q_free: "AIに自由に伝える", q_free_s: "任意",
    free_ph: "例：写真映えする場所中心で、途中カフェで休みたい。坂は苦手。", ex: "こんなふうに話してもOK",
    go: "✨ AIに巡礼ルートをお願いする",
    ld: ["好みを理解しています", "35か所に点数をつけています", "何千通りの道を比べています", "選んだ理由をまとめています"], ld_t: "AIがルートを組み立て中",
    ld_other: "少々お待ちください…",
    back: "← 選び直す", cand: "おすすめ{n}", ai_pick: "⭐ AIのおすすめ", why: "AIがこの道を選んだ理由", course: "コースを一目で",
    stay: "見学 約{m}分", walk_leg: "徒歩{m}分 · {km}km · {g}", starts: "出発地の候補（AIが選択）", start_btn: "🚶 この道で歩き始める",
    one_place: "一か所をじっくり巡る道です", listen: "🔊 物語を聞く", stop: "✋ やめる", tired: "😮‍💨 疲れた",
    bored: "😐 見どころがない", photo: "📷 写真を残す", photo2: "📷 写真を変える", memo: "ひとこと残す（日記に入ります）",
    nearby: "近くの立ち寄りスポット", swap_to: "次の目的地をここに変える", no_alt: "近くにほかの場所がありません。",
    pc: "📮 巡礼はがき", pc_s: "写真を選んではがきにします", pc_pick: "はがきに入れる写真", pc_none: "写真がなければイラストのはがきにします", pc_dl: "📥 はがきを保存", pc_share: "共有",
    pc_to: "To. 未来のわたしへ", pc_from: "From. ハン・ジョル・ド巡礼者", pc_greet: "慶州より、", pc_msg1: "今日は{n}か所、{km}km歩いたよ。", pc_msg2: "次は、もう一寺。",
    pc_hold: "保存できないときは画像を長押しして保存してください",
    story_by_ai: "Claudeが整えた物語", story_rule: "今日の記録から紡いだ物語",
    cmp: "状況別AIおすすめ比較", cmp_s: "同じ好みでも、時刻と天気でAIが選ぶ道が変わります。", cmp_go: "今の好みで比べる",
    cmp_base: "条件", cmp_left: "使える時間{m}分 · 日の入り{s}", cmp_changed: "晴れと違う", cmp_rules: "AIが守るルール",
    rule_rain: "☔ 雨 → 屋内で締めくくり加点、坂は減点", rule_cold: "🥶 氷点下 → 1〜2か所、暖かい屋内", rule_hot: "🥵 猛暑 → 木陰・森の道に加点", rule_sun: "🌇 夕方 → 日の入り20分前に終了",
    w_맑음: "☀️ 晴れ", w_비: "☔ 雨", w_영하: "🥶 氷点下", w_폭염: "🥵 猛暑", t_indoor_end: "屋内で締め", t_shade: "木陰の道", t_nearest: "時間が少なく一番近い所だけ", cmp_need: "先に「巡礼」タブで好みを選ぶと、その好みで比べます。今は初期設定で比べます。",
    map_t: "寺院マップ", map_s: "アイコンで種類がわかります", start_here: "ここから始める", kakao: "カカオマップで道案内",
    log_t: "巡礼記録の分析", log_s: "区間ごとの完走率と中断理由でコースを自動改善", apply: "🛠 改善を適用してみる", undo: "元に戻す", my_log: "わたしの記録（この端末）",
    set_t: "発表用設定", set_w: "天気", set_time: "時刻", set_m: "季節（月）", now: "今", live: "リアルタイム", close: "閉じる", apply_btn: "適用",
    tab1: "巡礼", tab2: "地図", tab3: "AI比較", tab4: "記録", err: "問題が発生しました", retry: "もう一度", rerouted: "道を組み直しました",
    walked_to: "{n}に到着", done_t: "巡礼完了", home: "最初へ", rec: "次の巡礼のおすすめ", near_end: "☕ 終点近くの休憩所", photos: "今日の写真",
    new_story: "書き直す", stop_q: "どうしてやめましたか？（コース改善に使います）", stop_ok: "ここで終わる", lang: "言語",
  },
  zh: {
    how: "使用方法",
    dir_t: "🧭 详细路线指引", dir_rough: "这是大致方向，准确路线请用Kakao地图步行导航确认。", from_here: "从{n}导航",
    map_big: "放大查看", map_close: "关闭",
    how1: "扫描二维码",
    how1s: "在寺院入口",
    how2: "选择喜好",
    how2s: "同伴·时间·步行量",
    how3: "AI巡礼路线",
    how3s: "故事·日记·明信片",
    hero_q: "从{n}出发，\n再多走一寺吧？",
    qr_t: "请扫描寺院入口的二维码",
    qr_s: "AI会规划从你扫码的寺院出发的巡礼路线。",
    qr_cam: "📷 用相机扫码",
    qr_demo: "🧭 演示：选择扫码的寺院",
    qr_here: "📍 扫码地点",
    qr_from: "从这里出发，步行再连起1~3座寺院。",
    qr_other: "其他寺院二维码",
    qr_need: "请先扫描寺院二维码",
    qr_nocam: "此浏览器无法在应用内识别二维码。用手机相机扫描寺院二维码，就会直接打开该寺院页面。",
    qr_scanning: "请把二维码对准方框",
    qr_bad: "不是再一寺的二维码",
    qr_list: "选择扫码的寺院（演示）",
    cmp_m1: "⏰ 按时间·天气",
    cmp_m2: "📍 按扫码寺院",
    cmp_qr_s: "同样的喜好、现在的天气，只换扫码的寺院。",
    cmp_used: "从{n}处扫码出发的路线经过{m}个不同地点",
    cmp_go2: "按扫码寺院对比",
    cmp_from: "扫码：{n}",

    hero_ey: "TODAY IN GYEONGJU", hero_t: "再多走一寺，\n出发吧？", hero_s: "根据你的喜好、今天的天气和日落时间，\nAI为你重新规划巡礼路线。",
    tip_rain: "☔ 下雨天，优先寻找在室内结束的路线", tip_cold: "🧣 天冷，安排短而温暖的路线", tip_hot: "🥵 天热，树荫和林间小路加分", tip_clear: "☀️ 适合散步的好天气",
    make: "生成AI巡礼路线", make_s: "选得越多，AI规划的路线越不同",
    q_start: "从哪里出发？", st_ai: "🤖 交给AI", st_ai_s: "从35处中按喜好挑选", st_qr: "📍 {n}", st_qr_s: "扫码地点", st_pick: "🧭 自己选", st_pick_s: "选择出发地",
    st_ai_note: "出发地也由AI挑选，从符合你喜好的地点聚集的街区开始。",
    q_time: "有多少时间？", end_at: "约{t}结束 · 会在日落前结束", minus: "−5分钟", plus: "+5分钟",
    q_who: "和谁一起走？", q_level: "走多少路？", q_int: "对什么感兴趣？", q_int_s: "可多选", q_free: "想对AI说的话", q_free_s: "可选",
    free_ph: "例：以拍照好看的地方为主，中途想在咖啡馆休息，不想爬坡。", ex: "可以这样说",
    go: "✨ 请AI规划巡礼路线",
    ld: ["正在理解你的喜好", "正在为35处地点打分", "正在比较数千条路线", "正在整理推荐理由"], ld_t: "AI正在规划路线",
    ld_other: "请稍候…",
    back: "← 重新选择", cand: "推荐{n}", ai_pick: "⭐ AI推荐", why: "AI选择这条路线的理由", course: "路线一览",
    stay: "参观约{m}分钟", walk_leg: "步行{m}分钟 · {km}公里 · {g}", starts: "出发地候选（AI挑选）", start_btn: "🚶 按这条路线出发",
    one_place: "深度游览一处的路线", listen: "🔊 听故事", stop: "✋ 不走了", tired: "😮‍💨 好累",
    bored: "😐 没什么看头", photo: "📷 留张照片", photo2: "📷 换照片", memo: "留下一句话（会写进日记）",
    nearby: "附近可以顺路去的地方", swap_to: "把下一站改成这里", no_alt: "附近没有其他地点。",
    pc: "📮 巡礼明信片", pc_s: "选一张照片做成明信片", pc_pick: "放进明信片的照片", pc_none: "没有照片就做成插画明信片", pc_dl: "📥 保存明信片", pc_share: "分享",
    pc_to: "To. 未来的我", pc_from: "From. 再一寺巡礼者", pc_greet: "来自庆州，", pc_msg1: "今天走了{n}处、{km}公里。", pc_msg2: "下次，再多走一寺。",
    pc_hold: "无法保存时，请长按图片保存",
    story_by_ai: "由Claude润色的故事", story_rule: "用今天的记录编成的故事",
    cmp: "不同情况下的AI推荐对比", cmp_s: "同样的喜好，时间和天气不同，AI选的路线也不同。", cmp_go: "用当前喜好来对比",
    cmp_base: "条件", cmp_left: "可用时间{m}分钟 · 日落{s}", cmp_changed: "与晴天不同", cmp_rules: "AI遵守的规则",
    rule_rain: "☔ 下雨 → 室内结束加分，上坡减分", rule_cold: "🥶 零下 → 只去1~2处，温暖室内", rule_hot: "🥵 酷暑 → 树荫林路加分，上坡减分", rule_sun: "🌇 傍晚 → 日落前20分钟结束",
    w_맑음: "☀️ 晴", w_비: "☔ 雨", w_영하: "🥶 零下", w_폭염: "🥵 酷暑", t_indoor_end: "室内结束", t_shade: "树荫路", t_nearest: "时间紧，只去最近一处", cmp_need: "先在“巡礼”页选择喜好，就会按你的喜好对比。现在使用默认值。",
    map_t: "寺院地图", map_s: "用图标区分类型", start_here: "从这里出发", kakao: "Kakao地图导航",
    log_t: "巡礼记录分析", log_s: "根据各路段完成率和中断原因自动改进路线", apply: "🛠 试试改进", undo: "撤销", my_log: "我的记录（本设备）",
    set_t: "演示设置", set_w: "天气", set_time: "时间", set_m: "季节（月）", now: "现在", live: "实时", close: "关闭", apply_btn: "应用",
    tab1: "巡礼", tab2: "地图", tab3: "AI对比", tab4: "记录", err: "出了点问题", retry: "重试", rerouted: "已重新规划路线",
    walked_to: "到达{n}", done_t: "巡礼完成", home: "回到首页", rec: "下次巡礼推荐", near_end: "☕ 终点附近的休息处", photos: "今天的照片",
    new_story: "重新写", stop_q: "为什么停下？（用于改进路线）", stop_ok: "就到这里", lang: "语言",
  },
};

/* ------------------------------------------------------------------ Streamlit 연결 (컴포넌트 프로토콜) */
const ST = {
  send(type, data) { window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*"); },
  ready() { this.send("streamlit:componentReady", { apiVersion: 1 }); },
  height(h) { this.send("streamlit:setFrameHeight", { height: h }); },
  value(v) { this.send("streamlit:setComponentValue", { value: v, dataType: "json" }); },
};

let B = null, C = null, QR = null, DEMO = {}, LLM = false;
const S = {
  tab: "walk", screen: "setup", qr: null, cmpMode: "time",
  choice: { who: "혼자", minutes: 120, level: "가볍게", interests: [], free: "" },
  plan: null, cand: 0, walk: null, done: null, compare: null, cmpFixed: false,
  mapKinds: null, mapSel: null, pending: null, bored: null, sheet: null, pcPhoto: null, lastResp: null,
};
const maps = [];

/* ------------------------------------------------------------------ 도우미 */
const $ = (sel, el = document) => el.querySelector(sel);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const lang = () => (B ? B.lang : "ko");
function josa(s) {
  return s.replace(/(.)(["'’”」』)]*)\[([^/\]]+)\/([^\]]+)\]/g, (m, ch, q, a, b) => {
    const code = ch.charCodeAt(0) - 0xac00;
    let use = b;
    if (code >= 0 && code < 11172) {
      const jong = code % 28;
      use = a === "으로" ? (jong === 0 || jong === 8 ? b : a) : jong ? a : b;
    } else if (/\d/.test(ch)) use = a;
    return ch + q + use;
  });
}
function fill(str, kw) {
  let s = String(str || "");
  if (kw) for (const k in kw) s = s.split("{" + k + "}").join(kw[k]);
  s = s.replace(/을\(를\)|\(을\)를/g, "[을/를]").replace(/\(으\)로/g, "[으로/로]").replace(/이\(가\)/g, "[이/가]");
  return s.includes("[") ? josa(s) : s;
}
const t = (k, kw) => fill(B && B.S[k] != null ? B.S[k] : k, kw);       // 기존 문구 (i18n.py)
const x = (k, kw) => {  // 새 문구
  const d = TX[lang()] || TX.ko;
  const v = d[k] != null ? d[k] : TX.ko[k] != null ? TX.ko[k] : k;
  return Array.isArray(v) ? v : fill(v, kw);
};
const lab = (g, v) => (B && B.L[g] && B.L[g][v]) || v;
const P = (id) => B.places.find((p) => p.id === id) || { id, name: id, kind: "landmark", lat: 35.83, lon: 129.22 };
const pname = (id) => P(id).name;
function fmtMin(m) {
  m = Math.round(m);
  const h = Math.floor(m / 60), mm = m % 60;
  if (h && mm) return t("hm", { h, m: mm });
  return h ? t("h", { h }) : t("m", { m: mm });
}
function icon(kind, size = 22) {
  const c = B.pins.color[kind] || "#ccc";
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24"><circle cx="12" cy="12" r="12" fill="${c}"/><g transform="translate(2,2)">${B.pins.inner[kind] || ""}</g></svg>`;
}
function pinHtml(kind, n, grey) {
  const c = grey ? "#D9CFC9" : B.pins.color[kind];
  const badge = n != null ? `<div style="position:absolute;top:-8px;right:-9px;min-width:17px;height:17px;border-radius:9px;background:#3B312D;color:#fff;font:800 10.5px/17px sans-serif;text-align:center;border:2px solid #fff;padding:0 2px">${n}</div>` : "";
  return `<div style="position:relative;width:34px;height:44px;filter:drop-shadow(0 3px 4px rgba(90,60,40,.3))"><svg width="34" height="44" viewBox="0 0 36 46"><path d="M18 45 C18 45 3 28.5 3 17 A15 15 0 1 1 33 17 C33 28.5 18 45 18 45 Z" fill="${c}" stroke="#fff" stroke-width="2.5"/><g transform="translate(8,7)">${B.pins.inner[kind] || ""}</g></svg>${badge}</div>`;
}
const KIND_EMOJI = { cafe: "☕", meal: "🍚", craft: "🎨", culture: "🏛️" };
function toast(msg) {
  const o = document.createElement("div");
  o.className = "toast";
  o.textContent = msg;
  $("#frame").appendChild(o);
  setTimeout(() => o.remove(), 2600);
}
function nowDate() { return C ? new Date(C.now) : new Date(); }
function clockAdd(date, min) { return new Date(date.getTime() + min * 60000); }
const hhmm = (d) => `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
function sunsetDate() { const d = nowDate(); const [h, m] = (C.sunset || "17:30").split(":").map(Number); const s = new Date(d); s.setHours(h, m, 0, 0); return s; }
function demoTime() { return DEMO && DEMO.time && DEMO.time !== "지금"; }

/* ------------------------------------------------------------------ 요청 (파이썬에 계산 부탁) */
let reqSeq = 0;
function ask(kind, payload, opts = {}) {
  const id = `${Date.now().toString(36)}-${++reqSeq}`;
  S.pending = { id, kind, opts };
  showLoading(kind);
  ST.value({ id, kind, payload: payload || {} });
}
function onResp(resp) {
  if (!resp || !S.pending || resp.id !== S.pending.id) return false;
  const { kind, opts } = S.pending;
  S.pending = null;
  hideLoading();
  const d = resp.data || {};
  if (d.error) { toast(x("err") + " · " + d.error.slice(0, 80)); console.error(d.error); return true; }
  if (kind === "plan") {
    S.plan = d; S.cand = Math.max(0, d.cands.findIndex((c) => c.picked)); S.screen = "plan"; S.tab = "walk";
    if (opts.keepWalk && S.walk) { /* 언어만 바뀐 경우 */ }
    scrollTop();
  } else if (kind === "route") {
    if (S.walk) {
      S.walk.route = d;
      S.walk.stops = d.stops.map((s) => s.id);
      if (opts.toast) toast(opts.toast);
    }
  } else if (kind === "alts") {
    S.bored = d;
  } else if (kind === "finish") {
    S.done = d; S.screen = "done"; S.pcPhoto = S.pcPhoto || firstPhoto(); scrollTop();
  } else if (kind === "compare") {
    S.compare = d;
  } else if (kind === "lang" || kind === "demo") {
    afterReload(kind);
  }
  return true;
}
function afterReload(kind) {
  // 언어·날씨가 바뀌면, 보고 있던 화면의 내용을 새로 받아요
  if (S.screen === "plan" && S.plan) setTimeout(() => requestPlan(), 30);
  else if (S.screen === "walk" && S.walk) setTimeout(() => ask("route", { stops: S.walk.stops, who: S.walk.who, storyInterest: S.walk.storyInterest }), 30);
  else if (S.screen === "done" && S.walk) setTimeout(() => finishWalk(S.walk.stopped, true), 30);
  if (S.compare) S.compare = null;
}
function requestPlan() {
  if (!S.qr) { toast(x("qr_need")); S.sheet = "qr"; renderSheet(); return; }
  ask("plan", { choice: S.choice, start: S.qr });   // 순례길은 언제나 QR을 찍은 사찰에서 시작해요
}

/* ------------------------------------------------------------------ 로딩 · 시트 */
let ldTimer = null;
function showLoading(kind) {
  const ov = $("#overlay");
  if (kind === "plan") {
    const steps = x("ld");
    ov.innerHTML = `<div class="loading"><div class="lotus">🪷</div><b style="font-size:17px">${esc(x("ld_t"))}</b><div class="ls">${steps.map((s, i) => `<div data-i="${i}"><span class="num" style="background:#E5DBD4">${i + 1}</span>${esc(s)}</div>`).join("")}</div></div>`;
    let i = 0;
    const tick = () => {
      ov.querySelectorAll(".ls div").forEach((d, j) => { d.className = j < i ? "ok" : j === i ? "on" : ""; const n = d.querySelector(".num"); n.style.background = j < i ? "#5E9F76" : j === i ? "#E8795A" : "#E5DBD4"; n.textContent = j < i ? "✓" : j + 1; });
      if (i < steps.length - 1) i++;
    };
    tick(); clearInterval(ldTimer); ldTimer = setInterval(tick, 900);
  } else if (kind !== "lang" && kind !== "demo") {
    ov.innerHTML = `<div class="loading" style="background:rgba(255,252,248,.7)"><div class="lotus">🪷</div><b>${esc(x("ld_other"))}</b></div>`;
  }
}
function hideLoading() { clearInterval(ldTimer); $("#overlay").innerHTML = ""; renderSheet(); }
function scrollTop() { const s = $("#scroll"); if (s) s.scrollTop = 0; }

/* ------------------------------------------------------------------ 공통 조각 */
function header() {
  const l = B.langs.find((v) => v.id === lang());
  return `<div class="top"><div class="logo">🪷</div><div class="brand"><div class="nm">${lang() === "ko" ? "한 절 더" : "Han Jeol Deo"}</div><div class="tg">TEMPLE · STORY · WALK</div></div>
    <button class="pill" data-act="sheet" data-v="lang">🌐 ${esc(lang().toUpperCase())}</button>
    <button class="iconbtn" data-act="sheet" data-v="demo" title="${esc(x("set_t"))}">⚙️</button></div>
    <div class="wx"><div><div class="t">${esc(C.line1)}</div><div class="s">🌇 ${esc(C.line2)}</div></div>
    <div class="src">${lang() === "ko" ? esc(C.source) : ""}${demoTime() ? `<br>⏰ ${esc(DEMO.time)}` : ""}</div></div>`;
}
function shopCard(s) {
  const badge = s.partner === "후보" ? ` · <b>${esc(t("rest_soon"))}</b>` : s.partner === "제휴" ? ` · <b>${esc(t("rest_partner"))}</b>` : "";
  const coupon = s.coupon ? ` · 🎟️ ${esc(s.coupon)}` : "";
  return `<div class="shop"><div class="k">${KIND_EMOJI[s.kind] || "📍"}</div><div style="flex:1;min-width:0">
    <div class="nm">${esc(s.name)} <span class="muted small" style="font-weight:600">${esc(s.kindLabel)} · ${esc(s.src)}${badge}${coupon}</span></div>
    <div class="why">${(s.why || []).map(esc).join(" · ")}</div>
    <div class="acts"><a class="mini sage" href="${esc(s.url)}" target="_blank" rel="noopener">🧭 ${esc(s.from ? x("from_here", { n: s.from }) : t("rest_dir"))} ›</a></div></div></div>`;
}
function stepsHtml(lg, open) {
  if (!lg.steps || !lg.steps.length) return "";
  const li = lg.steps.map((v, i) => `<li><span class="sn">${i + 1}</span><span>${esc(v)}</span></li>`).join("");
  return `<details class="dirs" ${open ? "open" : ""}><summary>${esc(x("dir_t"))}</summary><ol>${li}</ol>${lg.detailed ? "" : `<div class="small muted">${esc(x("dir_rough"))}</div>`}</details>`;
}
function stopIcon(id, n) {
  const k = P(id).kind;
  return `<div class="ic" style="background:${B.pins.color[k]}22">${icon(k, 26)}${n != null ? `<span class="n">${n}</span>` : ""}</div>`;
}
function routeLine(stops) { return stops.map((id) => esc(pname(id))).join(" › "); }

/* ------------------------------------------------------------------ 1) 고르기 */
function setupView() {
  const c = S.choice;
  const tip = C.rain ? x("tip_rain") : C.cold ? x("tip_cold") : C.hot ? x("tip_hot") : x("tip_clear");
  const endAt = (() => { const e = clockAdd(nowDate(), c.minutes); const ss = sunsetDate(); return hhmm(e > ss ? clockAdd(ss, -20) : e); })();
  const pct = ((c.minutes - 30) / (300 - 30)) * 100;
  const q = S.qr ? P(S.qr) : null;
  const qrCard = q ? `<div class="card qr"><div class="eyebrow">${esc(x("qr_here"))}</div>
      <div class="row">${icon(q.kind, 40)}<div style="flex:1;min-width:0"><h3>${esc(q.name)}</h3><div class="small muted">${esc(lab("icon", q.kind))} · ${esc(q.era)}</div></div>
      <button class="mini" data-act="sheet" data-v="qr">${esc(x("qr_other"))}</button></div>
      <p class="small" style="margin:8px 0 0">${esc(q.short)}</p><div class="qrnote">🧭 ${esc(x("qr_from"))}</div></div>`
    : `<div class="card qr scan"><div style="font-size:42px;line-height:1">📷</div><h3 style="margin-top:6px">${esc(x("qr_t"))}</h3><p class="sub" style="margin:4px 0 12px">${esc(x("qr_s"))}</p>
      <button class="btn coral sm" data-act="scan">${esc(x("qr_cam"))}</button><div style="height:8px"></div>
      <button class="btn ghost sm" data-act="sheet" data-v="qr">${esc(x("qr_demo"))}</button></div>`;
  return `${header()}${qrCard}
  <div class="card"><h2>${esc(x("how"))}</h2>
    <div class="how"><div><span class="num">1</span><b>${esc(x("how1"))}</b><span>${esc(x("how1s"))}</span></div>
    <div><span class="num">2</span><b>${esc(x("how2"))}</b><span>${esc(x("how2s"))}</span></div>
    <div><span class="num">3</span><b>${esc(x("how3"))}</b><span>${esc(x("how3s"))}</span></div></div></div>
  <div class="hero"><div class="sun"></div><div class="emoji">${C.rain ? "☔" : C.cold ? "🧣" : "🪷"}</div>
    <div class="eyebrow">${esc(x("hero_ey"))}</div><h1>${esc(q ? x("hero_q", { n: q.name }) : x("hero_t"))}</h1><p>${esc(x("hero_s"))}</p><span class="tip">${esc(tip)}</span></div>
  <div class="card"><div class="between"><div><h2>${esc(x("make"))}</h2><p class="sub">${esc(x("make_s"))}</p></div><span style="font-size:26px">🧭</span></div>
    <div class="step"><span class="num">1</span>${esc(x("q_who"))}</div>
    <div class="chips">${B.opts.who.map((w) => `<button class="chip ${c.who === w ? "on" : ""}" data-act="who" data-v="${esc(w)}">${esc(lab("who2", w))}</button>`).join("")}</div>
    <div class="step"><span class="num">2</span>${esc(x("q_time"))}</div>
    <div class="timebox"><div class="timebig" id="timebig">${timeBig(c.minutes)}</div>
      <div class="timeend" id="timeend">${esc(x("end_at", { t: endAt }))}</div>
      <div class="timerow"><button class="stepbtn" data-act="time" data-v="-5">${esc(x("minus"))}</button>
        <input type="range" id="trange" min="30" max="300" step="5" value="${c.minutes}" style="--p:${pct}%">
        <button class="stepbtn" data-act="time" data-v="5">${esc(x("plus"))}</button></div>
      <div class="ticks"><span>30${lang() === "en" ? "m" : lang() === "ko" ? "분" : "分"}</span><span>${esc(t("h", { h: 2 }))}</span><span>${esc(t("h", { h: 5 }))}</span></div>
      <div class="chips" style="justify-content:center;margin-top:8px">${[60, 90, 120, 180, 240].map((m) => `<button class="chip sm ${c.minutes === m ? "on" : ""}" data-act="timeset" data-v="${m}">${esc(fmtMin(m))}</button>`).join("")}</div></div>
    <div class="step"><span class="num">3</span>${esc(x("q_level"))}</div>
    <div class="levels">${B.opts.level.map((lv) => { const [a, ...b] = lab("level2", lv).split("·"); return `<button class="level ${c.level === lv ? "on" : ""}" data-act="level" data-v="${esc(lv)}"><b>${esc(a.trim())}</b><span>${esc(b.join("·").trim())}</span></button>`; }).join("")}</div>
    <div class="step"><span class="num">4</span>${esc(x("q_int"))} <span class="opt">${esc(x("q_int_s"))}</span></div>
    <div class="chips wrap">${B.opts.interest.map((it) => `<button class="chip coral ${c.interests.includes(it) ? "on" : ""}" data-act="int" data-v="${esc(it)}">${esc(lab("interest2", it))}</button>`).join("")}</div>
    <div class="step"><span class="num">5</span>${esc(x("q_free"))} <span class="opt">${esc(x("q_free_s"))}</span></div>
    <textarea id="free" maxlength="300" placeholder="${esc(x("free_ph"))}">${esc(c.free)}</textarea>
    <div class="sub" style="margin:6px 0 4px">${esc(x("ex"))}</div>
    <div class="chips">${B.examples.map((e) => `<button class="chip sm" data-act="ex" data-v="${esc(e)}">+ ${esc(e)}</button>`).join("")}</div>
    <div style="height:14px"></div>
    <button class="btn coral" data-act="plan">${esc(x("go"))}</button></div>`;
}
function timeBig(m) {
  const h = Math.floor(m / 60), mm = m % 60;
  const hu = { ko: "시간", en: "h", ja: "時間", zh: "小时" }[lang()], mu = { ko: "분", en: "min", ja: "分", zh: "分钟" }[lang()];
  return (h ? `<span class="v">${h}</span><span class="u">${hu}</span>` : "") + `<span class="v">${String(mm).padStart(h ? 2 : 1, "0")}</span><span class="u">${mu}</span>`;
}

/* ------------------------------------------------------------------ 2) 추천 보기 */
function planView() {
  const pl = S.plan, c = pl.cands[S.cand];
  const stops = c.stops.map((s) => s.id);
  const tabs = pl.cands.map((r, i) => `<button class="${i === S.cand ? "on" : ""}" data-act="cand" data-v="${i}">${r.picked ? esc(x("ai_pick")) : esc(x("cand", { n: i + 1 }))}<small>${esc(fmtMin(r.totalMin))} · ${(r.dist / 1000).toFixed(1)}km</small></button>`).join("");
  const reasons = c.reasons.map((r) => `<div class="reason"><i>✔️</i><span>${esc(r)}</span></div>`).join("");
  const notes = pl.notes.map((n) => `<div class="reason"><i>•</i><span>${esc(n)}</span></div>`).join("");
  const chip = pl.planner === "agent" ? `<span class="tag lav">${esc(t("chip_agent"))}</span>` : `<span class="tag">${esc(t("chip_rule"))}</span>`;
  const tl = [];
  c.stops.forEach((s, i) => {
    const p = P(s.id);
    tl.push(`<div class="stop">${stopIcon(s.id, i + 1)}<div class="body"><b>${esc(p.name)}</b> <span class="tag">${esc(lab("icon", p.kind))}</span><div class="small muted">${esc(s.title)}</div><div class="small" style="margin-top:2px">${esc(p.short)}</div></div></div>`);
    if (i < c.legs.length) {
      const lg = c.legs[i];
      const sh = (c.legShops[i] || []).map(shopCard).join("");
      tl.push(`<div class="leg"><span class="ln">🚶 ${esc(x("walk_leg", { m: Math.round(lg.min), km: (lg.dist / 1000).toFixed(1), g: lg.grade }))}</span>${lg.guessed ? ` <span class="muted">${esc(t("guess"))}</span>` : ""}${stepsHtml(lg, false)}${sh}</div>`);
    }
  });
  if (c.stops.length === 1) tl.push(`<div class="small muted" style="margin:4px 0 0 49px">${esc(x("one_place"))}</div>${(c.stops[0].near || []).map(shopCard).join("")}`);
  const ws = pl.prefs.weights.map(([k, v]) => `<div class="wbar"><span class="lb">${esc(k)}</span><div class="bg"><div class="fg" style="width:${Math.min(100, v * 250)}%"></div></div><span>${Math.round(v * 100)}%</span></div>`).join("");
  const pool = pl.process.pool.map(([id, n, u, th]) => `<tr><td>${icon(P(id).kind, 15)} ${esc(n)}</td><td style="text-align:right">${u.toFixed(2)}</td><td>&nbsp;${esc(th || "-")}</td></tr>`).join("");
  const starts = pl.process.starts.length ? `<div class="pline">${esc(x("starts"))}</div><div>${pl.process.starts.map(([n, u, pt]) => `<span class="tag lav">${esc(n)} ${pt.toFixed(1)}</span>`).join("")}</div>` : "";
  const by = pl.prefs.by === "claude" ? t("by_claude") : t("by_rule");
  return `${header()}
  <div class="backbar"><button data-act="back">${esc(x("back"))}</button></div>
  <div class="cands">${tabs}</div>
  <div class="card"><div class="eyebrow">${esc(t("plan_title"))}</div>
    <div style="font-weight:900;font-size:16.5px;line-height:1.45">${routeLine(stops)}</div>
    <div class="stats"><div class="stat"><div class="v">${(c.dist / 1000).toFixed(1)}km</div><div class="l">${esc(t("stat_dist"))}</div></div>
      <div class="stat"><div class="v">${esc(fmtMin(c.totalMin))}</div><div class="l">${esc(t("stat_total"))}</div></div>
      <div class="stat"><div class="v">${stops.length}</div><div class="l">${esc(t("stat_pieces"))}</div></div></div>
    <div style="margin-top:8px">${chip}${pl.prefs.tops.map((v) => `<span class="tag coral">${esc(v)}</span>`).join("")}<span class="tag sky">${esc(lab("who2", S.choice.who))}</span></div></div>
  <div class="map" id="map-plan"></div><div style="height:12px"></div>
  <div class="card"><h2>🤖 ${esc(x("why"))}</h2>${pl.aiReason && c.picked ? `<div class="aiq">💬 ${esc(pl.aiReason)}</div>` : ""}<div style="margin-top:8px">${reasons}${notes}</div>
    <details class="proc"><summary>${esc(t("ai_process"))}</summary>
      <div class="pline">${esc(t("proc_1", { t: pl.prefs.tops.join(" · ") }))}</div><div class="small muted">${esc(t("proc_1b", { by }))}</div>${ws}
      ${pl.prefs.effects.length ? `<div style="margin-top:6px">${pl.prefs.effects.map(([q, e]) => `<span class="tag butter">‘${esc(q)}’ → ${esc(e)}</span>`).join("")}</div>` : ""}
      ${starts}
      <div class="pline">${esc(t("proc_2", { r: pl.process.radius.toFixed(1), k: pl.process.pool.length }))}</div>
      <table class="ptable"><tr class="muted"><td>${esc(t("col_place"))}</td><td style="text-align:right">${esc(t("col_score"))}</td><td>&nbsp;${esc(t("col_theme"))}</td></tr>${pool}</table>
      <div class="pline">${esc(t("proc_3", { e: pl.process.evaluated.toLocaleString(), f: pl.process.feasible.toLocaleString() }))}</div>
      <div class="pline">${esc(t("proc_4"))}</div></details></div>
  <div class="card"><h2>${esc(x("course"))}</h2><div class="tl">${tl.join("")}</div>
    ${c.legShops.some((v) => v.length) ? `<p class="sub" style="margin-top:8px">${esc(t("shops_title"))}</p>` : ""}</div>
  <button class="btn coral" data-act="startwalk">${esc(x("start_btn"))}</button><div style="height:10px"></div>`;
}

/* ------------------------------------------------------------------ 3) 걷기 */
function beginWalk() {
  const c = S.plan.cands[S.cand];
  const st = nowDate();
  S.walk = { route: c, stops: c.stops.map((s) => s.id), idx: 0, arrived: [c.stops[0].id], arrivedAt: { [c.stops[0].id]: st.toISOString() },
    who: S.choice.who, storyInterest: S.plan.storyInterest, missions: [], memos: {}, moods: {}, photos: {}, events: [],
    walkedM: 0, startTs: st.toISOString(), usedTired: false, bored: 0, stopped: null };
  S.screen = "walk"; S.bored = null; scrollTop();
}
function plannedClock(i) {
  const w = S.walk, r = w.route;
  let m = 0;
  for (let k = 0; k < i && k < r.legs.length; k++) m += r.legs[k].min + 15;
  return clockAdd(new Date(w.startTs), m);
}
function walkView() {
  const w = S.walk, r = w.route, i = w.idx;
  const s = r.stops[i], p = P(s.id);
  const total = r.stops.length;
  const dots = `<div class="dots">${r.stops.map((_, k) => `<span class="${k < w.arrived.length ? "on" : ""}"></span>`).join("")}<em>${esc(t("dots", { a: w.arrived.length, b: total }))}</em></div>`;
  const status = { ok: `<span class="tag sage">${esc(t("st_ok"))}</span>`, review: `<span class="tag butter">${esc(t("st_review"))}</span>`, pending: `<span class="tag">${esc(t("st_pending"))}</span>` }[s.status] || "";
  const src = s.sources.length ? `<div class="src">${esc(t("sources"))}: ${s.sources.map((v) => `<a href="${esc(v.url)}" target="_blank" rel="noopener">${esc(v.title)}</a>`).join(" · ")}</div>` : "";
  const photo = w.photos[s.id];
  const mood = w.moods[s.id];
  const seasons = (s.seasonNow || []).map((v) => `<div class="card season"><div class="eyebrow" style="color:#9A7414">${esc(t("season_open", { label: v.label }))}</div><div>${esc(v.text)}</div></div>`).join("") +
    (s.seasonLater || []).map((v) => `<p class="sub">${esc(t("season_later", { months: v.months, label: v.label }))}</p>`).join("");
  let next = "";
  if (i < total - 1) {
    const n = r.stops[i + 1], lg = r.legs[i];
    const sh = (r.legShops[i] || []).map(shopCard).join("");
    next = `<div class="card next"><div class="eyebrow" style="color:#33658F">${esc(t("next"))}</div>
      <div class="row">${icon(P(n.id).kind, 26)}<h3>${esc(pname(n.id))}</h3></div>
      <div class="small" style="margin-top:4px">🚶 ${esc(x("walk_leg", { m: Math.round(lg.min), km: (lg.dist / 1000).toFixed(1), g: lg.grade }))}</div>
      ${s.teaser ? `<div class="teaser">📖 ${esc(s.teaser)}</div>` : ""}${stepsHtml(lg, true)}${sh}
      <div class="src" style="margin-top:8px"><a href="${esc(r.kakaoLegs[i])}" target="_blank" rel="noopener">${esc(t("kakao_walk"))}</a></div></div>
      <div class="map" id="map-walk" style="height:210px"></div><div style="height:12px"></div>
      <button class="btn coral" data-act="arrive">${esc(t("arrive", { n: pname(n.id) }))}</button>
      <div class="btns3"><button class="btn ghost" data-act="tired">${esc(x("tired"))}</button><button class="btn ghost" data-act="bored">${esc(x("bored"))}</button><button class="btn ghost" data-act="sheet" data-v="stop">${esc(x("stop"))}</button></div>
      ${S.bored ? boredPanel() : ""}`;
  } else {
    next = `<div class="card season"><h3>${esc(t("last_title"))}</h3><p style="margin:6px 0 0">${esc(t("last_body"))}</p></div>
      ${(s.near || []).length ? `<div class="card"><h2>${esc(x("nearby"))}</h2>${s.near.map(shopCard).join("")}</div>` : ""}
      <button class="btn coral" data-act="finish">${esc(t("finish"))}</button>`;
  }
  return `${header()}${dots}
  <div class="card"><div class="eyebrow">${esc(t("here"))} · ${esc(s.title)}</div>
    <div class="row">${icon(p.kind, 30)}<h3>${esc(p.name)}</h3></div>
    ${s.diff ? `<div class="diff">${esc(t("diff"))} · ${esc(s.diff)}</div>` : ""}
    <div style="margin-top:8px"><span class="tag butter">${esc(t("interest_story", { i: lab("interest", w.storyInterest) }))}</span>${status}</div>
    <div class="story">${esc(s.story)}</div>${src}
    <div style="margin-top:10px"><button class="mini coral" data-act="speak">${esc(x("listen"))}</button></div></div>
  <div class="card mission"><div class="eyebrow" style="color:#3F7A55">${esc(t("mission"))}</div><div>${esc(s.mission)}</div>
    <label class="check"><input type="checkbox" data-act="mission" ${w.missions.includes(s.id) ? "checked" : ""}> ${esc(t("mission_done"))}</label></div>
  <div class="card"><input type="text" id="memo" placeholder="${esc(x("memo"))}" value="${esc(w.memos[s.id] || "")}" maxlength="80">
    <div class="small muted" style="margin-top:10px">${esc(t("mood_q"))}</div>
    <div class="moods">${B.opts.mood.map((m) => `<button class="${mood === m ? "on" : ""}" data-act="mood" data-v="${m}">${m}</button>`).join("")}</div>
    <div class="photo">${photo ? `<img src="${photo}" alt="">` : ""}<label class="upload">${esc(photo ? x("photo2") : x("photo"))}<input type="file" accept="image/*" data-act="photo"></label></div></div>
  ${seasons}${next}`;
}
function boredPanel() {
  const b = S.bored, w = S.walk;
  const alts = b.alts.length ? b.alts.map((a) => `<div class="shop"><div class="k">${icon(P(a.id).kind, 26)}</div><div style="flex:1"><div class="nm">${esc(pname(a.id))}</div>
    <div class="why">${esc(t("alt_near", { km: a.km.toFixed(1), t: a.theme }))}</div>
    <div class="acts"><button class="mini sage" data-act="swap" data-v="${a.id}">${esc(x("swap_to"))}</button></div></div></div>`).join("") : `<p class="sub">${esc(x("no_alt"))}</p>`;
  return `<div class="card season" style="margin-top:10px"><div class="eyebrow" style="color:#9A7414">${esc(t("bored_title"))}</div>${alts}
    ${b.near.length ? `<div class="pline" style="margin-top:10px">${esc(x("nearby"))}</div>${b.near.map(shopCard).join("")}` : ""}</div>`;
}
function arrive() {
  const w = S.walk, r = w.route, i = w.idx;
  const n = r.stops[i + 1].id;
  w.walkedM += r.legs[i].dist;
  w.idx += 1;
  w.arrived.push(n);
  w.arrivedAt[n] = (demoTime() ? plannedClock(i + 1) : new Date()).toISOString();
  S.bored = null;
  scrollTop();
}
function tired() {
  const w = S.walk, i = w.idx;
  w.usedTired = true;
  if (w.stops.length - i - 1 >= 2) {
    const skipped = w.stops[i + 1];
    const ns = w.stops.slice(0, i + 1).concat(w.stops.slice(i + 2));
    w.events.push({ type: "tired", at: w.stops[i], skipped });
    ask("route", { stops: ns, who: w.who, storyInterest: w.storyInterest }, { toast: t("toast_skip", { a: pname(skipped), b: pname(ns[i + 1]) }) });
  } else {
    w.events.push({ type: "tired", at: w.stops[i] });
    toast(t("toast_slow"));
  }
}
function swap(id) {
  const w = S.walk, i = w.idx;
  const from = w.stops[i + 1];
  const ns = w.stops.slice(0, i + 1).concat([id], w.stops.slice(i + 2).filter((v) => v !== id));
  w.events.push({ type: "swap", from, to: id, at: w.stops[i] });
  w.bored += 1;
  S.bored = null;
  ask("route", { stops: ns, who: w.who, storyInterest: w.storyInterest }, { toast: t("toast_swap", { n: pname(id) }) });
}
function finishWalk(stopped, again) {
  const w = S.walk;
  if (!again) {
    w.stopped = stopped || null;
    const last = w.arrived.length - 1;
    w.endTs = (demoTime() ? clockAdd(plannedClock(last), stopped ? 0 : 15) : new Date()).toISOString();
    saveLog(w);
  }
  ask("finish", { walk: { stops: w.stops, legs: w.route.legs, totalMin: w.route.totalMin, arrived: w.arrived, who: w.who,
    storyInterest: w.storyInterest, missions: w.missions, walkedM: w.walkedM, startTs: w.startTs, endTs: w.endTs,
    memos: w.memos, moods: w.moods, photos: Object.keys(w.photos), events: w.events, stopped: w.stopped,
    usedTired: w.usedTired, bored: w.bored } });
}
function saveLog(w) {
  try {
    const k = "hanjeolde_logs";
    const logs = JSON.parse(localStorage.getItem(k) || "[]");
    logs.push({ at: new Date().toISOString(), stops: w.stops, arrived: w.arrived, stopped: w.stopped });
    localStorage.setItem(k, JSON.stringify(logs.slice(-50)));
  } catch (e) { /* 저장소를 못 쓰는 환경 */ }
}
function speak(text) {
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = B.tts; u.rate = 0.95;
    speechSynthesis.speak(u);
  } catch (e) { toast("🔇"); }
}

/* ------------------------------------------------------------------ 4) 일지 · 엽서 */
function firstPhoto() { const w = S.walk; if (!w) return null; const k = w.arrived.find((p) => w.photos[p]); return k ? w.photos[k] : null; }
function doneView() {
  const d = S.done, w = S.walk, s = d.stats;
  const photos = w.arrived.filter((p) => w.photos[p]);
  const st = d.story;
  const recs = d.recs.map((r) => `<div class="card ${r.kind === "new" ? "next" : ""}"><span class="tag ${r.kind === "new" ? "sky" : "coral"}">${esc(t(r.kind === "new" ? "rec_new" : "rec_similar"))}</span>
    <h3 style="margin-top:4px">${esc(r.title)}</h3><p class="sub">${esc(r.sub)}</p><div class="small" style="margin-top:6px">${routeLine(r.stops)}</div>
    <div class="reason"><i>💡</i><span>${esc(r.reason)}</span></div>
    <button class="btn ghost sm" data-act="recgo" data-v="${esc(r.stops[0])}">${esc(t("rec_go", { t: r.title }))}</button></div>`).join("");
  const thumbs = photos.map((p) => `<button class="${S.pcPhoto === w.photos[p] ? "on" : ""}" data-act="pcphoto" data-v="${p}"><img src="${w.photos[p]}" alt=""></button>`).join("");
  return `${header()}
  <div class="card cover"><div class="eyebrow">${esc(t("journal"))}</div><h3>${esc(st.title)}</h3>
    <div style="margin-top:6px"><span class="tag">${esc(C.line1)}</span><span class="tag sky">${esc(lab("who2", w.who))}</span>${w.stopped ? `<span class="tag butter">${esc(lab("stop", w.stopped))}</span>` : `<span class="tag sage">${esc(x("done_t"))}</span>`}</div>
    <div class="stats four"><div class="stat"><div class="v">${s.km.toFixed(1)}</div><div class="l">km</div></div><div class="stat"><div class="v">${esc(fmtMin(s.minutes))}</div><div class="l">${esc(t("pc_time"))}</div></div>
      <div class="stat"><div class="v">${s.steps.toLocaleString()}</div><div class="l">${esc(t("pc_steps"))}</div></div><div class="stat"><div class="v">${s.pieces}/${s.total}</div><div class="l">${esc(t("stat_pieces"))}</div></div></div>
    ${d.badges.length ? `<div class="pline">${esc(t("jr_badges"))}</div>${d.badges.map((b) => `<span class="badge">${b.emoji} ${esc(b.label)}</span>`).join("")}` : ""}</div>
  <div class="card book"><div class="between"><span class="tag ${d.byClaude ? "lav" : ""}">${esc(d.byClaude ? x("story_by_ai") : x("story_rule"))}</span><button class="mini coral" data-act="speakstory">🔊</button></div>
    <h3>📖 ${esc(st.title)}</h3>${st.paras.map((p) => `<p>${esc(p)}</p>`).join("")}</div>
  <div class="card"><h2>${esc(x("pc"))}</h2><p class="sub">${esc(x("pc_s"))}</p>
    <div class="pline">${esc(x("pc_pick"))}</div>
    <div class="thumbs">${thumbs}<label class="upload" style="width:68px;height:68px;justify-content:center;padding:0;font-size:24px">+<input type="file" accept="image/*" data-act="pcupload"></label></div>
    ${photos.length || S.pcPhoto ? "" : `<p class="sub">${esc(x("pc_none"))}</p>`}
    <div style="margin-top:10px"><canvas class="pc" id="pc"></canvas></div>
    <div style="display:grid;grid-template-columns:2fr 1fr;gap:8px;margin-top:10px"><button class="btn coral sm" data-act="pcdl">${esc(x("pc_dl"))}</button><button class="btn ghost sm" data-act="pcshare">${esc(x("pc_share"))}</button></div>
    <p class="sub" style="margin-top:6px">${esc(x("pc_hold"))}</p><img id="pcimg" style="display:none;width:100%;margin-top:8px;border-radius:10px" alt=""></div>
  ${recs ? `<div class="step">${esc(x("rec"))}</div>${recs}` : ""}
  ${d.near.length ? `<div class="card"><h2>${esc(x("near_end"))}</h2>${d.near.map(shopCard).join("")}</div>` : ""}
  <button class="btn ghost" data-act="home">${esc(x("home"))}</button><div style="height:8px"></div>`;
}
async function drawCard() {
  const cv = $("#pc");
  if (!cv || !S.done) return;
  const w = S.walk, d = S.done;
  const memo = w.arrived.map((p) => w.memos[p]).filter(Boolean)[0];
  const last = w.arrived[w.arrived.length - 1];
  const photoPid = w.arrived.find((p) => w.photos[p] === S.pcPhoto);
  await Postcard.draw(cv, {
    lang: lang(), photo: S.pcPhoto, place: pname(photoPid || last), kind: P(photoPid || last).kind,
    date: nowDate(), rain: C.rain, cold: C.cold, hot: C.hot, season: C.season,
    greet: x("pc_greet"), to: x("pc_to"), from: x("pc_from"),
    lines: [d.story.title, x("pc_msg1", { n: w.arrived.length, km: d.stats.km.toFixed(1) }), memo ? `“${memo}”` : "", x("pc_msg2")].filter(Boolean),
    stampSvg: B.pins.inner[P(photoPid || last).kind], stampColor: B.pins.color[P(photoPid || last).kind],
  });
}

/* ------------------------------------------------------------------ 지도 탭 */
function mapView() {
  const kinds = S.mapKinds || B.pins.legend.slice();
  const sel = S.mapSel ? P(S.mapSel) : null;
  return `${header()}<div class="card"><h2>${esc(x("map_t"))}</h2><p class="sub">${esc(x("map_s"))} · ${esc(t("map_caption", { n: B.places.length }))}</p>
    <div class="chips" style="margin-top:8px">${B.pins.legend.map((k) => `<button class="chip sm ${kinds.includes(k) ? "on" : ""}" data-act="kind" data-v="${k}">${icon(k, 16)} ${esc(lab("icon", k))}</button>`).join("")}</div></div>
    <div class="map tall" id="map-all"></div><div style="height:12px"></div>
    ${sel ? `<div class="card"><div class="row">${icon(sel.kind, 30)}<div><h3>${esc(sel.name)}</h3><div class="small muted">${esc(sel.era)} · ${esc(lab("icon", sel.kind))}</div></div></div>
      <p style="margin:10px 0 8px;font-size:14px">${esc(sel.desc)}</p><div class="row"><a class="mini" href="${esc(sel.kakao)}" target="_blank" rel="noopener">${esc(x("kakao"))} ›</a>
      ${sel.id !== "campus" ? `<button class="mini coral" data-act="mapstart" data-v="${sel.id}">📷 ${esc(x("start_here"))}</button>` : ""}</div></div>` : ""}`;
}

/* ------------------------------------------------------------------ AI 비교 탭 */
function compareView() {
  const c = S.choice;
  const startId = S.qr || "bunhwangsa";
  const base = `<span class="tag sky">${esc(lab("who2", c.who))}</span><span class="tag">${esc(fmtMin(c.minutes))}</span><span class="tag">${esc(lab("level2", c.level).split("·")[0])}</span>${c.interests.map((v) => `<span class="tag coral">${esc(lab("interest2", v))}</span>`).join("")}<span class="tag lav">📍 ${esc(pname(startId))}</span>`;
  let grid = "";
  const seg = `<div class="seg" style="margin-top:10px"><button class="${S.cmpMode === "time" ? "on" : ""}" data-act="cmpmode" data-v="time">${esc(x("cmp_m1"))}</button><button class="${S.cmpMode === "qr" ? "on" : ""}" data-act="cmpmode" data-v="qr">${esc(x("cmp_m2"))}</button></div>`;
  if (S.compare && S.compare.mode === "qr" && S.cmpMode === "qr") {
    const d = S.compare;
    grid = `<div class="card"><p class="sub">${esc(x("cmp_qr_s"))}</p><div class="tag coral" style="margin-top:6px">${esc(x("cmp_used", { n: d.rows.length, m: d.used }))}</div>
      ${d.notes.map((n) => `<div class="reason small"><i>•</i><span>${esc(n)}</span></div>`).join("")}</div>
      ${d.rows.map((r) => `<div class="cell" style="margin-bottom:8px;min-height:0"><div class="between"><span class="w">${icon(P(r.qr).kind, 18)} ${esc(x("cmp_from", { n: pname(r.qr) }))}</span><span class="mt">${esc(fmtMin(r.totalMin))} · ${(r.dist / 1000).toFixed(1)}km</span></div>
        <div class="rt">${r.stops.map((id, i) => `${i ? "<span class='muted'> › </span>" : ""}${icon(P(id).kind, 14)} ${esc(pname(id))}`).join("")}</div>
        ${r.why ? `<div class="small muted">${esc(r.why)}</div>` : ""}</div>`).join("")}`;
  } else if (S.compare && S.compare.mode !== "qr" && S.cmpMode === "time") {
    grid = S.compare.grid.map((row) => {
      const sunny = row.cells[0];
      const left = Math.max(0, row.cells[0].budget);
      return `<div class="timeh">🕘 ${esc(row.time)}<div class="bar"><i style="width:${Math.min(100, (left / Math.max(c.minutes, 1)) * 100)}%"></i></div><span class="small muted">${esc(x("cmp_left", { m: left, s: sunny.sunset }))}</span></div>
      <div class="grid4">${row.cells.map((cell) => {
        const changed = cell.stops.join() !== sunny.stops.join();
        const tags = cell.tags.map((tg) => `<span class="tag ${tg === "indoor_end" ? "sky" : tg === "nearest" ? "butter" : "sage"}">${esc(x("t_" + tg))}</span>`).join("");
        return `<div class="cell ${changed ? "changed" : ""}"><div class="between"><span class="w">${esc(x("w_" + cell.weather))}</span>${changed ? `<span class="tag coral" style="margin:0">${esc(x("cmp_changed"))}</span>` : ""}</div>
          <div class="rt">${cell.stops.map((id, i) => `${icon(P(id).kind, 14)} ${esc(pname(id))}`).join("<br>")}</div>
          <div class="mt">${esc(fmtMin(cell.totalMin))} · ${(cell.dist / 1000).toFixed(1)}km</div>${tags}</div>`;
      }).join("")}</div>`;
    }).join("");
  }
  return `${header()}<div class="card"><h2>🧪 ${esc(x("cmp"))}</h2><p class="sub">${esc(x("cmp_s"))}</p>
    <div class="pline">${esc(x("cmp_base"))}</div><div>${base}</div>
    ${S.plan ? "" : `<p class="sub" style="margin-top:6px">${esc(x("cmp_need"))}</p>`}
    <div class="pline">${esc(x("cmp_rules"))}</div>
    <div class="rules"><div>${esc(x("rule_rain"))}</div><div>${esc(x("rule_cold"))}</div><div>${esc(x("rule_hot"))}</div><div>${esc(x("rule_sun"))}</div></div>
    ${seg}<div style="height:12px"></div><button class="btn coral sm" data-act="compare" data-v="${startId}">${esc(S.cmpMode === "qr" ? x("cmp_go2") : x("cmp_go"))}</button></div>${grid}`;
}

/* ------------------------------------------------------------------ 기록 탭 (⑥ 중단 분석) */
function logView() {
  const a = B.analysis;
  if (!a) return `${header()}<div class="empty">${esc(t("no_seg"))}</div>`;
  const rows = (S.fixOn ? a.after : a.before);
  const ob = a.overallBefore, oa = a.overallAfter;
  const bars = rows.map((r, k) => `<div class="segbar ${r.seg === a.worst.seg && !S.fixOn ? "bad" : ""}"><div class="between small" style="font-weight:800"><span>${esc(r.name)}</span><span>${r.rate.toFixed(0)}%</span></div>
    <div class="bg"><div class="fg" style="width:${r.rate}%"></div></div><div class="small muted">${esc(t("seg_line", { a: r.in, b: r.arr }))}${r.why ? esc(t("seg_why", { r: r.why })) : ""}</div></div>`).join("");
  let mine = [];
  try { mine = JSON.parse(localStorage.getItem("hanjeolde_logs") || "[]"); } catch (e) { /* */ }
  return `${header()}<div class="card"><h2>📊 ${esc(x("log_t"))}</h2><p class="sub">${esc(x("log_s"))}</p>
    <div class="tag butter" style="margin-top:8px">${esc(t("v_banner"))}</div>
    <div class="stats"><div class="stat"><div class="v">${(S.fixOn ? oa : ob).starts}</div><div class="l">${esc(t("s_starts"))}</div></div>
      <div class="stat"><div class="v">${(S.fixOn ? oa : ob).rate.toFixed(0)}%</div><div class="l">${esc(t("s_rate"))}</div></div>
      <div class="stat"><div class="v">${rows.reduce((s, r) => s + r.stops, 0)}</div><div class="l">${esc(t("s_stops"))}</div></div></div></div>
  <div class="card"><h2>${esc(t("seg_title"))}</h2>${bars}</div>
  <div class="card season"><div class="eyebrow" style="color:#9A7414">${esc(t("worst"))}</div><h3>${esc(a.worst.name)}</h3>
    <p style="margin:6px 0">${t("worst_line", { r: a.worst.rate.toFixed(0), w: esc(a.worst.why) })}</p>
    <div class="reason"><i>🛠</i><span>${esc(t("fix_sugg", { t: a.worst.sugg }))}</span></div>
    ${S.fixOn ? `<div class="stats" style="grid-template-columns:1fr 1fr"><div class="stat"><div class="v">${a.worst.rate.toFixed(0)}→${(a.worst.after || 0).toFixed(0)}%</div><div class="l">${esc(t("cmp_seg", { d: ((a.worst.after || 0) - a.worst.rate).toFixed(0) }))}</div></div>
      <div class="stat"><div class="v">${ob.rate.toFixed(0)}→${oa.rate.toFixed(0)}%</div><div class="l">${esc(t("cmp_all", { d: (oa.rate - ob.rate).toFixed(0) }))}</div></div></div>` : ""}
    <div style="height:8px"></div><button class="btn ${S.fixOn ? "ghost" : "coral"} sm" data-act="fix">${esc(S.fixOn ? x("undo") : x("apply"))}</button></div>
  <div class="card"><h2>${esc(x("my_log"))}</h2>${mine.length ? mine.slice(-5).reverse().map((m) => `<div class="small" style="margin:6px 0">• ${esc(m.at.slice(0, 16).replace("T", " "))} · ${m.arrived.length}/${m.stops.length} ${m.stopped ? "· " + esc(lab("stop", m.stopped)) : "✔"}</div>`).join("") : `<p class="sub">${esc(t("real_empty"))}</p>`}</div>`;
}

/* ------------------------------------------------------------------ 시트 (언어 · 발표 설정 · 그만하기) */
function renderSheet() {
  const ov = $("#overlay");
  if (S.pending) return;
  if (!S.sheet) { ov.innerHTML = ""; return; }
  let body = "";
  if (S.sheet === "lang") {
    body = `<h2>🌐 ${esc(x("lang"))}</h2>${B.langs.map((l) => `<button class="btn ${l.id === lang() ? "" : "ghost"}" style="margin-bottom:8px" data-act="lang" data-v="${l.id}">${esc(l.name)}</button>`).join("")}`;
  } else if (S.sheet === "demo") {
    const ws = ["실시간", "맑음", "비", "영하", "폭염"], ts = ["지금", "10:00", "13:00", "15:30", "16:30"];
    const wl = (v) => (v === "실시간" ? x("live") : x("w_" + v));
    body = `<h2>⚙️ ${esc(x("set_t"))}</h2>
      <div class="pline">${esc(x("set_w"))}</div><div class="chips wrap">${ws.map((v) => `<button class="chip sm ${DEMO.weather === v ? "on" : ""}" data-act="dw" data-v="${v}">${esc(wl(v))}</button>`).join("")}</div>
      <div class="pline">${esc(x("set_time"))}</div><div class="chips wrap">${ts.map((v) => `<button class="chip sm ${(DEMO.time || "지금") === v ? "on" : ""}" data-act="dt" data-v="${v}">${esc(v === "지금" ? x("now") : v)}</button>`).join("")}</div>
      <div class="pline">${esc(x("set_m"))}</div><div class="chips wrap"><button class="chip sm ${!DEMO.month ? "on" : ""}" data-act="dm" data-v="">${esc(x("now"))}</button>${[1, 4, 7, 10].map((m) => `<button class="chip sm ${DEMO.month === m ? "on" : ""}" data-act="dm" data-v="${m}">${m}</button>`).join("")}</div>
      <div style="height:14px"></div><button class="btn" data-act="demoapply">${esc(x("apply_btn"))}</button>`;
  } else if (S.sheet === "qr") {
    const groups = B.pins.legend.filter((k) => k !== "start").map((k) => {
      const ps = B.places.filter((p) => p.kind === k && p.id !== "campus");
      return ps.length ? `<div class="pline">${icon(k, 16)} ${esc(lab("icon", k))}</div><div class="chips wrap">${ps.map((p) => `<button class="chip sm ${S.qr === p.id ? "on" : ""}" data-act="qrpick" data-v="${p.id}">${esc(p.name)}</button>`).join("")}</div>` : "";
    }).join("");
    body = `<h2>📷 ${esc(x("qr_list"))}</h2><button class="btn coral sm" data-act="scan">${esc(x("qr_cam"))}</button><div id="qrcam"></div>${groups}`;
  } else if (S.sheet === "stop") {
    body = `<h2>${esc(x("stop_q"))}</h2>${B.opts.stop.map((k) => `<button class="btn ghost" style="margin-bottom:8px;justify-content:flex-start" data-act="stopwhy" data-v="${esc(k)}">${esc(lab("stop", k))}</button>`).join("")}`;
  }
  ov.innerHTML = `<div class="sheet-bg" data-act="closesheet"><div class="sheet" data-stop="1">${body}<div style="height:6px"></div><button class="btn ghost sm" data-act="closesheet">${esc(x("close"))}</button></div></div>`;
}
let demoDraft = null;

/* ------------------------------------------------------------------ 그리기 */
function render() {
  if (!B) return;
  maps.splice(0).forEach((m) => { try { m.remove(); } catch (e) { /* */ } });
  const sc = $("#scroll");
  const keep = sc.scrollTop;
  let html = "";
  if (S.tab === "walk") html = S.screen === "plan" && S.plan ? planView() : S.screen === "walk" && S.walk ? walkView() : S.screen === "done" && S.done ? doneView() : setupView();
  else if (S.tab === "map") html = mapView();
  else if (S.tab === "cmp") html = compareView();
  else html = logView();
  sc.innerHTML = html;
  sc.scrollTop = keep;
  $("#tabbar").innerHTML = [["walk", "🚶", x("tab1")], ["map", "🗺️", x("tab2")], ["cmp", "🧪", x("tab3")], ["log", "📊", x("tab4")]]
    .map(([k, i, l]) => `<button class="${S.tab === k ? "on" : ""}" data-act="tab" data-v="${k}"><span class="i">${i}</span>${esc(l)}</button>`).join("");
  document.documentElement.lang = lang();
  setTimeout(afterRender, 0);
}
function afterRender() {
  if (typeof L === "undefined") return;
  if ($("#map-plan") && S.plan) { const c = S.plan.cands[S.cand]; routeMap("map-plan", c, null, c.legShops.flat()); }
  if ($("#map-walk") && S.walk) { const r = S.walk.route; routeMap("map-walk", r, S.walk.arrived, r.legShops[S.walk.idx] || [], S.walk.idx); }
  if ($("#map-all")) allMap();
  if ($("#pc")) drawCard();
}
function baseMap(id) {
  const m = L.map(id, { zoomControl: true, attributionControl: true, scrollWheelZoom: false, touchZoom: true, doubleClickZoom: true, tap: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(m);
  m.zoomControl.setPosition("bottomright");
  const box = document.getElementById(id);
  box._lmap = m;
  const b = document.createElement("button");
  b.className = "mapbtn"; b.dataset.act = "mapfull"; b.setAttribute("aria-label", x("map_big")); b.textContent = "⤢ " + x("map_big");
  box.appendChild(b);
  maps.push(m);
  return m;
}
function routeMap(id, r, done, shops, focusLeg) {
  const m = baseMap(id);
  const pts = [];
  r.legs.forEach((lg, i) => {
    const a = P(lg.from), b = P(lg.to);
    const line = lg.coords || [[a.lat, a.lon], [b.lat, b.lon]];
    L.polyline(line, { color: "#E8795A", weight: focusLeg === i ? 7 : 5, opacity: focusLeg == null || focusLeg === i ? 0.9 : 0.35, dashArray: lg.coords ? null : "8 10" }).addTo(m);
  });
  (shops || []).forEach((s) => L.marker([s.lat, s.lon], { icon: L.divIcon({ html: `<div class="shopdot">${KIND_EMOJI[s.kind] || "📍"}</div>`, className: "", iconSize: [22, 22], iconAnchor: [11, 11] }) }).bindTooltip(s.name).addTo(m));
  r.stops.forEach((s, i) => {
    const p = P(s.id);
    pts.push([p.lat, p.lon]);
    L.marker([p.lat, p.lon], { icon: L.divIcon({ html: pinHtml(p.kind, i + 1, done && !done.includes(s.id)), className: "", iconSize: [34, 44], iconAnchor: [17, 43] }) }).bindTooltip(p.name).addTo(m);
  });
  document.getElementById(id)._pts = pts;
  if (pts.length === 1) m.setView(pts[0], 16); else m.fitBounds(pts, { padding: [36, 36] });
}
function allMap() {
  const kinds = S.mapKinds || B.pins.legend;
  const m = baseMap("map-all");
  m.setView([35.825, 129.23], 12);
  B.places.filter((p) => kinds.includes(p.kind)).forEach((p) => {
    L.marker([p.lat, p.lon], { icon: L.divIcon({ html: pinHtml(p.kind, null, false), className: "", iconSize: [34, 44], iconAnchor: [17, 43] }) })
      .bindTooltip(p.name).on("click", () => { S.mapSel = p.id; render(); setTimeout(() => { const sc = $("#scroll"); sc.scrollTop = sc.scrollHeight; }, 50); }).addTo(m);
  });
}

/* ------------------------------------------------------------------ 이벤트 */
function readPhoto(file, cb) {
  const fr = new FileReader();
  fr.onload = () => {
    const img = new Image();
    img.onload = () => {
      const s = Math.min(1, 1600 / Math.max(img.width, img.height));
      const cv = document.createElement("canvas");
      cv.width = Math.round(img.width * s); cv.height = Math.round(img.height * s);
      cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
      cb(cv.toDataURL("image/jpeg", 0.86));
    };
    img.src = fr.result;
  };
  fr.readAsDataURL(file);
}
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act]");
  if (!el) return;
  if (el.dataset.stop) return;
  const act = el.dataset.act, v = el.dataset.v;
  const c = S.choice;
  if (el.tagName === "INPUT" && el.type !== "checkbox") return;
  switch (act) {
    case "tab": S.tab = v; scrollTop(); break;
    case "time": c.minutes = Math.min(300, Math.max(30, c.minutes + Number(v))); break;
    case "timeset": c.minutes = Number(v); break;
    case "who": c.who = v; break;
    case "level": c.level = v; break;
    case "int": c.interests = c.interests.includes(v) ? c.interests.filter((i) => i !== v) : c.interests.concat([v]); break;
    case "ex": c.free = (c.free ? c.free.replace(/[.\s]*$/, "") + ". " : "") + v; break;
    case "plan": requestPlan(); return;
    case "back": S.screen = "setup"; scrollTop(); break;
    case "cand": S.cand = Number(v); break;
    case "startwalk": beginWalk(); break;
    case "arrive": arrive(); break;
    case "tired": tired(); return;
    case "bored": if (S.bored) { S.bored = null; break; } ask("alts", { cur: S.walk.stops[S.walk.idx], stops: S.walk.stops, who: S.walk.who }); return;
    case "swap": swap(v); return;
    case "finish": finishWalk(null); return;
    case "speak": speak(S.walk.route.stops[S.walk.idx].story); return;
    case "speakstory": speak(S.done.story.paras.join(" ")); return;
    case "mission": { const id = S.walk.stops[S.walk.idx]; const m = S.walk.missions; if (el.checked) { if (!m.includes(id)) m.push(id); } else S.walk.missions = m.filter((q) => q !== id); return; }
    case "mood": { const id = S.walk.stops[S.walk.idx]; S.walk.moods[id] = S.walk.moods[id] === v ? undefined : v; break; }
    case "pcphoto": S.pcPhoto = S.walk.photos[v]; break;
    case "pcdl": Postcard.download($("#pc"), `hanjeolde_postcard_${hhmm(nowDate()).replace(":", "")}.png`, $("#pcimg")); return;
    case "pcshare": Postcard.share($("#pc"), $("#pcimg")); return;
    case "recgo": S.qr = v; S.screen = "setup"; S.plan = null; S.walk = null; S.done = null; scrollTop(); break;
    case "home": S.screen = "setup"; S.plan = null; S.walk = null; S.done = null; S.pcPhoto = null; scrollTop(); break;
    case "kind": { const ks = S.mapKinds || B.pins.legend.slice(); S.mapKinds = ks.includes(v) ? ks.filter((k) => k !== v) : ks.concat([v]); if (!S.mapKinds.length) S.mapKinds = B.pins.legend.slice(); break; }
    case "mapstart": S.tab = "walk"; S.screen = "setup"; S.qr = v; S.plan = null; scrollTop(); break;
    case "compare": ask("compare", { choice: c, start: v, month: DEMO.month || null, mode: S.cmpMode }); return;
    case "cmpmode": S.cmpMode = v; break;
    case "mapfull": {
      const box = el.closest(".map");
      const on = !box.classList.contains("full");
      box.classList.toggle("full", on);
      el.textContent = on ? "✕ " + x("map_close") : "⤢ " + x("map_big");
      setTimeout(() => {
        if (!box._lmap) return;
        box._lmap.invalidateSize();
        const pts = box._pts || [];
        if (pts.length > 1) box._lmap.fitBounds(pts, { padding: [50, 50] }); else if (pts.length === 1) box._lmap.setView(pts[0], 16);
      }, 80);
      return;
    }
    case "scan": QRScan.open(); return;
    case "qrpick": S.qr = v; S.sheet = null; QRScan.close(); S.plan = null; renderSheet(); break;
    case "fix": S.fixOn = !S.fixOn; break;
    case "sheet": S.sheet = v; demoDraft = Object.assign({}, DEMO); renderSheet(); return;
    case "closesheet": if (e.target === el || el.tagName === "BUTTON") { S.sheet = null; QRScan.close(); renderSheet(); } return;
    case "lang": S.sheet = null; if (v !== lang()) ask("lang", { lang: v }); else renderSheet(); return;
    case "dw": demoDraft.weather = v; DEMO = Object.assign({}, DEMO, { weather: v }); renderSheet(); return;
    case "dt": demoDraft.time = v; DEMO = Object.assign({}, DEMO, { time: v }); renderSheet(); return;
    case "dm": demoDraft.month = v ? Number(v) : null; DEMO = Object.assign({}, DEMO, { month: v ? Number(v) : null }); renderSheet(); return;
    case "demoapply": S.sheet = null; ask("demo", demoDraft || DEMO); return;
    case "stopwhy": S.sheet = null; finishWalk(v); return;
    default: return;
  }
  render();
});
document.addEventListener("input", (e) => {
  if (e.target.id === "trange") {
    S.choice.minutes = Number(e.target.value);
    e.target.style.setProperty("--p", ((S.choice.minutes - 30) / 270) * 100 + "%");
    $("#timebig").innerHTML = timeBig(S.choice.minutes);
    const en = clockAdd(nowDate(), S.choice.minutes), ss = sunsetDate();
    $("#timeend").textContent = x("end_at", { t: hhmm(en > ss ? clockAdd(ss, -20) : en) });
  } else if (e.target.id === "free") S.choice.free = e.target.value;
  else if (e.target.id === "memo" && S.walk) S.walk.memos[S.walk.stops[S.walk.idx]] = e.target.value;
});
document.addEventListener("change", (e) => {
  if (e.target.id === "trange") render();
  const act = e.target.dataset && e.target.dataset.act;
  if (act === "photo" && e.target.files[0]) {
    const id = S.walk.stops[S.walk.idx];
    readPhoto(e.target.files[0], (url) => { S.walk.photos[id] = url; if (!S.pcPhoto) S.pcPhoto = url; render(); });
  } else if (act === "pcupload" && e.target.files[0]) {
    readPhoto(e.target.files[0], (url) => { const id = S.walk.arrived[S.walk.arrived.length - 1]; if (!S.walk.photos[id]) S.walk.photos[id] = url; S.pcPhoto = url; render(); });
  } else if (act === "mission") {
    const id = S.walk.stops[S.walk.idx]; const m = S.walk.missions;
    if (e.target.checked) { if (!m.includes(id)) m.push(id); } else S.walk.missions = m.filter((q) => q !== id);
  }
});

/* ------------------------------------------------------------------ QR 인식 (휴대폰 카메라 · BarcodeDetector) */
const QRScan = (() => {
  let stream = null, timer = null;
  function parse(raw) {
    try { const u = new URL(raw); const t = u.searchParams.get("temple") || u.searchParams.get("start"); if (t) return t; } catch (e) { /* 주소가 아니면 id로 봐요 */ }
    return String(raw || "").trim();
  }
  async function open() {
    if (S.sheet !== "qr") { S.sheet = "qr"; renderSheet(); }
    const box = $("#qrcam");
    if (!("BarcodeDetector" in window) || !navigator.mediaDevices) { box.innerHTML = `<p class="sub" style="margin:10px 0">${esc(x("qr_nocam"))}</p>`; return; }
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      box.innerHTML = `<div class="cam"><video playsinline muted autoplay></video><i></i></div><p class="sub" style="text-align:center">${esc(x("qr_scanning"))}</p>`;
      const v = box.querySelector("video"); v.srcObject = stream;
      const det = new BarcodeDetector({ formats: ["qr_code"] });
      timer = setInterval(async () => {
        try {
          const r = await det.detect(v);
          if (r && r[0]) {
            const id = parse(r[0].rawValue);
            if (B.places.some((p) => p.id === id && p.id !== "campus")) { S.qr = id; S.sheet = null; S.plan = null; close(); renderSheet(); render(); toast("📍 " + pname(id)); }
            else toast(x("qr_bad"));
          }
        } catch (e) { /* 다음 프레임 */ }
      }, 400);
    } catch (e) { box.innerHTML = `<p class="sub" style="margin:10px 0">${esc(x("qr_nocam"))}</p>`; }
  }
  function close() { clearInterval(timer); timer = null; if (stream) stream.getTracks().forEach((t) => t.stop()); stream = null; }
  return { open, close };
})();

/* ------------------------------------------------------------------ 시작 */
window.addEventListener("message", (ev) => {
  const d = ev.data;
  if (!d || d.type !== "streamlit:render") return;
  const a = d.args || {};
  const first = !B;
  const langChanged = B && a.bundle && a.bundle.lang !== B.lang;
  B = a.bundle; C = a.cond; QR = a.qr || null; DEMO = Object.assign({}, a.demo || {}); LLM = !!a.llm;
  if (first && QR) S.qr = QR;
  const handled = onResp(a.resp);
  if (first || handled || langChanged) render();
});
ST.ready();
ST.height(window.innerHeight || 800);
window.addEventListener("resize", () => ST.height(window.innerHeight || 800));

# 모두의 비상벨 — EmergencyBell MCP 기획

> **modu-emergencybell(모두의비상벨)**  
> PlayMCP / AGENTIC PLAYER 10 · `modu-emergencybell-mcp`

---

## 1. 한 줄 포지션

**밖에서 급할 때, 누구에게 전화하고 어디로 가면 되는지 알려준다.**

- **핫라인** (119·1339·112·1330 … + **화장실 비상벨** 설명) → 화장실 → 야간·주말 진료 → 응급실 → 약국
- **119 대신 전화·진단·구급차 호출은 하지 않는다** (번호·행동 **안내**만)

---

## 2. 브랜드: 왜 「모두의 비상벨」인가

| | **비상벨** (단독) | **모두의 비상벨** (채택) |
|---|------------------|-------------------------|
| 인상 | 고령·장애 쪽으로 좁게 느껴질 수 있음 | **누구나** 급할 때 쓸 수 있음 (급똥, 주말 아이 열, 약국) |
| 정책 톤 | — | **모두의 AI** 계열과 맞음 |
| 데이터 | 비상벨 필드와 일치 | description에서 “공중화장실 비상벨”로 구체화 |
| PlayMCP | — | `modu-emergencybell(모두의비상벨)` · identify `modu-emergencybell` |

**표기 규칙**

| 용도 | 값 |
|------|-----|
| 서비스 표시명 | 모두의 비상벨 |
| 영문·description | modu-emergencybell(모두의비상벨) |
| identify_name | `modu-emergencybell` |
| FastMCP / repo | `modu-emergencybell-mcp` |

---

## 3. 주제 경계 (IN / OUT)

### IN — MCP가 할 일

| 축 | 내용 |
|----|------|
| **When** | 지금 · 오늘 밤 · 주말 · 공휴일 |
| **Where** | 밖 · 낯선 동네 · 여행지 |
| **What** | **어디로 가면 되는지** (시설·기관 목록 + 전화·운영·거리) |
| **Who** | 누구나 (특히 동반·이동이 어려운 상황) |

### OUT — 하지 않을 것

| 제외 | 이유 |
|------|------|
| 119·112 **신고/호출** | 상용·법적 영역 |
| 증상 **진단·처방** | 의료 행위 |
| 어린이집·예방접종·키즈카페 | 키즈허브 |
| 장기요양·치매 행정 | 돌봄내비 |
| 무장애 **여행 코스** | 클리어루트 |
| e약은요·약 병용 deep dive | 집안 약사·yakjalal |

**면책 (모든 의료 관련 응답):**  
*생명이 위협되면 119. 본 서비스는 공공데이터 안내이며 진단이 아닙니다.*

---

## 4. 화장실 비상벨 vs 전화 핫라인

한국인도 **119 / 1339 / 112 / 110** 차이를 모르는 경우가 많다.  
화장실 **벽 비상벨**은 119가 **아니라** 시설 직원 호출이다 — 이 구분이 「모두의 비상벨」의 핵심 교육 포인트.

### 긴급 신고 3종 (공식 분류)

| 번호 | 역할 | MVP |
|------|------|-----|
| **112** | 범죄·폭력·**사이버 해킹** 등 경찰 | ✅ |
| **119** | 화재·구조·구급·유해물질·해양·**안전신고** | ✅ |
| **110** | 정부 민원·**비긴급** (민방위 포함) — 긴급 아님 | ✅ (헷갈릴 때 구분용) |

### 분야별·생활 비상 (추가 반영)

| 번호 | 용도 |
|------|------|
| **117** | 학교폭력 신고 (1388 청소년 상담과 구분) |
| **1366** | 여성·가족 긴급 상담 |
| **1388** | 청소년 상담 |
| **123** | 한전 전기 고장 (감전·화재 → 119) |
| **1544-4500** | 가스 누출·사고 (1577-1377 **섭취** 중독과 구분) |

**데이터 출처 (Phase 2 연동 후보):** 국민안전24 · 재난안전데이터공유플랫폼 · 공공데이터포털 시·군·구 비상연락망

| | 화장실 **비상벨** (벽 버튼) | **전화** 핫라인 |
|---|---------------------------|----------------|
| 연결 | 해당 건물·관리실·경비 | 119·1339·112 등 |
| 언제 | 화장실 안 넘어짐, 문 안 열림, 급한 몸 불편 | 생명 위협, 범죄, 독극물, 의료 상담 |
| MCP | `get_emergency_hotlines` (restroom_help) + `search_restroom` | `get_emergency_hotlines` |

**행동 순서 (화장실 안 위기):**  
1) **비상벨** 누름 → 2) 응답 없거나 의식·호흡 이상 → **119** → 3) 필요 시 `find_emergency_room`

---

## 5. 사용자 시나리오

```text
[뭐부터?]       → get_emergency_hotlines(situation_description="밖에서 급함 어디에 전화")
[화장실 안]     → get_emergency_hotlines("화장실에서 넘어짐/비상벨") → search_restroom (bell)
[배변 급함]     → search_restroom (open_now, infant/wheelchair/bell)
[주말 아이]     → 1339 안내 → find_open_clinic (소아, QT=공휴)
[ER]            → 119 안내 → find_emergency_room (병상)
[외국인]        → get_emergency_hotlines (foreign_visitor) → 1330·1339
[약]            → find_open_pharmacy (Phase 2)
```

---

## 6. MCP Tool 구성

### MVP (6개)

| # | Tool | 설명 |
|---|------|------|
| 1 | **`get_emergency_hotlines`** | **「이 상황에서 어디에 전화해야 해?」** — 상황 설명 → 번호·순서·다음 행동 |
| 2 | `search_restroom` | 장소명 geocode + 필터 |
| 3 | `find_nearest_restroom` | 좌표 + 필터 |
| 4 | `find_open_clinic` | 야간·공휴·소아과 |
| 5 | `find_emergency_room` | ER + 실시간 병상 |
| 6 | `get_dataset_info` | (선택) 데이터 통계 — 대회용, 빼도 5개 |

### Phase 2 (+2)

| # | Tool | 설명 |
|---|------|------|
| 7 | `find_open_pharmacy` | 요일·지역 약국 |
| 8 | `get_facility_detail` | 화장실/병원/약국 상세 |

### `get_emergency_hotlines` — 구현 방향

> **핵심 질문:** 「~~한 상황에서 **어디에 전화**해야 해?」  
> 핫라인 **목록**이 아니라, 사용자가 말한 상황에 **누구에게 먼저 전화할지** 답한다.

| 항목 | 내용 |
|------|------|
| **역할** | 상황 → **1순위 번호** + 2순위 + 화장실 비상벨(해당 시) + **다음 tool** |
| **데이터** | [`data/hotlines/hotlines.json`](../data/hotlines/hotlines.json) — `situation_routing` + `example_questions_ko` |
| **속도** | 로컬 JSON → **100ms 이내** |
| **파라미터** | **`situation_description`** (str, 필수) — 사용자 말 그대로. 예: `"화장실에서 넘어졌어"`, `"119랑 1339 뭐가 달라"` |
| | `language` (`ko` \| `en`, default `ko`) |
| | `situation` (enum, 선택) — 호스트 AI가 이미 분류했으면 넘김. 없으면 **키워드 매칭**으로 routing |
| **응답 형식** | 1줄 **`headline_ko`**: 「**이 상황에서는 → ○○**」 → 번호 상세 → 면책 → `next_step` |
| **전화** | MCP **발신 안 함** |

**대화 예시 (PlayMCP starter)**

```text
사용자: "화장실 비상벨 누르면 119야?"
→ get_emergency_hotlines(situation_description="화장실 비상벨 119인지")
→ "이 상황에서는 → 화장실 벽 비상벨 (119 아님). 응답 없으면 119."

사용자: "할머니가 갑자기 아프신데 어디에 전화해?"
→ get_emergency_hotlines(situation_description="할머니 갑자기 아픔")
→ "이 상황에서는 → 1339. 의식·호흡 문제면 119."

사용자: "밖에서 급한데 뭐부터?"
→ get_emergency_hotlines(situation_description="밖에서 급함 뭐부터")
→ unsure routing
```

**키워드 매칭 (MVP, 서버 내부)**

- `situation_description`을 `keywords_ko`와 매칭 → 최다 hit인 `situation_routing` 키 선택
- hit 없거나 동점 → `unsure`
- 호스트 LLM이 `situation` enum을 같이 넘기면 **enum 우선** (더 정확)

**`situation` → 번호 매핑 (요약)**

| situation | 1순위 | 2순위 |
|-----------|-------|-------|
| `life_threatening` | 119 | 1339 |
| `medical_urgent` | 1339 | 119 |
| `restroom_help` | **비상벨**(현장) | 119 |
| `foreign_visitor` | 1330, 1339 | 119 |
| `poison` | 1577-1377 | 119 |
| `police` | 112 | 119 |
| `mental_crisis` | 129, 1393 | 119 |
| `school_violence` | 117 | 1388, 112 |
| `utility_electric` | 123 | 119 |
| `utility_gas` | 1544-4500 | 119 |
| `safety_hazard` | 119 | 112 |
| `unsure` | 1339 | 119, 112 (110=비긴급만) |

### `search_restroom` / `find_nearest_restroom` 필터

| `user_type` | 의미 |
|-------------|------|
| `general` | 일반 |
| `wheelchair` | 장애인·휠체어 |
| `child` | 어린이용 변기 |
| `infant_care` | 기저귀 교환대 |
| `elderly_safety` | **비상벨** 설치 |

---

## 7. 데이터·API

상세 목록: [`data/api.json`](../data/api.json)

| 구분 | 소스 | 상태 |
|------|------|------|
| **긴급 핫라인** | `data/hotlines/hotlines.json` | ✅ MVP 데이터 |
| 공중화장실 | 행정안전부 CSV → 로컬 JSON | ✅ 구현됨 |
| Geocode | Kakao Local API | ✅ 구현됨 |
| 응급실·병상 | 국립중앙의료원 ErmctInfoInqireService | 🔲 |
| 야간·공휴 진료 | HsptlAsembySearchService | 🔲 |
| 소아 야간 (보조) | HIRA spclMdlrtHospInfoService | 🔲 선택 |
| 약국 (요일) | ErmctInsttInfoInqireService | 🔲 2차 |

---

## 8. 경쟁 포지션

| 서비스 | 겹침 | 모두의 비상벨 차별 |
|--------|------|-------------------|
| 급똥 서울 | 화장실 | **전국** + 비상벨 **브랜드** |
| 지금 여기 응급실 | ER·약국 | **화장실·접근성** 동선 |
| MedInfo | 병원·약국 | **비상벨·이동약자** 한 MCP |
| 키즈허브 | ER 등 | **핫라인+화장실+급함만** |

---

## 9. PlayMCP 등록 초안

**Description (EN):**

> modu-emergencybell(모두의비상벨) tells you **which hotline to call** (119, 1339, 112, 1330, poison center, etc.) and explains **restroom emergency buttons** vs phone numbers. Also finds accessible restrooms with call bells, night/holiday clinics, and ER bed availability. Information only—does not place calls or diagnose. Call 119 for life-threatening emergencies.

**Starter messages:**

1. **119랑 1339 차이가 뭐야?** 아이가 아픈데 뭐부터 해?  
2. 화장실 **비상벨** 누르면 119 연결돼?  
3. COEX 근처 **비상벨** 있는 장애인 화장실  
4. 일요일 밤 아이 열 — 마포구 **지금 여는** 소아과  
5. *I'm in Myeongdong, not sure 119 or hospital first*  

---

## 10. 구현 로드맵

### Phase 0 — 리브랜딩 (완료)

- [x] `modu_emergencybell.py`, FastMCP `modu-emergencybell`
- [x] Tool description → `modu-emergencybell(모두의비상벨)`
- [x] `where_toilet.py` 제거

### Phase 1 — MVP (대회 제출)

- [ ] **`get_emergency_hotlines`** — `situation_description` + 키워드 매칭 + headline 응답 (API 없음)
- [ ] 화장실 2 tool (기존)
- [ ] `find_open_clinic` (15000736)
- [ ] `find_emergency_room` (15000563)
- [ ] 공공데이터 API 키 · Docker 배포

### Phase 2

- [ ] `find_open_pharmacy` (15000576)
- [ ] `get_facility_detail`
- [ ] ER↔화장실 거리 정렬 (Kakao distance)

---

## 11. 성공 기준

- [ ] PlayMCP 심사: streamable-http, tool 3~10, description EN + 서비스명
- [ ] p99 응답 3초 이내 (화장실 로컬 + API 캐시)
- [ ] starter 5개가 **한 MCP** 안에서 자연스럽게 동작

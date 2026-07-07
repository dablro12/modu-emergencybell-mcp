# 모두의 비상벨 — MCP 서비스 설명

PlayMCP 등록·심사용 문서입니다. 기술 배포는 [DEPLOY_KC.md](./DEPLOY_KC.md), 기획은 [PLAN.md](./PLAN.md)를 참고하세요.

---

## 한 줄 소개

**밖에서 급할 때, 누구에게 전화하고 어디로 가면 되는지 알려주는 긴급·생활 안내 MCP**

| 항목 | 값 |
|------|-----|
| 서비스명 | 모두의 비상벨 |
| MCP 식별자 (`identify_name`) | `modu-emergencybell` |
| 표기 (description) | **modu-emergencybell(모두의비상벨)** |
| 전송 방식 | Streamable HTTP |
| 인증 | 없음 (공개 안내 MCP) |

---

## MCP 서버 설명 (PlayMCP Description — EN)

> **modu-emergencybell(모두의비상벨)** helps people in Korea when they are outside and need urgent guidance: which number to call (119, 1339, 112, 182, 1330), nearest public restrooms with on-site emergency buttons, outdoor crime-prevention safety bells, night/holiday clinics and pharmacies, ER bed availability, subway lockers and wheelchair access, nearby ATMs and free WiFi, veterinary hospitals, Safe182 child-safety houses, and foreign-visitor phrase cards. Information only — does not place calls, diagnose, or dispatch emergency services.

---

## MCP 서버 설명 (PlayMCP Description — KO)

> **modu-emergencybell(모두의비상벨)** 은 밖에서 급할 때 **어디에 전화하고 어디로 가야 하는지** 알려줍니다. 119·1339·112·182·1330 안내, 공중화장실·화장실 비상벨, 길·공원 안전비상벨, 야간·공휴 병원·약국·응급실, 지하철 물품보관함·휠체어리프트, ATM·무료 와이파이·동물병원, 안전Dream 아동안전지킴이집, 장애인 편의시설, 외국인 문장 카드를 제공합니다. 전화 연결·진단·신고 대행은 하지 않습니다.

---

## 제공 Tool (12개)

자연어 **장소명**만 받습니다. 좌표는 내부 지오코딩으로 처리합니다.

| Tool | 사용자 질문 예시 | 데이터 소스 |
|------|----------------|-------------|
| `get_emergency_hotlines` | 119랑 1339 차이? 화장실 비상벨은 119? | 정적 핫라인 JSON |
| `search_restroom` | 명동 근처 화장실 | 행정안전부 공중화장실 + Kakao |
| `find_nearest_restroom` | 강남역 화장실, 휠체어 화장실 | 동일 |
| `find_open_clinic` | 일요일 밤 마포구 소아과 | 국립중앙의료원 병원 API |
| `find_emergency_room` | 서울 강남구 응급실 병상 | 국립중앙의료원 응급실 API |
| `find_open_pharmacy` | 종로구 오늘 여는 약국 | 국립중앙의료원 약국 API |
| `find_safety_bell` | 이태원 근처 안전비상벨 | 행안부 안전비상벨 CSV |
| `get_phrase_card` | Myeongdong hospital phrase card | 정적 문장 카드 |
| `find_subway_facility_tool` | 강남역 물품보관함 / 엘리베이터 | 서울·부산·인천 지하철 CSV |
| `find_safe_place` | 종로 아동안전지킴이집 | 경찰청 안전Dream API |
| `find_accessible_facility_tool` | 서울역 휠체어 화장실 | 공중화장실 + 지하철 + 장애인편의시설 API |
| `find_outdoor_service_tool` | 강남역 ATM / 무료 와이파이 / 동물병원 | 역사 ATM CSV + data.go.kr |

### `find_accessible_facility_tool`

- 장소명 검색: `getDisConvFaclList` (목록) + `getFacInfoOpenApiJpEvalInfoList` (기구표 상세)
- `facility_id`로 승강기·장애인화장실 등 기구표 직접 조회 가능

### `find_outdoor_service_tool` service 값

- `atm` — 전국 도시광역철도 역사 ATM (공공데이터 CSV). **`station_query`에 역명 권장** (예: 강남역). 역명이 없으면 가까운 역으로 안내.
- `wifi` — 행정안전부 무료 와이파이
- `vet_hospital` — 행정안전부 동물병원

### `find_safe_place` category 값

- `child_safety_house` — 아동안전지킴이집 (기본)
- `elderly`, `youth`, `child_welfare`, `crime_area`, `violence_support`, `all`

---

## Starter Messages (PlayMCP 심사용)

1. 119랑 1339 차이가 뭐야? 아이가 아픈데 뭐부터 해?
2. 화장실 **비상벨** 누르면 119 연결돼?
3. 종로구 근처 **아동안전지킴이집** 어디 있어?
4. 강남역 **물품보관함**이랑 **엘리베이터** 알려줘
5. 명동 근처 **ATM**이랑 **무료 와이파이**
6. 일요일 밤 마포구 **지금 여는 약국**
7. 서울역 **휠체어 화장실** 어디 있어?
8. I'm in Myeongdong — **phrase card** for hospital

---

## 하지 않는 것 (면책)

- 119·112·182 **전화 연결·신고 대행**
- 증상 **진단·처방**
- 구급차·경찰 **출동 요청**
- 실시간 대중교통 길찾기 (ODsay 미사용)

모든 의료·응급 응답에는 **생명이 위협되면 119** 안내를 포함합니다.

---

## API 키 (GitHub Secrets)

| Secret | 용도 |
|--------|------|
| `KAKAO_REST_API_KEY` | 장소 지오코딩 |
| `DATA_GO_KR_SERVICE_KEY` | 공공데이터 (Decoding) |
| `DATA_GO_KR_SERVICE_KEY_ENCODED` | NEMC XML (Encoding) |
| `SAFE182_AUTH_ID` / `SAFE182_AUTH_KEY` | 안전Dream |

---

## 관련 문서

| 문서 | 설명 |
|------|------|
| [PLAN.md](./PLAN.md) | 기획·포지션·로드맵 |
| [DEPLOY_KC.md](./DEPLOY_KC.md) | KC 이미지 배포·Secrets |
| [kakao_guide/](./kakao_guide/) | PlayMCP 심사·등록 가이드 |
| [../data/api.json](../data/api.json) | API·데이터 목록 |

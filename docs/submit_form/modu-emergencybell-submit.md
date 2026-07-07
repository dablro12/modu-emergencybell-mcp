# modu-emergencybell(모두의비상벨) — PlayMCP 최종 제출

PlayMCP KC 컨테이너 등록, MCP 마켓 심사, AGENTIC PLAYER 10 예선 제출용 문서입니다.  
기술 배포: [DEPLOY_KC.md](../DEPLOY_KC.md) · Tool 상세: [README.md](../README.md)

---

## 1. MCP Container 정보 (KC)

| 항목 | 값 |
|------|-----|
| MCP 서버 이름 | `modu-emergencybell-mcp` |
| 레지스트리 호스트 | `ghcr.io` |
| 이미지명 | `dablro12/modu-emergencybell-mcp` |
| 이미지 태그 | `latest` |
| MCP Endpoint | `https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io/mcp` |

### MCP 설명 (KC / 컨테이너용)

밖에서 급할 때, 누구에게 전화하고 어디로 가야 할지 막막할 때 쓰는 비상 도우미입니다. **modu-emergencybell(모두의비상벨)** 은 채팅 한 번으로 긴급 연락처부터 갈 곳까지 안내하는 MCP입니다.

- **통합 안내** — `emergency_guide_tool` 하나로 가스 누출·발열·화장실·약국 등 자연어 질문 자동 연결
- 새벽 아이 39도 열 — 가까운 응급실·열린 약국·소아과 한 번에
- 화장실 비상벨·장애인 화장실 — 휠체어/기저귀/비상벨 키워드 자동 인식
- 길가 안전비상벨 — 밤길·공원·골목 범죄예방 비상벨 위치
- 주말·공휴·야간 — 일요일 소아과, 심야 약국, 응급실 병상 여유 병원
- 지하철 편의 — 역사 물품보관함·엘리베이터·역내 ATM (서울·부산·인천 로컬 데이터)
- 동·역만 알려도 OK — `창신동`→종로구, `연산9동`→부산 연제구 자동 보정
- 특수 상황 전화 — 독극물, 가스 누출(1544-4500), 정신위기, 실종(112)
- 외국인 관광객 — 병원·약국 영·한·일·중 문장 카드

2026년 국립중앙의료원·행정안전부·경찰청 Safe182·장애인편의시설 등 공공데이터 기반입니다. 전화 연결·진단·신고 대행은 하지 않습니다.

---

## 2. 심사 정보 (PlayMCP 마켓 등록)

| 항목 | 값 |
|------|-----|
| **MCP 명** | 모두의비상벨 - 밖에서 막막할때 |
| **MCP 식별자** | `emergencyBell` |
| **인증 방식** | 인증 사용하지 않음 |
| **MCP Endpoint** | `https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io/mcp` |

> 코드·Docker 식별자는 `modu-emergencybell`. PlayMCP 폼 `emergencyBell`과 콘솔 값을 맞춰 주세요.

### Tool 개수 (13개 — 카카오 권장 3~20개 범위)

| # | Tool | 기능 요약 |
|---|------|-----------|
| 1 | `emergency_guide_tool` | **권장 진입점** — 자연어 질문→의도 분류→다중 API 자동 연계 |
| 2 | `get_emergency_hotlines` | 상황별 긴급전화 (119/112/1339/1544 가스 등) |
| 3 | `find_nearest_restroom` | GPS 또는 장소명 기준 최근접 화장실 |
| 4 | `search_restroom` | 지역명 화장실 검색 (휠체어·기저귀·비상벨 필터) |
| 5 | `find_open_clinic` | 요일별 진료 병원 (소아·내과 등, NEMC) |
| 6 | `find_emergency_room` | 응급실 실시간 병상 (NEMC) |
| 7 | `find_open_pharmacy` | 요일별 영업 약국 (NEMC) |
| 8 | `find_safety_bell` | 길가 범죄예방 안전비상벨 (행안부 CSV) |
| 9 | `get_phrase_card` | 외국인용 병원·약국 문장 카드 |
| 10 | `find_subway_facility_tool` | 지하철 물품보관함·엘리베이터 (로컬 CSV) |
| 11 | `find_safe_place` | Safe182 아동안전지킴이집·청소년시설 |
| 12 | `find_accessible_facility_tool` | 장애인 편의시설·역 접근성 |
| 13 | `find_outdoor_service_tool` | 역사 ATM·무료 WiFi·동물병원 |

### 데이터 출처

| 데이터 | 출처 |
|--------|------|
| 야간/휴일 병원·약국·응급실 | 국립중앙의료원 공공데이터 |
| 공중화장실 | 행정안전부 MOIS |
| 안전비상벨 | 행정안전부 범죄예방 CSV |
| Safe182 | 경찰청 안전Dream Open API |
| 지하철 보관함·접근성·ATM | 국토교통부/지자체 공개 CSV (로컬 인덱스) |
| 장애인 편의시설 | 한국사회보장정보원 API |
| 무료 WiFi·동물병원 | 공공데이터포털 JSON |
| 지오코딩 | Kakao Local (역·POI·좌표) + juso 도로명주소 (동·구 행정구역) |

### 카카오 심사 정책 준수 체크

- [x] Tool 13개 (권장 3~20개)
- [x] Tool Description 영·한 병기, LLM 파라미터 가이드 포함
- [x] "kakao" prefix/suffix 미사용
- [x] 개인정보·민감정보 수집 없음
- [x] 유료 결제 불필요 (공공 API + 오픈 데이터)
- [x] 응답 24k 미만 (목록 limit 기본 5)
- [x] 면책 문구 포함 (의료·신고 대행 아님)
- [x] 사전 스모크 테스트 17시나리오 + pytest 43건 통과

### 대화 예시 (Starter Messages)

1. 집에서 가스 냄새가 날 때 어떻게 해?
2. 종로구 창신동 오늘 여는 약국
3. 강남역 근처 휠체어 화장실
4. 새벽에 아이 39도인데 마포구 소아과·약국
5. 부산 광안리 안전비상벨 어디 있어?
6. Wheelchair restroom near Myeongdong St?

---

## 3. 예선 제출 폼 (AGENTIC PLAYER 10)

| 항목 | 내용 |
|------|------|
| 이름 | 최대현 |
| PlayMCP 서비스명 | **모두의비상벨 - 밖에서 막막할때** |
| [신청1] PlayMCP 상세 페이지 URL | _(제출 시 URL 입력)_ |
| 현재 소속 구분 | 학교 |
| 소속명 | 서울대학교 |
| 소속 기관 홈페이지 URL | https://snuh.medisc.org/ |

### 서비스 소개 및 AGENTIC PLAYER 10 지원 사유

밖에서 급할 때 **119·1339·112·1544 중 어디에 전화해야 하는지**, **지금 문 연 병원·약국·응급실은 어디인지**, **화장실 비상벨·길가 안전비상벨·역사 ATM·물품보관함**은 어디인지를 한 번의 대화로 안내하는 공공데이터 기반 MCP입니다.

**emergency_guide_tool**이 자연어를 해석해 12개 전문 Tool을 유기적으로 연결하고, `창신동`·`연산9동`처럼 동 이름만 알려도 시·구를 자동 보정합니다. 에이전트가 잘못된 파라미터(`elevator`→접근성, `gas_leak`→가스 핫라인)를 넣어도 서버에서 정규화합니다.

의료진·공공데이터를 조합해 응급 상황에서 정보가 막막한 시민·관광객·보호자가 **실행 가능한 다음 행동**을 얻습니다. 전화 연결·진단·신고 대행은 하지 않습니다.

---

## 4. 알려진 제한

- Kakao/juso 키 미설정 시 랜드마크·시도 중심점 폴백(경고 문구 표시)
- ATM·물품보관함은 **지하철 역사 데이터** 위주 (길거리 ATM 미포함)
- WiFi·Safe182·일부 시설은 해당 지역 데이터 유무에 따라 결과 없을 수 있음
- NEMC 약국/병원은 **요일 단위** 안내 — 새벽 영업은 전화 확인 필요

---

## 관련 문서

| 문서 | 설명 |
|------|------|
| [README.md](../README.md) | Tool 목록·Starter Messages |
| [DEPLOY_KC.md](../DEPLOY_KC.md) | KC 배포·GitHub Secrets |
| [modu-emergencybell.md](../modu-emergencybell.md) | API 등록 정리 |
| [submit_form/form.md](./form.md) | 제출 원본 메모 |

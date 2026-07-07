# modu-emergencybell(모두의비상벨) — PlayMCP 최종 제출

PlayMCP KC 컨테이너 등록, MCP 마켓 심사, AGENTIC PLAYER 10 예선 제출용 **최종 문서**입니다.

- 기술 배포: [DEPLOY_KC.md](../DEPLOY_KC.md)
- Tool 호출 예제: [TOOL_EXAMPLES.md](../TOOL_EXAMPLES.md)
- 카톡 스타일 테스트: [KAKAOTALK_TOOL_TESTS.md](../KAKAOTALK_TOOL_TESTS.md)
- 글로벌 가이드 (KO·EN·ZH): [GLOBAL_KAKAOTALK.md](../GLOBAL_KAKAOTALK.md)
- Tool 상세: [README.md](../README.md) · [English](README_Eng.md) · [中文](README_Chi.md) · [日本語](README_Jpn.md)

---

## 1. MCP Container 정보 (KC)


| 항목           | 값                                                                          |
| ------------ | -------------------------------------------------------------------------- |
| MCP 서버 이름    | `modu-emergencybell-mcp`                                                   |
| 레지스트리 호스트    | `ghcr.io`                                                                  |
| 이미지명         | `dablro12/modu-emergencybell-mcp`                                          |
| 이미지 태그       | `latest`                                                                   |
| MCP Endpoint | `https://modu-emergencybell-mcp-server.playmcp-endpoint.kakaocloud.io/mcp` |


### MCP 설명 (KC / 컨테이너용)

"급할 때 필요한 정보를 알려드려요." **modu-emergencybell(모두의비상벨)** 은 위기 순간, 지금 무엇부터 해야 할지 빠르게 알려주는 생활안전 도우미 MCP입니다.

아이가 아프거나, 가족이 다치거나, 귀가가 늦어 불안한 순간에도 카톡처럼 상황을 입력하면 **지금 연락할 곳, 바로 갈 곳, 다음 행동**을 순서대로 안내합니다.

- 응급실 병상, 야간/공휴일 약국·진료기관을 가까운 위치 기준으로 조회
- `연락처 + 바로 갈 곳 + 카카오맵`을 함께 제공해 즉시 이동 가능
- 안전비상벨, 아동안전지킴이집, 지하철 접근성 정보를 통합 확인
- 장애인 화장실·엘리베이터 등 이동약자 편의 정보 지원
- 한국어·영어·중국어·일본어 기반 다국어 안내 지원

2026년 국립중앙의료원·행정안전부·경찰청·국토교통부·국가보훈부 등 공공데이터 기반이며, 전화 연결·진단·신고 대행은 하지 않습니다.

---

## 2. 심사 정보 (PlayMCP 마켓 등록)


| 항목               | 값                                                                          |
| ---------------- | -------------------------------------------------------------------------- |
| **MCP 명**        | 모두의비상벨 - 밖에서 막막할때                                                          |
| **MCP 식별자**      | `emergencyBell` (코드: `modu-emergencybell`)                                 |
| **인증 방식**        | 인증 사용하지 않음                                                                 |
| **MCP Endpoint** | `https://modu-emergencybell-mcp-server.playmcp-endpoint.kakaocloud.io/mcp` |


### Tool 개수 (15개 — 카카오 권장 3~20개)


| #   | Tool                            | 기능 요약                                     |
| --- | ------------------------------- | ----------------------------------------- |
| 1   | `classify_emergency_intent`     | **라우팅** — 의도 분류·권장 Tool·장소 추출 (read-only) |
| 2   | `emergency_guide_tool`          | **통합 진입점** — 자연어→다중 API 자동 연계             |
| 3   | `get_emergency_hotlines`        | 119/112/1339/1544 가스 등 상황별 전화             |
| 4   | `find_nearest_restroom`         | 화장실 (place_query + **user_request**)      |
| 5   | `search_restroom`               | 지역명 화장실 검색                                |
| 6   | `find_open_clinic`              | 요일별 진료 병원 (NEMC)                          |
| 7   | `find_veteran_hospital`         | 보훈 위탁병원 (국가보훈부)                           |
| 8   | `find_emergency_room`           | 응급실 실시간 병상 (NEMC)                         |
| 9   | `find_open_pharmacy`            | 요일별 약국 (NEMC)                             |
| 10  | `find_safety_bell`              | 길가 안전비상벨 + 치안 통계                          |
| 11  | `get_phrase_card`               | 외국인 문장 카드                                 |
| 12  | `find_subway_facility_tool`     | 지하철 물품보관함·엘리베이터                           |
| 13  | `find_safe_place`               | Safe182 아동안전지킴이집                          |
| 14  | `find_accessible_facility_tool` | 장애인 편의시설·휠체어 화장실                          |
| 15  | `find_outdoor_service_tool`     | ATM·WiFi·동물병원·버스정류장                       |


### MCP Prompts (12개 — 선택 기능)


| prompt                 | 용도            |
| ---------------------- | ------------- |
| `urgent_restroom`      | 급똥·화장실        |
| `gas_leak_emergency`   | 가스 누새         |
| `child_fever_night`    | 새벽 아이 발열      |
| `missing_child`        | 아이 실종         |
| `wheelchair_access`    | 휠체어·접근성       |
| `night_safety_crime`   | 야간 치안         |
| `foreign_tourist_help` | 외국인 관광객       |
| `subway_locker`        | 물품보관함         |
| `dong_only_pharmacy`   | 동만으로 약국/병원    |
| `wifi_bus_vet`         | WiFi·버스·동물병원  |
| `veteran_hospital`     | 보훈 위탁병원       |
| `classify_before_call` | Tool 선택 애매할 때 |


### 데이터 출처


| 데이터             | 출처                              |
| --------------- | ------------------------------- |
| 야간/휴일 병원·약국·응급실 | 국립중앙의료원                         |
| 공중화장실           | 행정안전부 MOIS                      |
| 안전비상벨           | 행정안전부 범죄예방 CSV                  |
| 치안 통계           | 경찰청 범죄발생 통계                     |
| 버스정류장           | 국토교통부 (~22만 건, 빌드 인덱스)          |
| 보훈 위탁병원         | 국가보훈부 odcloud                   |
| Safe182         | 경찰청 안전Dream API                 |
| 지하철 보관함·접근성·ATM | 국토교통부/지자체 CSV                   |
| 장애인 편의시설        | 한국사회보장정보원                       |
| 무료 WiFi·동물병원    | 공공데이터포털 JSON                    |
| 지오코딩            | Kakao Local + juso 도로명주소 + 랜드마크 |


### GitHub Actions Secrets (이미지 빌드)


| Secret                                  | 용도                         |
| --------------------------------------- | -------------------------- |
| `KAKAO_REST_API_KEY`                    | Kakao Local                |
| `DATA_GO_KR_SERVICE_KEY` / `_ENCODED`   | NEMC, WiFi, 장애인시설, Safe182 |
| `ODCLOUD_SERVICE_KEY`                   | 버스정류장·보훈병원 인덱스 빌드          |
| `JUSO_CONFM_KEY` / `JUSO_ENG_CONFM_KEY` | 도로명주소 한·영                  |
| `SAFE182_AUTH_ID` / `SAFE182_AUTH_KEY`  | Safe182                    |


### 카카오 심사 정책 준수

- [x] Tool 15개 (3~20개)
- [x] Description 영·한, WHEN TO USE, `user_request` 가이드
- [x] "kakao" prefix/suffix 미사용
- [x] 개인정보 수집 없음 · 유료 결제 없음
- [x] 응답 limit 기본 5 (24k 미만)
- [x] 면책 문구 (의료·신고 대행 아님)
- [x] 실패 응답 `isError: true` (MCP 권장)
- [x] 주소형 입력 juso 1순위
- [x] pytest 85+ · 카톡 15건 · 글로벌 EN/ZH (`scripts/global_tool_tests.py`)

### 대화 예시 (Starter Messages)

1. 집에서 가스 냄새가 날 때 어떻게 해?
2. **명동성당쪽인데 급똥이야 화장실 알려줘**
3. 종로구 창신동 오늘 여는 약국
4. 강남역 근처 휠체어 화장실
5. 새벽에 아이 39도인데 마포구 소아과·약국
6. 부산 광안리 안전비상벨 어디 있어?
7. 홍대 무료 와이파이 어디야?
8. 강남역 버스정류장 어디야?
9. Wheelchair restroom near Myeongdong Cathedral?
10. 明洞圣堂附近哪里有轮椅厕所？
11. 강남구 밤에 걸어도 안전할까?

### Tool 호출 예시 (PlayMCP 테스트)

상세 JSON은 [TOOL_EXAMPLES.md](../TOOL_EXAMPLES.md) 참고.

**급똥 화장실 (user_request만)**

```json
{
  "name": "find_nearest_restroom",
  "arguments": {
    "user_request": "명동성당쪽인데 급똥이야 화장실 알려줘"
  }
}
```

**라우팅 먼저**

```json
{
  "name": "classify_emergency_intent",
  "arguments": {
    "user_request": "강남역 화장실이랑 약국 알려줘"
  }
}
```

**복합 질문**

```json
{
  "name": "emergency_guide_tool",
  "arguments": {
    "user_request": "새벽에 아이 39도인데 마포구",
    "place_query": "마포구"
  }
}
```

---

## 3. 예선 제출 폼 (AGENTIC PLAYER 10)


| 항목                       | 내용                                                   |
| ------------------------ | ---------------------------------------------------- |
| 이름                       | 최대현                                                  |
| PlayMCP 서비스명             | **모두의비상벨 - 밖에서 막막할때**                                |
| [신청1] PlayMCP 상세 페이지 URL | *(제출 시 URL 입력)*                                      |
| 현재 소속 구분                 | 학교                                                   |
| 소속명                      | 서울대학교                                                |
| 소속 기관 홈페이지 URL           | [https://snuh.medisc.org/](https://snuh.medisc.org/) |


### 서비스 소개 및 지원 사유

모두의비상벨은 "검색"보다 "행동"에 집중합니다. 사용자가 카톡처럼 "익선동인데 엄마 무릎에서 피 나, 응급실이랑 약국 알려줘"라고 보내면, 복잡한 탐색 없이 **연락처·이동 경로·주변 시설**을 한 번에 제공합니다.

특히 의료 정보에만 머물지 않고, 안전비상벨·아동안전지킴이집·지하철 접근성·장애인 편의시설까지 함께 안내해 위기 상황에서 실제로 움직일 수 있는 선택지를 넓혔습니다. 외국인도 다국어 입력으로 동일한 흐름을 이용할 수 있습니다.

`classify_emergency_intent`와 `emergency_guide_tool`을 통해 자연어 원문(`user_request`)에서 장소·의도를 복구하고, 실사용 대화형 입력에도 안정적으로 응답합니다. 전화 연결·진단·신고 대행은 하지 않습니다.

---

## 4. 배포 체크리스트

1. `main` push → GitHub Actions → `ghcr.io/dablro12/modu-emergencybell-mcp:latest`
2. PlayMCP KC → 이미지 `latest` 재배포
3. PlayMCP 콘솔 → **「정보 불러오기」** → Tool 15개 확인
4. Starter Message로 [TOOL_EXAMPLES.md](../TOOL_EXAMPLES.md) 시나리오 테스트

---

## 5. 알려진 제한

- Kakao/juso 키 미설정 시 랜드마크·시도 중심점 폴백 (경고 문구)
- 버스정류장·보훈병원 인덱스는 **Docker 빌드 시** ODCLOUD 키 필요
- ATM·물품보관함은 지하철 역사 데이터 위주
- NEMC 약국/병원은 요일 단위 — 새벽 영업은 전화 확인
- Prompts는 클라이언트가 `prompts/list` 지원할 때만 UI 노출

---

## 관련 문서


| 문서                                      | 설명                     |
| --------------------------------------- | ---------------------- |
| [TOOL_EXAMPLES.md](../TOOL_EXAMPLES.md) | Tool·Prompt 호출 JSON 예제 |
| [README.md](../README.md)               | 개요                     |
| [DEPLOY_KC.md](../DEPLOY_KC.md)         | KC 배포·Secrets          |



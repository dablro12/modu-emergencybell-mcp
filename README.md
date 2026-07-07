<div align="center">

# modu-emergencybell · 모두의비상벨

### 밖에서 급할 때 — 누구에게 전화하고, 어디로 가야 하는지

[![PlayMCP](https://img.shields.io/badge/PlayMCP-Registered-FEE500?style=for-the-badge&logo=kakaotalk&logoColor=000)](https://playmcp.kakaocloud.io)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-6366f1?style=for-the-badge)](https://modelcontextprotocol.io)
[![Tools](https://img.shields.io/badge/Tools-15-22c55e?style=for-the-badge)](docs/TOOL_EXAMPLES.md)
[![Tests](https://img.shields.io/badge/pytest-85%20passed-0ea5e9?style=for-the-badge)](scripts/kakaotalk_tool_tests.py)

<br>

> **카카오 2026 AGENTIC PLAYER 10 대회 · 예선 제출 MCP 서버**
>
> PlayMCP 마켓 등록 · 공공데이터 기반 긴급·생활 안내 에이전트

<br>

| | |
|---|---|
| **서비스명** | 모두의비상벨 — 밖에서 막막할 때 |
| **MCP 식별자** | `modu-emergencybell` |
| **Endpoint** | `https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io/mcp` |
| **전송** | Streamable HTTP · 인증 없음 |

</div>

---

## 한 줄 소개

카카오톡에서 **「명동성당쪽 급똥」**, **「새벽에 아이 39도」**, **「성수동 밤길 무서워」** 같은 구어체 한 마디로  
**119·112·1339·1544 안내**, **화장실·약국·응급실·안전비상벨·지하철 보관함·WiFi**까지 연결하는 **공공데이터 MCP**입니다.

LLM이 Tool을 잘못 고르거나 `place_query`를 비워도, 서버가 **`user_request` 원문**에서 장소와 의도를 복구합니다.

---

## 왜 이 MCP인가

| 설계 포인트 | 설명 |
|-------------|------|
| **의도 라우팅** | `classify_emergency_intent` — Tool 선택 가이드 (read-only) |
| **통합 진입점** | `emergency_guide_tool` — 자연어 → 다중 공공 API 자동 연계 |
| **카톡 원문 복구** | `user_request`에 사용자 문장 전체 전달 → 장소·의도 서버 추출 |
| **지오코딩 2트랙** | 주소형 → **juso 1순위** · 랜드마크·역 → Kakao POI + 보정 |
| **MCP 권장 패턴** | 실패 시 빈 문자열 대신 **`isError: true`** 반환 |
| **시나리오 Prompt 12개** | 급똥·가스·실종·휠체어·외국인 등 템플릿 제공 |

> 정보 안내 전용 — 전화 연결·진단·신고 대행을 하지 않습니다.

---

## MCP Primitives

| Primitive | 개수 | 비고 |
|-----------|------|------|
| **Tools** | 15 | 카카오 권장 3~20개 |
| **Prompts** | 12 | 시나리오별 호출 가이드 |
| Resources | — | 데이터는 Tool로 노출 |

### Tools

| Tool | 역할 |
|------|------|
| `classify_emergency_intent` | 의도 분류 · 권장 Tool · 장소 추출 |
| `emergency_guide_tool` | **통합 진입점** — 복합 질문 오케스트레이션 |
| `get_emergency_hotlines` | 119 / 112 / 1339 / 1544 등 상황별 전화 |
| `find_nearest_restroom` | 근처 공중화장실 (`user_request` 지원) |
| `search_restroom` | 지역명·유형별 화장실 검색 |
| `find_open_clinic` | 요일별 진료 병원 (NEMC) |
| `find_veteran_hospital` | 보훈 위탁병원 |
| `find_emergency_room` | 응급실 실시간 병상 (NEMC) |
| `find_open_pharmacy` | 요일별 약국 (NEMC) |
| `find_safety_bell` | 길·공원 안전비상벨 + 치안 통계 |
| `get_phrase_card` | 외국인 병원·약국 문장 카드 (EN/JA/ZH) |
| `find_subway_facility_tool` | 지하철 물품보관함 · 엘리베이터 |
| `find_safe_place` | Safe182 아동안전지킴이집 |
| `find_accessible_facility_tool` | 장애인 편의시설 · 휠체어 화장실 |
| `find_outdoor_service_tool` | ATM · WiFi · 동물병원 · 버스정류장 |

---

## 바로 써보기

PlayMCP · MCP Inspector에서 Endpoint를 연결한 뒤, 아래 문장을 그대로 보내 보세요.

```
명동성당쪽인데 급똥이야 화장실 알려줘
```

```
새벽에 아이 39도인데 마포구 소아과·약국
```

```
서울특별시 중구 세종대로 110 근처 화장실
```

에이전트가 Tool을 직접 호출할 때는 **`user_request`에 카톡 원문 전체**를 넣는 것을 권장합니다.

```json
{
  "name": "find_nearest_restroom",
  "arguments": {
    "user_request": "ㅋㅋㅋ 코엑스 별관쪽 화장실 급함 진짜 죽겠다"
  }
}
```

카톡 스타일 **Tool별 테스트 15건** → [docs/KAKAOTALK_TOOL_TESTS.md](docs/KAKAOTALK_TOOL_TESTS.md)

---

## 아키텍처

```
사용자 메시지
    │
    ├─ classify_emergency_intent ──► 권장 Tool + 추출 장소
    │
    └─ 개별 Tool / emergency_guide_tool
            │
            ├─ intent_routing · place_context  (의도·키워드)
            ├─ place_resolver                    (juso → Kakao → 랜드마크)
            └─ NEMC · 행안부 · 경찰청 · 국토부 …  (공공 API)
```

---

## 데이터 출처

국립중앙의료원 · 행정안전부 · 경찰청 · 국토교통부 · 국가보훈부 · 한국사회보장정보원 · Kakao Local · juso 도로명주소

상세 목록 → [docs/submit_form/modu-emergencybell-submit.md](docs/submit_form/modu-emergencybell-submit.md#데이터-출처)

---

## PlayMCP · 카카오 가이드라인 준수

- [x] Tool 15개 (권장 3~20개) · Description 영·한 · WHEN TO USE
- [x] `kakao` prefix/suffix 미사용 · 개인정보·유료 결제 없음
- [x] 응답 limit 기본 5건 (24k 미만) · 면책 문구 포함
- [x] 실패 응답 `isError: true` · 주소형 입력 juso 1순위
- [x] pytest 85+ · 카톡 스타일 시나리오 15/15

---

## 로컬 개발

```bash
git clone https://github.com/dablro12/modu-emergencybell-mcp.git
cd modu-emergencybell-mcp
cp .env.example .env          # API 키 설정
pip install -e .
python scripts/process_restroom_data.py
python modu_emergencybell.py    # http://0.0.0.0:8000/mcp
```

```bash
pytest -q
python scripts/kakaotalk_tool_tests.py
```

배포 · GitHub Secrets · KC 등록 → [docs/DEPLOY_KC.md](docs/DEPLOY_KC.md)

---

## 문서

| 문서 | 내용 |
|------|------|
| [docs/TOOL_EXAMPLES.md](docs/TOOL_EXAMPLES.md) | Tool · Prompt JSON 호출 예제 |
| [docs/KAKAOTALK_TOOL_TESTS.md](docs/KAKAOTALK_TOOL_TESTS.md) | 카톡 스타일 Tool별 테스트 |
| [docs/submit_form/modu-emergencybell-submit.md](docs/submit_form/modu-emergencybell-submit.md) | PlayMCP · AGENTIC PLAYER 10 제출 패키지 |
| [docs/kakao_guide/](docs/kakao_guide/) | 카카오 MCP 심사·등록 가이드 |

---

<div align="center">

**카카오 2026 AGENTIC PLAYER 10 · 예선 제출**

모두의비상벨 — 밖에서 막막할 때, 다음 행동을 알려드립니다.

</div>

<div align="center">

<img src="assets/app_icon.png" width="128" alt="모두의비상벨 앱 아이콘" />

# modu-emergencybell · 모두의비상벨

### 밖에서 급할 때 — 누구에게 전화하고, 어디로 가야 하는지

[![PlayMCP](https://img.shields.io/badge/PlayMCP-Registered-FEE500?style=for-the-badge&logo=kakaotalk&logoColor=000)](https://playmcp.kakaocloud.io)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-6366f1?style=for-the-badge)](https://modelcontextprotocol.io)
[![Tools](https://img.shields.io/badge/Tools-15-22c55e?style=for-the-badge)](docs/TOOL_EXAMPLES.md)
[![Global](https://img.shields.io/badge/Global-KO·EN·ZH-f97316?style=for-the-badge)](docs/GLOBAL_KAKAOTALK.md)
[![Tests](https://img.shields.io/badge/pytest-90%2B-0ea5e9?style=for-the-badge)](scripts/kakaotalk_tool_tests.py)

<br>

> **카카오 2026 AGENTIC PLAYER 10 대회 · 예선 제출 MCP 서버**
>
> PlayMCP · **한국에 있는 모든 사람**을 위한 공공데이터 비상·생활 안내

<br>

| | |
|---|---|
| **서비스명** | 모두의비상벨 — 밖에서 막막할 때 |
| **MCP 식별자** | `modu-emergencybell` |
| **Endpoint** | `https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io/mcp` |
| **입력 언어** | 한국어 · English · 中文 (`user_request` 원문) |
| **전송** | Streamable HTTP · 인증 없음 |

**English / 中文** → [docs/GLOBAL_KAKAOTALK.md](docs/GLOBAL_KAKAOTALK.md)

</div>

---

## 한 줄 소개

카카오톡에서 **「명동성당쪽 급똥」**, **「Wheelchair restroom near Myeongdong」**, **「明洞圣堂附近厕所」** 한 마디로  
**119·112·1339·1544**, **화장실·약국·응급실·안전비상벨·지하철 보관함·WiFi**까지 연결하는 **포용형 공공데이터 MCP**입니다.

> **일반인 · 외국인 · 장애인 · 사회적 약자 · 관광객** — 모두 같은 Tool 15개로 안내받을 수 있습니다.

---

## 글로벌 카카오톡 (KO · EN · ZH)

Tool 내부는 한국 공공 API 기준이지만, **입력은 다국어**로 받습니다.

```
외국어/한국어 메시지
    → user_request 원문을 Tool에 전달
    → 서버: 장소·의도 추출 (Myeongdong / 明洞 / 강남역)
    → 한국어 공공데이터 조회 (주소·시설명은 한글 유지)
    → 에이전트가 사용자 언어로 최종 번역
```

| 언어 | 예시 메시지 |
|------|-------------|
| 🇰🇷 | `명동성당쪽 급똥 화장실` |
| 🇺🇸 | `Wheelchair restroom near Myeongdong Cathedral` |
| 🇨🇳 | `明洞圣堂附近哪里有轮椅厕所？` |

상세 가이드 · Tool별 예시 → **[docs/GLOBAL_KAKAOTALK.md](docs/GLOBAL_KAKAOTALK.md)**

```bash
python scripts/global_tool_tests.py   # 영·중 15건
python scripts/kakaotalk_tool_tests.py  # 한국어 15건
```

---

## 왜 이 MCP인가

| 설계 포인트 | 설명 |
|-------------|------|
| **포용·글로벌** | 한·영·중 `user_request` + 랜드마크·역명 다국어 해석 |
| **의도 라우팅** | `classify_emergency_intent` — Tool 선택 + 입력 언어 힌트 |
| **통합 진입점** | `emergency_guide_tool` — 자연어 → 다중 공공 API |
| **카톡 원문 복구** | `place_query` 비어 있어도 서버가 장소·의도 추출 |
| **지오코딩 2트랙** | 주소형 → **juso 1순위** · 랜드마크 → Kakao + 보정 |
| **MCP 권장 패턴** | 실패 시 **`isError: true`** |

> 정보 안내 전용 — 전화 연결·진단·신고 대행을 하지 않습니다.

---

## MCP Primitives

| Primitive | 개수 | 비고 |
|-----------|------|------|
| **Tools** | 15 | 카카오 권장 3~20개 |
| **Prompts** | 12 | 시나리오별 호출 가이드 |

### Tools

| Tool | 역할 |
|------|------|
| `classify_emergency_intent` | 의도 · Tool · 장소 · **입력 언어** 추정 |
| `emergency_guide_tool` | **통합 진입점** |
| `get_emergency_hotlines` | 119 / 112 / 1339 / 1544 |
| `find_nearest_restroom` | 공중화장실 (`wheelchair` 등 자동) |
| `search_restroom` | 지역명·유형별 화장실 |
| `find_open_clinic` | 요일별 진료 병원 |
| `find_veteran_hospital` | 보훈 위탁병원 |
| `find_emergency_room` | 응급실 병상 |
| `find_open_pharmacy` | 요일별 약국 |
| `find_safety_bell` | 안전비상벨 + 치안 통계 |
| `get_phrase_card` | 현장용 문장 카드 (선택) |
| `find_subway_facility_tool` | 물품보관함 · 엘리베이터 |
| `find_safe_place` | Safe182 아동안전지킴이집 |
| `find_accessible_facility_tool` | 장애인 편의시설 |
| `find_outdoor_service_tool` | ATM · WiFi · 동물병원 · 버스 |

---

## 바로 써보기

**한국어**
```
새벽에 아이 39도인데 마포구 소아과·약국
```

**English**
```
Wheelchair restroom near Myeongdong Cathedral — urgent!
```

**中文**
```
弘大附近有免费 WiFi 吗？
```

```json
{
  "name": "find_nearest_restroom",
  "arguments": {
    "user_request": "Wheelchair restroom near Myeongdong Cathedral — urgent!"
  }
}
```

---

## 아키텍처

```
사용자 (KO / EN / ZH)
    │
    ├─ classify_emergency_intent ──► Tool + 장소 + 언어 힌트
    │
    └─ Tool / emergency_guide_tool
            ├─ i18n_support · place_context
            ├─ place_resolver (juso → Kakao → 랜드마크)
            └─ NEMC · 행안부 · 경찰청 · 국토부 …
```

---

## 데이터 출처

국립중앙의료원 · 행정안전부 · 경찰청 · 국토교통부 · 국가보훈부 · 한국사회보장정보원 · Kakao Local · juso

---

## PlayMCP · 카카오 가이드라인 준수

- [x] Tool 15개 · Description 영·한 · WHEN TO USE
- [x] 다국어 `user_request` · 포용 설계 (장애인·외국인·약자)
- [x] `isError: true` · juso 1순위 · pytest + 글로벌 시나리오

---

## 로컬 개발

```bash
git clone https://github.com/dablro12/modu-emergencybell-mcp.git
cd modu-emergencybell-mcp
cp .env.example .env
pip install -e .
python scripts/process_restroom_data.py
python modu_emergencybell.py
```

```bash
pytest -q
python scripts/kakaotalk_tool_tests.py
python scripts/global_tool_tests.py
```

배포 → [docs/DEPLOY_KC.md](docs/DEPLOY_KC.md)

---

## Repository layout

```
modu-emergencybell-mcp/
├── README.md              # 이 문서
├── Dockerfile             # PlayMCP KC 이미지
├── modu_emergencybell.py    # MCP 서버 진입점
├── *.py                   # 도메인 모듈
├── assets/                # 앱 아이콘
├── data/
│   ├── sources/           # 공중화장실 원본 CSV (1개)
│   ├── toilet_data/       # 화장실 JSON 색인
│   ├── emergencybell/     # 안전비상벨·치안 JSON
│   ├── subway/            # 지하철·ATM JSON
│   ├── hotlines/          # 핫라인 JSON
│   └── phrases/           # 문장 카드 JSON
├── docs/                  # 배포·테스트·제출 문서
├── scripts/               # 데이터 가공 · 스모크 테스트
├── server/requirements.txt
└── tests/
```

---

## 문서

| 문서 | 내용 |
|------|------|
| [docs/GLOBAL_KAKAOTALK.md](docs/GLOBAL_KAKAOTALK.md) | **글로벌** KO · EN · ZH 가이드 |
| [docs/KAKAOTALK_TOOL_TESTS.md](docs/KAKAOTALK_TOOL_TESTS.md) | 카톡 스타일 한국어 테스트 |
| [docs/TOOL_EXAMPLES.md](docs/TOOL_EXAMPLES.md) | JSON 호출 예제 |
| [docs/submit_form/modu-emergencybell-submit.md](docs/submit_form/modu-emergencybell-submit.md) | AGENTIC PLAYER 10 제출 |

<div align="center">

**카카오 2026 AGENTIC PLAYER 10 · 예선 제출**

모두의비상벨 — **한국에 있는 모든 사람**을 위한 다음 행동 안내

</div>

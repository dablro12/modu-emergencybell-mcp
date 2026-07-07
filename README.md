# modu-emergencybell(모두의비상벨)

PlayMCP / AGENTIC PLAYER 10 — **밖에서 급할 때, 누구에게 전화하고 어디로 갈지**

| 항목 | 값 |
|------|-----|
| 서비스명 | 모두의비상벨 - 밖에서 막막할때 |
| MCP 식별자 | `modu-emergencybell` |
| 표기 | **modu-emergencybell(모두의비상벨)** |
| 전송 | Streamable HTTP |
| Endpoint | `https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io/mcp` |

---

## MCP 구성

| Primitive | 개수 | 설명 |
|-----------|------|------|
| **Tools** | 15 | 공공데이터 조회 (화장실·약국·핫라인 등) |
| **Prompts** | 12 | 시나리오별 Tool 호출 가이드 템플릿 |
| Resources | — | 미사용 (데이터는 Tool로 노출) |

실패 응답은 MCP 권장대로 **`isError: true`** (`mcp_tool_result.py`).

---

## Tools (15)

| Tool | 설명 |
|------|------|
| `classify_emergency_intent` | 의도 분류·권장 Tool 라우팅 (read-only) |
| `emergency_guide_tool` | **통합 진입점** — 자연어→다중 API 연계 |
| `get_emergency_hotlines` | 119/112/1339/1544 등 상황별 전화 |
| `find_nearest_restroom` | 화장실 (`user_request` + `place_query`) |
| `search_restroom` | 지역명 화장실 검색 |
| `find_open_clinic` | 요일별 진료 병원 (NEMC) |
| `find_veteran_hospital` | 보훈 위탁병원 |
| `find_emergency_room` | 응급실 병상 (NEMC) |
| `find_open_pharmacy` | 요일별 약국 (NEMC) |
| `find_safety_bell` | 길가 안전비상벨 + 치안 통계 |
| `get_phrase_card` | 외국인 문장 카드 |
| `find_subway_facility_tool` | 지하철 물품보관함·엘리베이터 |
| `find_safe_place` | Safe182 아동안전지킴이집 |
| `find_accessible_facility_tool` | 장애인 편의시설 |
| `find_outdoor_service_tool` | ATM·WiFi·동물병원·버스정류장 |

개별 Tool 호출 시 **`user_request`에 카톡 원문 전체**를 넣으면 서버가 장소를 복구합니다.

---

## Prompts (12)

`urgent_restroom`, `gas_leak_emergency`, `child_fever_night`, `missing_child`, `wheelchair_access`, `night_safety_crime`, `foreign_tourist_help`, `subway_locker`, `dong_only_pharmacy`, `wifi_bus_vet`, `veteran_hospital`, `classify_before_call`

---

## 지오코딩

```
주소형(도로명·번지·OO동) → juso 1순위 → Kakao geocode
랜드마크·역(COEX, 강남역)   → Kakao POI + 랜드마크 보정
```

---

## 문서

| 문서 | 내용 |
|------|------|
| [docs/TOOL_EXAMPLES.md](docs/TOOL_EXAMPLES.md) | JSON 호출 예제 |
| [docs/KAKAOTALK_TOOL_TESTS.md](docs/KAKAOTALK_TOOL_TESTS.md) | **카톡 스타일** Tool별 테스트 문장 |
| [docs/submit_form/modu-emergencybell-submit.md](docs/submit_form/modu-emergencybell-submit.md) | PlayMCP 최종 제출 |
| [docs/DEPLOY_KC.md](docs/DEPLOY_KC.md) | KC 배포·Secrets |

---

## PlayMCP 배포 (ghcr)

`main` push → GitHub Actions → `ghcr.io/dablro12/modu-emergencybell-mcp:latest`

### GitHub Secrets

| Secret | 용도 |
|--------|------|
| `KAKAO_REST_API_KEY` | Kakao Local |
| `DATA_GO_KR_SERVICE_KEY` / `_ENCODED` | NEMC, WiFi, 장애인시설, Safe182 |
| `ODCLOUD_SERVICE_KEY` / `_ENCODED` | 버스정류장·보훈병원 인덱스 빌드 |
| `JUSO_CONFM_KEY` / `JUSO_ENG_CONFM_KEY` | 도로명주소 한·영 |
| `SAFE182_AUTH_ID` / `SAFE182_AUTH_KEY` | Safe182 |

### KC 등록

| 항목 | 값 |
|------|-----|
| Registry | `ghcr.io` |
| image | `dablro12/modu-emergencybell-mcp:latest` |
| 인증 | 없음 |

배포 후 PlayMCP 콘솔 → **「정보 불러오기」** → Tool **15개** 확인.

---

## 로컬 실행

```bash
cp .env.example .env
pip install -e .
python scripts/process_restroom_data.py   # 화장실 JSON
python modu_emergencybell.py              # http://0.0.0.0:8000/mcp
```

### 테스트

```bash
pytest -q
python scripts/kakaotalk_tool_tests.py   # 카톡 스타일 Tool별 1건
python scripts/final_tool_smoke_test.py
```

---

## 데이터 출처

| 데이터 | 출처 |
|--------|------|
| 핫라인 | `data/hotlines/hotlines.json` |
| 공중화장실 | 행정안전부 |
| 안전비상벨·치안 | 행정안전부 CSV · 경찰청 범죄통계 |
| 병원·약국·응급실 | 국립중앙의료원 API |
| 버스정류장·보훈병원 | 국토교통부·국가보훈부 (빌드 인덱스) |
| 지하철·WiFi·장애인시설 | 공공데이터 CSV/API |
| 지오코딩 | Kakao Local + juso 도로명주소 |

기획: [docs/PLAN.md](docs/PLAN.md)

---

## 면책

정보 안내 전용입니다. 전화 연결·진단·신고 대행을 하지 않습니다.

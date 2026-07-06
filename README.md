# modu-emergencybell(모두의비상벨)

PlayMCP / AGENTIC PLAYER 10 — **밖에서 급할 때, 누구에게 전화하고 어디로 갈지**

| 항목 | 값 |
|------|-----|
| 서비스명 | 모두의 비상벨 |
| MCP 식별자 | `modu-emergencybell` |
| 표기 (description) | **modu-emergencybell(모두의비상벨)** |
| 전송 | Streamable HTTP |
| Repo | `modu-emergencybell-mcp` |

---

## Tools (10)

PlayMCP 권장 **3~10개** 범위. Tool 이름·서버 이름에 **`kakao` 미포함** (심사 정책).

| Tool | 설명 |
|------|------|
| `get_emergency_hotlines` | 이 상황에서 **어디에 전화**해야 하는지 |
| `search_restroom` | 장소명 → 공중화장실 (비상벨 필터) |
| `find_nearest_restroom` | GPS → 가까운 화장실 |
| `find_open_clinic` | 야간·공휴 병·의원 (NEMC 공공 API) |
| `find_emergency_room` | 응급실 실시간 병상 (NEMC 공공 API) |
| `find_open_pharmacy` | 요일·지역 약국 (NEMC 15000576) |
| `find_safety_bell` | 길·공원 **범죄예방** 안전비상벨 (MOIS CSV) |
| `get_phrase_card` | 외국인 병원·약국용 문장 카드 (정적) |
| `get_restroom_detail` | 화장실 상세 (MOIS ID) |
| `get_dataset_info` | 화장실 데이터 통계 |

모든 Tool description은 영문 + **modu-emergencybell(모두의비상벨)** 병기 ([개발가이드](docs/kakao_guide/kakao_mcp_개발가이드.md)).

---

## 로컬 실행

```bash
cp .env.example .env
# KAKAO_REST_API_KEY, DATA_GO_KR_SERVICE_KEY, DATA_GO_KR_SERVICE_KEY_ENCODED

pip install -e .
python scripts/process_restroom_data.py   # 화장실 JSON (Git 미포함 시)
python scripts/process_safety_bell_data.py  # 안전비상벨 JSON (CSV만 있을 때)
python modu_emergencybell.py
# → http://0.0.0.0:8000/mcp (streamable-http)
```

```bash
./server/run.sh
```

---

## Docker / PlayMCP in KC 배포

Apple Silicon은 **`--platform linux/amd64`** 필수 ([컨테이너 가이드](docs/kakao_guide/kakao_mcp_등록가이드_container.md)).

```bash
docker build --platform linux/amd64 -f Dockerfile -t modu-emergencybell .
docker run --env-file .env -p 8000:8000 modu-emergencybell
```

**Git 소스 빌드** ([가이드](docs/kakao_guide/kakao_mcp_등록가이드_gitsource.md)):

- 저장소 루트 `Dockerfile` 사용 (또는 Dockerfile 경로: `server/Dockerfile`)
- 빌드 후 KC Endpoint URL → PlayMCP 등록

---

## 환경 변수

| 변수 | 용도 |
|------|------|
| `KAKAO_REST_API_KEY` | 장소 geocode ([Local API](https://developers.kakao.com/docs/ko/local/dev-guide) 활성화) |
| `DATA_GO_KR_SERVICE_KEY` | 국립중앙의료원 응급·병원·**약국** API |
| `DATA_GO_KR_SERVICE_KEY_ENCODED` | (선택) Encoding 키 — 일부 API 403 시 fallback |
| `MCP_HOST` / `MCP_PORT` | HTTP 바인딩 (기본 `0.0.0.0:8000`) |

Kakao Local 비활성 시 **시·군·구 문자열 파싱 fallback**으로 병원·응급실·약국·안전비상벨은 동작합니다.

### 안전비상벨 데이터 빌드

CSV만 있을 때 JSON 인덱스 생성:

```bash
python scripts/process_safety_bell_data.py
# → data/emergencybell/safety_bell_records.json (~93k)
```

---

## PlayMCP 등록 초안

**MCP 식별자:** `modu-emergencybell`

**Description (EN, 심사용):**

> modu-emergencybell(모두의비상벨) tells you **which hotline to call** in your situation (119, 1339, 112, 1330, poison center, etc.) and explains **restroom wall emergency buttons** vs phone numbers. Also finds accessible restrooms with on-site call bells, night/holiday clinics, and ER bed availability from Korean public data. Information only—does not place calls or diagnose. Call 119 for life-threatening emergencies.

**Starter messages:**

1. 119랑 1339 차이가 뭐야? 아이가 아픈데 뭐부터 해?
2. 화장실 **비상벨** 누르면 119 연결돼?
3. COEX 근처 **비상벨** 있는 장애인 화장실
4. 일요일 밤 아이 열 — 마포구 **지금 여는** 소아과
5. I'm in Myeongdong, not sure 119 or hospital first

---

## 심사 체크리스트

[`docs/kakao_guide/`](docs/kakao_guide/) 기준:

| 항목 | 상태 |
|------|------|
| Streamable HTTP | ✅ |
| Tool 3~10개 | ✅ (7) |
| Tool/Server 이름에 `kakao` 없음 | ✅ |
| description에 서비스명 병기 | ✅ |
| annotations 5종 | ✅ readOnly, non-destructive, openWorld, idempotent |
| 응답 마크다운 (raw API X) | ✅ |
| 데이터 출처 표기 | ✅ 응답 하단 + 면책 |
| p99 3초 / 평균 100ms (핫라인·화장실 로컬) | ✅ 목표 |
| 24k 응답 초과 방지 (`limit` 기본 5) | ✅ |

---

## 데이터 출처

| 데이터 | 출처 |
|--------|------|
| 핫라인 | `data/hotlines/hotlines.json` (공식 번호 큐레이션) |
| 공중화장실 | 행정안전부 공중화장실정보 (로컬 JSON) |
| 병·의원·응급실 | 국립중앙의료원 공공데이터 API |
| Geocode | Kakao Local (서버 내부, Tool 이름에 미노출) |

기획: [`docs/PLAN.md`](docs/PLAN.md) · API: [`data/api.json`](data/api.json)

---

## 폴더 구조

```text
modu-emergencybell-mcp/
├── modu_emergencybell.py    # MCP 진입점
├── helpers.py               # 화장실 검색·포맷
├── hotlines.py              # 상황별 전화 안내
├── nemc_client.py           # 응급·병원 API
├── region_parse.py          # 시군구 fallback
├── kakao_local.py           # geocode (내부)
├── Dockerfile               # Git 빌드용 (루트)
├── data/
│   ├── hotlines/
│   └── toilet_data/
├── docs/kakao_guide/        # PlayMCP 심사·배포 가이드
└── server/
    ├── Dockerfile
    └── run.sh
```

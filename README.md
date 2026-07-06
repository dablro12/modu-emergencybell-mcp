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

## Tools (9)

PlayMCP 권장 **3~10개**. Tool·서버 이름에 **`kakao` 미포함**.

| Tool | 설명 |
|------|------|
| `get_emergency_hotlines` | 이 상황에서 **어디에 전화**해야 하는지 |
| `search_restroom` | 장소명 → 공중화장실 (비상벨 필터) |
| `find_nearest_restroom` | GPS → 가까운 화장실 |
| `find_open_clinic` | 야간·공휴 병·의원 (NEMC 공공 API) |
| `find_emergency_room` | 응급실 실시간 병상 (NEMC 공공 API) |
| `find_open_pharmacy` | 요일·지역 약국 (NEMC 15000576) |
| `find_safety_bell` | 길·공원 **범죄예방** 안전비상벨 |
| `get_phrase_card` | 외국인 병원·약국용 문장 카드 |
| `get_restroom_detail` | 화장실 상세 (MOIS ID) |

---

## PlayMCP in KC 배포 (권장: ghcr 이미지)

KC **Git 소스 빌드**에는 환경 변수 입력 UI가 없습니다.  
**GitHub Actions**가 Secrets로 API 키를 넣어 이미지를 빌드하고 **ghcr.io**에 push합니다.

### 1) GitHub Repository Secrets 등록

Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret 이름 | 값 |
|-------------|-----|
| `DATA_GO_KR_SERVICE_KEY` | 공공데이터 Decoding 키 |
| `DATA_GO_KR_SERVICE_KEY_ENCODED` | 공공데이터 Encoding 키 |
| `KAKAO_REST_API_KEY` | Kakao REST API 키 |

> 키는 **Git에 커밋하지 않습니다.** CI 빌드 시에만 이미지에 주입됩니다.

### 2) Actions로 이미지 빌드

`main`에 push하면 [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml)이 자동 실행됩니다.

이미지: `ghcr.io/dablro12/modu-emergencybell-mcp:latest`

### 3) PlayMCP in KC — **이미지 등록**

[컨테이너 가이드](docs/kakao_guide/kakao_mcp_등록가이드_container.md)

| 항목 | 값 |
|------|-----|
| Registry 호스트 | `ghcr.io` |
| image_name | `dablro12/modu-emergencybell-mcp` |
| image_tag | `latest` |
| Registry 사용자/비밀번호 | GitHub PAT (`read:packages`) — 패키지가 private일 때 |

Apple Silicon 로컬 빌드 시에만 `--platform linux/amd64` 필요. **Actions는 amd64로 빌드합니다.**

### 4) PlayMCP 마켓

1. KC Endpoint URL 복사 (예: `https://….playmcp-endpoint.kakaocloud.io/mcp`)
2. [playmcp.kakao.com](https://playmcp.kakao.com) → 개발자 콘솔 → MCP 등록
3. MCP 식별자: `modu-emergencybell`
4. **인증 방식: 없음** (공개 안내 MCP — OAuth/Key Token 불필요)
5. 「정보 불러오기」→ Tool 9개 확인 → 테스트 → 심사

---

## 로컬 PC에서 이미지 직접 빌드 (참고)

컨테이너 개발 환경이 아닌 **본인 PC/Mac**에서:

```bash
git clone https://github.com/dablro12/modu-emergencybell-mcp.git
cd modu-emergencybell-mcp

docker build --platform linux/amd64 \
  --build-arg DATA_GO_KR_SERVICE_KEY="여기_Decoding_키" \
  --build-arg DATA_GO_KR_SERVICE_KEY_ENCODED="여기_Encoding_키" \
  --build-arg KAKAO_REST_API_KEY="여기_Kakao_키" \
  -t ghcr.io/dablro12/modu-emergencybell-mcp:latest .

docker run --rm -p 8000:8000 ghcr.io/dablro12/modu-emergencybell-mcp:latest
# → http://localhost:8000/mcp
```

ghcr push (선택):

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u dablro12 --password-stdin
docker push ghcr.io/dablro12/modu-emergencybell-mcp:latest
```

---

## 로컬 실행 (개발)

```bash
cp .env.example .env
pip install -e .
python scripts/process_restroom_data.py   # 화장실 JSON (Git 미포함)
python modu_emergencybell.py
```

---

## 심사·API 키 관련

| 질문 | 답 |
|------|-----|
| 이미지에 API 키 넣어도 되나? | **운영자 본인 키**를 CI Secrets로 이미지에 주입하는 것은 일반적. **Public Git에 키 커밋만 금지.** |
| PlayMCP OAuth/Key Token? | **사용자 인증**용. 공공 API 키 대체 아님. 공개 안내 MCP는 **인증 없음** 권장. |
| 제3자 키 이슈? | 본인이 data.go.kr·Kakao에 **활용신청한 키**면 OK. |

---

## PlayMCP 등록 초안

**Description (EN):**

> modu-emergencybell(모두의비상벨) tells you which hotline to call (119, 1339, 112, 1330, etc.), finds restrooms with on-site call bells, outdoor crime-prevention safety bells, night/holiday clinics, pharmacies, ER beds, and foreign-visitor phrase cards. Information only—does not place calls or diagnose.

**Starter messages:**

1. 119랑 1339 차이가 뭐야? 아이가 아픈데 뭐부터 해?
2. 화장실 **비상벨** 누르면 119 연결돼?
3. 종로구 근처 **안전비상벨** 어디 있어?
4. 일요일 밤 마포구 **지금 여는 약국**
5. I'm in Myeongdong — **phrase card** for hospital

---

## 데이터 출처

| 데이터 | 출처 |
|--------|------|
| 핫라인 | `data/hotlines/hotlines.json` |
| 공중화장실 | 행정안전부 공중화장실정보 |
| 안전비상벨 | 행정안전부 전국안전비상벨위치 표준데이터 |
| 병·의원·응급실·약국 | 국립중앙의료원 공공데이터 API |

기획: [`docs/PLAN.md`](docs/PLAN.md) · API: [`data/api.json`](data/api.json)

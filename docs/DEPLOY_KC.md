# PlayMCP in KC 배포 가이드 (실패 시 체크리스트)

## 1. GitHub Actions 확인

https://github.com/dablro12/modu-emergencybell-mcp/actions

- **Publish Docker image** → ✅ success 여야 함
- 최신 커밋 SHA 예: `32a7c18068d288ac60c2c8428e194d8df5bbcf74`

---

## 2. GHCR 패키지 공개 (가장 흔한 실패 원인)

GHCR 이미지가 **private**이면 KC가 pull 못 해서 **Starting에서 실패**합니다.

### 방법 A — 패키지를 Public으로 (권장, PAT 불필요)

1. https://github.com/dablro12?tab=packages
2. **modu-emergencybell-mcp** 클릭
3. **Package settings** (우측 또는 톱니)
4. **Change visibility** → **Public**

### 방법 B — Private 유지 + KC에 PAT 입력

GitHub → Settings → Developer settings → **Personal access tokens (classic)**

- Scope: **`read:packages`** 체크
- 토큰 발급 후 KC 등록 폼에 입력:

| KC 항목 | 값 |
|---------|-----|
| Registry 사용자 | `dablro12` (GitHub 아이디) |
| Registry 비밀번호 | 발급한 PAT (ghp_...) |

---

## 3. KC 이미지 등록 — 복붙용

https://playmcp.kakaocloud.io → **+ 새 MCP 서버 등록** → **이미지 등록**

| 항목 | 값 |
|------|-----|
| MCP 서버 이름 | `modu-emergencybell` |
| 설명 | `모두의비상벨 MCP` |
| Registry 호스트 | `ghcr.io` |
| Registry 사용자 | (Public이면 **비움**) / Private이면 `dablro12` |
| Registry 비밀번호 | (Public이면 **비움**) / Private이면 PAT |
| image_name | `dablro12/modu-emergencybell-mcp` |
| image_tag | `latest` 또는 `main` (Actions success 이후) |

> ⚠️ `32a7c18` 같은 **짧은 SHA는 태그로 없을 수 있음**.  
> 전체 SHA `32a7c18068d288ac60c2c8428e194d8df5bbcf74` 또는 **`latest`** / **`main`** 사용.

---

## 4. 자주 하는 실수

| 실수 | 결과 |
|------|------|
| image_name에 `ghcr.io/` 포함 | pull 실패 |
| 대문자 사용 | GHCR는 소문자만 |
| Private 패키지인데 PAT 안 넣음 | Starting → Error |
| Git 소스 빌드 사용 | API 키(Secrets) 주입 안 됨 → Tool 빈 응답 |
| arm64 로컬 빌드 | KC는 **linux/amd64**만 (Actions는 amd64) |

---

## 5. 성공 확인

Status **Active** 후 Endpoint URL 복사:

```bash
curl -sS "https://YOUR-ENDPOINT.playmcp-endpoint.kakaocloud.io/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

JSON 응답이 오면 KC 배포 성공.

---

## 6. GitHub Secrets (Docker 빌드 시 API 키 주입)

Repository → **Settings** → **Secrets and variables** → **Actions**

| Secret | 용도 |
|--------|------|
| `DATA_GO_KR_SERVICE_KEY` | 공공데이터 (Decoding) |
| `DATA_GO_KR_SERVICE_KEY_ENCODED` | 공공데이터 (Encoding, NEMC XML용) |
| `KAKAO_REST_API_KEY` | Kakao Local 지오코딩 |
| `SAFE182_AUTH_ID` / `SAFE182_AUTH_KEY` | 경찰청 안전Dream |

---

## 7. PlayMCP 마켓

https://playmcp.kakao.com/console

- Endpoint URL 붙여넣기 (KC에서 복사)
- MCP 식별자: `modu-emergencybell`
- Tool 테스트 실행

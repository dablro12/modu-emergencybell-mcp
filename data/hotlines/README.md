# 상황별 전화 안내 (정적 데이터)

MCP tool **`get_emergency_hotlines`** — **「이 상황에서 어디에 전화해야 해?」** 에 답한다.

핫라인 **전화번호부**가 아니라, 사용자가 말한 상황 → **1순위로 걸 번호** + 다음 행동.

## 사용 흐름

```text
사용자: "화장실에서 넘어졌어 어디에 전화해?"
        ↓
AI → get_emergency_hotlines(situation_description="화장실에서 넘어짐")
        ↓
응답: "이 상황에서는 → 화장실 벽 비상벨 (119 아님). 응답 없으면 119."
```

- **외부 API 없음** — `hotlines.json`만 로드
- MCP는 **전화를 걸지 않음**
- `situation_description` 키워드 → `situation_routing` 매칭 (없으면 `unsure`)

## 긴급 3종 vs 분야별

| 구분 | 번호 |
|------|------|
| **112** | 경찰·범죄·사이버 |
| **119** | 재난·구급·안전신고 |
| **110** | 민원·**비긴급** (110 ≠ 119) |
| **117** | 학교폭력 (≠ 1388 상담) |
| **123** / **1544-4500** | 전기 / 가스 (누출 ≠ 1577 섭취) |

출처: 국민안전24 · 재난안전데이터공유플랫폼 · 공공데이터포털 (시·군·구 연락망은 Phase 2)

## 공중화장실 비상벨 vs 전화

| | 화장실 **비상벨** | **119** 등 |
|---|------------------|------------|
| 연결 | 시설 관리인·경비 | 구급·소방·경찰 |
| 언제 | 화장실 안 넘어짐·문 안 열림·급한 몸 불편 | 생명 위협·큰 사고 |
| MCP | `restroom_help` routing + `search_restroom` | `get_emergency_hotlines` |

## 데이터 구조

- `hotlines[]` — 번호·기관·when_ko
- `situation_routing{}` — 상황별 primary/secondary, **example_questions_ko**, **headline_ko**
- `restroom_emergency_bell` — 벽 버튼 전용 설명

배포 전 각 기관 공식 사이트에서 번호 재확인.

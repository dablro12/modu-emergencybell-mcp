# Global KakaoTalk Guide · 글로벌 카카오톡 가이드 · 全球 KakaoTalk 指南

**modu-emergencybell(모두의비상벨)** — 한국에 있는 **모든 사람**을 위한 MCP  
일반인 · 외국인 · 장애인 · 사회적 약자 · 관광객

| | |
|---|---|
| Endpoint | `https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io/mcp` |
| Tools | 15 (한국 공공데이터 조회) |
| 입력 | **한국어 · English · 中文** (`user_request` 원문 전달) |
| 출력 | Tool은 한국어 마크다운 → **에이전트가 사용자 언어로 번역** |

---

# 🇰🇷 한국어 (KOR)

## 누구를 위한 서비스인가요?

- 길에서 화장실·약국·응급실이 급한 **일반 시민**
- 밤길·치안이 걱정되는 **사회적 약자**
- 휠체어·유아 동반 **장애인·보호자**
- 한국어가 서툰 **외국인 관광객·체류자** (영·중 입력도 서버가 해석)

## 어떻게 동작하나요?

```
카카오톡 메시지 (한·영·중)
    → 에이전트가 user_request 원문을 Tool에 전달
    → MCP가 장소·의도 추출 + 공공데이터 조회
    → 한국어 결과 (주소·시설명은 한글 유지)
    → 에이전트가 사용자 언어로 설명
```

서버가 하는 일: **명동성당**, `Myeongdong Cathedral`, `明洞圣堂` 같은 표현을 같은 좌표로 해석합니다.

## 바로 써보기

```
명동성당쪽인데 급똥이야 화장실 알려줘
```

```
강남역 근처 휠체어 화장실 어디있어?
```

```
새벽에 아이 39도인데 마포구 소아과·약국
```

## Tool 호출 (권장)

```json
{
  "name": "find_nearest_restroom",
  "arguments": {
    "user_request": "명동성당쪽인데 급똥이야 화장실 알려줘"
  }
}
```

## 포용 설계

| 대상 | Tool 예시 |
|------|-----------|
| 장애인 | `find_accessible_facility_tool`, `user_type=wheelchair` |
| 유아·보호자 | `search_restroom` + `infant_care` |
| 아동·청소년 | `find_safe_place` |
| 보훈 대상 | `find_veteran_hospital` |
| 외국인 | 모든 Tool + `user_request` 영·중 원문 |

로컬 테스트: `python scripts/kakaotalk_tool_tests.py`

---

# 🇺🇸 English (ENG)

## Who is this for?

Anyone in Korea who needs **actionable help outdoors** — tourists, expats, students, and residents who prefer English in KakaoTalk.

## How it works

1. You send a message in **English** (or mixed English + Korean place names).
2. The KakaoTalk agent calls MCP tools with your **full original text** in `user_request`.
3. The server resolves places (`Myeongdong`, `Gangnam Station`, `COEX`) and queries **Korean public data**.
4. The agent **translates the answer** to English. **Korean addresses stay in Korean** — show them to taxi drivers or staff.

## Try these messages

```
Wheelchair restroom near Myeongdong Cathedral — urgent!
```

```
Sunday morning headache medicine — pharmacy near Jongno 3-ga?
```

```
I'm scared walking alone at Seongsu cafe street at night. Any safety bells?
```

```
Where can I store my luggage at Seomyeon Station, Busan?
```

## Recommended tool call

```json
{
  "name": "find_nearest_restroom",
  "arguments": {
    "user_request": "Wheelchair restroom near Myeongdong Cathedral — urgent!"
  }
}
```

## Inclusive by design

| Need | Tool |
|------|------|
| Disability access | `find_accessible_facility_tool` |
| Infant care restroom | `search_restroom` + `user_type=infant_care` |
| Child safety | `find_safe_place` |
| Emergency numbers | `get_emergency_hotlines` |
| Night clinic / pharmacy | `find_open_clinic`, `find_open_pharmacy` |

Run tests: `python scripts/global_tool_tests.py`

---

# 🇨🇳 中文 (CHI)

## 为谁服务？

在韩国的**所有人**——游客、留学生、务工者、需要无障碍设施的人士。可用**中文**在 KakaoTalk 中提问。

## 工作原理

1. 用**中文**（或中英混合）发送消息。
2. KakaoTalk 智能体将完整原文放入 `user_request` 调用 MCP 工具。
3. 服务器识别地点（如 **明洞**、**江南**、**海云台**）并查询韩国公共数据。
4. 智能体将结果**翻译成中文**；**韩文地址保留**，便于出示给司机或店员。

## 试用例句

```
明洞圣堂附近哪里有轮椅厕所？很急！
```

```
弘大附近有免费 WiFi 吗？
```

```
釜山海云台附近晚上走路安全吗？有安全铃吗？
```

```
孩子在弘大走丢了，马浦区有青少年庇护所吗？
```

## 推荐调用

```json
{
  "name": "find_nearest_restroom",
  "arguments": {
    "user_request": "明洞圣堂附近哪里有轮椅厕所？很急！"
  }
}
```

## 包容性设计

| 需求 | 工具 |
|------|------|
| 无障碍 | `find_accessible_facility_tool` |
| 母婴厕所 | `search_restroom` + `infant_care` |
| 儿童安全 | `find_safe_place` |
| 急救电话 | `get_emergency_hotlines` |
| 夜间诊所/药店 | `find_open_clinic`, `find_open_pharmacy` |

测试：`python scripts/global_tool_tests.py`

---

## Architecture (all languages)

```
User message (KO / EN / ZH)
    │
    ├─ classify_emergency_intent → tool routing + detected language hint
    │
    └─ Tools / emergency_guide_tool
            ├─ i18n_support · place_context   (intent + place from any language)
            ├─ landmarks · juso · Kakao       (Myeongdong / 明洞 / 강남역)
            └─ NEMC · MOIS · Police · MOT …   (Korean public APIs)
```

## Disclaimer (면책)

Information only. Does not place emergency calls, diagnose, or dispatch services.  
**Life-threatening emergency → call 119 (Korea).**

## Related docs

- [KAKAOTALK_TOOL_TESTS.md](./KAKAOTALK_TOOL_TESTS.md) — Korean scenarios (15 tools)
- [TOOL_EXAMPLES.md](./TOOL_EXAMPLES.md) — JSON examples
- [README.md](../README.md) — Repository overview (Korean default)

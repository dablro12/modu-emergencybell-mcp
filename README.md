<div align="center">

<img src="assets/app_icon.png" width="120" alt="모두의비상벨" />

# 모두의비상벨

### 밖에서 막막할 때 — 다음에 뭘 하면 되는지 알려드려요

**한국어** · [English](docs/README_Eng.md) · [中文](docs/README_Chi.md) · [日本語](docs/README_Jpn.md)

<br>

[![PlayMCP](https://img.shields.io/badge/PlayMCP-사용_가능-FEE500?style=flat-square)](https://playmcp.kakaocloud.io)
[![AGENTIC PLAYER 10](https://img.shields.io/badge/카카오_2026-AGENTIC_PLAYER_10-000?style=flat-square&logo=kakaotalk&logoColor=FEE500)](https://playmcp.kakaocloud.io)

> 카카오톡에서 **한 마디**로 급할 때 필요한 정보를 찾는 비상·생활 도우미입니다.  
> **일반인 · 외국인 · 장애인 · 사회적 약자** 모두 사용할 수 있습니다.

</div>

---

## 이게 뭐예요?

한국 밖에서 갑자기 급할 때 — **어디에 전화하고, 어디로 가야 하는지** 막막하잖아요.

**모두의비상벨**은 카카오톡 에이전트와 연결하면, 말하듯이 물어보기만 해도 **119·112·1339 안내**, **가까운 화장실·약국·응급실**, **밤길 안전비상벨**, **지하철 짐 보관함**, **무료 WiFi** 같은 **실제 공공데이터**를 바탕으로 알려줍니다.

> 전화를 대신 걸거나, 진단·신고를 대신하지는 않아요. **정보 안내**만 합니다.

---

## 이런 때 써보세요

| 상황 | 이렇게 물어보세요 |
|------|-------------------|
| 🚽 **급한 화장실** | 「명동성당 쪽인데 화장실 급해」 |
| 💊 **밤·주말 약국** | 「종로3가 일요일 아침 약국 어디 있어?」 |
| 🌡️ **아이가 아플 때** | 「새벽에 아이 39도인데 마포구 소아과·약국」 |
| 📞 **어디에 전화?** | 「가스 냄새 나는데 119야 1544야?」 |
| 🌙 **밤길이 무서울 때** | 「성수동 카페거리 밤에 혼자 걷는데 비상벨 어딨어」 |
| ♿ **휠체어 화장실** | 「강남역 근처 휠체어 화장실」 |
| 🧳 **지하철 짐 맡기기** | 「서면역 캐리어 맡을 데 있어?」 |
| 🌍 **외국인 관광객** | 영·중·일로도 질문 가능 ([English](docs/README_Eng.md) · [中文](docs/README_Chi.md) · [日本語](docs/README_Jpn.md)) |

**한 번에 여러 가지**가 급하면 이렇게요:

> 「익선동인데 엄마 무릎에서 피 나 — 응급실이랑 약국 알려줘」

---

## 어떻게 쓰나요?

### 카카오톡 · PlayMCP 사용자

1. PlayMCP에서 **모두의비상벨** MCP를 연결합니다.
2. 평소 카톡하듯 **위치 + 상황**을 한 문장으로 보냅니다.
3. 에이전트가 가까운 시설·전화번호·다음 행동을 알려줍니다.

**팁:** 「강남역」「명동성당」「창신동」처럼 **대략적인 위치**만 알려도 됩니다.  
**팁:** 외국인은 영어·중국어·일본어로 물어봐도 됩니다. 주소는 한글로 나와 택시·카운터에 보여주기 좋아요.

### 개발자 · MCP 연결

| 항목 | 값 |
|------|-----|
| Endpoint | `https://modu-emergencybell-mcp.playmcp-endpoint.kakaocloud.io/mcp` |
| 식별자 | `modu-emergencybell` |

기술 문서 → [docs/DEPLOY_KC.md](docs/DEPLOY_KC.md) · [docs/TOOL_EXAMPLES.md](docs/TOOL_EXAMPLES.md)

---

## 바로 복사해서 써보기

```
명동성당쪽인데 급똥이야 화장실 알려줘
```

```
집에서 가스 냄새가 날 때 어떻게 해?
```

```
강남역 근처 휠체어 화장실 어디있어?
```

```
서울특별시 중구 세종대로 110 근처 화장실
```

더 많은 예시 → [카톡 스타일 테스트](docs/KAKAOTALK_TOOL_TESTS.md)

---

## 누구를 위한 서비스인가요?

- 🧑‍🤝‍🧑 **일반 시민** — 길에서 화장실·약국·응급실이 급할 때  
- 🌏 **외국인·관광객** — 한국어가 어려워도 영·중으로 질문  
- ♿ **장애인·보호자** — 휠체어 화장실, 유아 수유·기저귀 공간  
- 🌙 **사회적 약자** — 밤길 치안, 안전비상벨, 아동·청소년 쉼터  
- 🎖️ **보훈 대상** — 위탁병원 안내  

---

## 꼭 알아두세요

- 생명이 위협되면 **즉시 119**에 전화하세요.
- 야간·공휴일 병원·약국 정보는 **요일 기준**이며, 새벽 영업은 **전화 확인**이 필요할 수 있어요.
- 안내는 참고용이며, **의료 진단·신고 대행**을 하지 않습니다.

---

## 더 보기

| 문서 | 내용 |
|------|------|
| [English README](docs/README_Eng.md) | English user guide |
| [中文 README](docs/README_Chi.md) | 中文用户指南 |
| [日本語 README](docs/README_Jpn.md) | 日本語ガイド |
| [GLOBAL_KAKAOTALK.md](docs/GLOBAL_KAKAOTALK.md) | 다국어 상세 · 테스트 |
| [modu-emergencybell-submit.md](docs/submit_form/modu-emergencybell-submit.md) | AGENTIC PLAYER 10 제출 |

---

<div align="center">

**카카오 2026 AGENTIC PLAYER 10 · 예선 제출**

모두의비상벨 — 한국에 있는 **모든 사람**을 위한 다음 행동 안내

</div>

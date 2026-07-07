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
| 🧒 **아이가 뭘 삼켰을 때** | 「레고 블록 삼켰어 어떻게 하지」 |
| 💊 **약을 잘못 먹었을 때** | 「강아지 약을 내 약인 줄 알고 먹었어」 |
| 🤕 **어디 과로 가야 해?** | 「축구 후 목 쑤시고 머리 아파 신설동역 근처」 |
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

## 사용하는 공공 API

| 구분 | API (공공데이터포털) | 용도 |
|------|----------------------|------|
| **NEMC** | 국립중앙의료원 응급의료정보 | 야간·휴일 진료 병원, 응급실 병상, 약국 |
| **HIRA** | 건강보험심사평가원 질병정보서비스 | 증상 키워드 → 질병·진료과 참고 |
| **HIRA** | 병원정보·의료기관별상세·비급여진료비 | 병원 기본 정보 (확장 예정) |
| **MFDS** | 식약처 e약은요 | 의약품 효능·주의사항 참고 |
| **MFDS** | DUR 품목·성분정보 | 약물 상호작용 참고 (확장 예정) |
| **행안부** | 공중화장실·안전비상벨·동물병원 CSV | 화장실·비상벨·동물병원 로컬 검색 |
| **경찰청** | Safe182 | 아동안전지킴이집·쉼터 |
| **Kakao** | 로컬 API | 장소·좌표 해석 |
| **행안부** | 도로명주소(Juso) | 주소 정규화 |

> 심평원·식약처 API는 공공데이터포털에서 **서비스별 활용신청** 후 `DATA_GO_KR_SERVICE_KEY`로 연동합니다.  
> API 미연동 시에도 **규칙 기반 트리아지 + NEMC**로 기본 안내가 동작합니다.

### MCP Tool 구성 (12개)

| Tool | 역할 |
|------|------|
| `emergency_guide_tool` | **복합 질문 1순위** — 화장실·의료·안전·트리아지 통합 |
| `health_triage_tool` | 중독·오복용·증상→진료과·e약은요 참고 |
| `find_medical_care` | 병원·약국·응급실 통합 (NEMC) |
| `get_emergency_hotlines` | 119/112/1339 신고번호 |
| `find_nearest_restroom` | 공중화장실 |
| `find_safety_bell` | 야간 안전비상벨 |
| `find_veteran_hospital` | 보훈 위탁병원 |
| `find_outdoor_service_tool` | ATM·WiFi·동물병원·버스 |
| `find_accessible_facility_tool` | 휠체어·장애인 시설 |
| `find_subway_facility_tool` | 지하철 보관함·엘리베이터 |
| `find_safe_place` | 아동안전지킴이집 |
| `get_phrase_card` | 외국인 문장 카드 |

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

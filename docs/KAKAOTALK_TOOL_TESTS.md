# 카톡 스타일 Tool 테스트 — Tool당 1문장

PlayMCP·MCP Inspector에서 **사용자가 실제로 보낼 법한 메시지**입니다.  
에이전트에게는 `user_request`에 **아래 문장 전체**를 넣고, Tool은 표에 지정된 것을 호출하세요.

로컬 일괄 실행:

```bash
python scripts/kakaotalk_tool_tests.py
```

---

## 1. `classify_emergency_intent`

> 야 나 지금 혜화골목길인데 화장실도 급하고 근처 편의점도 없어 뭐부터 해야돼

```json
{
  "name": "classify_emergency_intent",
  "arguments": {
    "user_request": "야 나 지금 혜화골목길인데 화장실도 급하고 근처 편의점도 없어 뭐부터 해야돼"
  }
}
```

---

## 2. `emergency_guide_tool`

> 엄마 무릎에서 피나는데 익선동 근처야 응급실이랑 약국 좀 알려줘

```json
{
  "name": "emergency_guide_tool",
  "arguments": {
    "user_request": "엄마 무릎에서 피나는데 익선동 근처야 응급실이랑 약국 좀 알려줘",
    "place_query": "익선동"
  }
}
```

---

## 3. `get_emergency_hotlines`

> 옆집에서 매운 냄새? 같은 가스 냄새 나는데 신고 어디로 해야함

```json
{
  "name": "get_emergency_hotlines",
  "arguments": {
    "situation_description": "옆집에서 매운 냄새? 같은 가스 냄새 나는데 신고 어디로 해야함",
    "situation": "utility_gas"
  }
}
```

---

## 4. `find_nearest_restroom`

> ㅋㅋㅋ 코엑스 별관쪽 화장실 급함 진짜 죽겠다

```json
{
  "name": "find_nearest_restroom",
  "arguments": {
    "user_request": "ㅋㅋㅋ 코엑스 별관쪽 화장실 급함 진짜 죽겠다"
  }
}
```

---

## 5. `search_restroom`

> 해운대 해수욕장에서 기저귀 갈만한 데 없을까 아가 데리고 왔어

```json
{
  "name": "search_restroom",
  "arguments": {
    "query": "해운대 해수욕장",
    "user_request": "해운대 해수욕장에서 기저귀 갈만한 데 없을까 아가 데리고 왔어",
    "user_type": "infant_care"
  }
}
```

---

## 6. `find_open_clinic`

> 토요일 밤인데 팔에 두드러기 올라서 영등포구 의원 아직 열린 데 있어?

```json
{
  "name": "find_open_clinic",
  "arguments": {
    "place_query": "영등포구",
    "user_request": "토요일 밤인데 팔에 두드러기 올라서 영등포구 의원 아직 열린 데 있어?",
    "specialty": "general",
    "treatment_day": "토요일"
  }
}
```

---

## 7. `find_veteran_hospital`

> 할아버지 국가유공자신데 부산 서면 쪽 위탁병원 어디 있는지 좀

```json
{
  "name": "find_veteran_hospital",
  "arguments": {
    "place_query": "부산 서면",
    "user_request": "할아버지 국가유공자신데 부산 서면 쪽 위탁병원 어디 있는지 좀"
  }
}
```

---

## 8. `find_emergency_room`

> 교통사고 목격했는데 용산구 응급실 자리 있나 지금?

```json
{
  "name": "find_emergency_room",
  "arguments": {
    "place_query": "용산구",
    "user_request": "교통사고 목격했는데 용산구 응급실 자리 있나 지금?"
  }
}
```

---

## 9. `find_open_pharmacy`

> 일요일 아침인데 두통약 살 약국 종로3가 근처 없냐

```json
{
  "name": "find_open_pharmacy",
  "arguments": {
    "place_query": "종로3가",
    "user_request": "일요일 아침인데 두통약 살 약국 종로3가 근처 없냐",
    "treatment_day": "일요일"
  }
}
```

---

## 10. `find_safety_bell`

> 성수동 카페거리 밤에 혼자 걷는데 비상벨 어딨어 무서움

```json
{
  "name": "find_safety_bell",
  "arguments": {
    "place_query": "성수동",
    "user_request": "성수동 카페거리 밤에 혼자 걷는데 비상벨 어딨어 무서움"
  }
}
```

---

## 11. `get_phrase_card`

> 일본인 친구랑 약국 가는데 페니실린 알레르기 있다고 영어로 뭐라고 말하지

```json
{
  "name": "get_phrase_card",
  "arguments": {
    "scenario": "pharmacy_allergy_check",
    "language": "en"
  }
}
```

---

## 12. `find_subway_facility_tool`

> 부산 서면역에서 캐리어 맡을 수 있는 데 있어? 짐 너무 무거워

```json
{
  "name": "find_subway_facility_tool",
  "arguments": {
    "station_query": "서면역",
    "user_request": "부산 서면역에서 캐리어 맡을 수 있는 데 있어? 짐 너무 무거워",
    "facility_type": "locker"
  }
}
```

---

## 13. `find_safe_place`

> 초등학생 동생이 놀이터에서 못 찾겠다ㅠㅠ 마포구 쉼터 같은 데 있어?

```json
{
  "name": "find_safe_place",
  "arguments": {
    "place_query": "마포구",
    "user_request": "초등학생 동생이 놀이터에서 못 찾겠다ㅠㅠ 마포구 쉼터 같은 데 있어?",
    "category": "youth"
  }
}
```

---

## 14. `find_accessible_facility_tool`

> 여의도공원 휠체어 화장실 어디있는지 아는 사람??

```json
{
  "name": "find_accessible_facility_tool",
  "arguments": {
    "place_query": "여의도공원",
    "user_request": "여의도공원 휠체어 화장실 어디있는지 아는 사람??"
  }
}
```

---

## 15. `find_outdoor_service_tool` (버스정류장)

> 이태원입구역에서 버스 탈 건데 정류장이 어디있는거임 ㅋㅋ

```json
{
  "name": "find_outdoor_service_tool",
  "arguments": {
    "place_query": "이태원입구역",
    "user_request": "이태원입구역에서 버스 탈 건데 정류장이 어디있는거임 ㅋㅋ",
    "service": "bus_stop"
  }
}
```

---

## 주소형 입력 (juso 1순위) 보너스

> 서울특별시 중구 세종대로 110 근처 화장실

```json
{
  "name": "find_nearest_restroom",
  "arguments": {
    "user_request": "서울특별시 중구 세종대로 110 근처 화장실",
    "place_query": "서울특별시 중구 세종대로 110"
  }
}
```

juso 해석 후 `source`에 `juso` 또는 `juso+kakao_address`가 잡히면 정상입니다.

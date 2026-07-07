# modu-emergencybell — Tool 호출 예제 모음

PlayMCP·MCP Inspector·에이전트 테스트용 **실제 `tools/call` arguments** 예시입니다.

> **공통 규칙**
> - 자연어 **원문 전체** → `user_request` (또는 `user_request` / `situation_description` / `query`)
> - **장소만** → `place_query` / `station_query` (명동성당, 강남역, 창신동)
> - `급똥`, `화장실`, `와이파이`는 장소가 **아님**
> - 복합 질문 → `emergency_guide_tool` 또는 `classify_emergency_intent` 먼저

---

## 0. 라우팅 (의도 분류)

### Tool이 애매할 때

```json
{
  "name": "classify_emergency_intent",
  "arguments": {
    "user_request": "명동성당쪽인데 급똥이야 화장실 알려줘"
  }
}
```

### 복합 질문 (권장 진입점)

```json
{
  "name": "emergency_guide_tool",
  "arguments": {
    "user_request": "강남역 근처 화장실이랑 약국 알려줘",
    "place_query": "강남역"
  }
}
```

---

## 1. 긴급 전화

| 사용자 말 | Tool | arguments |
|-----------|------|-----------|
| 집에서 가스 냄새 | `get_emergency_hotlines` | `{"situation_description": "집에서 가스 냄새가 날 때", "situation": "utility_gas"}` |
| 119랑 1339 차이? | `get_emergency_hotlines` | `{"situation_description": "119랑 1339 차이? 아이가 열이 나요"}` |
| 아이 실종했어요 | `get_emergency_hotlines` | `{"situation_description": "아이가 실종됐어요", "situation": "police"}` |

---

## 2. 화장실

| 사용자 말 | Tool | arguments |
|-----------|------|-----------|
| 명동성당쪽 급똥 | `find_nearest_restroom` | `{"user_request": "명동성당쪽인데 급똥이야", "place_query": "명동성당"}` |
| place_query 없이 | `find_nearest_restroom` | `{"user_request": "명동성당쪽인데 급똥이야 화장실"}` |
| 강남역 휠체어 화장실 | `search_restroom` | `{"query": "강남역", "user_type": "wheelchair"}` |
| COEX 기저귀 교환대 | `find_nearest_restroom` | `{"place_query": "COEX", "user_request": "코엑스 기저귀 갈 곳"}` |
| Wheelchair near Hongdae | `find_nearest_restroom` | `{"place_query": "홍대", "user_request": "wheelchair restroom near Hongdae"}` |

---

## 3. 병원·약국·응급실

| 사용자 말 | Tool | arguments |
|-----------|------|-----------|
| 창신동 약국 (동만) | `find_open_pharmacy` | `{"place_query": "창신동", "user_request": "종로구 창신동 오늘 약국"}` |
| 연산9동 내과 | `find_open_clinic` | `{"place_query": "연산9동", "specialty": "internal", "user_request": "연산9동 내과"}` |
| 일요일 밤 소아과 | `find_open_clinic` | `{"place_query": "서울 마포구", "specialty": "pediatric", "treatment_day": "일요일"}` |
| 강남구 응급실 병상 | `find_emergency_room` | `{"place_query": "서울 강남구", "user_request": "강남 응급실 병상"}` |
| 새벽 아이 39도 | `emergency_guide_tool` | `{"user_request": "새벽에 아이 39도인데 마포구", "place_query": "마포구"}` |

---

## 4. 치안·안전

| 사용자 말 | Tool | arguments |
|-----------|------|-----------|
| 이태원 안전비상벨 | `find_safety_bell` | `{"place_query": "이태원", "user_request": "서울 이태원 안전비상벨"}` |
| 광안리 밤에 안전? | `emergency_guide_tool` | `{"user_request": "부산 광안리 밤에 걸어도 안전할까?"}` |
| 강남구 범죄 통계 | `find_safety_bell` | `{"place_query": "강남구", "user_request": "강남구 밤에 안전할까"}` |

---

## 5. 지하철·야외 시설

| 사용자 말 | Tool | arguments |
|-----------|------|-----------|
| 강남역 물품보관함 | `find_subway_facility_tool` | `{"station_query": "강남역", "facility_type": "locker"}` |
| 서울역 엘리베이터 | `find_subway_facility_tool` | `{"station_query": "서울역", "facility_type": "accessibility"}` |
| 홍대 와이파이 | `find_outdoor_service_tool` | `{"place_query": "홍대", "service": "wifi", "user_request": "홍대 와이파이"}` |
| 강남역 버스정류장 | `find_outdoor_service_tool` | `{"place_query": "강남역", "service": "bus_stop"}` |
| 강남 동물병원 | `find_outdoor_service_tool` | `{"place_query": "강남구", "service": "vet_hospital"}` |
| 명동 ATM | `find_outdoor_service_tool` | `{"place_query": "명동", "service": "atm", "station_query": "명동역"}` |

---

## 6. 접근성·Safe182·보훈·외국인

| 사용자 말 | Tool | arguments |
|-----------|------|-----------|
| 명동성당 휠체어 | `find_accessible_facility_tool` | `{"place_query": "명동성당", "user_request": "명동성당 휠체어 화장실"}` |
| ❌ 잘못된 예 | `find_accessible_facility_tool` | `{"facility_id": "wheelchair_restroom"}` ← **금지** |
| 종로 안전지킴이집 | `find_safe_place` | `{"place_query": "종로구", "category": "child_safety_house"}` |
| 보훈 위탁병원 | `find_veteran_hospital` | `{"place_query": "강남구", "user_request": "국가유공자 위탁병원"}` |
| 영어 병원 문장 | `get_phrase_card` | `{"scenario": "hospital_visit", "language": "en"}` |
| 약 알레르기 영어 | `get_phrase_card` | `{"scenario": "pharmacy_allergy_check", "language": "en"}` |

---

## 7. MCP Prompts (시나리오 템플릿)

`prompts/get` 지원 클라이언트에서 사용. 이름 → Tool 호출 가이드 문자열 반환.

| prompt name | 용도 |
|-------------|------|
| `urgent_restroom` | 급똥·화장실 |
| `gas_leak_emergency` | 가스 누새 |
| `child_fever_night` | 새벽 아이 발열 |
| `missing_child` | 아이 실종 |
| `wheelchair_access` | 휠체어·접근성 |
| `night_safety_crime` | 야간 치안 |
| `foreign_tourist_help` | 외국인 관광객 |
| `subway_locker` | 물품보관함 |
| `dong_only_pharmacy` | 동만으로 약국/병원 |
| `wifi_bus_vet` | WiFi·버스·동물병원 |
| `veteran_hospital` | 보훈 위탁병원 |
| `classify_before_call` | Tool 선택 애매할 때 |

---

## 8. PlayMCP 스타터 메시지 (심사용)

1. 집에서 가스 냄새가 날 때 어떻게 해?
2. 명동성당쪽인데 급똥이야 화장실 알려줘
3. 종로구 창신동 오늘 여는 약국
4. 강남역 근처 휠체어 화장실
5. 새벽에 아이 39도인데 마포구 소아과·약국
6. 부산 광안리 안전비상벨 어디 있어?
7. 홍대 무료 와이파이 어디야?
8. 강남역 버스정류장 어디야?
9. Wheelchair restroom near Myeongdong Cathedral?
10. 강남구 밤에 걸어도 안전할까?

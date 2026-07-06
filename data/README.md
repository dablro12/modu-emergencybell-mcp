# data/toilet_data — 공중화장실 데이터

행정안전부 **전국 공중화장실 표준데이터** CSV를 가공한 파일 모음입니다.

## 원본

| 파일 | 설명 |
|------|------|
| `공중화장실정보.csv` | UTF-8 변환된 원본 (~59,757건, 좌표 없음) |

## 가공 파일 (`공중화장실_##`)

| 파일 | 설명 |
|------|------|
| `공중화장실_01_전체레코드.json` | 정규화된 전체 레코드 (MCP Server 로드용) |
| `공중화장실_02_메타정보.json` | 출처, 건수, 이용자·개방 유형 정의 |
| `공중화장실_03_이용자유형_색인.json` | 이용자 유형별 `관리번호` 목록 |
| `공중화장실_04_개방시간유형_색인.json` | 개방 시간 유형별 ID 목록 |
| `공중화장실_05_지역_색인.json` | 시도+시군구별 ID 목록 |
| `공중화장실_06_통계요약.json` | 유형·시설·지역 Top20 통계 |

## 재생성

```bash
python scripts/process_restroom_data.py
```

CSV만 수정했을 때 위 명령으로 JSON을 다시 만듭니다.

---

## 이용자 유형 (`user_types.tags`)

| tag | 의미 | CSV 기준 |
|-----|------|----------|
| `general` | 일반 이용 | 모든 개방 화장실 |
| `wheelchair` | 장애인·휠체어 | 남/여 장애인용 대·소변기 ≥ 1 |
| `child` | 어린이 | 남/여 어린이용 대·소변기 ≥ 1 |
| `infant_care` | 영유아 동반 | 기저귀교환대유무 = Y |
| `elderly_safety` | 고령·안전 취약 | 비상벨설치여부 = Y |

한 화장실에 여러 tag가 동시에 붙을 수 있습니다.

---

## 개방 시간 유형 (`opening.type`)

| type | 원본 `개방시간` | 설명 |
|------|----------------|------|
| `always` | 상시 | 24시간 개방으로 간주 |
| `scheduled` | 정시 | `개방시간상세` 파싱 필요 |
| `irregular` | 불규칙 | 시간 예측 어려움 |
| `closed` | 미개방 | 미개방 유형 |
| `unknown` | (빈값) | 정보 없음 |

`open_now=true` Tool 호출 시: `상시`는 항상 포함, `정시`는 KST 기준 시간대 매칭 시도.

---

## 시설 필드 (`facilities`)

| 필드 | 설명 |
|------|------|
| `emergency_bell` | 비상벨 |
| `diaper_station` | 기저귀 교환대 |
| `cctv_entrance` | 입구 CCTV |
| `safety_management_target` | 안전관리시설 대상 |
| `wheelchair_*` / `child_*` | 성별·유형별 칸 수 |

---

## 좌표·반경 검색

원본 CSV에는 **WGS84 위·경도가 없습니다.**

반경 검색(`100m`, `500m`) 흐름:

1. [Kakao Local API](https://developers.kakao.com/docs/ko/local/dev-guide)로 사용자 장소 → 좌표
2. `coord2regioncode`로 행정구역 힌트
3. `공중화장실_05_지역_색인` / 레코드 `region`으로 1차 필터
4. (향후) 주소 geocode 캐시 추가 시 정밀 거리 계산

---

## 레코드 예시

```json
{
  "id": "202530000000100840",
  "name": "올림픽기념국민생활관",
  "road_address": "서울특별시 종로구 성균관로 91",
  "region": { "sido": "서울특별시", "sigungu": "종로구" },
  "user_types": {
    "tags": ["general", "wheelchair", "elderly_safety"],
    "wheelchair": true,
    "infant_care": false
  },
  "opening": {
    "type": "scheduled",
    "type_raw": "정시",
    "detail": "월-금06:00~22:00 ..."
  }
}
```

---

## Docker

`server/Dockerfile`에서 `data/` 전체를 이미지에 포함합니다.  
`공중화장실_01_전체레코드.json`이 약 110MB이므로 이미지 크기에 반영됩니다.

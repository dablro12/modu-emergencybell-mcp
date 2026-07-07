# PlayMCP in KC — linux/amd64 빌드 필수 (Apple Silicon: --platform linux/amd64)
FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY modu_emergencybell.py helpers.py hotlines.py nemc_client.py region_parse.py landmarks.py kakao_local.py juso_client.py place_context.py place_resolver.py emergency_guide.py restroom_parser.py safety_bell.py crime_stats.py bus_stop.py veteran_hospital.py phrases.py datago_json_client.py subway_facility.py subway_atm.py outdoor_services.py safe182_client.py accessible_facility_client.py ./
COPY scripts/ ./scripts/
COPY data/ ./data/

RUN python scripts/process_restroom_data.py && \
    test -f data/toilet_data/공중화장실_01_전체레코드.json && \
    python scripts/process_subway_data.py && \
    test -f data/subway/subway_index.json && \
    python scripts/process_subway_atm_data.py && \
    test -f data/subway/subway_atm_index.json && \
    python scripts/process_crime_stats_data.py && \
    test -f data/emergencybell/crime_stats_index.json && \
    python scripts/process_bus_stop_data.py && \
    test -f data/bus/bus_stop_index.json && \
    python scripts/process_veteran_hospital_data.py && \
    test -f data/medical/veteran_hospital_index.json

# CI/GitHub Secrets → build-arg 로 주입 (공개 repo에 키 커밋 금지)
ARG DATA_GO_KR_SERVICE_KEY=""
ARG DATA_GO_KR_SERVICE_KEY_ENCODED=""
ARG ODCLOUD_SERVICE_KEY=""
ARG ODCLOUD_SERVICE_KEY_ENCODED=""
ARG KAKAO_REST_API_KEY=""
ARG JUSO_CONFM_KEY=""
ARG JUSO_ENG_CONFM_KEY=""
ARG SAFE182_AUTH_ID=""
ARG SAFE182_AUTH_KEY=""
ENV DATA_GO_KR_SERVICE_KEY=${DATA_GO_KR_SERVICE_KEY}
ENV DATA_GO_KR_SERVICE_KEY_ENCODED=${DATA_GO_KR_SERVICE_KEY_ENCODED}
ENV ODCLOUD_SERVICE_KEY=${ODCLOUD_SERVICE_KEY}
ENV ODCLOUD_SERVICE_KEY_ENCODED=${ODCLOUD_SERVICE_KEY_ENCODED}
ENV KAKAO_REST_API_KEY=${KAKAO_REST_API_KEY}
ENV JUSO_CONFM_KEY=${JUSO_CONFM_KEY}
ENV JUSO_ENG_CONFM_KEY=${JUSO_ENG_CONFM_KEY}
ENV SAFE182_AUTH_ID=${SAFE182_AUTH_ID}
ENV SAFE182_AUTH_KEY=${SAFE182_AUTH_KEY}

ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

CMD ["python", "modu_emergencybell.py"]

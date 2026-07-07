# PlayMCP in KC — linux/amd64 빌드 필수 (Apple Silicon: --platform linux/amd64)
FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY modu_emergencybell.py helpers.py hotlines.py nemc_client.py region_parse.py landmarks.py kakao_local.py restroom_parser.py safety_bell.py phrases.py datago_json_client.py finmap_client.py odsay_client.py subway_facility.py outdoor_services.py ./
COPY scripts/ ./scripts/
COPY data/ ./data/

RUN python scripts/process_restroom_data.py && \
    test -f data/toilet_data/공중화장실_01_전체레코드.json && \
    python scripts/process_subway_data.py && \
    test -f data/subway/subway_index.json

# CI/GitHub Secrets → build-arg 로 주입 (공개 repo에 키 커밋 금지)
ARG DATA_GO_KR_SERVICE_KEY=""
ARG DATA_GO_KR_SERVICE_KEY_ENCODED=""
ARG KAKAO_REST_API_KEY=""
ARG ODSAY_API_KEY=""
ARG KFTC_FINMAP_CLIENT_ID=""
ARG KFTC_FINMAP_CLIENT_SECRET=""
ARG KFTC_FINMAP_BASE_URL="https://testfinmapapi.kftc.or.kr"
ENV DATA_GO_KR_SERVICE_KEY=${DATA_GO_KR_SERVICE_KEY}
ENV DATA_GO_KR_SERVICE_KEY_ENCODED=${DATA_GO_KR_SERVICE_KEY_ENCODED}
ENV KAKAO_REST_API_KEY=${KAKAO_REST_API_KEY}
ENV ODSAY_API_KEY=${ODSAY_API_KEY}
ENV KFTC_FINMAP_CLIENT_ID=${KFTC_FINMAP_CLIENT_ID}
ENV KFTC_FINMAP_CLIENT_SECRET=${KFTC_FINMAP_CLIENT_SECRET}
ENV KFTC_FINMAP_BASE_URL=${KFTC_FINMAP_BASE_URL}

ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

CMD ["python", "modu_emergencybell.py"]

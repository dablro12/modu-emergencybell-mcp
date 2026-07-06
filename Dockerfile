# Git 소스 빌드 기본 경로용 (server/Dockerfile 과 동일)
FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY modu_emergencybell.py helpers.py hotlines.py nemc_client.py region_parse.py kakao_local.py restroom_parser.py safety_bell.py phrases.py ./
COPY scripts/ ./scripts/
COPY data/ ./data/

RUN python scripts/process_restroom_data.py && \
    test -f data/toilet_data/공중화장실_01_전체레코드.json

ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

CMD ["python", "modu_emergencybell.py"]

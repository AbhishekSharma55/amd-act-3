# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY shared/ /build/shared/
ENV VITE_USE_MOCKS=0
RUN npm run build

FROM python:3.12-slim-bookworm AS python-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

FROM python-base AS dependencies
RUN python -m venv /opt/venv
COPY backend/requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir --only-binary=:all: -r /tmp/requirements.txt

FROM python-base AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/backend \
    PORT=7860 \
    STATIC_DIR=/app/backend/static \
    SOLVER_WORKERS=2 \
    ALLOW_RULE_FALLBACK=0
WORKDIR /app
RUN useradd --create-home --uid 1000 --user-group rehearsal
COPY --from=dependencies /opt/venv /opt/venv
COPY backend/app/ /app/backend/app/
COPY shared/ /app/shared/
COPY --from=frontend /build/frontend/dist/ /app/backend/static/
USER 1000:1000
EXPOSE 7860
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import json,os,urllib.request; r=urllib.request.urlopen('http://127.0.0.1:'+os.environ['PORT']+'/api/health',timeout=3); assert json.load(r)['ok'] is True"]
CMD ["python", "-m", "app.serve"]

# Multi-stage build for VELORA
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
# Unique build id so clients detect new deploy
ARG RAILWAY_GIT_COMMIT_SHA
ARG BUILD_TIME
RUN BUILD_ID="${RAILWAY_GIT_COMMIT_SHA:-$(date +%s)}" &&     echo "{\"v\":\"$BUILD_ID\",\"built\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > public/version.json &&     echo "VELORA build $BUILD_ID" &&     npm run build

FROM python:3.11-slim
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

ENV PYTHONPATH=/app/backend
ENV UPLOAD_DIR=/app/uploads
RUN mkdir -p /app/uploads

WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

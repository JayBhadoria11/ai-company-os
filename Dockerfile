# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# AI Company OS - production image
#
# Multi-stage build from the repository root:
#   1. Build the React dashboard with Node.
#   2. Install Python dependencies and copy the built dashboard into a slim
#      Python runtime, so a single uvicorn process serves both API and UI.
#
# Build:  docker build -t ai-company-os .
# Run:    docker run -p 8000:8000 -e NEBIUS_API_KEY=... ai-company-os
# ---------------------------------------------------------------------------

# ---- Stage 1: build the React frontend ----------------------------------
FROM node:22-alpine AS frontend
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime --------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY --from=frontend /app/frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

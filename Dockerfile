# ==========================================
# Multi-Stage Dockerfile for SentinelGIS
# ==========================================

# --- Stage 1: Build React Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
# Set production build flag so API calls default to relative same-origin paths
ENV NODE_ENV=production
RUN npm run build

# --- Stage 2: Python Backend Runtime ---
FROM python:3.11-slim AS runtime
WORKDIR /app

# Install system dependencies if required for compiling
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy Backend Application Code & Data
COPY backend/ ./backend/

# Copy compiled Frontend build from Stage 1 into frontend/build
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Expose default port
EXPOSE 8000

ENV PORT=8000
ENV HOST=0.0.0.0
ENV ENVIRONMENT=production

# Start Uvicorn ASGI server
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]

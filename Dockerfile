# ============================================================
# Stage 1: Build React frontend
# ============================================================
FROM node:22-alpine AS frontend

WORKDIR /web

# Install dependencies first for better layer caching
COPY web/package.json web/package-lock.json ./
RUN npm ci

# Build the frontend
COPY web/ ./
RUN npm run build

# ============================================================
# Stage 2: Install Python dependencies
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies (kept as insurance for any future
# source-only packages; all current deps ship prebuilt wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies to user site-packages
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================
# Stage 3: Runtime image
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 analyst

# Copy installed packages from builder
COPY --from=builder /root/.local /home/analyst/.local

# Copy application code
COPY agent/ ./agent/
COPY api/ ./api/

# Copy built frontend from frontend stage
COPY --from=frontend /web/dist/ ./web/dist/

# Set environment variables
ENV PATH=/home/analyst/.local/bin:$PATH \
    PYTHONPATH=/app \
    DATA_DIR=/app/data

# Create data directory
RUN mkdir -p /app/data && chown -R analyst:analyst /app

# Switch to non-root user
USER analyst

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Runtime stage
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

# Create web/dist directory if it doesn't exist (for first-time builds)
RUN mkdir -p ./web/dist
COPY web/dist/ ./web/dist/ || true

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
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

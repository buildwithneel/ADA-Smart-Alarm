# --- Base Stage ---
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /code

# Install system dependencies needed for PostgreSQL client and runtime healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group
RUN groupadd --system --gid 10001 ada && \
    useradd --system --uid 10001 --gid ada --no-create-home ada

# --- Development / Builder Stage ---
FROM base AS builder

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Final Production Stage ---
FROM base AS runner

# Copy installed python dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source code and set correct ownership
COPY --chown=ada:ada . .

# Switch to non-root user for security
USER ada

# Expose FastAPI port
EXPOSE 8000

# Health check to ensure the container is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Production command running with 4 uvicorn workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]


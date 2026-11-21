# =============================================================================
# SpaceBuddy Telegram Bot — Dockerfile
# Multi-stage build: "builder" installs deps, "runtime" runs the bot.
# =============================================================================

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools needed by some Python packages (e.g. cryptography)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first so Docker can cache this layer separately
COPY requirements.txt .

# Install runtime dependencies into an isolated prefix so we can copy cleanly
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Labels / OCI metadata
LABEL org.opencontainers.image.title="SpaceBuddy"
LABEL org.opencontainers.image.description="Telegram bot for NASA APOD & asteroid tracking"
LABEL org.opencontainers.image.source="https://github.com/your-username/Space_Buddy-Bot"

# Non-root user for security
RUN addgroup --system spacebuddy \
    && adduser  --system --ingroup spacebuddy --no-create-home spacebuddy

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source (respects .dockerignore)
COPY --chown=spacebuddy:spacebuddy . .

# Persistent volume for the SQLite database
# Map this to a host directory or named volume so data survives restarts.
VOLUME ["/app/data"]

# Tell config.py to store the DB inside /app/data by default.
# Override DATABASE_PATH in your .env or docker-compose.yml as needed.
ENV DATABASE_PATH=/app/data/space_buddy.db \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Drop root privileges
USER spacebuddy

# Health-check: verify the Python environment is importable
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import bot" || exit 1

# Entrypoint: run the bot via main.py
CMD ["python", "main.py"]

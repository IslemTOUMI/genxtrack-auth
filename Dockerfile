# ---- base image ----
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/usr/local/bin:${PATH}"

# Librairies système utiles (psycopg[binary] n'en a pas besoin, mais pour confort)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl tzdata build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- builder: installer deps ----
FROM base AS builder
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

# ---- runtime ----
FROM base AS runtime
WORKDIR /app

# Copie deps depuis builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copie du code
COPY app ./app
COPY wsgi.py .
COPY migrations ./migrations
COPY docker/entrypoint.sh ./entrypoint.sh

# Droits + LF
RUN chmod +x ./entrypoint.sh

# Port d’écoute gunicorn
EXPOSE 8000

# Variables par défaut (override via compose)
ENV APP_ENV=production \
    FLASK_ENV=production \
    ENFORCE_HTTPS=false \
    RATELIMIT_STORAGE_URI=redis://redis:6379/0 \
    DATABASE_URL=postgresql+psycopg://app_user:app_password_strong@db:5432/app_db

# Healthcheck (utilise /healthz)
HEALTHCHECK --interval=15s --timeout=3s --retries=10 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

# --- Swagger UI assets (served locally, no CDN needed) ---
RUN mkdir -p /app/static/swagger && \
    curl -L https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui.css -o /app/static/swagger/swagger-ui.css && \
    curl -L https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui-bundle.js -o /app/static/swagger/swagger-ui-bundle.js

ENTRYPOINT ["./entrypoint.sh"]
# gunicorn est lancé dans l'entrypoint après migrations

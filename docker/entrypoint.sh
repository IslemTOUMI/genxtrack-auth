#!/usr/bin/env bash
set -euo pipefail

# Eviter les CRLF depuis Windows

echo "[entrypoint] Waiting for Postgres at ${DATABASE_URL}"
# Boucle jusqu'à ce que la DB réponde
python - <<'PY'
import os, time
import psycopg

url = os.getenv("DATABASE_URL") or ""
# Convertit l’URL SQLAlchemy -> URL psycopg (libpq)
if url.startswith("postgresql+psycopg://"):
    url_psycopg = url.replace("postgresql+psycopg://", "postgresql://", 1)
elif url.startswith("postgresql+psycopg2://"):
    url_psycopg = url.replace("postgresql+psycopg2://", "postgresql://", 1)
else:
    url_psycopg = url

for i in range(60):
    try:
        with psycopg.connect(url_psycopg, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1;")
        print("[entrypoint] Postgres is up.")
        break
    except Exception as e:
        print("[entrypoint] Postgres not ready, retrying...", e)
        time.sleep(2)
else:
    raise SystemExit("[entrypoint] Postgres did not become ready in time.")
PY


# Migrations DB
echo "[entrypoint] Running migrations..."
export FLASK_APP=wsgi.py
flask db upgrade

# Lancement gunicorn
echo "[entrypoint] Starting gunicorn..."
# Workers: 2 * CPU + 1 ; threads 4 (API I/O bound)
exec gunicorn --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --threads ${GUNICORN_THREADS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-30} \
    wsgi:app

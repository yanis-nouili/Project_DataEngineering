#!/usr/bin/env sh
set -e

echo "Waiting for Postgres..."
python - <<'PY'
import os, time, psycopg2
host=os.getenv("POSTGRES_HOST","db")
db=os.getenv("POSTGRES_DB","ligue1")
user=os.getenv("POSTGRES_USER","yanis")
pwd=os.getenv("POSTGRES_PASSWORD","yanis123")
port=int(os.getenv("POSTGRES_PORT","5432"))

for _ in range(60):
    try:
        psycopg2.connect(host=host, dbname=db, user=user, password=pwd, port=port).close()
        print(" Postgres is ready")
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("Postgres not reachable after 60s")
PY

echo "Running scrapers..."
python -m scraper.run_all || echo "Scraping failed (continuing)"

echo "Starting Streamlit..."
exec streamlit run app/app.py --server.port=8501 --server.address=0.0.0.0

#!/bin/sh
set -e

echo "Waiting for Postgres at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
until python - <<'PYEOF'
import os, socket, sys, time
host = os.environ.get("POSTGRES_HOST", "postgres")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect((host, port))
    sys.exit(0)
except Exception:
    sys.exit(1)
PYEOF
do
  sleep 1
done
echo "Postgres is up."

# Only the web service should run migrations/collectstatic; Celery
# containers pass a different command and skip straight to exec.
if [ "$1" = "gunicorn" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
fi

exec "$@"

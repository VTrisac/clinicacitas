#!/usr/bin/env bash
# Build en Render: dependencias, app React (si hay Node), estáticos, migraciones y datos de ejemplo.
set -o errexit
pip install -r requirements.txt
if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm ci && npm run build)
else
  echo "Node no disponible: se usa la build de React incluida en static/reserva/"
fi
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_demo

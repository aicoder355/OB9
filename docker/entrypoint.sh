#!/usr/bin/env bash
set -e

# Default to web mode; set RUN_MODE=bot to run the Telegram bot
RUN_MODE=${RUN_MODE:-web}

if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

if [ "$RUN_MODE" = "bot" ]; then
  echo "Starting Telegram bot (polling)..."
  python - <<'PY'
from crm.telegram_bot import create_application
app = create_application()
app.run_polling()
PY
else
  echo "Starting Django development server..."
  python manage.py runserver 0.0.0.0:8000
fi

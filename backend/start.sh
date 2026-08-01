#!/usr/bin/env bash
set -e

ENV=${1:-dev}

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database..."
python seed.py

echo "Ensuring AI models are downloaded..."
# Models cached in volume; skip redundant download loop


echo "Starting application in $ENV mode..."
if [ "$ENV" = "dev" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

#!/usr/bin/env bash
set -e

ENV=${1:-dev}

echo "Running database migrations..."
alembic upgrade head

echo "Seeding database..."
python seed.py

echo "Ensuring AI models are downloaded..."
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

echo "Starting application in $ENV mode..."
if [ "$ENV" = "dev" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

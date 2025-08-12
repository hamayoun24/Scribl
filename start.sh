#!/usr/bin/env bash

set -e

PORT=${PORT:-5000}

echo "Starting FastAPI app on 0.0.0.0:$PORT"

exec python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --proxy-headers \
    --forwarded-allow-ips="*"

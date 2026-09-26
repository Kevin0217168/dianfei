#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"
source .venv/bin/activate 2>/dev/null || true
exec uvicorn app:app --host 0.0.0.0 --port 8000

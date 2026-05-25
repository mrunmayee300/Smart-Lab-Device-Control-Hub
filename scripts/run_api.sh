#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
uvicorn smart_lab.api.main:app --host "${SMART_LAB_API_HOST:-0.0.0.0}" --port "${SMART_LAB_API_PORT:-8000}"

#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m grpc_tools.protoc -I proto \
  --python_out=src/smart_lab/grpc_generated \
  --grpc_python_out=src/smart_lab/grpc_generated \
  proto/smart_lab.proto
cp -n .env.example .env || true
echo "Smart Lab development environment is ready."

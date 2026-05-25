FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential make \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY proto ./proto

RUN pip install --upgrade pip \
    && pip install ".[dev]" \
    && python -m grpc_tools.protoc -I proto \
        --python_out=src/smart_lab/grpc_generated \
        --grpc_python_out=src/smart_lab/grpc_generated \
        proto/smart_lab.proto

EXPOSE 8000 50051 9100

CMD ["uvicorn", "smart_lab.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

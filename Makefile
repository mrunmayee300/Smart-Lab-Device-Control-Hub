.PHONY: install dev test lint format proto run grpc docker-up docker-down

install:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

dev: install proto

test:
	pytest -q --cov=smart_lab --cov-report=term-missing

lint:
	ruff check src tests

format:
	ruff format src tests
	ruff check --fix src tests

proto:
	python -m grpc_tools.protoc -I proto \
		--python_out=src/smart_lab/grpc_generated \
		--grpc_python_out=src/smart_lab/grpc_generated \
		proto/smart_lab.proto

run:
	uvicorn smart_lab.api.main:app --host 0.0.0.0 --port 8000 --reload

grpc:
	python -m smart_lab.grpc_server.server

docker-up:
	docker compose up --build

docker-down:
	docker compose down --volumes

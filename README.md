# Smart Lab Device Control Hub

Production-style Python systems engineering backend for real-time laboratory instrument control. The platform simulates medical/R&D lab devices, streams telemetry, executes assay workflows, exposes REST/WebSocket/gRPC interfaces, and demonstrates Linux-friendly concurrency, multiprocessing, and IPC patterns.

## What It Demonstrates

- FastAPI backend with async endpoints, OpenAPI docs, background services, and WebSocket telemetry.
- Independent simulated instruments for temperature, pH, microfluidic flow, spectrometry, and voltage.
- `asyncio` for I/O polling, multiprocessing for CPU feature extraction, and threading for socket IPC.
- IPC via `multiprocessing.Queue`, shared memory, TCP sockets, and pipes.
- SQLAlchemy async ORM with SQLite locally and PostgreSQL in Docker Compose.
- Protobuf/gRPC device, command, and telemetry services.
- Typer CLI for device operations, assays, logs, and monitoring.
- Retryable/cancellable assay scheduler with execution history.
- Docker, Compose, Makefile, shell scripts, structured JSON logging, and GitHub Actions CI.

## Architecture

```mermaid
flowchart LR
    CLI[labctl CLI] --> API[FastAPI REST API]
    UI[WebSocket clients] --> WS[Telemetry and Assay WS]
    GRPC[gRPC clients] --> G[Device/Command/Telemetry gRPC]
    API --> DM[Device Manager]
    G --> DM
    DM --> DEV[Simulated Devices]
    DEV --> BUS[UART/I2C/SPI Simulation]
    DM --> EB[Event Bus]
    EB --> WS
    EB --> WR[Worker Runtime]
    DM --> INGEST[Telemetry Ingest]
    INGEST --> DB[(SQLite/PostgreSQL)]
    API --> SCH[Assay Scheduler]
    SCH --> DM
    WR --> MQ[multiprocessing.Queue]
    MQ --> CPU[CPU Worker Processes]
    CPU --> SHM[Shared Memory Heartbeat]
    WR --> SOCK[Threaded Status Socket]
```

## Folder Structure

```text
src/smart_lab/
  api/              FastAPI routes, WebSockets, app lifecycle
  cli/              labctl Typer CLI and optional gRPC client helpers
  database/         SQLAlchemy async models, sessions, repository
  devices/          Simulated devices and UART/I2C/SPI transport behavior
  grpc_server/      Async gRPC service implementation
  grpc_generated/   Generated protobuf stubs from make proto
  monitoring/       CPU, memory, device, queue, and worker snapshots
  scheduler/        Multi-step assay orchestration
  services/         Device manager, telemetry ingest, rate limit, worker runtime
  shared/           Pydantic contracts, config, logging, event bus
  workers/          IPC primitives, CPU worker pool, socket status service
proto/              Protocol Buffer definitions
tests/              Unit, async, API, IPC, and concurrency tests
scripts/            Linux-friendly bootstrap and runtime scripts
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
make proto
make run
```

Open API docs at `http://127.0.0.1:8000/docs`.

Run with Docker:

```bash
docker compose up --build
```

## CLI Examples

```bash
labctl devices
labctl start-device temp_sensor_1
labctl stop-device pump_1
labctl reset-device voltage_reader_1
labctl run-assay blood_test
labctl monitor
labctl logs --limit 25
```

## API Examples

```bash
curl http://127.0.0.1:8000/api/v1/devices
curl http://127.0.0.1:8000/api/v1/devices/health
curl -X POST http://127.0.0.1:8000/api/v1/devices/temp_sensor_1/commands \
  -H "Content-Type: application/json" \
  -d '{"command":"start"}'
curl -X POST http://127.0.0.1:8000/api/v1/assays/run \
  -H "Content-Type: application/json" \
  -d '{"assay_id":"blood_test"}'
```

WebSocket streams:

- `ws://127.0.0.1:8000/ws/telemetry`
- `ws://127.0.0.1:8000/ws/assays`

## gRPC

Generate protobuf stubs:

```bash
make proto
```

Run the gRPC server:

```bash
make grpc
```

Services defined in `proto/smart_lab.proto`:

- `DeviceService.ListDevices`
- `DeviceService.GetDeviceHealth`
- `CommandService.Execute`
- `TelemetryService.StreamTelemetry`

## Concurrency Model

Device polling uses `asyncio` because simulated UART/I2C/SPI traffic is I/O-bound and benefits from cooperative scheduling. CPU-heavy spectral feature extraction is isolated in a multiprocessing worker pool so numerical work cannot block the event loop. A small threaded TCP status server provides low-overhead IPC health probes while the API remains responsive.

The in-process event bus fans out telemetry and assay updates to WebSocket clients, worker bridges, and internal services. Device commands are synchronized per manager to avoid conflicting state transitions like simultaneous reset and start.

## IPC Model

- `multiprocessing.Queue` carries telemetry payloads from the async runtime to CPU workers.
- Shared memory stores worker heartbeat and processing counters for fast status reads.
- Pipes support parent-to-worker control messages such as health checks and shutdown.
- A threaded TCP socket exposes runtime state for local Linux probes and supervisor scripts.

## Database

Local development defaults to SQLite:

```text
SMART_LAB_DATABASE_URL=sqlite+aiosqlite:///./smart_lab.db
```

Docker Compose uses PostgreSQL:

```text
postgresql+asyncpg://smart_lab:smart_lab@postgres:5432/smart_lab
```

Stored data includes device configs, telemetry, structured logs, assay history, and worker events.

## Testing and CI

```bash
make lint
make test
```

GitHub Actions runs install, protobuf generation, Ruff linting, pytest with coverage, and Docker build validation.

## Screenshot Descriptions

- OpenAPI dashboard: FastAPI `/docs` showing device, telemetry, assay, worker, and monitoring endpoints grouped under `/api/v1`.
- Live telemetry client: WebSocket viewer receiving temperature, pH, pump, spectrometer, and voltage events with device IDs and timestamps.
- CLI monitor: terminal output showing process CPU, memory, device count, and queue depth refreshing every few seconds.
- Assay history view: JSON response showing a `blood_test` run progressing through pump priming, sensor startup, spectrometer readout, and completion.

## Production Notes

For a deployed medical-device backend, add authenticated transport, audit-signing, regulatory traceability, database migrations, hardware abstraction interfaces, and per-device safety envelopes. This project is intentionally simulator-first, but the architecture separates transport, device contracts, command execution, and telemetry storage so real drivers can be introduced behind the same interfaces.

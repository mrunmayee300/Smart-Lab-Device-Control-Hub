# API Reference

Interactive OpenAPI documentation is available at `/docs` when the API server is running.

## Core Endpoints

- `GET /api/v1/health` returns service health.
- `GET /api/v1/devices` lists registered devices.
- `POST /api/v1/devices/register` registers a device configuration.
- `GET /api/v1/devices/health` returns device runtime state.
- `POST /api/v1/devices/{device_id}/commands` executes `start`, `stop`, `reset`, `calibrate`, or `set_rate`.
- `GET /api/v1/telemetry` returns persisted telemetry.
- `GET /api/v1/assays` lists assay definitions.
- `POST /api/v1/assays/run` starts an assay.
- `POST /api/v1/assays/{run_id}/cancel` cancels a running assay.
- `GET /api/v1/assays/history` returns assay execution history.
- `GET /api/v1/workers/status` returns runtime worker state.
- `GET /api/v1/monitoring` returns CPU, memory, queue, worker, and device snapshots.

## Streams

- `GET ws://host/ws/telemetry` streams live telemetry events.
- `GET ws://host/ws/assays` streams assay state changes.

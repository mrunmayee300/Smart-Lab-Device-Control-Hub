# Architecture Notes

## System Flow

1. The FastAPI lifespan initializes the database, discovers configured devices, starts telemetry ingest, and starts IPC worker runtime when enabled.
2. Clients issue commands through REST, CLI, or gRPC.
3. `DeviceManager` serializes command execution, updates device state, and starts/stops async polling tasks.
4. Polling tasks simulate UART/I2C/SPI frames, read values, publish telemetry events, and enqueue telemetry for persistence.
5. `TelemetryIngestService` writes telemetry to the database.
6. `WorkerRuntime` subscribes to telemetry events and forwards payloads through `multiprocessing.Queue` to CPU workers.
7. CPU workers extract numerical features and publish worker heartbeat data through shared memory.
8. WebSocket subscribers receive live telemetry and assay events through the event bus.

## Device Model

Each device implements:

- `start`, `stop`, `reset`, `calibrate`, and `set_rate` command behavior.
- Async `poll_once` and `stream` methods.
- Health metrics with current state, error count, queue depth, transport, and uptime.
- Transport-specific simulated bus behavior.

## Fault Tolerance

- Device command failures move a device to `FAULTED`.
- Assay steps retry with exponential backoff and fail the run only after retry exhaustion.
- Telemetry queues are bounded to prevent unbounded memory growth.
- WebSocket event queues drop oldest messages when slow consumers fall behind.
- Worker shutdown uses cooperative stop events, pipe messages, join timeouts, and process termination fallback.

## Extending With Real Hardware

Replace `devices/communication.py` bus classes with pyserial, smbus, or spidev adapters while keeping `SimulatedDevice` contracts stable. Real hardware should add command safety validation, calibration records, hardware watchdogs, and audit-grade event persistence.

# CLI Guide

`labctl` communicates with the FastAPI backend by default. Set `SMART_LAB_API_URL` to point at another API instance.

```bash
export SMART_LAB_API_URL=http://127.0.0.1:8000/api/v1
```

## Commands

- `labctl devices` lists devices.
- `labctl start-device temp_sensor_1` starts a device.
- `labctl stop-device pump_1` stops a device.
- `labctl reset-device voltage_reader_1` resets a device.
- `labctl run-assay blood_test` starts the built-in blood chemistry workflow.
- `labctl monitor` polls backend CPU, memory, device count, and queue depth.
- `labctl logs --limit 25` shows recent structured log records.

Generate protobuf stubs with `make proto` before using optional gRPC client helpers in `smart_lab.cli.grpc_client`.

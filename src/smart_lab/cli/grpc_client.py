import asyncio
import sys
from pathlib import Path

import grpc
from google.protobuf.empty_pb2 import Empty

from smart_lab.shared.config import get_settings

GENERATED_DIR = Path(__file__).resolve().parents[1] / "grpc_generated"
if str(GENERATED_DIR) not in sys.path:
    sys.path.insert(0, str(GENERATED_DIR))

try:
    import smart_lab_pb2_grpc
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Generate protobuf stubs with `make proto` before using gRPC CLI calls") from exc


async def list_devices_grpc() -> list[dict]:
    settings = get_settings()
    async with grpc.aio.insecure_channel(f"{settings.grpc_host}:{settings.grpc_port}") as channel:
        stub = smart_lab_pb2_grpc.DeviceServiceStub(channel)
        response = await stub.ListDevices(Empty())
        return [
            {
                "device_id": device.device_id,
                "device_type": device.device_type,
                "transport": device.transport,
                "enabled": device.enabled,
            }
            for device in response.devices
        ]


def list_devices() -> list[dict]:
    return asyncio.run(list_devices_grpc())

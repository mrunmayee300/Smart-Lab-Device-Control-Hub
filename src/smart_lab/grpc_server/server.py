import asyncio
import logging
import sys
from pathlib import Path

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.timestamp_pb2 import Timestamp

from smart_lab.services.device_manager import device_manager
from smart_lab.shared.config import get_settings
from smart_lab.shared.event_bus import event_bus
from smart_lab.shared.models import CommandType

GENERATED_DIR = Path(__file__).resolve().parents[1] / "grpc_generated"
if str(GENERATED_DIR) not in sys.path:
    sys.path.insert(0, str(GENERATED_DIR))

try:
    import smart_lab_pb2
    import smart_lab_pb2_grpc
except ImportError as exc:  # pragma: no cover - exercised after protobuf generation
    raise RuntimeError("Generate protobuf stubs with `make proto` before running gRPC") from exc

logger = logging.getLogger(__name__)


class DeviceService(smart_lab_pb2_grpc.DeviceServiceServicer):
    async def ListDevices(self, request: Empty, context) -> smart_lab_pb2.DeviceList:
        return smart_lab_pb2.DeviceList(
            devices=[
                smart_lab_pb2.Device(
                    device_id=config.device_id,
                    device_type=config.device_type.value,
                    transport=config.transport.value,
                    enabled=config.enabled,
                )
                for config in device_manager.list_configs()
            ]
        )

    async def GetDeviceHealth(self, request: smart_lab_pb2.DeviceId, context) -> smart_lab_pb2.CommandResponse:
        for health in device_manager.health():
            if health.device_id == request.device_id:
                return smart_lab_pb2.CommandResponse(
                    command_id="health",
                    device_id=request.device_id,
                    accepted=True,
                    message=health.model_dump_json(),
                )
        return smart_lab_pb2.CommandResponse(
            command_id="health", device_id=request.device_id, accepted=False, message="unknown device"
        )


class CommandService(smart_lab_pb2_grpc.CommandServiceServicer):
    async def Execute(self, request: smart_lab_pb2.CommandRequest, context) -> smart_lab_pb2.CommandResponse:
        result = await device_manager.command(
            request.device_id,
            CommandType(request.command),
            payload=dict(request.payload),
            priority=request.priority,
        )
        return smart_lab_pb2.CommandResponse(
            command_id=result.command_id,
            device_id=result.device_id,
            accepted=result.accepted,
            message=result.message,
        )


class TelemetryService(smart_lab_pb2_grpc.TelemetryServiceServicer):
    async def StreamTelemetry(self, request: Empty, context):
        async for event in event_bus.subscribe("telemetry"):
            timestamp = Timestamp()
            timestamp.FromJsonString(event["timestamp"])
            yield smart_lab_pb2.TelemetryEvent(
                device_id=event["device_id"],
                device_type=event["device_type"],
                metric=event["metric"],
                value=event["value"],
                unit=event["unit"],
                quality=event["quality"],
                sequence=event["sequence"],
                timestamp=timestamp,
            )


async def serve() -> None:
    settings = get_settings()
    server = grpc.aio.server()
    smart_lab_pb2_grpc.add_DeviceServiceServicer_to_server(DeviceService(), server)
    smart_lab_pb2_grpc.add_CommandServiceServicer_to_server(CommandService(), server)
    smart_lab_pb2_grpc.add_TelemetryServiceServicer_to_server(TelemetryService(), server)
    bind = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(bind)
    await server.start()
    logger.info("gRPC server started", extra={"bind": bind})
    await server.wait_for_termination()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()

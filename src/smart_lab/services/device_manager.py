import asyncio
import contextlib
import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from smart_lab.database.repository import Repository
from smart_lab.devices.base import SimulatedDevice
from smart_lab.devices.registry import build_device, discover_devices
from smart_lab.shared.event_bus import EventBus, event_bus
from smart_lab.shared.models import (
    CommandResult,
    CommandType,
    DeviceCommand,
    DeviceConfig,
    DeviceHealth,
    Telemetry,
)

logger = logging.getLogger(__name__)


class DeviceManager:
    def __init__(self, bus: EventBus | None = None) -> None:
        self.devices: dict[str, SimulatedDevice] = {}
        self.telemetry_buffer: asyncio.Queue[Telemetry] = asyncio.Queue(maxsize=10_000)
        self._poll_tasks: dict[str, asyncio.Task] = {}
        self._command_lock = asyncio.Lock()
        self.bus = bus or event_bus

    async def discover_and_register(self, session: AsyncSession | None = None) -> list[DeviceConfig]:
        configs = discover_devices()
        for config in configs:
            self.register(config)
            if session:
                await Repository(session).upsert_device(config)
        return configs

    def register(self, config: DeviceConfig) -> SimulatedDevice:
        device = build_device(config)
        self.devices[config.device_id] = device
        return device

    def list_configs(self) -> list[DeviceConfig]:
        return [device.config for device in self.devices.values()]

    def health(self) -> list[DeviceHealth]:
        return [
            device.health(queue_depth=self.telemetry_buffer.qsize())
            for device in sorted(self.devices.values(), key=lambda item: item.device_id)
        ]

    async def command(
        self, device_id: str, command: CommandType, payload: dict | None = None, priority: int = 5
    ) -> CommandResult:
        device = self.devices.get(device_id)
        if device is None:
            return CommandResult(
                command_id=str(uuid4()),
                device_id=device_id,
                accepted=False,
                message="unknown device",
            )
        device_command = DeviceCommand(
            command_id=str(uuid4()),
            device_id=device_id,
            command=command,
            priority=priority,
            payload=payload or {},
        )
        async with self._command_lock:
            result = await device.execute(device_command)
            if result.accepted and command == CommandType.START:
                self._ensure_polling(device_id)
            if command == CommandType.STOP:
                await self._cancel_polling(device_id)
        await self.bus.publish("commands", result.model_dump(mode="json"))
        return result

    async def start_all(self) -> None:
        await asyncio.gather(
            *(self.command(device_id, CommandType.START) for device_id in self.devices),
            return_exceptions=False,
        )

    async def stop_all(self) -> None:
        await asyncio.gather(
            *(self.command(device_id, CommandType.STOP) for device_id in list(self.devices)),
            return_exceptions=True,
        )

    async def shutdown(self) -> None:
        await self.stop_all()
        for task in list(self._poll_tasks.values()):
            task.cancel()
        await asyncio.gather(*self._poll_tasks.values(), return_exceptions=True)
        self._poll_tasks.clear()

    def _ensure_polling(self, device_id: str) -> None:
        task = self._poll_tasks.get(device_id)
        if task and not task.done():
            return
        self._poll_tasks[device_id] = asyncio.create_task(self._poll_device(device_id), name=f"poll-{device_id}")

    async def _cancel_polling(self, device_id: str) -> None:
        task = self._poll_tasks.pop(device_id, None)
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _poll_device(self, device_id: str) -> None:
        device = self.devices[device_id]
        async for telemetry in device.stream():
            if self.telemetry_buffer.full():
                _ = self.telemetry_buffer.get_nowait()
            self.telemetry_buffer.put_nowait(telemetry)
            await self.bus.publish("telemetry", telemetry.model_dump(mode="json"))


device_manager = DeviceManager()

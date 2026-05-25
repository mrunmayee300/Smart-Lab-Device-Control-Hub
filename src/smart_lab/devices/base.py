import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from smart_lab.devices.communication import SimulatedBus
from smart_lab.shared.models import (
    CommandResult,
    CommandType,
    DeviceCommand,
    DeviceConfig,
    DeviceHealth,
    DeviceState,
    Telemetry,
)

logger = logging.getLogger(__name__)


class SimulatedDevice(ABC):
    """Base class for a simulated lab device with async polling and commands."""

    metric_name: str
    unit: str

    def __init__(self, config: DeviceConfig, bus: SimulatedBus) -> None:
        self.config = config
        self.bus = bus
        self.state = DeviceState.REGISTERED
        self.error_count = 0
        self.sequence = 0
        self._started_at = time.monotonic()
        self._state_lock = asyncio.Lock()

    @property
    def device_id(self) -> str:
        return self.config.device_id

    async def start(self) -> None:
        async with self._state_lock:
            self.state = DeviceState.STARTING
            await self.bus.transact(b"START")
            self.state = DeviceState.RUNNING
            logger.info("device started", extra={"device_id": self.device_id})

    async def stop(self) -> None:
        async with self._state_lock:
            await self.bus.transact(b"STOP")
            self.state = DeviceState.STOPPED
            logger.info("device stopped", extra={"device_id": self.device_id})

    async def reset(self) -> None:
        async with self._state_lock:
            self.state = DeviceState.RESETTING
            await self.bus.transact(b"RESET")
            self.error_count = 0
            self.sequence = 0
            self.state = DeviceState.STOPPED

    async def execute(self, command: DeviceCommand) -> CommandResult:
        try:
            match command.command:
                case CommandType.START:
                    await self.start()
                case CommandType.STOP:
                    await self.stop()
                case CommandType.RESET:
                    await self.reset()
                case CommandType.CALIBRATE:
                    await self.calibrate()
                case CommandType.SET_RATE:
                    rate = command.payload.get("poll_interval_seconds")
                    if isinstance(rate, int | float) and rate > 0:
                        self.config.poll_interval_seconds = float(rate)
                case _:
                    raise ValueError(f"unsupported command {command.command}")
            return CommandResult(
                command_id=command.command_id,
                device_id=self.device_id,
                accepted=True,
                message="command completed",
            )
        except Exception as exc:
            self.error_count += 1
            self.state = DeviceState.FAULTED
            logger.exception("device command failed", extra={"device_id": self.device_id})
            return CommandResult(
                command_id=command.command_id,
                device_id=self.device_id,
                accepted=False,
                message=str(exc),
            )

    async def calibrate(self) -> None:
        await self.bus.transact(b"CALIBRATE")
        await asyncio.sleep(0.05)

    async def poll_once(self) -> Telemetry:
        if self.state != DeviceState.RUNNING:
            raise RuntimeError(f"{self.device_id} is not running")
        started = time.perf_counter()
        await self.bus.transact(f"READ:{self.metric_name}".encode())
        value = await self.read_value()
        self.sequence += 1
        latency_ms = (time.perf_counter() - started) * 1000
        return Telemetry(
            device_id=self.device_id,
            device_type=self.config.device_type,
            metric=self.metric_name,
            value=value,
            unit=self.unit,
            sequence=self.sequence,
            quality=max(0.7, min(1.0, 1.0 - random.random() * 0.02)),
            metadata={"transport": self.bus.transport.value, "latency_ms": round(latency_ms, 3)},
        )

    async def stream(self) -> AsyncIterator[Telemetry]:
        while self.state == DeviceState.RUNNING:
            try:
                yield await self.poll_once()
            except Exception:
                self.error_count += 1
                logger.exception("device polling failed", extra={"device_id": self.device_id})
            await asyncio.sleep(self.config.poll_interval_seconds)

    def health(self, queue_depth: int = 0) -> DeviceHealth:
        return DeviceHealth(
            device_id=self.device_id,
            state=self.state,
            error_count=self.error_count,
            queue_depth=queue_depth,
            details={
                "transport": self.bus.transport.value,
                "uptime_seconds": time.monotonic() - self._started_at,
            },
        )

    @abstractmethod
    async def read_value(self) -> float:
        raise NotImplementedError

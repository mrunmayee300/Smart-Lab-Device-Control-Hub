import asyncio
import random
from abc import ABC, abstractmethod

from smart_lab.shared.models import TransportType


class SimulatedBus(ABC):
    def __init__(self, latency_range_ms: tuple[int, int] = (5, 25)) -> None:
        self.latency_range_ms = latency_range_ms
        self._lock = asyncio.Lock()

    async def _latency(self) -> None:
        low, high = self.latency_range_ms
        await asyncio.sleep(random.uniform(low, high) / 1000)

    @property
    @abstractmethod
    def transport(self) -> TransportType:
        raise NotImplementedError

    async def transact(self, frame: bytes) -> bytes:
        async with self._lock:
            await self._latency()
            return await self._handle_frame(frame)

    @abstractmethod
    async def _handle_frame(self, frame: bytes) -> bytes:
        raise NotImplementedError


class UartBus(SimulatedBus):
    @property
    def transport(self) -> TransportType:
        return TransportType.UART

    async def _handle_frame(self, frame: bytes) -> bytes:
        return b"UART:ACK:" + frame


class I2CBus(SimulatedBus):
    @property
    def transport(self) -> TransportType:
        return TransportType.I2C

    async def _handle_frame(self, frame: bytes) -> bytes:
        checksum = sum(frame) % 256
        return b"I2C:ACK:" + bytes([checksum])


class SpiBus(SimulatedBus):
    @property
    def transport(self) -> TransportType:
        return TransportType.SPI

    async def _handle_frame(self, frame: bytes) -> bytes:
        return b"SPI:ACK:" + frame[::-1]

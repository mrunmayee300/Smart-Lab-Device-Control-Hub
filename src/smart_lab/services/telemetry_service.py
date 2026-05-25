import asyncio
import contextlib
import logging

from smart_lab.database.repository import Repository
from smart_lab.database.session import AsyncSessionLocal
from smart_lab.services.device_manager import DeviceManager
from smart_lab.shared.event_bus import EventBus, event_bus
from smart_lab.shared.models import Telemetry

logger = logging.getLogger(__name__)


class TelemetryIngestService:
    def __init__(self, manager: DeviceManager, bus: EventBus | None = None) -> None:
        self.manager = manager
        self.bus = bus or event_bus
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="telemetry-ingest")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task

    async def _run(self) -> None:
        while True:
            telemetry: Telemetry = await self.manager.telemetry_buffer.get()
            try:
                async with AsyncSessionLocal() as session:
                    await Repository(session).save_telemetry(telemetry)
            except Exception:
                logger.exception("failed to persist telemetry", extra={"device_id": telemetry.device_id})

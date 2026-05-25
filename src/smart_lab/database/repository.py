from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from smart_lab.database.models import (
    AssayHistoryRecord,
    DeviceRecord,
    LogRecord,
    TelemetryRecord,
    WorkerEventRecord,
)
from smart_lab.shared.models import AssayRunState, DeviceConfig, Telemetry


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_device(self, config: DeviceConfig) -> DeviceRecord:
        record = await self.session.get(DeviceRecord, config.device_id)
        if record is None:
            record = DeviceRecord(device_id=config.device_id)
            self.session.add(record)
        record.device_type = config.device_type.value
        record.transport = config.transport.value
        record.enabled = config.enabled
        record.parameters = config.parameters
        await self.session.commit()
        return record

    async def list_devices(self) -> list[DeviceRecord]:
        result = await self.session.execute(select(DeviceRecord).order_by(DeviceRecord.device_id))
        return list(result.scalars())

    async def save_telemetry(self, telemetry: Telemetry) -> TelemetryRecord:
        record = TelemetryRecord(
            device_id=telemetry.device_id,
            device_type=telemetry.device_type.value,
            metric=telemetry.metric,
            value=telemetry.value,
            unit=telemetry.unit,
            quality=telemetry.quality,
            sequence=telemetry.sequence,
            metadata_json=telemetry.metadata,
            created_at=telemetry.timestamp,
        )
        self.session.add(record)
        await self.session.commit()
        return record

    async def latest_telemetry(
        self, device_id: str | None = None, limit: int = 100
    ) -> list[TelemetryRecord]:
        statement = select(TelemetryRecord).order_by(desc(TelemetryRecord.created_at)).limit(limit)
        if device_id:
            statement = statement.where(TelemetryRecord.device_id == device_id)
        result = await self.session.execute(statement)
        return list(result.scalars())

    async def append_log(self, component: str, level: str, message: str, **context: object) -> None:
        self.session.add(
            LogRecord(component=component, level=level, message=message, context=context)
        )
        await self.session.commit()

    async def list_logs(self, limit: int = 100) -> list[LogRecord]:
        result = await self.session.execute(
            select(LogRecord).order_by(desc(LogRecord.created_at)).limit(limit)
        )
        return list(result.scalars())

    async def create_assay_run(self, run_id: str, assay_id: str, name: str) -> None:
        self.session.add(
            AssayHistoryRecord(
                run_id=run_id,
                assay_id=assay_id,
                name=name,
                state=AssayRunState.QUEUED.value,
                started_at=None,
                completed_at=None,
                result={},
            )
        )
        await self.session.commit()

    async def update_assay_run(
        self, run_id: str, state: AssayRunState, result: dict | None = None
    ) -> None:
        record = await self.session.get(AssayHistoryRecord, run_id)
        if record is None:
            return
        now = datetime.now(UTC)
        record.state = state.value
        if state == AssayRunState.RUNNING and record.started_at is None:
            record.started_at = now
        if state in {AssayRunState.COMPLETED, AssayRunState.FAILED, AssayRunState.CANCELLED}:
            record.completed_at = now
        if result is not None:
            record.result = result
        await self.session.commit()

    async def list_assay_runs(self, limit: int = 100) -> list[AssayHistoryRecord]:
        result = await self.session.execute(
            select(AssayHistoryRecord).order_by(desc(AssayHistoryRecord.created_at)).limit(limit)
        )
        return list(result.scalars())

    async def append_worker_event(self, worker_id: str, event_type: str, **details: object) -> None:
        self.session.add(
            WorkerEventRecord(worker_id=worker_id, event_type=event_type, details=details)
        )
        await self.session.commit()

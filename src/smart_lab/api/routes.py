from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from smart_lab.api.schemas import CommandRequest, RegisterDeviceRequest, RunAssayRequest
from smart_lab.database.repository import Repository
from smart_lab.database.session import get_session
from smart_lab.monitoring.system import monitoring_service
from smart_lab.scheduler.assay import assay_scheduler
from smart_lab.services.device_manager import device_manager
from smart_lab.services.rate_limit import SlidingWindowRateLimiter
from smart_lab.shared.config import get_settings

router = APIRouter()
rate_limiter = SlidingWindowRateLimiter(get_settings().max_command_rate_per_minute)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": get_settings().app_name}


@router.post("/devices/register", status_code=status.HTTP_201_CREATED)
async def register_device(
    request: RegisterDeviceRequest, session: AsyncSession = Depends(get_session)
) -> dict:
    device_manager.register(request.config)
    await Repository(session).upsert_device(request.config)
    return request.config.model_dump(mode="json")


@router.get("/devices")
async def list_devices() -> list[dict]:
    return [config.model_dump(mode="json") for config in device_manager.list_configs()]


@router.get("/devices/health")
async def device_health() -> list[dict]:
    return [health.model_dump(mode="json") for health in device_manager.health()]


@router.post("/devices/{device_id}/commands")
async def execute_command(device_id: str, payload: CommandRequest, request: Request) -> dict:
    key = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="command rate limit exceeded"
        )
    result = await device_manager.command(
        device_id=device_id,
        command=payload.command,
        payload=payload.payload,
        priority=payload.priority,
    )
    if not result.accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
    return result.model_dump(mode="json")


@router.get("/telemetry")
async def latest_telemetry(
    device_id: str | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = await Repository(session).latest_telemetry(device_id=device_id, limit=min(limit, 1000))
    return [
        {
            "device_id": row.device_id,
            "device_type": row.device_type,
            "metric": row.metric,
            "value": row.value,
            "unit": row.unit,
            "quality": row.quality,
            "sequence": row.sequence,
            "timestamp": row.created_at.isoformat(),
            "metadata": row.metadata_json,
        }
        for row in rows
    ]


@router.get("/logs")
async def logs(limit: int = 100, session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = await Repository(session).list_logs(limit=min(limit, 1000))
    return [
        {
            "component": row.component,
            "level": row.level,
            "message": row.message,
            "context": row.context,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/assays")
async def list_assays() -> list[dict]:
    return [assay.model_dump(mode="json") for assay in assay_scheduler.list_assays()]


@router.post("/assays/run")
async def run_assay(request: RunAssayRequest) -> dict:
    if request.assay_id not in assay_scheduler.assays:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown assay")
    run = await assay_scheduler.run_assay(request.assay_id)
    return assay_scheduler.serialize_run(run)


@router.post("/assays/{run_id}/cancel")
async def cancel_assay(run_id: str) -> dict:
    cancelled = await assay_scheduler.cancel(run_id)
    if not cancelled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown assay run")
    return {"run_id": run_id, "cancelled": True}


@router.get("/assays/history")
async def assay_history(
    limit: int = 100, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    rows = await Repository(session).list_assay_runs(limit=min(limit, 1000))
    return [
        {
            "run_id": row.run_id,
            "assay_id": row.assay_id,
            "name": row.name,
            "state": row.state,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "result": row.result,
        }
        for row in rows
    ]


@router.get("/workers/status")
async def worker_status() -> dict:
    return await monitoring_service.snapshot()


@router.get("/monitoring")
async def monitoring() -> dict:
    return await monitoring_service.snapshot()

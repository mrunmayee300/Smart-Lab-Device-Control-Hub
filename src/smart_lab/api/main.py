from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from smart_lab.api.routes import router as api_router
from smart_lab.api.websockets import router as websocket_router
from smart_lab.database.init_db import init_database
from smart_lab.database.session import AsyncSessionLocal
from smart_lab.services.device_manager import device_manager
from smart_lab.services.telemetry_service import TelemetryIngestService
from smart_lab.services.worker_runtime import worker_runtime
from smart_lab.shared.config import get_settings
from smart_lab.shared.logging import configure_logging

telemetry_ingest = TelemetryIngestService(device_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_database()
    async with AsyncSessionLocal() as session:
        await device_manager.discover_and_register(session)
    telemetry_ingest.start()
    if settings.enable_worker_runtime:
        worker_runtime.start()
    yield
    if settings.enable_worker_runtime:
        await worker_runtime.stop()
    await telemetry_ingest.stop()
    await device_manager.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Real-time laboratory device orchestration backend with asyncio, "
            "IPC, WebSockets, and gRPC."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router)
    return app


app = create_app()

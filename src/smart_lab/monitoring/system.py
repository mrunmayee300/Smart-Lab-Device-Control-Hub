import asyncio
import os
from dataclasses import dataclass
from typing import Any

import psutil

from smart_lab.services.device_manager import DeviceManager, device_manager
from smart_lab.services.worker_runtime import worker_runtime


@dataclass
class MonitoringService:
    manager: DeviceManager = device_manager

    async def snapshot(self) -> dict[str, Any]:
        await asyncio.sleep(0)
        process = psutil.Process(os.getpid())
        return {
            "process": {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(interval=None),
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "threads": process.num_threads(),
            },
            "host": {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_percent": psutil.virtual_memory().percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0],
            },
            "workers": {
                "telemetry_queue_depth": self.manager.telemetry_buffer.qsize(),
                "device_count": len(self.manager.devices),
                "runtime": worker_runtime.snapshot(),
            },
            "devices": [health.model_dump(mode="json") for health in self.manager.health()],
        }


monitoring_service = MonitoringService()

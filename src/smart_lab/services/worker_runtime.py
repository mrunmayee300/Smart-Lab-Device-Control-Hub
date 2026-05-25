import asyncio
import contextlib
from multiprocessing import Queue

from smart_lab.shared.config import get_settings
from smart_lab.shared.event_bus import event_bus
from smart_lab.services.device_manager import DeviceManager, device_manager
from smart_lab.workers.cpu_worker import CpuWorkerPool
from smart_lab.workers.ipc import IpcPrimitives, read_shared_json
from smart_lab.workers.socket_status import ThreadedStatusSocket


class WorkerRuntime:
    def __init__(self, manager: DeviceManager) -> None:
        self.manager = manager
        self.ipc: IpcPrimitives | None = None
        self.pool: CpuWorkerPool | None = None
        self.status_socket: ThreadedStatusSocket | None = None
        self._bridge_task: asyncio.Task | None = None

    def start(self) -> None:
        settings = get_settings()
        self.ipc = IpcPrimitives.create()
        self.pool = CpuWorkerPool(
            telemetry_queue=self.ipc.telemetry_queue,
            result_queue=self.ipc.result_queue,
            shared_name=self.ipc.shared_state.name,
            count=settings.cpu_worker_count,
        )
        self.pool.start()
        self.status_socket = ThreadedStatusSocket(
            settings.ipc_socket_host, settings.ipc_socket_port, self.snapshot
        )
        self.status_socket.start()
        self._bridge_task = asyncio.create_task(self._bridge_telemetry(), name="worker-telemetry-bridge")

    async def stop(self) -> None:
        if self._bridge_task:
            self._bridge_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._bridge_task
        if self.status_socket:
            self.status_socket.stop()
        if self.pool:
            self.pool.stop()
        if self.ipc:
            self.ipc.close()

    def snapshot(self) -> dict:
        shared = read_shared_json(self.ipc.shared_state) if self.ipc else {}
        return {
            "shared_memory": shared,
            "cpu_workers": [
                {"pid": process.pid, "alive": process.is_alive()} for process in self.pool.processes
            ]
            if self.pool
            else [],
            "queue_depths": {
                "to_cpu": _safe_qsize(self.ipc.telemetry_queue) if self.ipc else 0,
                "from_cpu": _safe_qsize(self.ipc.result_queue) if self.ipc else 0,
            },
        }

    async def _bridge_telemetry(self) -> None:
        assert self.ipc is not None
        async for telemetry in event_bus.subscribe("telemetry"):
            self.ipc.telemetry_queue.put(telemetry)


def _safe_qsize(queue: Queue) -> int:
    try:
        return queue.qsize()
    except NotImplementedError:
        return -1


worker_runtime = WorkerRuntime(device_manager)

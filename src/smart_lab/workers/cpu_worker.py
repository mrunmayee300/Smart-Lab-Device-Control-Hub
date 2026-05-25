from __future__ import annotations

import math
import os
import queue
import signal
import time
from multiprocessing import Event, Process, Queue, shared_memory
from multiprocessing.connection import Connection
from typing import Any

from smart_lab.workers.ipc import write_shared_json


def spectral_feature_extraction(samples: list[float]) -> dict[str, float]:
    """CPU-oriented numerical routine used to demonstrate multiprocessing offload."""

    if not samples:
        return {"mean": 0.0, "rms": 0.0, "peak": 0.0}
    mean = sum(samples) / len(samples)
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    peak = max(samples)
    # Intentional extra math to make the process useful under load.
    _ = sum(math.sin(value) * math.cos(value / 2.0) for value in samples for _ in range(100))
    return {"mean": mean, "rms": rms, "peak": peak}


def cpu_worker_main(
    worker_id: str,
    telemetry_queue: Queue,
    result_queue: Queue,
    shared_name: str,
    pipe: Connection,
    stop_event: Event,
) -> None:
    memory = shared_memory.SharedMemory(name=shared_name)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    processed = 0
    try:
        while not stop_event.is_set():
            heartbeat = {
                "worker_id": worker_id,
                "pid": os.getpid(),
                "processed": processed,
                "heartbeat_at": time.time(),
            }
            write_shared_json(memory, heartbeat)
            if pipe.poll():
                message = pipe.recv()
                if message == "stop":
                    break
                pipe.send({"worker_id": worker_id, "state": "alive", "processed": processed})
            try:
                payload: dict[str, Any] = telemetry_queue.get(timeout=0.25)
            except queue.Empty:
                continue
            values = payload.get("samples") or [float(payload.get("value", 0.0))]
            result_queue.put(
                {
                    "worker_id": worker_id,
                    "device_id": payload.get("device_id"),
                    "features": spectral_feature_extraction([float(value) for value in values]),
                    "processed_at": time.time(),
                }
            )
            processed += 1
    finally:
        memory.close()


class CpuWorkerPool:
    def __init__(
        self, telemetry_queue: Queue, result_queue: Queue, shared_name: str, count: int
    ) -> None:
        self.telemetry_queue = telemetry_queue
        self.result_queue = result_queue
        self.shared_name = shared_name
        self.count = count
        self.stop_event = Event()
        self.processes: list[Process] = []
        self.pipes: list[Connection] = []

    def start(self) -> None:
        for index in range(self.count):
            parent_pipe, child_pipe = __import__("multiprocessing").Pipe(duplex=True)
            process = Process(
                target=cpu_worker_main,
                args=(
                    f"cpu-worker-{index}",
                    self.telemetry_queue,
                    self.result_queue,
                    self.shared_name,
                    child_pipe,
                    self.stop_event,
                ),
                daemon=True,
            )
            process.start()
            child_pipe.close()
            self.processes.append(process)
            self.pipes.append(parent_pipe)

    def stop(self, timeout: float = 5.0) -> None:
        self.stop_event.set()
        for pipe in self.pipes:
            try:
                pipe.send("stop")
            except OSError:
                pass
        for process in self.processes:
            process.join(timeout=timeout)
            if process.is_alive():
                process.terminate()

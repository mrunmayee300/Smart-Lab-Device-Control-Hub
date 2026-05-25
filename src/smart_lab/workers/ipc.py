from __future__ import annotations

import json
import socket
import struct
from dataclasses import dataclass
from multiprocessing import Pipe, Queue, shared_memory
from multiprocessing.connection import Connection
from typing import Any


@dataclass
class IpcPrimitives:
    telemetry_queue: Queue
    result_queue: Queue
    shared_state: shared_memory.SharedMemory
    parent_pipe: Connection
    child_pipe: Connection

    @classmethod
    def create(cls, shared_bytes: int = 1024) -> IpcPrimitives:
        parent_pipe, child_pipe = Pipe(duplex=True)
        return cls(
            telemetry_queue=Queue(maxsize=10_000),
            result_queue=Queue(maxsize=10_000),
            shared_state=shared_memory.SharedMemory(create=True, size=shared_bytes),
            parent_pipe=parent_pipe,
            child_pipe=child_pipe,
        )

    def close(self) -> None:
        self.parent_pipe.close()
        self.child_pipe.close()
        self.shared_state.close()
        self.shared_state.unlink()


def write_shared_json(memory: shared_memory.SharedMemory, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    if len(data) + 4 > memory.size:
        raise ValueError("shared memory payload too large")
    memory.buf[:4] = struct.pack("!I", len(data))
    memory.buf[4 : 4 + len(data)] = data


def read_shared_json(memory: shared_memory.SharedMemory) -> dict[str, Any]:
    size = struct.unpack("!I", memory.buf[:4])[0]
    if size == 0:
        return {}
    return json.loads(bytes(memory.buf[4 : 4 + size]).decode("utf-8"))


def send_socket_message(
    host: str, port: int, payload: dict[str, Any], timeout: float = 2.0
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    with socket.create_connection((host, port), timeout=timeout) as client:
        client.sendall(struct.pack("!I", len(data)) + data)
        header = client.recv(4)
        if not header:
            return {}
        size = struct.unpack("!I", header)[0]
        response = client.recv(size)
        return json.loads(response.decode("utf-8"))

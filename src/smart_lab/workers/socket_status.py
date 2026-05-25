import json
import socketserver
import struct
import threading


class StatusHandler(socketserver.BaseRequestHandler):
    state_provider: staticmethod

    def handle(self) -> None:
        header = self.request.recv(4)
        if not header:
            return
        size = struct.unpack("!I", header)[0]
        _ = self.request.recv(size)
        response = json.dumps(self.state_provider()).encode("utf-8")
        self.request.sendall(struct.pack("!I", len(response)) + response)


class ThreadedStatusSocket:
    """Small TCP IPC endpoint for process health checks and external probes."""

    def __init__(self, host: str, port: int, state_provider) -> None:
        self.host = host
        self.port = port
        handler = type(
            "BoundStatusHandler", (StatusHandler,), {"state_provider": staticmethod(state_provider)}
        )
        self.server = socketserver.ThreadingTCPServer((host, port), handler)
        self.server.daemon_threads = True
        self._thread = threading.Thread(
            target=self.server.serve_forever, name="status-socket", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=2.0)

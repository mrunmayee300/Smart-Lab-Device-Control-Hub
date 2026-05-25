from smart_lab.workers.ipc import IpcPrimitives, read_shared_json, write_shared_json


def test_shared_memory_json_round_trip() -> None:
    ipc = IpcPrimitives.create()
    try:
        write_shared_json(ipc.shared_state, {"worker_id": "cpu-worker-1", "processed": 5})
        payload = read_shared_json(ipc.shared_state)
        assert payload == {"worker_id": "cpu-worker-1", "processed": 5}
    finally:
        ipc.close()

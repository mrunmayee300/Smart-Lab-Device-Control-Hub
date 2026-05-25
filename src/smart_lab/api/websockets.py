from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from smart_lab.shared.event_bus import event_bus

router = APIRouter()


@router.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        async for event in event_bus.subscribe("telemetry"):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/assays")
async def assay_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        async for event in event_bus.subscribe("assays"):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return

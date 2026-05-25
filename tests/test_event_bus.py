import asyncio

import pytest

from smart_lab.shared.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_delivers_published_events() -> None:
    bus = EventBus()

    async def receive_once() -> dict:
        async for event in bus.subscribe("telemetry"):
            return event
        raise AssertionError("subscription ended unexpectedly")

    task = asyncio.create_task(receive_once())
    await asyncio.sleep(0)
    await bus.publish("telemetry", {"device_id": "temp_sensor_1", "value": 37.2})

    event = await asyncio.wait_for(task, timeout=1.0)
    assert event["device_id"] == "temp_sensor_1"
    assert event["value"] == 37.2

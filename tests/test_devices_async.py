import pytest

from smart_lab.devices.registry import build_device
from smart_lab.shared.models import (
    CommandType,
    DeviceCommand,
    DeviceConfig,
    DeviceType,
    TransportType,
)


@pytest.mark.asyncio
async def test_temperature_sensor_start_poll_stop() -> None:
    device = build_device(
        DeviceConfig(
            device_id="temp_test",
            device_type=DeviceType.TEMPERATURE_SENSOR,
            transport=TransportType.I2C,
            poll_interval_seconds=0.01,
        )
    )

    result = await device.execute(
        DeviceCommand(command_id="1", device_id="temp_test", command=CommandType.START)
    )
    assert result.accepted

    telemetry = await device.poll_once()
    assert telemetry.device_id == "temp_test"
    assert telemetry.metric == "temperature"
    assert 30.0 < telemetry.value < 45.0

    result = await device.execute(
        DeviceCommand(command_id="2", device_id="temp_test", command=CommandType.STOP)
    )
    assert result.accepted

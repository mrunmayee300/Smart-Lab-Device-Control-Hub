from smart_lab.devices.communication import I2CBus, SpiBus, UartBus
from smart_lab.devices.simulators import (
    MicrofluidicPump,
    PHSensor,
    Spectrometer,
    TemperatureSensor,
    VoltageReader,
)
from smart_lab.shared.config import get_settings
from smart_lab.shared.models import DeviceConfig, DeviceType, TransportType

DEVICE_CLASSES = {
    DeviceType.TEMPERATURE_SENSOR: TemperatureSensor,
    DeviceType.PH_SENSOR: PHSensor,
    DeviceType.MICROFLUIDIC_PUMP: MicrofluidicPump,
    DeviceType.SPECTROMETER: Spectrometer,
    DeviceType.VOLTAGE_READER: VoltageReader,
}

BUS_CLASSES = {
    TransportType.UART: UartBus,
    TransportType.I2C: I2CBus,
    TransportType.SPI: SpiBus,
}


def build_device(config: DeviceConfig):
    bus = BUS_CLASSES[config.transport]()
    return DEVICE_CLASSES[config.device_type](config=config, bus=bus)


def default_device_configs() -> list[DeviceConfig]:
    interval = get_settings().device_poll_interval_seconds
    return [
        DeviceConfig(
            device_id="temp_sensor_1",
            device_type=DeviceType.TEMPERATURE_SENSOR,
            transport=TransportType.I2C,
            poll_interval_seconds=interval,
        ),
        DeviceConfig(
            device_id="ph_sensor_1",
            device_type=DeviceType.PH_SENSOR,
            transport=TransportType.UART,
            poll_interval_seconds=interval,
        ),
        DeviceConfig(
            device_id="pump_1",
            device_type=DeviceType.MICROFLUIDIC_PUMP,
            transport=TransportType.SPI,
            poll_interval_seconds=interval,
            parameters={"target_flow_ul_min": 120.0},
        ),
        DeviceConfig(
            device_id="spectrometer_1",
            device_type=DeviceType.SPECTROMETER,
            transport=TransportType.UART,
            poll_interval_seconds=interval,
            parameters={"wavelength_nm": 540.0},
        ),
        DeviceConfig(
            device_id="voltage_reader_1",
            device_type=DeviceType.VOLTAGE_READER,
            transport=TransportType.I2C,
            poll_interval_seconds=interval,
        ),
    ]


def discover_devices() -> list[DeviceConfig]:
    """Dynamic discovery hook; replace with pyserial/I2C/SPI probes on hardware."""

    return default_device_configs()

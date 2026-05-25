from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeviceType(StrEnum):
    TEMPERATURE_SENSOR = "temperature_sensor"
    PH_SENSOR = "ph_sensor"
    MICROFLUIDIC_PUMP = "microfluidic_pump"
    SPECTROMETER = "spectrometer"
    VOLTAGE_READER = "voltage_reader"


class DeviceState(StrEnum):
    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    FAULTED = "faulted"
    RESETTING = "resetting"


class CommandType(StrEnum):
    START = "start"
    STOP = "stop"
    RESET = "reset"
    CALIBRATE = "calibrate"
    SET_RATE = "set_rate"


class TransportType(StrEnum):
    UART = "uart"
    I2C = "i2c"
    SPI = "spi"


class Telemetry(BaseModel):
    device_id: str
    device_type: DeviceType
    metric: str
    value: float
    unit: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    quality: float = Field(default=1.0, ge=0.0, le=1.0)
    sequence: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceConfig(BaseModel):
    device_id: str
    device_type: DeviceType
    transport: TransportType
    poll_interval_seconds: float = Field(default=0.5, gt=0)
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)


class DeviceHealth(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    device_id: str
    state: DeviceState
    heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_count: int = 0
    queue_depth: int = 0
    latency_ms: float = 0
    details: dict[str, Any] = Field(default_factory=dict)


class DeviceCommand(BaseModel):
    command_id: str
    device_id: str
    command: CommandType
    priority: int = Field(default=5, ge=0, le=10)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CommandResult(BaseModel):
    command_id: str
    device_id: str
    accepted: bool
    message: str
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssayStep(BaseModel):
    step_id: str
    device_id: str
    command: CommandType
    delay_seconds: float = Field(default=0, ge=0)
    timeout_seconds: float = Field(default=10, gt=0)
    retries: int = Field(default=2, ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)


class AssayDefinition(BaseModel):
    assay_id: str
    name: str
    steps: list[AssayStep]
    concurrent: bool = False


class AssayRunState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerState(BaseModel):
    worker_id: str
    process_id: int | None = None
    state: str
    heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    queue_depth: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)

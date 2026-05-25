from pydantic import BaseModel, Field

from smart_lab.shared.models import CommandType, DeviceConfig


class CommandRequest(BaseModel):
    command: CommandType
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=5, ge=0, le=10)


class RegisterDeviceRequest(BaseModel):
    config: DeviceConfig


class RunAssayRequest(BaseModel):
    assay_id: str

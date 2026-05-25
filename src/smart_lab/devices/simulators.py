import asyncio
import math
import random
import time

from smart_lab.devices.base import SimulatedDevice


class TemperatureSensor(SimulatedDevice):
    metric_name = "temperature"
    unit = "celsius"

    async def read_value(self) -> float:
        await asyncio.sleep(0)
        wave = math.sin(time.monotonic() / 12) * 1.8
        return round(37.0 + wave + random.gauss(0, 0.08), 3)


class PHSensor(SimulatedDevice):
    metric_name = "ph"
    unit = "pH"

    async def read_value(self) -> float:
        await asyncio.sleep(0)
        drift = math.sin(time.monotonic() / 18) * 0.15
        return round(7.4 + drift + random.gauss(0, 0.015), 3)


class MicrofluidicPump(SimulatedDevice):
    metric_name = "flow_rate"
    unit = "ul_min"

    async def read_value(self) -> float:
        await asyncio.sleep(0)
        target = float(self.config.parameters.get("target_flow_ul_min", 120.0))
        pulsation = math.sin(time.monotonic() * 3) * target * 0.04
        return round(max(0.0, target + pulsation + random.gauss(0, target * 0.01)), 3)


class Spectrometer(SimulatedDevice):
    metric_name = "absorbance"
    unit = "au"

    async def read_value(self) -> float:
        await asyncio.sleep(0)
        wavelength = float(self.config.parameters.get("wavelength_nm", 540.0))
        baseline = 0.65 + (wavelength - 540.0) / 1000.0
        return round(max(0.0, baseline + random.gauss(0, 0.02)), 4)


class VoltageReader(SimulatedDevice):
    metric_name = "voltage"
    unit = "volts"

    async def read_value(self) -> float:
        await asyncio.sleep(0)
        ripple = math.sin(time.monotonic() * 8) * 0.03
        return round(3.3 + ripple + random.gauss(0, 0.005), 4)

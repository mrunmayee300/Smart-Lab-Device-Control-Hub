import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from smart_lab.database.repository import Repository
from smart_lab.database.session import AsyncSessionLocal
from smart_lab.services.device_manager import DeviceManager, device_manager
from smart_lab.shared.event_bus import EventBus, event_bus
from smart_lab.shared.models import AssayDefinition, AssayRunState, AssayStep


def built_in_assays() -> dict[str, AssayDefinition]:
    return {
        "blood_test": AssayDefinition(
            assay_id="blood_test",
            name="Blood Chemistry Microfluidic Run",
            concurrent=False,
            steps=[
                AssayStep(step_id="start_temp", device_id="temp_sensor_1", command="start"),
                AssayStep(step_id="start_ph", device_id="ph_sensor_1", command="start"),
                AssayStep(
                    step_id="prime_pump",
                    device_id="pump_1",
                    command="set_rate",
                    payload={"poll_interval_seconds": 0.25},
                ),
                AssayStep(
                    step_id="start_pump", device_id="pump_1", command="start", delay_seconds=0.2
                ),
                AssayStep(step_id="read_spectrometer", device_id="spectrometer_1", command="start"),
                AssayStep(step_id="voltage_guard", device_id="voltage_reader_1", command="start"),
            ],
        )
    }


@dataclass
class AssayRun:
    run_id: str
    definition: AssayDefinition
    state: AssayRunState = AssayRunState.QUEUED
    current_step: str | None = None
    results: list[dict] = field(default_factory=list)


class AssayScheduler:
    def __init__(self, manager: DeviceManager, bus: EventBus | None = None) -> None:
        self.manager = manager
        self.bus = bus or event_bus
        self.assays = built_in_assays()
        self.runs: dict[str, AssayRun] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def list_assays(self) -> list[AssayDefinition]:
        return list(self.assays.values())

    async def run_assay(self, assay_id: str) -> AssayRun:
        definition = self.assays[assay_id]
        run = AssayRun(run_id=str(uuid4()), definition=definition)
        self.runs[run.run_id] = run
        async with AsyncSessionLocal() as session:
            await Repository(session).create_assay_run(
                run.run_id, definition.assay_id, definition.name
            )
        task = asyncio.create_task(self._execute(run), name=f"assay-{run.run_id}")
        self._tasks[run.run_id] = task
        return run

    async def cancel(self, run_id: str) -> bool:
        task = self._tasks.get(run_id)
        run = self.runs.get(run_id)
        if task is None or run is None:
            return False
        task.cancel()
        run.state = AssayRunState.CANCELLED
        async with AsyncSessionLocal() as session:
            await Repository(session).update_assay_run(
                run_id, AssayRunState.CANCELLED, {"steps": run.results}
            )
        await self.bus.publish("assays", self.serialize_run(run))
        return True

    async def _execute(self, run: AssayRun) -> None:
        run.state = AssayRunState.RUNNING
        await self._persist_and_publish(run)
        try:
            if run.definition.concurrent:
                await asyncio.gather(
                    *(self._execute_step(run, step) for step in run.definition.steps)
                )
            else:
                for step in run.definition.steps:
                    await self._execute_step(run, step)
            run.state = AssayRunState.COMPLETED
        except asyncio.CancelledError:
            run.state = AssayRunState.CANCELLED
            raise
        except Exception as exc:
            run.state = AssayRunState.FAILED
            run.results.append({"error": str(exc)})
        finally:
            await self._persist_and_publish(run)

    async def _execute_step(self, run: AssayRun, step: AssayStep) -> None:
        run.current_step = step.step_id
        if step.delay_seconds:
            await asyncio.sleep(step.delay_seconds)
        last_error: str | None = None
        for attempt in range(step.retries + 1):
            try:
                result = await asyncio.wait_for(
                    self.manager.command(
                        step.device_id,
                        step.command,
                        payload=step.payload,
                        priority=8,
                    ),
                    timeout=step.timeout_seconds,
                )
                run.results.append(
                    {
                        "step_id": step.step_id,
                        "attempt": attempt + 1,
                        "result": result.model_dump(mode="json"),
                    }
                )
                if result.accepted:
                    await self._persist_and_publish(run)
                    return
                last_error = result.message
            except Exception as exc:
                last_error = str(exc)
            await asyncio.sleep(min(2**attempt * 0.2, 2.0))
        raise RuntimeError(f"step {step.step_id} failed after retries: {last_error}")

    async def _persist_and_publish(self, run: AssayRun) -> None:
        async with AsyncSessionLocal() as session:
            await Repository(session).update_assay_run(
                run.run_id, run.state, {"steps": run.results}
            )
        await self.bus.publish("assays", self.serialize_run(run))

    @staticmethod
    def serialize_run(run: AssayRun) -> dict:
        return {
            "run_id": run.run_id,
            "assay_id": run.definition.assay_id,
            "name": run.definition.name,
            "state": run.state.value,
            "current_step": run.current_step,
            "results": run.results,
        }


assay_scheduler = AssayScheduler(device_manager)

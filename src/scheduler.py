"""Scheduled tasks for periodic SRE operations."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Coroutine

logger = logging.getLogger(__name__)


class TaskFrequency(str, Enum):
    EVERY_MINUTE = "every_minute"
    EVERY_5_MINUTES = "every_5_minutes"
    EVERY_15_MINUTES = "every_15_minutes"
    EVERY_HOUR = "every_hour"
    EVERY_6_HOURS = "every_6_hours"
    EVERY_DAY = "every_day"


FREQUENCY_SECONDS = {
    TaskFrequency.EVERY_MINUTE: 60,
    TaskFrequency.EVERY_5_MINUTES: 300,
    TaskFrequency.EVERY_15_MINUTES: 900,
    TaskFrequency.EVERY_HOUR: 3600,
    TaskFrequency.EVERY_6_HOURS: 21600,
    TaskFrequency.EVERY_DAY: 86400,
}


@dataclass
class ScheduledTask:
    name: str
    description: str
    frequency: TaskFrequency
    handler: Callable[..., Coroutine]
    enabled: bool = True
    last_run: datetime | None = None
    last_status: str = "pending"
    run_count: int = 0
    error_count: int = 0


@dataclass
class TaskResult:
    task_name: str
    success: bool
    message: str
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TaskScheduler:
    """Runs scheduled SRE tasks at defined intervals."""

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False

    def register(self, task: ScheduledTask) -> None:
        self._tasks[task.name] = task
        logger.info("Registered task: %s (%s)", task.name, task.frequency.value)

    async def _run_task(self, task: ScheduledTask) -> TaskResult:
        try:
            result = await task.handler()
            task.last_run = datetime.now(timezone.utc)
            task.last_status = "success"
            task.run_count += 1
            logger.info("Task '%s' completed successfully.", task.name)
            return TaskResult(task_name=task.name, success=True, message="OK", data=result or {})
        except Exception as exc:
            task.last_status = f"error: {exc}"
            task.error_count += 1
            logger.error("Task '%s' failed: %s", task.name, exc)
            return TaskResult(task_name=task.name, success=False, message=str(exc))

    async def _task_loop(self, task: ScheduledTask) -> None:
        interval = FREQUENCY_SECONDS[task.frequency]
        while self._running:
            if task.enabled:
                await self._run_task(task)
            await asyncio.sleep(interval)

    async def start(self) -> None:
        self._running = True
        logger.info("Starting scheduler with %d tasks.", len(self._tasks))
        loops = [self._task_loop(t) for t in self._tasks.values()]
        await asyncio.gather(*loops)

    def stop(self) -> None:
        self._running = False
        logger.info("Scheduler stopped.")

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "tasks": {
                name: {
                    "frequency": t.frequency.value,
                    "enabled": t.enabled,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "last_status": t.last_status,
                    "run_count": t.run_count,
                    "error_count": t.error_count,
                }
                for name, t in self._tasks.items()
            },
        }

"""Cron-based scheduler for timed publishing tasks."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from apscheduler.schedulers.asyncio import AsyncIOScheduler


@dataclass
class ScheduleConfig:
    """Configuration for a single book's schedule."""
    book: str
    time: str = "08:00"
    chapters_per_day: int = 1

    @property
    def times(self) -> list[str]:
        """Parse time string into list of times."""
        return [t.strip() for t in self.time.split(",")]

    @classmethod
    def from_dict(cls, data: dict) -> ScheduleConfig:
        return cls(
            book=data.get("book", ""),
            time=data.get("time", "08:00"),
            chapters_per_day=data.get("chapters_per_day", 1),
        )


def load_schedules(path: Path | str) -> list[ScheduleConfig]:
    """Load schedule configurations from YAML file.

    Args:
        path: Path to schedule YAML file.

    Returns:
        List of ScheduleConfig objects.
    """
    path = Path(path)
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        return [ScheduleConfig.from_dict(s) for s in data.get("schedules", [])]


async def start_scheduler(
    schedules: list[ScheduleConfig],
    callback,
) -> None:
    """Starts async scheduler with schedule callbacks.

    Args:
        schedules: List of schedule configurations.
        callback: Async function to call when schedule triggers.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler()

    for schedule in schedules:
        for time_str in schedule.times:
            try:
                hour, minute = time_str.split(":")
                scheduler.add_job(
                    callback,
                    "cron",
                    hour=int(hour),
                    minute=int(minute),
                    args=[schedule.book, schedule.chapters_per_day],
                    id=f"{schedule.book}_{time_str}",
                )
            except ValueError:
                continue

    scheduler.start()


async def run_scheduler(
    schedules: list[ScheduleConfig],
    callback,
) -> None:
    """Starts async scheduler with schedule callbacks.

    Args:
        schedules: List of schedule configurations.
        callback: Async function to call when schedule triggers.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler()

    for schedule in schedules:
        for time_str in schedule.times:
            try:
                hour, minute = time_str.split(":")
                scheduler.add_job(
                    callback,
                    "cron",
                    hour=int(hour),
                    minute=int(minute),
                    args=[schedule.book, schedule.chapters_per_day],
                    id=f"{schedule.book}_{time_str}",
                )
            except ValueError:
                continue

    scheduler.start()

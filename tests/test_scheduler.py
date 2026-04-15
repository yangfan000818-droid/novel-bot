"""Tests for scheduler module."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from novel_bot.scheduler import ScheduleConfig, load_schedules


class TestScheduleConfig:
    """Tests for ScheduleConfig dataclass."""

    def test_default_values(self) -> None:
        config = ScheduleConfig(book="test-book")
        assert config.book == "test-book"
        assert config.time == "08:00"
        assert config.chapters_per_day == 1

    def test_parse_times_single(self) -> None:
        config = ScheduleConfig(book="test", time="08:00")
        assert config.times == ["08:00"]

    def test_parse_times_multiple(self) -> None:
        config = ScheduleConfig(book="test", time="08:00,14:00,20:00")
        assert config.times == ["08:00", "14:00", "20:00"]

    def test_parse_times_strips_whitespace(self) -> None:
        config = ScheduleConfig(book="test", time=" 08:00 , 14:00 ")
        assert config.times == ["08:00", "14:00"]

    def test_from_dict(self) -> None:
        data = {"book": "my-book", "time": "09:30", "chapters_per_day": 3}
        config = ScheduleConfig.from_dict(data)
        assert config.book == "my-book"
        assert config.time == "09:30"
        assert config.chapters_per_day == 3

    def test_from_dict_missing_fields(self) -> None:
        config = ScheduleConfig.from_dict({})
        assert config.book == ""
        assert config.time == "08:00"
        assert config.chapters_per_day == 1


class TestLoadSchedules:
    """Tests for load_schedules function."""

    def test_load_from_valid_yaml(self, tmp_path: Path) -> None:
        schedule_file = tmp_path / "schedule.yaml"
        content = (
            "schedules:\n"
            "  - book: test-book-1\n"
            "    time: '08:00,14:00'\n"
            "    chapters_per_day: 2\n"
            "  - book: test-book-2\n"
            "    time: '09:00'\n"
        )
        schedule_file.write_text(content, encoding="utf-8")

        schedules = load_schedules(schedule_file)
        assert len(schedules) == 2
        assert schedules[0].book == "test-book-1"
        assert schedules[0].times == ["08:00", "14:00"]
        assert schedules[0].chapters_per_day == 2
        assert schedules[1].book == "test-book-2"
        assert schedules[1].times == ["09:00"]

    def test_load_empty_schedules(self, tmp_path: Path) -> None:
        schedule_file = tmp_path / "schedule.yaml"
        schedule_file.write_text("schedules: []\n", encoding="utf-8")

        schedules = load_schedules(schedule_file)
        assert len(schedules) == 0

    def test_load_missing_file(self, tmp_path: Path) -> None:
        schedules = load_schedules(tmp_path / "nonexistent.yaml")
        assert len(schedules) == 0

    def test_load_empty_yaml(self, tmp_path: Path) -> None:
        schedule_file = tmp_path / "schedule.yaml"
        schedule_file.write_text("", encoding="utf-8")

        schedules = load_schedules(schedule_file)
        assert len(schedules) == 0

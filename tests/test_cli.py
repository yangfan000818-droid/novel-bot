"""Tests for CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from novel_bot.cli import main, publish, schedule


class TestCLI:
    """Test cases for CLI commands."""

    def test_main_help(self, cli_runner: CliRunner) -> None:
        """Test that main command shows help."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Novel Bot" in result.output

    def test_publish_help(self, cli_runner: CliRunner) -> None:
        """Test that publish command shows help."""
        result = cli_runner.invoke(main, ["publish", "--help"])
        assert result.exit_code == 0

    def test_schedule_help(self, cli_runner: CliRunner) -> None:
        """Test that schedule command shows help."""
        result = cli_runner.invoke(main, ["schedule", "--help"])
        assert result.exit_code == 0

    def test_publish_missing_book_dir(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test publish command with missing book directory."""
        with patch("novel_bot.cli.load_settings") as mock_settings:
            mock_settings.return_value.resolved_books_path = tmp_path
            result = cli_runner.invoke(main, ["publish", "missing-book"])

        assert result.exit_code != 0
        assert "找不到书籍目录" in result.output

    def test_publish_missing_book_json(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test publish command with missing book.json."""
        book_dir = tmp_path / "test-book"
        book_dir.mkdir()

        with patch("novel_bot.cli.load_settings") as mock_settings:
            mock_settings.return_value.resolved_books_path = tmp_path
            result = cli_runner.invoke(main, ["publish", "test-book"])

        assert result.exit_code != 0
        assert "找不到" in result.output

    def test_publish_with_chapters(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test publish command with a complete book structure."""
        book_dir = tmp_path / "test-book"
        book_dir.mkdir()
        chapters_dir = book_dir / "chapters"
        chapters_dir.mkdir()

        book_json = book_dir / "book.json"
        book_data = {
            "id": "test-id",
            "title": "测试小说",
            "platform": "tomato",
            "genre": "xuanhuan",
        }
        book_json.write_text(json.dumps(book_data, ensure_ascii=False, indent=2), encoding="utf-8")

        (chapters_dir / "0001_test.md").write_text(
            "# 第1章 测试\n\n测试内容", encoding="utf-8"
        )

        with patch("novel_bot.cli.load_settings") as mock_settings:
            mock_settings.return_value.resolved_books_path = tmp_path
            result = cli_runner.invoke(main, ["publish", "test-book"])

        assert result.exit_code == 0
        assert "解析到 1 章" in result.output

    def test_schedule_no_config(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test schedule command with missing config file."""
        with patch("novel_bot.cli.load_settings") as mock_settings, \
             patch("novel_bot.cli.load_schedules") as mock_load:
            mock_load.return_value = []
            result = cli_runner.invoke(main, ["schedule"])

        assert result.exit_code == 0
        assert "没有配置定时任务" in result.output

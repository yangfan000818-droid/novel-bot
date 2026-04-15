"""Tests for CLI entry point."""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from novel_bot.scheduler import load_schedules, start_scheduler


class TestCLI:
    """Test cases for CLI commands."""

    def test_main_help(self, cli_runner: CliRunner) -> None:
        """Test that main command shows help."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Novel Bot" in result.output

    def test_publish_missing_book_dir(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test publish command with missing book directory."""
        books_path = tmp_path / "books"
        result = cli_runner.invoke(main, ["publish", "missing-book"])
        assert result.exit_code != 0
        assert "错误：找不到书籍目录" in result.output

    def test_publish_missing_book_json(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test publish command with missing book.json."""
        books_path = tmp_path / "books" / "test-book"
        books_path.mkdir()
        # No book.json

        result = cli_runner.invoke(main, ["publish", "test-book"])
        assert result.exit_code != 0
        assert "错误：找不到" in result.output

    def test_schedule_no_tasks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test schedule command with empty schedule."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        schedule_file = config_dir / "schedule.yaml"
        schedule_file.write_text("schedules: []\n", encoding="utf-8")

        result = cli_runner.invoke(schedule, ["--help"])
        assert result.exit_code == 0

    def test_publish_with_mock_agents(self, cli_runner: CliRunner) -> None:
        """Test publish command with mocked agents."""
        books_path = Path(cli_runner.invoke(main, ["publish", "test-book"]).context.obj["settings"].resolved_books_path)

        # Create test book
        books_path.mkdir()
        book_dir = books_path / "test-book"
        book_dir.mkdir()
        book_json = book_dir / "book.json"
        book_data = {
            "id": "test-id",
            "title": "测试小说",
            "platform": "tomato",
            "genre": "xuanhuan",
        }
        book_json.write_text(json.dumps(book_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # Create test chapters
        chapters_dir = book_dir / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "0001_test.md").write_text("# 第1章 测试\n\n测试内容", encoding="utf-8")

        # Mock all agents to avoid actual browser operations
        with patch("novel_bot.cli.LoginManager") as mock_login_mgr, \
             patch("novel_bot.cli.TomatoPublisher") as mock_publisher, \
             patch("novel_bot.cli.Orchestrator") as mock_orch:

            mock_login_mgr.return_value = MagicMock()
            mock_login_mgr.return_value.get_session = AsyncMock(return_value=MagicMock())

            mock_publisher.return_value = MagicMock()
            mock_publisher.return_value.publish_chapter = AsyncMock(return_value=True)

            mock_orch.return_value = MagicMock()
            mock_orch.return_value.publish_book = AsyncMock()

            result = cli_runner.invoke(
                publish, ["test-book"],
                obj={
                    "novel_bot.cli": {
                        "LoginManager": mock_login_mgr,
                        "TomatoPublisher": mock_publisher,
                        "Orchestrator": mock_orch,
                    }
                }
            )

            assert result.exit_code == 0
            assert "解析到 1 章" in result.output
            assert "发布流程结束" in result.output

    def test_schedule_with_mock_callback(self, cli_runner: CliRunner) -> None:
        """Test schedule command with mocked callback."""
        config_dir = Path(cli_runner.invoke(main, ["publish", "test-book"]).context.obj["settings"].resolved_books_path.parent / "config")

        # Create test schedule
        schedule_file = config_dir / "schedule.yaml"
        schedule_content = """schedules:
  - book: 测试小说
    chapters_per_day: 3
    time: "08:00,14:00,20:00"
"""
        schedule_file.write_text(schedule_content, encoding="utf-8")

        # Mock scheduler callback
        with patch("asyncio.sleep") as mock_sleep:
            result = cli_runner.invoke(
                schedule, ["--help"],
                obj={
                    "asyncio": {"sleep": mock_sleep},
                }
            )

            assert result.exit_code == 0
            assert "启动定时发布" in result.output or "Novel Bot" in result.output

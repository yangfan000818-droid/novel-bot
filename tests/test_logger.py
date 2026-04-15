"""Tests for BookLogger."""
import pytest
from pathlib import Path
from novel_bot.monitor.logger import BookLogger


class TestBookLogger:
    """Test cases for BookLogger per-book daily logging."""

    def test_creates_log_file(self, tmp_path: Path) -> None:
        """Test that log file is created for a new book."""
        logger = BookLogger("测试书", log_dir=str(tmp_path))
        logger.info("测试消息")
        log_files = list(tmp_path.glob("测试书/*.log"))
        assert len(log_files) == 1

    def test_appends_to_same_day_file(self, tmp_path: Path) -> None:
        """Test that multiple messages append to same day's log file."""
        logger = BookLogger("测试书", log_dir=str(tmp_path))
        logger.info("第一条")
        logger.info("第二条")
        log_files = list(tmp_path.glob("测试书/*.log"))
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "第一条" in content
        assert "第二条" in content

    def test_warning_log_includes_level(self, tmp_path: Path) -> None:
        """Test that warning messages include WARNING level."""
        logger = BookLogger("测试书", log_dir=str(tmp_path))
        logger.warning("重试中")
        log_files = list(tmp_path.glob("测试书/*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "WARNING" in content

    def test_error_log_includes_level(self, tmp_path: Path) -> None:
        """Test that error messages include ERROR level."""
        logger = BookLogger("测试书", log_dir=str(tmp_path))
        logger.error("发布失败")
        log_files = list(tmp_path.glob("测试书/*.log"))
        content = log_files[0].read_text(encoding="utf-8")
        assert "ERROR" in content

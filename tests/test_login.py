"""Tests for LoginManager."""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from novel_bot.login.manager import LoginManager


class TestLoginManager:
    """Test cases for LoginManager cookie management."""

    def test_cookie_save_and_load(self, tmp_path: Path) -> None:
        """Test saving and loading cookies."""
        cookie_file = tmp_path / "cookies.json"
        manager = LoginManager(cookie_file=str(cookie_file))

        fake_cookies = [{"name": "session", "value": "abc123", "domain": ".tomato.com"}]
        manager.save_cookies(fake_cookies)

        assert cookie_file.exists()
        loaded = manager.load_cookies()
        assert loaded == fake_cookies

    def test_load_cookies_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        """Test loading cookies when file doesn't exist."""
        cookie_file = tmp_path / "nonexistent.json"
        manager = LoginManager(cookie_file=str(cookie_file))
        assert manager.load_cookies() == []

    def test_has_cookies_false_when_empty(self, tmp_path: Path) -> None:
        """Test has_cookies returns False when no cookie file exists."""
        manager = LoginManager(cookie_file=str(tmp_path / "none.json"))
        assert manager.has_cookies() is False

    def test_has_cookies_true_after_save(self, tmp_path: Path) -> None:
        """Test has_cookies returns True after saving cookies."""
        cookie_file = tmp_path / "cookies.json"
        manager = LoginManager(cookie_file=str(cookie_file))
        manager.save_cookies([{"name": "s", "value": "v", "domain": ".d"}])
        assert manager.has_cookies() is True

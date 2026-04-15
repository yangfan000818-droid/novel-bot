"""Tests for configuration management."""

import pytest
from pathlib import Path
from novel_bot.config import Settings, load_settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.books_path == Path("../books")
        assert s.publish_delay_min == 5
        assert s.publish_delay_max == 15
        assert s.headless is True

    def test_from_yaml(self, tmp_path):
        yaml_content = (
            "books_path: /some/other/path\n"
            "publish:\n"
            "  delay_min: 3\n"
            "  delay_max: 10\n"
            "  headless: false\n"
        )
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        s = load_settings(yaml_file)
        assert s.books_path == Path("/some/other/path")
        assert s.publish_delay_min == 3
        assert s.publish_delay_max == 10
        assert s.headless is False

    def test_partial_yaml_uses_defaults(self, tmp_path):
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text("books_path: /custom/path\n", encoding="utf-8")
        s = load_settings(yaml_file)
        assert s.books_path == Path("/custom/path")
        assert s.publish_delay_min == 5

    def test_resolve_books_path_relative_to_project_root(self, tmp_path):
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text("books_path: ../books\n", encoding="utf-8")
        s = load_settings(yaml_file, project_root=tmp_path)
        assert s.resolved_books_path == tmp_path.parent / "books"

    def test_resolve_absolute_path(self):
        s = Settings(books_path=Path("/absolute/path"))
        assert s.resolved_books_path == Path("/absolute/path")

    def test_missing_file_returns_defaults(self, tmp_path):
        s = load_settings(tmp_path / "nonexistent.yaml")
        assert s.books_path == Path("../books")

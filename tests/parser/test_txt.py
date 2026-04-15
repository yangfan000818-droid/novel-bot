"""Tests for TXT parser."""

import pytest
from pathlib import Path

from novel_bot.parser.txt import TxtParser
from novel_bot.models import Chapter


class TestTxtParser:
    """Tests for TxtParser class."""

    def test_parse_file_with_chapter_markers(self, tmp_path):
        """Should parse txt file with Chinese chapter markers."""
        f = tmp_path / "novel.txt"
        f.write_text(
            "第1章 标题\n\n正文一\n\n第2章 标题\n\n正文二",
            encoding="utf-8",
        )
        parser = TxtParser()
        chapters = parser.parse_file(f)
        assert len(chapters) == 2
        assert chapters[0].title == "第1章 标题"
        assert chapters[1].content.strip() == "正文二"

    def test_parse_file_with_english_markers(self, tmp_path):
        """Should parse txt file with English chapter markers."""
        f = tmp_path / "novel.txt"
        f.write_text(
            "Chapter 1 Start\n\nContent A\n\nChapter 2 Middle\n\nContent B",
            encoding="utf-8",
        )
        parser = TxtParser()
        chapters = parser.parse_file(f)
        assert len(chapters) == 2
        assert chapters[0].title == "Chapter 1 Start"

    def test_parse_file_single_chapter(self, tmp_path):
        """Should handle single chapter file correctly."""
        f = tmp_path / "novel.txt"
        f.write_text("第1章 开篇\n\n正文内容。", encoding="utf-8")
        parser = TxtParser()
        chapters = parser.parse_file(f)
        assert len(chapters) == 1
        assert chapters[0].title == "第1章 开篇"

    def test_parse_directory(self, tmp_path):
        """Should parse all txt files in a directory sorted by filename."""
        ch_dir = tmp_path / "chapters"
        ch_dir.mkdir()
        (ch_dir / "part2.txt").write_text("第2章\n\nB", encoding="utf-8")
        (ch_dir / "part1.txt").write_text("第1章\n\nA", encoding="utf-8")

        parser = TxtParser()
        chapters = parser.parse_directory(ch_dir)
        assert len(chapters) == 2
        assert chapters[0].title == "第1章"
        assert chapters[1].title == "第2章"

    def test_parse_directory_empty(self, tmp_path):
        """Should return empty list when directory has no txt files."""
        ch_dir = tmp_path / "empty"
        ch_dir.mkdir()

        parser = TxtParser()
        chapters = parser.parse_directory(ch_dir)
        assert len(chapters) == 0

    def test_cleans_ai_prefix(self, tmp_path):
        """Should apply clean_ai_prefix to chapter content."""
        f = tmp_path / "novel.txt"
        f.write_text("第1章\n\n💭思考\n\n正文开始", encoding="utf-8")
        parser = TxtParser()
        chapters = parser.parse_file(f)
        assert "💭" not in chapters[0].content
        assert "思考" not in chapters[0].content

    def test_chinese_numbers_in_markers(self, tmp_path):
        """Should recognize chapter markers with Chinese numbers."""
        f = tmp_path / "novel.txt"
        f.write_text("第零章 序章\n\n序\n\n第一章 开始\n\n正文", encoding="utf-8")
        parser = TxtParser()
        chapters = parser.parse_file(f)
        assert len(chapters) == 2
        assert chapters[0].title == "第零章 序章"
        assert chapters[1].title == "第一章 开始"

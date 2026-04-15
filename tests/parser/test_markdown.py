"""Tests for Markdown parser."""

import pytest
from pathlib import Path

from novel_bot.parser.markdown import MarkdownParser
from novel_bot.models import Chapter


class TestMarkdownParser:
    """Tests for MarkdownParser class."""

    def test_parse_single_file(self, tmp_path):
        """Should parse a single markdown file."""
        f = tmp_path / "chapter.md"
        f.write_text("# 第1章 测试\n\n💭AI思考\n\n正文开始。", encoding="utf-8")

        parser = MarkdownParser()
        chapter = parser.parse_file(f)
        assert chapter is not None
        assert chapter.title == "第1章 测试"
        assert "AI思考" not in chapter.content

    def test_parse_directory(self, tmp_path):
        """Should parse all markdown files in a directory sorted by filename."""
        ch_dir = tmp_path / "chapters"
        ch_dir.mkdir()
        (ch_dir / "0002_标题二.md").write_text("# 第2章 标题二\n\n正文二内容。", encoding="utf-8")
        (ch_dir / "0001_标题一.md").write_text("# 第1章 标题一\n\n正文一内容。", encoding="utf-8")
        (ch_dir / "0003_标题三.md").write_text("# 第3章 标题三\n\n正文三内容。", encoding="utf-8")

        parser = MarkdownParser()
        chapters = parser.parse_directory(ch_dir)

        assert len(chapters) == 3
        assert chapters[0].title == "第1章 标题一"
        assert chapters[0].index == 0
        assert chapters[1].title == "第2章 标题二"
        assert chapters[2].title == "第3章 标题三"

    def test_parse_directory_sorts_by_filename(self, tmp_path):
        """Should sort chapters by filename regardless of creation order."""
        ch_dir = tmp_path / "chapters"
        ch_dir.mkdir()
        (ch_dir / "0003_三.md").write_text("# 第3章\n\nC", encoding="utf-8")
        (ch_dir / "0001_一.md").write_text("# 第1章\n\nA", encoding="utf-8")
        (ch_dir / "0002_二.md").write_text("# 第2章\n\nB", encoding="utf-8")

        parser = MarkdownParser()
        chapters = parser.parse_directory(ch_dir)
        assert [ch.title for ch in chapters] == ["第1章", "第2章", "第3章"]

    def test_parse_directory_empty(self, tmp_path):
        """Should raise ValueError when directory is empty."""
        ch_dir = tmp_path / "empty"
        ch_dir.mkdir()

        parser = MarkdownParser()
        with pytest.raises(ValueError):
            parser.parse_directory(ch_dir)

    def test_parse_single_file_no_chapters(self, tmp_path):
        """Should raise ValueError when file has no chapter headers."""
        f = tmp_path / "no_chapter.md"
        f.write_text("Just some text without headers.", encoding="utf-8")

        parser = MarkdownParser()
        with pytest.raises(ValueError):
            parser.parse_file(f)

    def test_strips_title_from_content(self, tmp_path):
        """Should strip # title line from chapter content."""
        f = tmp_path / "chapter.md"
        f.write_text("# 第1章 标题\n\n第一段内容\n\n第二段内容。", encoding="utf-8")

        parser = MarkdownParser()
        chapter = parser.parse_file(f)
        assert chapter.title == "第1章 标题"
        assert "第一段内容" in chapter.content
        assert "第二段内容" in chapter.content
        assert "# 第1章 标题" not in chapter.content

    def test_cleans_ai_prefix_from_content(self, tmp_path):
        """Should apply clean_ai_prefix to chapter content."""
        f = tmp_path / "chapter.md"
        f.write_text("# 第1章\n\n💭思考...\n\n正文开始", encoding="utf-8")

        parser = MarkdownParser()
        chapter = parser.parse_file(f)
        assert "💭" not in chapter.content
        assert "思考" not in chapter.content

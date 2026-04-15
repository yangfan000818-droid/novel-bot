"""Tests for DOCX parser."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from novel_bot.parser.docx import DocxParser
from novel_bot.models import Chapter


def _make_para(text: str, style_name: str | None = None) -> MagicMock:
    """Create a mock paragraph with text and optional style."""
    para = MagicMock()
    para.text = text
    if style_name:
        para.style.name = style_name
    else:
        para.style = None
    return para


class TestDocxParser:
    """Tests for DocxParser class."""

    def test_recognizes_heading_by_style(self, tmp_path: Path) -> None:
        """Should recognize paragraphs with 'heading' in style name."""
        f = tmp_path / "test.docx"
        f.touch()

        para1 = _make_para("第一章 开篇", style_name="Heading 1")
        para2 = _make_para("这是正文内容")
        para3 = _make_para("第二章 继续", style_name="Heading 2")

        with patch("novel_bot.parser.docx.Document") as mock_doc_cls:
            mock_doc_cls.return_value.paragraphs = [para1, para2, para3]
            parser = DocxParser()
            chapters = parser.parse_file(f)

        assert len(chapters) == 2
        assert chapters[0].title == "第一章 开篇"
        assert chapters[1].title == "第二章 继续"
        assert "这是正文内容" in chapters[0].content

    def test_accumulates_non_heading_paragraphs(self, tmp_path: Path) -> None:
        """Should accumulate all non-heading paragraphs as chapter content."""
        f = tmp_path / "test.docx"
        f.touch()

        para1 = _make_para("第一章 开篇", style_name="Heading 1")
        para2 = _make_para("正文段落1")
        para3 = _make_para("正文段落2")
        para4 = _make_para("正文段落3")

        with patch("novel_bot.parser.docx.Document") as mock_doc_cls:
            mock_doc_cls.return_value.paragraphs = [para1, para2, para3, para4]
            parser = DocxParser()
            chapters = parser.parse_file(f)

        assert len(chapters) == 1
        assert chapters[0].title == "第一章 开篇"
        assert "正文段落1" in chapters[0].content
        assert "正文段落2" in chapters[0].content
        assert "正文段落3" in chapters[0].content

    def test_handles_only_content_no_headings(self, tmp_path: Path) -> None:
        """Should return empty list when no heading style paragraphs."""
        f = tmp_path / "test.docx"
        f.touch()

        para1 = _make_para("正文段落1")
        para2 = _make_para("正文段落2")

        with patch("novel_bot.parser.docx.Document") as mock_doc_cls:
            mock_doc_cls.return_value.paragraphs = [para1, para2]
            parser = DocxParser()
            chapters = parser.parse_file(f)

        assert len(chapters) == 0

    def test_handles_only_heading(self, tmp_path: Path) -> None:
        """Should create chapter from heading-only paragraph."""
        f = tmp_path / "test.docx"
        f.touch()

        para1 = _make_para("第一章 开篇", style_name="Heading 1")
        para2 = _make_para("")  # empty paragraph

        with patch("novel_bot.parser.docx.Document") as mock_doc_cls:
            mock_doc_cls.return_value.paragraphs = [para1, para2]
            parser = DocxParser()
            chapters = parser.parse_file(f)

        assert len(chapters) == 1
        assert chapters[0].title == "第一章 开篇"

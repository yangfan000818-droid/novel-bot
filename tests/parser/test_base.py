"""Tests for parser base module - AI prefix cleaning and chapter splitting."""

import pytest

from novel_bot.parser.base import clean_ai_prefix, split_chapters


class TestCleanAIPrefix:
    """Tests for clean_ai_prefix function."""

    def test_strips_thinking_block_before_separator(self):
        """Should strip AI thinking block before explicit separator."""
        content = (
            "💭AI 思考过程...\n"
            "更多思考...\n"
            "正文\n"
            "正式小说内容开始。"
        )
        result = clean_ai_prefix(content)
        assert result.startswith("正式小说内容开始。")
        assert "AI 思考过程" not in result
        assert "更多思考" not in result

    def test_strips_thinking_without_explicit_separator(self):
        """Should strip AI thinking when no explicit separator exists."""
        content = (
            "💭我需要将这段正文压缩...\n"
            "关键点回顾...\n"
            "核心要素要保留...\n"
            "\n"
            "春分第三日，沈家宗祠前的青石广场上挤满了人。"
        )
        result = clean_ai_prefix(content)
        assert result.strip().startswith("春分第三日")
        assert "我需要将" not in result
        assert "关键点回顾" not in result

    def test_preserves_content_with_no_prefix(self):
        """Should preserve content unchanged when no AI prefix exists."""
        content = "第一章 正文内容\n\n这是正常的小说正文。"
        result = clean_ai_prefix(content)
        assert result == content

    def test_preserves_content_starting_with_chapter_title(self):
        """Should preserve content that starts with chapter title directly."""
        content = "# 第1章 灵根中品\n\n正文内容。"
        result = clean_ai_prefix(content)
        assert result == content

    def test_strips_multiple_thinking_patterns(self):
        """Should strip multiple AI thinking markers."""
        content = (
            "💭分析内容...\n"
            "扩写策略...\n"
            "要点...\n"
            "另一个💭思考...\n"
            "正文开始。"
        )
        result = clean_ai_prefix(content)
        assert result.strip() == "正文开始。"


class TestSplitChapters:
    """Tests for split_chapters function."""

    def test_split_by_markdown_headers(self):
        """Should split markdown content by # headers."""
        content = "# 第1章 标题\n\n正文A\n\n# 第2章 标题\n\n正文B"
        chapters = split_chapters(content, format="markdown")
        assert len(chapters) == 2
        assert chapters[0].title == "第1章 标题"
        assert chapters[0].content.strip() == "正文A"
        assert chapters[1].index == 1

    def test_split_assigns_sequential_indices(self):
        """Should assign sequential indices starting from 0."""
        content = "# 第一章 A\n\nA\n\n# 第二章 B\n\nB\n\n# 第三章 C\n\nC"
        chapters = split_chapters(content, format="markdown")
        assert [ch.index for ch in chapters] == [0, 1, 2]

    def test_split_single_chapter(self):
        """Should handle single chapter correctly."""
        content = "# 第1章 唯一章节\n\n这是正文。"
        chapters = split_chapters(content, format="markdown")
        assert len(chapters) == 1
        assert chapters[0].index == 0
        assert chapters[0].title == "第1章 唯一章节"

    def test_split_empty_content(self):
        """Should handle empty content gracefully."""
        chapters = split_chapters("", format="markdown")
        assert len(chapters) == 0

    def test_split_txt_format(self):
        """Should split txt format by chapter markers."""
        content = "第1章 开篇\n\n正文一\n\n第2章 继续\n\n正文二"
        chapters = split_chapters(content, format="txt")
        assert len(chapters) == 2
        assert chapters[0].title == "第1章 开篇"
        assert chapters[1].content.strip() == "正文二"

    def test_split_unsupported_format_raises_error(self):
        """Should raise ValueError for unsupported format."""
        with pytest.raises(ValueError):
            split_chapters("content", format="unsupported")

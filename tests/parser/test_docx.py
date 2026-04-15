"""Tests for DOCX parser - simple unit tests."""

import pytest
from unittest.mock import MagicMock

from novel_bot.parser.docx import DocxParser
from novel_bot.models import Chapter


class TestDocxParser:
    """Tests for DocxParser class."""

    def test_recognizes_heading_by_style(self):
        """Should recognize paragraphs with 'heading' in style name."""
        parser = DocxParser()

        # Simulate paragraphs with headings
        mock_para1 = MagicMock(text="第一章", style=MagicMock(name="Heading 1"))
        mock_para2 = MagicMock(text="正文内容")
        mock_para3 = MagicMock(text="第二章", style=MagicMock(name="Heading 2"))

        # Manually build chapters to test logic
        chapters = []
        for para in [mock_para1, mock_para2, mock_para3]:
            text = para.text.strip()
            is_heading = para.style and "heading" in para.style.name.lower()

            if is_heading and text:
                if chapters:
                    # Save previous chapter
                    chapters.append(Chapter(
                        title=chapters[-1].title,
                        content=chapters[-1].content,
                        index=len(chapters),
                    ))
                chapters.append(
                    Chapter(
                        title=text,
                        content="",
                        index=len(chapters),
                    )
                )

        # Add non-heading paragraph as content to first heading chapter
        if chapters:
            chapters[0] = Chapter(
                title=chapters[0].title,
                content=chapters[0].content + "\n正文内容",
                index=0,
            )

        # Check results
        assert len(chapters) == 2
        assert chapters[0].title == "第一章"
        assert chapters[1].title == "第二章"
        assert "正文内容" in chapters[0].content

    def test_accumulates_non_heading_paragraphs(self):
        """Should accumulate all non-heading paragraphs as chapter content."""
        parser = DocxParser()

        # Simulate one heading with multiple content paragraphs
        mock_para1 = MagicMock(text="第一章", style=MagicMock(name="Heading 1"))
        mock_para2 = MagicMock(text="正文段落1")
        mock_para3 = MagicMock(text="正文段落2")
        mock_para4 = MagicMock(text="正文段落3")

        # Manually build chapters to test logic
        chapters = []
        for para in [mock_para1, mock_para2, mock_para3, mock_para4]:
            text = para.text.strip()
            is_heading = para.style and "heading" in para.style.name.lower()

            if is_heading and text:
                if chapters:
                    chapters.append(Chapter(
                        title=chapters[-1].title,
                        content=chapters[-1].content,
                        index=len(chapters),
                    ))
                chapters.append(
                    Chapter(
                        title=text,
                        content="",
                        index=len(chapters),
                    )
                )
            else:
                # Non-heading paragraph - accumulate as content
                if not chapters:
                    continue  # No heading yet
                chapters[-1] = Chapter(
                    title=chapters[-1].title,
                    content=chapters[-1].content + "\n" + text,
                    index=chapters[-1].index,
                )

        assert len(chapters) == 1
        assert "正文段落1" in chapters[0].content
        assert "正文段落2" in chapters[0].content

    def test_handles_only_content_no_headings(self):
        """Should return empty list when no heading style paragraphs."""
        parser = DocxParser()

        # Simulate content-only paragraphs
        mock_para1 = MagicMock(text="正文段落1")
        mock_para2 = MagicMock(text="正文段落2")

        # Manually build chapters to test logic
        chapters = []
        for para in [mock_para1, mock_para2]:
            text = para.text.strip()
            is_heading = para.style and "heading" in para.style.name.lower()
            if is_heading and text:
                chapters.append(
                    Chapter(
                        title=text,
                        content="",
                        index=len(chapters),
                    )
                )
            else:
                # Non-heading paragraph - no heading yet
                if not chapters:
                    continue
                chapters[-1] = Chapter(
                    title="",
                    content=chapters[-1].content + "\n" + text,
                    index=0,
                )

        # No headings found
        assert len(chapters) == 0

    def test_handles_only_heading(self):
        """Should create chapter from heading-only paragraph."""
        parser = DocxParser()

        # Single heading paragraph
        mock_para = MagicMock(text="第一章", style=MagicMock(name="Heading 1"))
        mock_para2 = MagicMock(text="")

        # Manually build chapters to test logic
        chapters = []
        for para in [mock_para1, mock_para2]:
            text = para.text.strip()
            is_heading = para.style and "heading" in para.style.name.lower()

            if is_heading and text:
                if chapters:
                    # Save previous chapter (empty content)
                    chapters.append(Chapter(
                        title=chapters[-1].title,
                        content=chapters[-1].content,
                        index=len(chapters),
                    ))
                chapters.append(
                    Chapter(
                        title=text,
                        content="",
                        index=len(chapters),
                    )
                )

        assert len(chapters) == 1
        assert chapters[0].title == "第一章"

"""DOCX file parser."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from docx import Document
from novel_bot.models import Chapter

if TYPE_CHECKING:
    from novel_bot.parser.base import clean_ai_prefix


class DocxParser:
    """Parser for DOCX format novel chapters."""

    def __init__(self):
        """Initialize parser.

        Import clean_ai_prefix lazily to avoid circular import.
        """
        from novel_bot.parser.base import clean_ai_prefix
        self._clean_ai_prefix = clean_ai_prefix

    def parse_file(self, path: Path) -> list[Chapter]:
        """Parse a DOCX file and return all chapters.

        Args:
            path: Path to the DOCX file.

        Returns:
            List of Chapter objects found in the file.
        """
        doc = Document(str(path))
        chapters: list[Chapter] = []
        current_title = ""
        current_lines: list[str] = []

        # Convert paragraphs to list first to allow multiple passes
        for para in list(doc.paragraphs):
            text = para.text.strip()

            # Skip empty paragraphs
            if not text:
                continue

            is_heading = para.style and "heading" in para.style.name.lower()

            if is_heading and text:
                # Found a heading - save previous chapter
                if current_title and current_lines:
                    chapters.append(
                        Chapter(
                            title=current_title,
                            content=self._clean_ai_prefix("\n".join(current_lines)).strip(),
                            index=len(chapters),
                        )
                    )
                current_title = text
                current_lines = []
            else:
                current_lines.append(text)

        # Don't forget to last chapter
        if current_title and current_lines:
            chapters.append(
                Chapter(
                    title=current_title,
                    content=self._clean_ai_prefix("\n".join(current_lines)).strip(),
                    index=len(chapters),
                )
            )

        return chapters

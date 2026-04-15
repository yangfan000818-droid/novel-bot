"""TXT file parser."""

from __future__ import annotations

from pathlib import Path

from novel_bot.models import Chapter
from novel_bot.parser.base import split_chapters, clean_ai_prefix


class TxtParser:
    """Parser for TXT format novel chapters."""

    def parse_file(self, path: Path) -> list[Chapter]:
        """Parse a single txt file and return all chapters.

        Args:
            path: Path to the txt file.

        Returns:
            List of Chapter objects found in the file.
        """
        content = path.read_text(encoding="utf-8")
        return split_chapters(content, format="txt")

    def parse_directory(self, dir_path: Path) -> list[Chapter]:
        """Parse all txt files in a directory.

        Files are sorted by filename and chapters maintain order.

        Args:
            dir_path: Path to the directory containing txt files.

        Returns:
            List of Chapter objects with sequential indices.
        """
        all_chapters: list[Chapter] = []
        offset = 0

        for f in sorted(dir_path.glob("*.txt")):
            chapters = self.parse_file(f)
            for ch in chapters:
                all_chapters.append(
                    Chapter(
                        title=ch.title,
                        content=ch.content,
                        index=ch.index + offset,
                    )
                )
            offset += len(chapters)
        return all_chapters

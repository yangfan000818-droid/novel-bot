"""Markdown file parser."""

from __future__ import annotations

from pathlib import Path

from novel_bot.models import Chapter
from novel_bot.parser.base import clean_ai_prefix, split_chapters


class MarkdownParser:
    """Parser for Markdown format novel chapters."""

    def parse_file(self, path: Path) -> Chapter:
        """Parse a single markdown file and return its first chapter.

        Args:
            path: Path to the markdown file.

        Returns:
            First Chapter object found in the file.

        Raises:
            ValueError: If no chapters are found in the file.
        """
        content = path.read_text(encoding="utf-8")
        chapters = split_chapters(content, format="markdown")
        if not chapters:
            raise ValueError(f"No chapters found in {path}")
        return chapters[0]

    def parse_directory(self, dir_path: Path) -> list[Chapter]:
        """Parse all markdown files in a directory.

        Files are sorted by filename to maintain chapter order.

        Args:
            dir_path: Path to the directory containing markdown files.

        Returns:
            List of Chapter objects with sequential indices.

        Raises:
            ValueError: If no markdown files are found in the directory.
        """
        md_files = sorted(dir_path.glob("*.md"))
        if not md_files:
            raise ValueError(f"No markdown files found in {dir_path}")

        result: list[Chapter] = []
        for i, f in enumerate(md_files):
            content = f.read_text(encoding="utf-8")
            cleaned = clean_ai_prefix(content)

            # Extract title from first # heading
            title = self._extract_title(cleaned) or f.stem.split("_", 1)[-1]
            # Strip # prefix from title
            title = title.lstrip("#").strip()

            result.append(
                Chapter(
                    title=title,
                    content=self._strip_title_line(cleaned),
                    index=i,
                )
            )
        return result

    def _extract_title(self, content: str) -> str:
        """Extract title from first # heading in content.

        Args:
            content: Markdown content.

        Returns:
            Title text without the # marker, or empty string.
        """
        for line in content.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    def _strip_title_line(self, content: str) -> str:
        """Remove title line from content if present.

        Args:
            content: Markdown content that may start with a title line.

        Returns:
            Content with title line removed, or original content.
        """
        lines = content.split("\n")
        if lines and lines[0].startswith("# "):
            return "\n".join(lines[1:]).strip()
        return content

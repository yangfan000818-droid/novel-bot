from __future__ import annotations

import re
from novel_bot.models import Chapter


# Pattern 1: AI thinking block ending with explicit separator
_THINKING_END_PATTERNS = [
    re.compile(r"^---\s*$", re.MULTILINE),
    re.compile(r"^小说正文\s*$", re.MULTILINE),
    re.compile(r"^正文\s*$", re.MULTILINE),
]

# Pattern 2: AI thinking starts with 💭 marker
_THINKING_START = re.compile(r"^💭", re.MULTILINE)

# Pattern 3: Keywords indicating AI reasoning text
_AI_REASONING_KEYWORDS = frozenset({
    "我来",
    "让我",
    "策略",
    "关键点",
    "核心",
    "需要",
    "修正",
    "扩写",
    "压缩",
    "保留",
    "精简",
    "减少",
    "注意",
    "现有",
    "分析",
    "补充",
    "要点",
})


def clean_ai_prefix(content: str) -> str:
    """Strip AI reasoning prefix from chapter content.

    Detection strategy:
    1. If content starts with 💭, find transition point to real narrative
    2. If "---" separator exists, take content after it
    3. If "小说正文" or "正文" line exists, take content after it
    4. Special case: "..." followed by narrative (common in AI-generated content)

    Args:
        content: Raw chapter content that may contain AI thinking prefix.

    Returns:
        Content with AI prefix removed, or original if no prefix detected.
    """
    if not content:
        return content

    # Try explicit separator patterns first
    for pattern in _THINKING_END_PATTERNS:
        match = pattern.search(content)
        if match:
            after = content[match.end():].strip()
            if after:
                return after

    # Check if AI thinking marker is present at all
    if not _THINKING_START.search(content[:50]):
        return content

    # Special case: detect "..." pattern (ellipsis followed by narrative)
    # This is common in AI-generated content like "核心要素要保留：..."
    _ELLIPSIS_PATTERN = re.compile(r"^\.\.\.\s*$", re.MULTILINE)
    if _ELLIPSIS_PATTERN.search(content):
        # Find the ellipsis marker
        lines = content.split("\n")
        ellipsis_idx = None
        for i, line in enumerate(lines):
            if _ELLIPSIS_PATTERN.match(line.strip()):
                ellipsis_idx = i
                break
        
        if ellipsis_idx is not None:
            # Find first narrative line after ellipsis
            narrative_start = ellipsis_idx + 1
            for i in range(narrative_start, len(lines)):
                line = lines[i].strip()
                if not line:
                    continue
                # Check if this looks like narrative (not AI reasoning keywords)
                first_chars = line[:4] if len(line) >= 4 else line
                is_ai_reasoning = any(keyword in first_chars for keyword in _AI_REASONING_KEYWORDS)
                has_emoji = "💭" in line[:4]
                
                if not is_ai_reasoning and not has_emoji and len(line) > 10:
                    narrative_start = i
                    break
            
            # Return everything from the first narrative line onwards
            if narrative_start > 0:
                return "\n".join(lines[narrative_start:]).strip()
        
        # If no narrative found after ellipsis, return content as-is
        return content

    # Fallback: filter out AI reasoning lines, keep the rest
    lines = content.split("\n")
    narrative_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Skip blank lines but keep them as narrative separator
        if not stripped:
            narrative_lines.append(line)
            continue

        # Check if line contains AI reasoning keywords
        first_chars = stripped[:4] if len(stripped) >= 4 else stripped
        is_ai_reasoning = any(keyword in first_chars for keyword in _AI_REASONING_KEYWORDS)

        # Also check for 💭 marker
        has_emoji = "💭" in stripped[:4]

        if is_ai_reasoning or has_emoji:
            # Skip this AI reasoning line
            continue

        # Keep this narrative line
        narrative_lines.append(line)

    result = "\n".join(narrative_lines).strip()
    return result if result else content


def split_chapters(content: str, format: str = "markdown") -> list[Chapter]:
    """Split content into Chapter objects based on format.

    Args:
        content: Raw chapter content.
        format: Either "markdown" or "txt".

    Returns:
        List of Chapter objects with sequential indices.

    Raises:
        ValueError: If format is not supported.
    """
    if format == "markdown":
        return _split_markdown(content)
    elif format == "txt":
        return _split_txt(content)
    else:
        raise ValueError(f"Unsupported format: {format}")


def _split_markdown(content: str) -> list[Chapter]:
    """Split markdown content by # headers."""
    lines = content.split("\n")
    chapters: list[Chapter] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("# "):
            if current_title and current_lines:
                chapters.append(Chapter(
                    title=current_title.lstrip("# "),
                    content=clean_ai_prefix("\n".join(current_lines).strip()),
                    index=len(chapters),
                ))
            current_title = line
            current_lines = []
        else:
            current_lines.append(line)

    # Don't forget to last chapter
    if current_title and current_lines:
        chapters.append(Chapter(
            title=current_title.lstrip("# "),
            content=clean_ai_prefix("\n".join(current_lines).strip()),
            index=len(chapters),
        ))

    return chapters


def _split_txt(content: str) -> list[Chapter]:
    """Split txt content by chapter markers."""
    pattern = re.compile(
        r"^(第[零一二三四五六七八九十百千\d]+[章节卷回]|Chapter\s+\d+)",
        re.IGNORECASE,
    )
    lines = content.split("\n")
    chapters: list[Chapter] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        match = pattern.match(line.strip())
        if match:
            if current_title and current_lines:
                chapters.append(Chapter(
                    title=current_title,
                    content=clean_ai_prefix("\n".join(current_lines).strip()),
                    index=len(chapters),
                ))
            current_title = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Don't forget to last chapter
    if current_title and current_lines:
        chapters.append(Chapter(
            title=current_title,
            content=clean_ai_prefix("\n".join(current_lines).strip()),
            index=len(chapters),
        ))

    return chapters

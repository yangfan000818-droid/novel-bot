"""Data models for the novel-bot system."""

from __future__ import annotations

import enum
from dataclasses import dataclass


@dataclass(frozen=True)
class Chapter:
    """A single chapter of a novel."""

    title: str
    content: str
    index: int

    @property
    def word_count(self) -> int:
        """Count Chinese characters (excluding spaces and newlines)."""
        return len(self.content.replace(" ", "").replace("\n", ""))


@dataclass
class Book:
    """Metadata for a novel loaded from book.json."""

    id: str
    title: str
    platform: str = "tomato"
    genre: str = ""
    status: str = "active"
    target_chapters: int = 0
    chapter_word_count: int = 0
    language: str = "zh"

    @classmethod
    def from_json(cls, data: dict) -> Book:
        """Create a Book from a JSON-compatible dict.

        Maps camelCase keys from book.json to snake_case fields.
        """
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            platform=data.get("platform", "tomato"),
            genre=data.get("genre", ""),
            status=data.get("status", "active"),
            target_chapters=data.get("targetChapters", 0),
            chapter_word_count=data.get("chapterWordCount", 0),
            language=data.get("language", "zh"),
        )


class TaskState(enum.Enum):
    """States for a publish task."""

    PENDING = "pending"
    PARSING = "parsing"
    LOGIN_CHECK = "login_check"
    PUBLISHING = "publishing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"

    def can_transition_to(self, other: TaskState, raise_error: bool = False) -> bool:
        """Check if transitioning to another state is valid."""
        allowed = _VALID_TRANSITIONS.get(self, set())
        if other in allowed:
            return True
        if raise_error:
            raise ValueError(f"Cannot transition from {self.name} to {other.name}")
        return False


_VALID_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PENDING: {TaskState.PARSING},
    TaskState.PARSING: {TaskState.LOGIN_CHECK, TaskState.FAILED},
    TaskState.LOGIN_CHECK: {TaskState.PUBLISHING, TaskState.FAILED},
    TaskState.PUBLISHING: {TaskState.VERIFYING, TaskState.FAILED},
    TaskState.VERIFYING: {TaskState.COMPLETED, TaskState.FAILED},
    TaskState.FAILED: {TaskState.PARSING, TaskState.PENDING},
}


class PublishProgress:
    """Tracks which chapters have been published for each book."""

    def __init__(self, data: dict[str, int] | None = None):
        self._data: dict[str, int] = data if data is not None else {}

    def update(self, book_title: str, chapter_index: int) -> None:
        """Update progress for a book. Only allows incrementing."""
        last = self._data.get(book_title, 0)
        if chapter_index <= last:
            raise ValueError(
                f"Cannot decrement progress for '{book_title}': "
                f"current={last}, attempted={chapter_index}"
            )
        self._data[book_title] = chapter_index

    def get_last_published(self, book_title: str) -> int:
        """Get the last published chapter index (0 if none)."""
        return self._data.get(book_title, 0)

    def to_dict(self) -> dict[str, int]:
        """Serialize to dict."""
        return dict(self._data)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> PublishProgress:
        """Deserialize from dict."""
        return cls(data)

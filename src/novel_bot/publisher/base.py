"""Base publisher interface for platform-agnostic publishing."""
from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page
    from novel_bot.models import Chapter


class BasePublisher(abc.ABC):
    """Abstract base class for platform publishers."""

    @abc.abstractmethod
    async def create_book(self, page: Page, title: str, **kwargs) -> str:
        """Create a new book on the platform.

        Args:
            page: Playwright Page object.
            title: Title of the book to create.
            **kwargs: Additional platform-specific parameters.

        Returns:
            Book ID of the created book.
        """

    @abc.abstractmethod
    async def publish_chapter(self, page: Page, book_id: str, chapter: Chapter) -> bool:
        """Publish a single chapter to a book.

        Args:
            page: Playwright Page object.
            book_id: ID of the book to publish to.
            chapter: Chapter object with title and content.

        Returns:
            True on success, False otherwise.
        """

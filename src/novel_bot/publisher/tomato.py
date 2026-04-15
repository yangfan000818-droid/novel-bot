"""Tomato Novel platform publisher implementation."""
from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from novel_bot.models import Chapter
from novel_bot.publisher.base import BasePublisher

if TYPE_CHECKING:
    from playwright.async_api import Page

TOMATO_AUTHOR_URL = "https://writer.tomatofn.com"


class TomatoPublisher(BasePublisher):
    """Publisher for Tomato Novel (番茄小说) platform."""

    RETRY_NETWORK = 3
    RETRY_PUBLISH = 3
    RETRY_STRUCTURE = 0

    def __init__(self, delay_min: int = 5, delay_max: int = 15) -> None:
        """Initialize Tomato publisher.

        Args:
            delay_min: Minimum delay between chapter publishes (seconds).
            delay_max: Maximum delay between chapter publishes (seconds).
        """
        self.delay_min = delay_min
        self.delay_max = delay_max

    async def create_book(self, page: Page, title: str, **kwargs) -> str:
        """Navigate to create book page and fill in book info.

        Args:
            page: Playwright Page object.
            title: Title of the book to create.
            **kwargs: Optional description and genre.

        Returns:
            Extracted book ID from URL or page.
        """
        await page.goto(f"{TOMATO_AUTHOR_URL}/book/create")

        await page.fill('input[name="title"]', title)

        description = kwargs.get("description", "")
        if description:
            await page.fill('textarea[name="description"]', description)

        genre = kwargs.get("genre", "")
        if genre:
            await page.select_option('select[name="genre"]', genre)

        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        return await self._extract_book_id(page)

    async def publish_chapter(self, page: Page, book_id: str, chapter: Chapter) -> bool:
        """Publish a single chapter to an existing book.

        Args:
            page: Playwright Page object.
            book_id: ID of the book to publish to.
            chapter: Chapter object with title and content.

        Returns:
            True on success.
        """
        await page.goto(f"{TOMATO_AUTHOR_URL}/book/{book_id}/chapter/create")

        await page.fill('input[name="title"]', chapter.title)
        await page.fill('textarea[name="content"]', chapter.content)

        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        await self._wait_random_delay()
        return True

    async def _extract_book_id(self, page: Page) -> str:
        """Extract book ID from current page URL after creation.

        Args:
            page: Playwright Page object.

        Returns:
            Extracted book ID string.

        Raises:
            ValueError: If book ID cannot be extracted.
        """
        url = page.url
        parts = url.rstrip("/").split("/")
        for i, part in enumerate(parts):
            if part == "book" and i + 1 < len(parts):
                return parts[i + 1]
        raise ValueError(f"Cannot extract book ID from URL: {url}")

    async def _wait_random_delay(self) -> None:
        """Wait for a random duration between min and max."""
        delay = random.uniform(self.delay_min, self.delay_max)
        await asyncio.sleep(delay)

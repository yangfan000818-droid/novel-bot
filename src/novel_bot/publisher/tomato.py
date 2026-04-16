"""Tomato Novel platform publisher implementation.

Publishes chapters via the fanqienovel.com author backend using
direct API calls through the authenticated browser context.

API flow:
  1. POST /api/author/article/new_article/v0/  → create draft, get item_id
  2. POST /api/author/article/cover_article/v0/ → save content (title + HTML)
  3. POST /api/author/publish_article/v0/       → submit for publishing
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import TYPE_CHECKING

from novel_bot.models import Chapter
from novel_bot.publisher.base import BasePublisher

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

TOMATO_AUTHOR_URL = "https://fanqienovel.com/main/writer"


class TomatoPublisher(BasePublisher):
    """Publisher for Tomato Novel (番茄小说) platform.

    Uses the author backend at fanqienovel.com/main/writer/.
    Chapters are published via direct API calls through the
    authenticated Playwright browser context.
    """

    RETRY_NETWORK = 3
    RETRY_PUBLISH = 3
    RETRY_STRUCTURE = 0

    def __init__(self, delay_min: int = 5, delay_max: int = 15) -> None:
        self.delay_min = delay_min
        self.delay_max = delay_max

    async def create_book(self, page: Page, title: str, **kwargs) -> str:
        raise NotImplementedError(
            "create_book requires headed browser mode. "
            "Navigate to the dashboard manually and click 创建新书."
        )

    async def publish_chapter(
        self,
        page: Page,
        book_id: str,
        chapter: Chapter,
        publish_time: int | None = None,
    ) -> bool:
        """Publish a single chapter via the Tomato Novel API.

        1. Navigate to publish page → triggers new_article API (auto-creates draft)
        2. Convert plain-text content to HTML
        3. Call cover_article API directly (saves content)
        4. Call publish_article API to submit chapter for publishing

        Args:
            page: Authenticated Playwright Page.
            book_id: Target book ID.
            chapter: Chapter with title and content.
            publish_time: Unix timestamp for scheduled publish.
                None = publish immediately.

        Returns:
            True if published successfully.
        """
        publish_url = f"{TOMATO_AUTHOR_URL}/{book_id}/publish/"
        logger.info("Navigating to publish page: %s", publish_url)

        # Step 1: Navigate — the SPA auto-calls new_article to create a draft
        # Set up response listener BEFORE navigation
        article_info: dict = {}

        async def on_new_article(response):
            url = response.url
            if "new_article" in url and "monitor" not in url:
                try:
                    body = await response.text()
                    data = json.loads(body)
                    if data.get("code") == 0:
                        article_info["item_id"] = data["data"]["item_id"]
                        article_info["volume_id"] = data["data"]["volume_id"]
                        article_info["volume_name"] = data["data"]["volume_data"][0]["volume_name"]
                except Exception:
                    pass

        page.on("response", on_new_article)
        await page.goto(publish_url, timeout=30000)
        title_input = page.locator('input[placeholder="请输入标题"]')
        await title_input.wait_for(state="visible", timeout=30000)
        await page.wait_for_timeout(3000)

        if not article_info.get("item_id"):
            raise RuntimeError("Failed to get item_id from new_article API")

        item_id = article_info["item_id"]
        volume_id = article_info["volume_id"]
        volume_name = article_info["volume_name"]
        logger.info("Draft created: item_id=%s", item_id)

        # Step 2: Convert plain text to HTML (skip editor typing entirely)
        content_html = self._content_to_html(chapter.content)
        logger.info(
            "Content prepared: %d chars plain → %d chars HTML",
            len(chapter.content),
            len(content_html),
        )

        # Step 3: Save draft via cover_article
        logger.info("Saving draft via cover_article API")
        save_result = await self._api_call(page, "/api/author/article/cover_article/v0/", {
            "book_id": book_id,
            "item_id": item_id,
            "title": chapter.title,
            "content": content_html,
            "volume_id": volume_id,
            "volume_name": volume_name,
        })

        save_data = json.loads(save_result)
        if save_data.get("code") != 0:
            raise RuntimeError(f"cover_article failed: {save_result}")
        logger.info("Draft saved: latest_version=%s", save_data.get("data", {}).get("latest_version"))

        # Step 4: Publish via publish_article
        pub_params: dict = {
            "book_id": book_id,
            "item_id": item_id,
            "title": chapter.title,
            "content": content_html,
            "volume_id": volume_id,
            "volume_name": volume_name,
        }
        if publish_time is not None:
            pub_params.update({
                "timer_status": "1",
                "timer_time": str(publish_time),
                "publish_status": "1",
                "device_platform": "pc",
                "speak_type": "0",
                "use_ai": "1",
                "timer_chapter_preview": "[]",
                "has_chapter_ad": "false",
                "need_pay": "0",
            })
            logger.info(
                "Scheduled publish at %d via publish_article API",
                publish_time,
            )
        else:
            logger.info("Publishing immediately via publish_article API")
        pub_result = await self._api_call(
            page, "/api/author/publish_article/v0/", pub_params,
        )

        pub_data = json.loads(pub_result)
        if pub_data.get("code") != 0:
            raise RuntimeError(f"publish_article failed: {pub_result}")

        logger.info("Chapter published: item_id=%s", pub_data.get("data", {}).get("item_id"))

        await self._wait_random_delay()
        return True

    @staticmethod
    def _content_to_html(text: str) -> str:
        """Convert plain-text chapter content to HTML for the API.

        Splits on double-newlines to create paragraphs wrapped in <p> tags.
        Single newlines within a paragraph are converted to <br> tags.
        """
        paragraphs = text.split("\n\n")
        html_parts: list[str] = []
        for para in paragraphs:
            stripped = para.strip()
            if not stripped:
                continue
            # Convert single newlines within a paragraph to <br>
            inner = stripped.replace("\n", "<br>")
            html_parts.append(f"<p>{inner}</p>")
        return "".join(html_parts)

    @staticmethod
    async def _api_call(page: Page, endpoint: str, params: dict) -> str:
        """Make an authenticated API call via in-page fetch.

        Uses the browser's authenticated session (cookies/csrf)
        to call the Tomato Novel author API directly.

        Args:
            page: Authenticated Playwright Page.
            endpoint: API endpoint path (e.g. "/api/author/article/cover_article/v0/").
            params: Form data parameters.

        Returns:
            Response body as string.
        """
        return await page.evaluate("""async (p) => {
            const fd = new URLSearchParams();
            fd.append('aid', '2503');
            fd.append('app_name', 'muye_novel');
            for (const [k, v] of Object.entries(p.params)) {
                fd.append(k, v);
            }
            const r = await fetch(p.endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
                body: fd.toString(),
                credentials: 'include',
            });
            return await r.text();
        }""", {"endpoint": endpoint, "params": params})

    async def _wait_random_delay(self) -> None:
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug("Waiting %.1f seconds", delay)
        await asyncio.sleep(delay)

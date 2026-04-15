"""Tests for TomatoPublisher."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from novel_bot.publisher.tomato import TomatoPublisher
from novel_bot.models import Chapter


class TestTomatoPublisher:
    """Test cases for Tomato Novel platform publishing."""

    def test_initializes_with_config(self) -> None:
        """Test publisher initializes with delay configuration."""
        publisher = TomatoPublisher(delay_min=3, delay_max=8)
        assert publisher.delay_min == 3
        assert publisher.delay_max == 8

    @pytest.mark.asyncio
    async def test_publish_chapter_calls_page_operations(self) -> None:
        """Test publish_chapter interacts with page correctly."""
        page = AsyncMock()
        page.goto = AsyncMock()
        page.fill = AsyncMock()
        page.click = AsyncMock()
        page.wait_for_load_state = AsyncMock()

        publisher = TomatoPublisher(delay_min=0, delay_max=0)
        chapter = Chapter(title="第1章 测试", content="正文内容", index=0)

        with patch.object(publisher, "_wait_random_delay", new_callable=AsyncMock):
            result = await publisher.publish_chapter(page, book_id="123", chapter=chapter)

        assert page.goto.called or page.click.called

    def test_retry_policy_from_spec(self) -> None:
        """Test retry constants match specification."""
        assert TomatoPublisher.RETRY_NETWORK == 3
        assert TomatoPublisher.RETRY_PUBLISH == 3
        assert TomatoPublisher.RETRY_STRUCTURE == 0

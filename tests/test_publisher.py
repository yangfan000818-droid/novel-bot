"""Tests for TomatoPublisher."""
import json
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
        """Test publish_chapter navigates and calls APIs (no editor typing)."""
        mock_locator = AsyncMock()
        mock_locator.wait_for = AsyncMock()

        page = AsyncMock()
        page.goto = AsyncMock()
        page.locator = MagicMock(return_value=mock_locator)
        page.wait_for_timeout = AsyncMock()

        saved_handlers: list = []

        def mock_on(event: str, handler: object) -> None:
            if event == "response":
                saved_handlers.append(handler)

        page.on = mock_on

        cover_resp = json.dumps({"code": 0, "data": {"latest_version": 2}})
        publish_resp = json.dumps({"code": 0, "data": {"item_id": "999"}})
        page.evaluate = AsyncMock(side_effect=[
            cover_resp,
            publish_resp,
        ])

        publisher = TomatoPublisher(delay_min=0, delay_max=0)
        chapter = Chapter(title="第1章 测试", content="正文内容", index=0)

        with patch.object(publisher, "_wait_random_delay", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="item_id"):
                await publisher.publish_chapter(page, book_id="123", chapter=chapter)

        assert page.goto.called

    def test_retry_policy_from_spec(self) -> None:
        """Test retry constants match specification."""
        assert TomatoPublisher.RETRY_NETWORK == 3
        assert TomatoPublisher.RETRY_PUBLISH == 3
        assert TomatoPublisher.RETRY_STRUCTURE == 0

    @pytest.mark.asyncio
    async def test_api_call_posts_form_data(self) -> None:
        """Test _api_call sends form data via in-page fetch."""
        page = AsyncMock()
        page.evaluate = AsyncMock(return_value='{"code":0}')

        result = await TomatoPublisher._api_call(
            page, "/api/author/article/cover_article/v0/",
            {"book_id": "123", "item_id": "456", "title": "test", "content": "<p>hi</p>"},
        )

        assert page.evaluate.called
        assert json.loads(result)["code"] == 0

    @pytest.mark.asyncio
    async def test_publish_raises_on_no_item_id(self) -> None:
        """Test publish_chapter raises when new_article gives no item_id."""
        mock_locator = AsyncMock()
        mock_locator.wait_for = AsyncMock()

        page = AsyncMock()
        page.goto = AsyncMock()
        page.locator = MagicMock(return_value=mock_locator)
        page.wait_for_timeout = AsyncMock()

        page.evaluate = AsyncMock(side_effect=[
            '{"code":-1,"message":"error"}',
        ])

        publisher = TomatoPublisher(delay_min=0, delay_max=0)

        with patch.object(publisher, "_wait_random_delay", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="item_id"):
                await publisher.publish_chapter(
                    page, book_id="123",
                    chapter=Chapter(title="test", content="content", index=0),
                )

    def test_content_to_html_paragraphs(self) -> None:
        """Test _content_to_html wraps paragraphs in <p> tags."""
        text = "第一段内容\n\n第二段内容\n\n第三段内容"
        html = TomatoPublisher._content_to_html(text)
        assert html == "<p>第一段内容</p><p>第二段内容</p><p>第三段内容</p>"

    def test_content_to_html_with_newlines(self) -> None:
        """Test _content_to_html converts single newlines to <br>."""
        text = "第一行\n第二行\n\n第二段"
        html = TomatoPublisher._content_to_html(text)
        assert html == "<p>第一行<br>第二行</p><p>第二段</p>"

    def test_content_to_html_empty_input(self) -> None:
        """Test _content_to_html handles empty input."""
        assert TomatoPublisher._content_to_html("") == ""
        assert TomatoPublisher._content_to_html("\n\n\n") == ""

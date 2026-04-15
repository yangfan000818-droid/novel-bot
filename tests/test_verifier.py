"""Tests for PublishVerifier."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from novel_bot.monitor.verifier import PublishVerifier


class TestPublishVerifier:
    """Test cases for PublishVerifier post-publish verification."""

    @pytest.mark.asyncio
    async def test_verify_success(self) -> None:
        """Test verification succeeds when success indicators found."""
        page = AsyncMock()
        page.content = AsyncMock(return_value='<div class="success">发布成功</div>')

        verifier = PublishVerifier()
        result = await verifier.verify(page, "第1章", 3000)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_verify_failure(self) -> None:
        """Test verification fails when failure indicators found."""
        page = AsyncMock()
        page.content = AsyncMock(return_value='<div class="error">发布失败</div>')

        verifier = PublishVerifier()
        result = await verifier.verify(page, "第1章", 3000)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_verify_uses_provided_logger(self) -> None:
        """Test verification logs through provided logger."""
        page = AsyncMock()
        page.content = AsyncMock(return_value='<div class="success">审核中</div>')
        mock_logger = MagicMock()

        verifier = PublishVerifier()
        result = await verifier.verify(page, "第1章", 3000, logger=mock_logger)
        assert result.success is True
        mock_logger.info.assert_called_once()

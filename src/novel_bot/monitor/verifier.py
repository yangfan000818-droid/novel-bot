"""Post-publish verification for detecting publish success/failure."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


@dataclass(frozen=True)
class VerifyResult:
    """Result of a publish verification check."""

    success: bool
    message: str


class PublishVerifier:
    """Verifies chapter publish status by analyzing page content."""

    _SUCCESS_PATTERNS = [
        re.compile(r"发布成功"),
        re.compile(r"审核中"),
        re.compile(r"提交成功"),
        re.compile(r"已保存"),
    ]

    _FAILURE_PATTERNS = [
        re.compile(r"发布失败"),
        re.compile(r"提交失败"),
        re.compile(r"操作失败"),
    ]

    async def verify(
        self,
        page: Page,
        chapter_title: str,
        expected_word_count: int,
        logger=None,
    ) -> VerifyResult:
        """Verify if chapter was successfully published.

        Analyzes page content for success/failure indicators.

        Args:
            page: Playwright Page object with publish result.
            chapter_title: Title of the chapter being verified.
            expected_word_count: Expected word count for validation (future use).
            logger: Optional BookLogger instance for logging.

        Returns:
            VerifyResult with success status and message.
        """
        content = await page.content()

        for pattern in self._SUCCESS_PATTERNS:
            if pattern.search(content):
                msg = f"章节 '{chapter_title}' 发布验证通过"
                if logger:
                    logger.info(msg)
                return VerifyResult(success=True, message=msg)

        for pattern in self._FAILURE_PATTERNS:
            if pattern.search(content):
                msg = f"章节 '{chapter_title}' 发布失败"
                if logger:
                    logger.error(msg)
                return VerifyResult(success=False, message=msg)

        # Indeterminate — no clear success or failure indicator
        msg = f"章节 '{chapter_title}' 验证结果不确定，请手动检查"
        if logger:
            logger.warning(msg)
        return VerifyResult(success=False, message=msg)

"""Orchestrator coordinates all agents and manages publishing workflow."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING

from novel_bot.models import Chapter, PublishProgress, TaskState
from novel_bot.monitor.logger import BookLogger

if TYPE_CHECKING:
    from novel_bot.parser.base import BaseParser
    from novel_bot.login.manager import LoginManager
    from novel_bot.publisher.base import BasePublisher
    from playwright.async_api import Page

# Import at runtime (outside TYPE_CHECKING block) since TYPE_CHECKING is False at runtime
from novel_bot.monitor.verifier import PublishVerifier


class Orchestrator:
    """Coordinates publishing agents and manages progress tracking."""

    def __init__(
        self,
        parser: BaseParser | None = None,
        login_manager: LoginManager | None = None,
        publisher: BasePublisher | None = None,
        verifier: PublishVerifier | None = None,
        progress_file: str = "data/progress.json",
    ) -> None:
        """Initialize orchestrator with dependency injection.

        Args:
            parser: Optional parser for parsing manuscript files.
            login_manager: Optional login manager for authentication.
            publisher: Optional publisher for platform publishing.
            verifier: Optional verifier for post-publish validation.
            progress_file: Path to store/load progress data.
        """
        self.parser = parser
        self.login_manager = login_manager
        self.publisher = publisher
        self.verifier = verifier or PublishVerifier()
        self._progress_file = Path(progress_file)
        self._progress = self._load_progress()

    def _load_progress(self) -> PublishProgress:
        """Load progress from JSON file.

        Returns:
            PublishProgress instance with loaded data.
        """
        if not self._progress_file.exists():
            return PublishProgress()
        data = json.loads(self._progress_file.read_text(encoding="utf-8"))
        return PublishProgress.from_dict(data)

    def _save_progress(self, data: dict[str, int]) -> None:
        """Save progress data to JSON file.

        Args:
            data: Dictionary mapping book titles to last published chapter index.
        """
        self._progress_file.parent.mkdir(parents=True, exist_ok=True)
        self._progress_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _get_pending_chapters(self, book_title: str, chapters: list[Chapter]) -> list[Chapter]:
        """Filter chapters to get only pending ones.

        Args:
            book_title: Title of the book.
            chapters: List of all chapters.

        Returns:
            List of chapters with index > last published index.
        """
        last = self._progress.get_last_published(book_title)
        return [ch for ch in chapters if ch.index > last]

    async def publish_book(
        self,
        book_title: str,
        chapters: list[Chapter],
        book_id: str | None = None,
    ) -> None:
        """Coordinate publishing workflow for a book.

        Args:
            book_title: Title of the book to publish.
            chapters: List of chapters to publish.
            book_id: Optional book ID on the platform.
        """
        logger = BookLogger(book_title)
        logger.info(f"开始发布流程，共 {len(chapters)} 章")

        pending = self._get_pending_chapters(book_title, chapters)
        if not pending:
            logger.info("所有章节已发布，无需操作")
            return

        logger.info(f"待发布 {len(pending)} 章，从第 {pending[0].index} 章开始")

        page = await self.login_manager.get_session()
        logger.info("登录成功")

        for chapter in pending:
            try:
                success = await self.publisher.publish_chapter(page, book_id or "", chapter)
                if success:
                    result = await self.verifier.verify(page, chapter.title, chapter.word_count, logger=logger)
                    if result.success:
                        self._progress.update(book_title, chapter.index)
                        self._save_progress(self._progress.to_dict())
                        logger.info(f"第 {chapter.index} 章 '{chapter.title}' 发布成功")
                    else:
                        logger.error(f"第 {chapter.index} 章 '{chapter.title}' 验证失败: {result.message}")
            except Exception as e:
                logger.error(f"第 {chapter.index} 章 '{chapter.title}' 发布异常: {e}")

        logger.info("发布流程结束")

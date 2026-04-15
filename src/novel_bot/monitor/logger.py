"""Per-book daily logger for tracking publishing operations."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


class BookLogger:
    """Logger that creates per-book, per-day log files."""

    def __init__(self, book_title: str, log_dir: str = "logs") -> None:
        """Initialize logger for a specific book.

        Args:
            book_title: Title of the book being logged.
            log_dir: Base directory for log files.
        """
        self._book_title = book_title
        self._log_dir = Path(log_dir) / book_title
        self._log_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self._log_dir / f"{today}.log"

        # Use unique logger name to avoid conflicts
        logger_name = f"novel_bot.{book_title}"
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(logging.DEBUG)
        # Prevent propagation to root logger
        self._logger.propagate = False

        # Clear any existing handlers to avoid duplicates
        self._logger.handlers.clear()

        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )
        self._logger.addHandler(handler)

    def info(self, message: str) -> None:
        """Log an informational message.

        Args:
            message: The message to log.
        """
        self._logger.info(message)

    def warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: The message to log.
        """
        self._logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: The message to log.
        """
        self._logger.error(message)

"""Publisher module for posting content to novel platforms."""
from novel_bot.publisher.base import BasePublisher
from novel_bot.publisher.tomato import TomatoPublisher

__all__ = ["BasePublisher", "TomatoPublisher"]

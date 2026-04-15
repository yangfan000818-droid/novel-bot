"""CLI entry point for novel-bot.

This module provides Click-based commands for:
- publish: Publish a book to the platform
- schedule: Start scheduled publishing tasks
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
import yaml

from novel_bot.config import load_settings
from novel_bot.models import Book
from novel_bot.monitor.logger import BookLogger
from novel_bot.login.manager import LoginManager
from novel_bot.publisher.tomato import TomatoPublisher
from novel_bot.orchestrator import Orchestrator
from novel_bot.monitor.verifier import PublishVerifier
from novel_bot.scheduler import load_schedules, start_scheduler


def _get_parser(file_ext: str):
    """Get parser class based on file extension.

    Args:
        file_ext: File extension without dot (e.g., 'md', 'txt').

    Returns:
        Parser class or None.
    """
    from novel_bot.parser.markdown import MarkdownParser
    from novel_bot.parser.txt import TxtParser
    from novel_bot.parser.docx import DocxParser

    parsers = {
        ".md": MarkdownParser,
        ".txt": TxtParser,
        ".docx": DocxParser,
    }
    cls = parsers.get(file_ext)
    return cls() if cls else None


@click.group()
@click.pass_context
def main(ctx):
    """Novel Bot — 自动发布小说到番茄小说平台"""
    ctx.ensure_object(dict)
    ctx.obj["settings"] = load_settings()


@main.command()
@click.argument("book_name")
@click.pass_context
def publish(ctx, book_name: str) -> None:
    """发布指定书籍"""
    settings = ctx.obj["settings"]
    books_path = settings.resolved_books_path

    book_dir = books_path / book_name
    if not book_dir.exists():
        click.echo(f"错误：找不到书籍目录 {book_dir}", err=True)
        sys.exit(1)

    # Load book.json
    book_json = book_dir / "book.json"
    if not book_json.exists():
        click.echo(f"错误：找不到 {book_json}", err=True)
        sys.exit(1)

    # Parse chapters
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.exists():
        click.echo(f"错误：找不到章节目录 {chapters_dir}", err=True)
        sys.exit(1)

    md_files = list(chapters_dir.glob("*.md"))
    txt_files = list(chapters_dir.glob("*.txt"))
    docx_files = list(chapters_dir.glob("*.docx"))

    if md_files:
        from novel_bot.parser.markdown import MarkdownParser
        parser = MarkdownParser()
        chapters = parser.parse_directory(chapters_dir)
    elif txt_files:
        from novel_bot.parser.txt import TxtParser
        parser = TxtParser()
        chapters = parser.parse_directory(chapters_dir)
    elif docx_files:
        from novel_bot.parser.docx import DocxParser
        parser = DocxParser()
        chapters = parser.parse_file(docx_files[0])
    else:
        click.echo("错误：chapters 目录下没有找到支持的文件格式", err=True)
        sys.exit(1)

    # Load book config
    import json
    book_data = json.loads(book_json.read_text(encoding="utf-8"))
    book = Book.from_json(book_data)

    click.echo(f"解析到 {len(chapters)} 章")


@main.command()
@click.pass_context
def schedule(ctx):
    """启动定时发布"""
    settings = ctx.obj["settings"]
    config_dir = Path(__file__).parent.parent.parent / "config"
    schedule_file = config_dir / "schedule.yaml"

    schedules = load_schedules(schedule_file)
    if not schedules:
        click.echo("没有配置定时任务，请编辑 config/schedule.yaml")
        return

    click.echo(f"加载到 {len(schedules)} 个定时任务")

    async def run():
        login_mgr = LoginManager(
            cookie_file=str(Path(__file__).parent.parent.parent / settings.cookie_file)
        )
        publisher = TomatoPublisher(
            delay_min=settings.publish_delay_min,
            delay_max=settings.publish_delay_max,
        )
        verifier = PublishVerifier()
        progress_file = str(Path(__file__).parent.parent.parent / settings.progress_file)

        async def publish_callback(book_name: str, chapters_count: int):
            books_path = settings.resolved_books_path
            book_dir = books_path / book_name
            book_json = book_dir / "book.json"

            book_data = json.loads(book_json.read_text(encoding="utf-8"))
            book = Book.from_json(book_data)

            # Get parser based on file extension
            chapters_dir = book_dir / "chapters"
            md_files = list(chapters_dir.glob("*.md"))
            txt_files = list(chapters_dir.glob("*.txt"))

            if md_files:
                from novel_bot.parser.markdown import MarkdownParser
                parser = MarkdownParser()
                chapters = parser.parse_directory(chapters_dir)
            else:
                from novel_bot.parser.txt import TxtParser
                parser = TxtParser()
                chapters = parser.parse_directory(chapters_dir)

            orch = Orchestrator(
                login_manager=login_mgr,
                publisher=publisher,
                verifier=verifier,
                progress_file=progress_file,
            )
            await orch.publish_book(book.title, chapters, book_id=book.id)

        scheduler = await start_scheduler(schedules, callback=publish_callback)
        click.echo("定时任务已启动，按 Ctrl+C 退出")
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            scheduler.shutdown()
            click.echo("定时任务已停止")

    asyncio.run(run())


if __name__ == "__main__":
    main()

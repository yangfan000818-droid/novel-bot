"""Batch publish chapters to Tomato Novel with publish time tracking."""
import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from novel_bot.models import Chapter
from novel_bot.publisher.tomato import TomatoPublisher

BOOKS_ROOT = Path("/Users/yfan/work/xs/books")
COOKIE_FILE = Path("data/cookies.json")
BOOKS_CONFIG_FILE = Path("data/books.json")


# ---------------------------------------------------------------------------
# Books config
# ---------------------------------------------------------------------------

def load_books_config() -> dict:
    """Load books configuration mapping book names to Tomato Novel book IDs."""
    if BOOKS_CONFIG_FILE.exists():
        with open(BOOKS_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_books_config(config: dict) -> None:
    """Persist books configuration to disk."""
    BOOKS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOKS_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def resolve_book(book_name: str, book_id_override: str | None = None) -> tuple[Path, Path, str]:
    """Resolve book paths and ID from book name.

    Returns (book_dir, chapters_dir, book_id).
    """
    book_dir = BOOKS_ROOT / book_name
    chapters_dir = book_dir / "txt"

    if not book_dir.exists():
        print(f"书籍目录不存在: {book_dir}")
        sys.exit(1)

    config = load_books_config()
    book_id = book_id_override or config.get(book_name, {}).get("book_id")
    if not book_id:
        print(f"未找到书籍 {book_name} 的 book_id，请使用 --book-id 指定")
        sys.exit(1)

    # Auto-save to config if using --book-id and not yet recorded
    if book_id_override and config.get(book_name, {}).get("book_id") != book_id_override:
        config.setdefault(book_name, {})["book_id"] = book_id_override
        save_books_config(config)

    return book_dir, chapters_dir, book_id


# ---------------------------------------------------------------------------
# Publish state management
# ---------------------------------------------------------------------------

def get_state_file(book_name: str) -> Path:
    """Get the per-book state file path."""
    return Path("data") / f"publish_state_{book_name}.json"


def load_state(book_name: str) -> dict:
    """Load publish state from disk. Returns empty state if not found."""
    state_file = get_state_file(book_name)
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"book_name": book_name, "chapters": [], "last_publish_time": 0}


def save_state(state: dict) -> None:
    """Persist publish state to disk."""
    book_name = state.get("book_name", "unknown")
    state_file = get_state_file(book_name)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def record_chapter(state: dict, index: int, title: str, publish_time: int, status: str) -> None:
    """Record a chapter publish event in state."""
    state["chapters"].append({
        "index": index,
        "title": title,
        "publish_time": publish_time,
        "status": status,
    })
    if publish_time > state["last_publish_time"]:
        state["last_publish_time"] = publish_time
    save_state(state)


def get_next_chapter_index(state: dict) -> int:
    """Get the next chapter index to publish (1-based)."""
    if not state["chapters"]:
        return 1
    return max(ch["index"] for ch in state["chapters"]) + 1


def check_publish_time(state: dict, requested_time: int | None) -> int | None:
    """Validate and return the effective publish time.

    Returns None for immediate publish, or a Unix timestamp for scheduled.
    Raises ValueError if the time constraint is violated.
    """
    last_pt = state["last_publish_time"]
    now = int(datetime.now().timestamp())

    if requested_time is None:
        # Immediate publish requested
        if now < last_pt:
            raise ValueError(
                f"当前时间早于最后发布时间 "
                f"({datetime.fromtimestamp(last_pt).strftime('%Y-%m-%d %H:%M')})，"
                f"请使用 --publish-time 指定更晚的时间"
            )
        return None

    # Scheduled publish — must be after last_publish_time
    if requested_time <= last_pt:
        raise ValueError(
            f"指定时间 {datetime.fromtimestamp(requested_time).strftime('%Y-%m-%d %H:%M')} "
            f"不晚于最后发布时间 "
            f"({datetime.fromtimestamp(last_pt).strftime('%Y-%m-%d %H:%M')})，"
            f"请选择更晚的时间"
        )
    return requested_time


# ---------------------------------------------------------------------------
# Chapter file parsing
# ---------------------------------------------------------------------------

def parse_chapter_file(filepath: Path) -> tuple[str, str]:
    """Parse a chapter file. Returns (title, content).

    Filename format: ``第N章_标题.txt``
      - Title extracted from filename
      - Content is the entire file text (pure story)
    """
    stem = filepath.stem
    title_part = re.sub(r"^\d+_", "", stem)
    title = title_part.replace("_", " ")
    content = filepath.read_text(encoding="utf-8").strip()
    return title, content


def load_chapters(chapters_dir: Path, start: int = 1, end: int | None = None) -> list[Chapter]:
    """Load and parse chapter files from the book directory."""
    files = sorted(chapters_dir.glob("*.txt"))
    if not files:
        print(f"No chapter files found in {chapters_dir}")
        sys.exit(1)

    chapters: list[Chapter] = []
    for i, filepath in enumerate(files, start=1):
        if i < start:
            continue
        if end is not None and i > end:
            break

        title, content = parse_chapter_file(filepath)
        if not content:
            print(f"  ⚠ {filepath.name}: 正文为空")
            continue

        chapters.append(Chapter(title=title, content=content, index=i))

    return chapters


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------

async def publish_all(
    chapters: list[Chapter],
    book_name: str,
    book_id: str,
    delay_min: int = 3,
    delay_max: int = 8,
    publish_time: int | None = None,
    publish_interval: int = 30,
) -> None:
    """Publish all chapters sequentially with state tracking."""
    state = load_state(book_name)

    with open(COOKIE_FILE, "r", encoding="utf-8") as f:
        cookies = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()

        publisher = TomatoPublisher(delay_min=delay_min, delay_max=delay_max)

        success_count = 0
        fail_count = 0

        for i, chapter in enumerate(chapters, start=1):
            chapter_publish_time: int | None = None
            if publish_time is not None:
                chapter_publish_time = publish_time + (i - 1) * publish_interval * 60
                time_str = datetime.fromtimestamp(chapter_publish_time).strftime("%Y-%m-%d %H:%M")
            else:
                time_str = "立即"

            print(
                f"\n[{i}/{len(chapters)}] "
                f"发布: {chapter.title} ({len(chapter.content)} 字) [{time_str}]"
            )
            try:
                result = await publisher.publish_chapter(
                    page, book_id=book_id, chapter=chapter,
                    publish_time=chapter_publish_time,
                )
                if result:
                    success_count += 1
                    print("  -> 成功")
                    # Record publish time (use scheduled time or now)
                    pt = chapter_publish_time or int(datetime.now().timestamp())
                    record_chapter(state, chapter.index, chapter.title, pt, "published")
            except Exception as e:
                fail_count += 1
                print(f"  -> 错误: {e}，停止发布")
                # Still record if it was a scheduled publish that got submitted
                if chapter_publish_time:
                    record_chapter(state, chapter.index, chapter.title, chapter_publish_time, "failed")
                break

        await browser.close()

    print(f"\n完成: {success_count} 成功, {fail_count} 失败")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="批量发布章节到番茄小说")
    parser.add_argument("--book", type=str, required=True, help="书籍名称（对应 books/ 下的目录名）")
    parser.add_argument("--book-id", type=str, default=None, help="番茄小说书籍 ID（首次指定后自动保存）")
    parser.add_argument("--start", type=int, default=None, help="起始章节号 (默认: 接续上次)")
    parser.add_argument("--end", type=int, default=None, help="结束章节号 (默认: 全部)")
    parser.add_argument("--dry-run", action="store_true", help="仅解析不发布")
    parser.add_argument(
        "--delay-min", type=int, default=3, help="章节间最小延迟秒数"
    )
    parser.add_argument(
        "--delay-max", type=int, default=8, help="章节间最大延迟秒数"
    )
    parser.add_argument(
        "--publish-time",
        type=str,
        default=None,
        help='定时发布首章时间，格式 "YYYY-MM-DD HH:MM"（默认：立即发布）',
    )
    parser.add_argument(
        "--publish-interval",
        type=int,
        default=30,
        help="定时发布章节间隔分钟数（默认：30）",
    )
    parser.add_argument(
        "--status", action="store_true", help="显示发布状态"
    )
    args = parser.parse_args()

    book_dir, chapters_dir, book_id = resolve_book(args.book, args.book_id)

    state = load_state(args.book)

    # --status: show publish history and exit
    if args.status:
        print(f"书籍: {args.book} (ID: {book_id})")
        if not state["chapters"]:
            print("暂无发布记录")
        else:
            print(f"已发布 {len(state['chapters'])} 章:")
            last_pt = state["last_publish_time"]
            print(f"  最后发布时间: {datetime.fromtimestamp(last_pt).strftime('%Y-%m-%d %H:%M')}")
            print(f"  下一章编号: {get_next_chapter_index(state)}")
            for ch in state["chapters"]:
                pt_str = datetime.fromtimestamp(ch["publish_time"]).strftime("%Y-%m-%d %H:%M")
                print(f"  {ch['index']}. {ch['title']} [{ch['status']}] {pt_str}")
        return

    # Determine start index: auto-continue from last published chapter
    if args.start is None:
        args.start = get_next_chapter_index(state)

    chapters = load_chapters(chapters_dir, args.start, args.end)

    if not chapters:
        print("没有可发布的章节")
        return

    print(f"\n书籍: {args.book} (ID: {book_id})")
    print(f"共 {len(chapters)} 章:")
    for ch in chapters:
        print(f"  {ch.index}. {ch.title} ({len(ch.content)} 字)")

    # Parse and validate publish time
    publish_time: int | None = None
    if args.publish_time:
        try:
            dt = datetime.strptime(args.publish_time, "%Y-%m-%d %H:%M")
            publish_time = int(dt.timestamp())
        except ValueError:
            print(f"时间格式错误: {args.publish_time}，请使用 YYYY-MM-DD HH:MM")
            return

    try:
        publish_time = check_publish_time(state, publish_time)
    except ValueError as e:
        print(f"  ✗ {e}")
        return

    if args.dry_run:
        print(f"\n--- 第一章内容预览 ({chapters[0].title}) ---")
        print(chapters[0].content[:500])
        if len(chapters[0].content) > 500:
            print("...")
        print(f"\n--- 最后一章内容预览 ({chapters[-1].title}) ---")
        print(chapters[-1].content[-200:])
        return

    print()
    asyncio.run(publish_all(
        chapters, args.book, book_id,
        args.delay_min, args.delay_max,
        publish_time=publish_time,
        publish_interval=args.publish_interval,
    ))


if __name__ == "__main__":
    main()

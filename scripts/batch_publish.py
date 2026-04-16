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

BOOK_DIR = Path("/Users/yfan/work/xs/books/太初破灭")
CHAPTERS_DIR = BOOK_DIR / "txt"
COOKIE_FILE = Path("data/cookies.json")
STATE_FILE = Path("data/publish_state.json")
BOOK_ID = "7629145838731676697"


# ---------------------------------------------------------------------------
# Publish state management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load publish state from disk. Returns empty state if not found."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"book_id": BOOK_ID, "chapters": [], "last_publish_time": 0}


def save_state(state: dict) -> None:
    """Persist publish state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
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


def load_chapters(start: int = 1, end: int | None = None) -> list[Chapter]:
    """Load and parse chapter files from the book directory."""
    files = sorted(CHAPTERS_DIR.glob("*.txt"))
    if not files:
        print(f"No chapter files found in {CHAPTERS_DIR}")
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
    delay_min: int = 3,
    delay_max: int = 8,
    publish_time: int | None = None,
    publish_interval: int = 30,
) -> None:
    """Publish all chapters sequentially with state tracking."""
    state = load_state()

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
                    page, book_id=BOOK_ID, chapter=chapter,
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

    state = load_state()

    # --status: show publish history and exit
    if args.status:
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

    chapters = load_chapters(args.start, args.end)

    if not chapters:
        print("没有可发布的章节")
        return

    print(f"\n共 {len(chapters)} 章:")
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
        chapters, args.delay_min, args.delay_max,
        publish_time=publish_time,
        publish_interval=args.publish_interval,
    ))


if __name__ == "__main__":
    main()

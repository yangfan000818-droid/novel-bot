"""Auto-write and publish chapters: inkos generates, then publishes to Tomato Novel.

Workflow per chapter:
  1. inkos write next → generate chapter
  2. Parse inkos chapter .md file
  3. Publish to Tomato Novel
  4. On content errors → inkos revise → retry publish
  5. On auth errors → stop and alert
  6. Daily limit: 10 chapters/day, excess scheduled to next day 8:00 + 30min intervals
"""
import argparse
import asyncio
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright

from novel_bot.models import Chapter
from novel_bot.publisher.tomato import TomatoPublisher

INKOS_BOOKS_DIR = Path("books")
BROWSER_DATA_DIR = Path("data/browser_data")
BOOKS_CONFIG_FILE = Path("data/books.json")

DAILY_LIMIT = 10
CHAPTER_INTERVAL_MIN = 30
DAY_START_HOUR = 8

# Maximum revise retries before giving up on a chapter
MAX_REVISE_ATTEMPTS = 2

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_books_config() -> dict:
    if BOOKS_CONFIG_FILE.exists():
        with open(BOOKS_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def get_state_file(book_name: str) -> Path:
    return Path("data") / f"auto_publish_state_{book_name}.json"


def load_state(book_name: str) -> dict:
    state_file = get_state_file(book_name)
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "book_name": book_name,
        "published": [],       # [{index, title, publish_time, status}]
        "today_date": "",
        "today_count": 0,
        "total_published": 0,
    }


def save_state(state: dict) -> None:
    book_name = state.get("book_name", "unknown")
    state_file = get_state_file(book_name)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def record_success(state: dict, index: int, title: str, publish_time: int) -> None:
    state["published"].append({
        "index": index,
        "title": title,
        "publish_time": publish_time,
        "status": "published",
    })
    state["total_published"] = state.get("total_published", 0) + 1
    today_str = datetime.now().strftime("%Y-%m-%d")
    if state.get("today_date") != today_str:
        state["today_date"] = today_str
        state["today_count"] = 0
    state["today_count"] = state.get("today_count", 0) + 1
    save_state(state)


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

def calc_publish_time(state: dict, chapter_index: int) -> int | None:
    """Calculate publish timestamp for a chapter.

    Returns None for immediate publish, or a Unix timestamp for scheduled.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_count = state.get("today_count", 0) if state.get("today_date") == today_str else 0

    if today_count < DAILY_LIMIT:
        return None  # immediate

    # Calculate which day and slot this chapter falls into
    # total_published so far determines the base, chapter_index is 1-based
    total_done = state.get("total_published", 0)
    # Position in the overall queue (0-based)
    overall_pos = total_done  # next slot after all published

    # How many days ahead from today
    day_offset = (overall_pos - DAILY_LIMIT) // DAILY_LIMIT + 1
    if day_offset < 1:
        day_offset = 1

    # Slot within that day
    slot_in_day = overall_pos % DAILY_LIMIT

    target_date = datetime.now().replace(
        hour=DAY_START_HOUR, minute=0, second=0, microsecond=0
    ) + timedelta(days=day_offset)

    publish_dt = target_date + timedelta(minutes=slot_in_day * CHAPTER_INTERVAL_MIN)
    return int(publish_dt.timestamp())


# ---------------------------------------------------------------------------
# Chapter parsing
# ---------------------------------------------------------------------------

def parse_inkos_chapter(filepath: Path) -> tuple[int, str, str]:
    stem = filepath.stem
    parts = stem.split("_", 1)
    chapter_number = int(parts[0])
    title = parts[1] if len(parts) > 1 else f"第{chapter_number}章"

    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    idx = 0
    if lines and lines[0].startswith("# "):
        idx = 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx < len(lines) and lines[idx].strip():
        idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    content = "\n".join(lines[idx:]).strip()
    return chapter_number, title, content


def load_latest_chapter(book_name: str) -> tuple[int, str, str] | None:
    """Load the latest chapter from inkos chapters directory."""
    chapters_dir = INKOS_BOOKS_DIR / book_name / "chapters"
    files = sorted(chapters_dir.glob("*.md"))
    if not files:
        return None
    return parse_inkos_chapter(files[-1])


# ---------------------------------------------------------------------------
# inkos commands
# ---------------------------------------------------------------------------

def inkos_write_next(book_name: str) -> Path | None:
    """Run inkos write next, detect new chapter by filesystem diff.

    Returns path to the newly created chapter file, or None on failure.
    """
    chapters_dir = INKOS_BOOKS_DIR / book_name / "chapters"
    existing = set(p.name for p in chapters_dir.glob("*.md"))

    print(f"\n{'='*60}")
    print(f"[inkos] 生成下一章...")
    result = subprocess.run(
        ["inkos", "write", "next", book_name, "--json", "--words", "2500"],
        capture_output=True, text=True, timeout=600,
    )
    # inkos may return non-zero but still write the chapter; check filesystem

    current = set(p.name for p in chapters_dir.glob("*.md"))
    new_files = current - existing
    if not new_files:
        print(f"[inkos] 错误: 未生成新章节文件")
        if result.stderr:
            print(f"  stderr: {result.stderr[-300:]}")
        return None

    # Return the new file (sorted to pick the latest numbered one)
    new_path = chapters_dir / sorted(new_files)[-1]
    print(f"[inkos] 新章节: {new_path.name}")
    return new_path


def inkos_revise(book_name: str, chapter: int, brief: str = "") -> bool:
    """Run inkos revise on a chapter. Returns True if successful."""
    cmd = ["inkos", "revise", book_name, str(chapter), "--mode", "rewrite", "--json"]
    if brief:
        cmd.extend(["--brief", brief])
    print(f"[inkos] 修正第{chapter}章...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"[inkos] 修正失败: {result.stderr[-300:]}")
        return False
    print("[inkos] 修正完成")
    return True


def inkos_approve(book_name: str, chapter: int) -> None:
    """Approve chapter in inkos."""
    subprocess.run(
        ["inkos", "review", "approve", book_name, str(chapter)],
        capture_output=True, text=True, timeout=30,
    )


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

CONTENT_ERROR_KEYWORDS = [
    "标题", "字数", "重复", "违规", "敏感", "内容", "不符合规范",
    "质量", "审核", "拒绝", "非法", "低质",
]

AUTH_ERROR_KEYWORDS = [
    "登录", "未授权", "unauthorized", "timeout", "Timeout",
    "navigate", "locator",
]


def classify_error(error_msg: str) -> str:
    """Classify a publish error as content/auth/unknown."""
    msg_lower = error_msg.lower()
    for kw in CONTENT_ERROR_KEYWORDS:
        if kw in error_msg:
            return "content"
    for kw in AUTH_ERROR_KEYWORDS:
        if kw.lower() in msg_lower:
            return "auth"
    return "unknown"


# ---------------------------------------------------------------------------
# Publishing
# ---------------------------------------------------------------------------

async def publish_chapter(
    book_id: str,
    chapter: Chapter,
    publish_time: int | None,
) -> tuple[bool, str]:
    """Publish a single chapter. Returns (success, error_message)."""
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(BROWSER_DATA_DIR),
            headless=True,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        publisher = TomatoPublisher(delay_min=3, delay_max=5)
        try:
            result = await publisher.publish_chapter(
                page, book_id=book_id, chapter=chapter,
                publish_time=publish_time,
            )
            await context.close()
            return result, ""
        except Exception as e:
            await context.close()
            return False, str(e)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def run(
    book_name: str,
    book_id: str,
    target_chapters: int = 10,
) -> None:
    """Main auto-publish loop. Only proceeds to next chapter after publish success."""
    state = load_state(book_name)

    print(f"书籍: {book_name} (ID: {book_id})")
    print(f"目标: 再发布 {target_chapters} 章")
    print(f"已发布: {state.get('total_published', 0)} 章")

    success_count = 0
    fail_count = 0

    for i in range(target_chapters):
        # Step 1: Generate chapter with inkos
        new_file = inkos_write_next(book_name)
        if not new_file:
            print(f"\n[停止] inkos 生成失败")
            fail_count += 1
            break

        # Step 2: Parse the new chapter
        chapter_num, title, content = parse_inkos_chapter(new_file)
        full_title = f"第{chapter_num}章 {title}"
        word_count = len(content.replace(" ", "").replace("\n", ""))
        print(f"[解析] 第{chapter_num}章 「{title}」 ({word_count} 字)")

        # Approve in inkos
        inkos_approve(book_name, chapter_num)

        # Step 3: Calculate publish time
        publish_time = calc_publish_time(state, chapter_num)
        if publish_time:
            time_str = datetime.fromtimestamp(publish_time).strftime("%Y-%m-%d %H:%M")
            print(f"[调度] 定时发布: {time_str}")
        else:
            time_str = "立即"

        # Step 4: Publish with retry on content errors
        chapter_obj = Chapter(title=full_title, content=content, index=chapter_num)
        published = False
        revise_attempts = 0

        while not published and revise_attempts <= MAX_REVISE_ATTEMPTS:
            success, error = await publish_chapter(book_id, chapter_obj, publish_time)
            if success:
                pt = publish_time or int(datetime.now().timestamp())
                record_success(state, chapter_num, full_title, pt)
                success_count += 1
                published = True
                print(f"  -> 发布成功 ({time_str})")
                break

            error_type = classify_error(error)
            print(f"  -> 失败 [{error_type}]: {error[:200]}")

            if error_type == "auth":
                print(f"\n[停止] 认证失效，请重新登录: .venv/bin/python login_interactive.py")
                return

            if error_type == "content" and revise_attempts < MAX_REVISE_ATTEMPTS:
                revise_attempts += 1
                brief = f"发布失败原因: {error[:200]}。请修正内容问题。"
                print(f"  [修正] 第{revise_attempts}次修正...")
                if inkos_revise(book_name, chapter_num, brief=brief):
                    # Re-read the revised file
                    _, title2, content2 = parse_inkos_chapter(new_file)
                    chapter_obj = Chapter(
                        title=full_title, content=content2, index=chapter_num,
                    )
                continue

            # Unknown error or max retries exceeded — STOP, do not continue
            print(f"  [停止] 无法发布第{chapter_num}章，不继续下一章")
            fail_count += 1
            return

        if not published:
            fail_count += 1
            return

        # Small delay between chapters
        if i < target_chapters - 1:
            await asyncio.sleep(2)

    print(f"\n{'='*60}")
    print(f"完成: {success_count} 成功, {fail_count} 失败")
    print(f"今日已发布: {state.get('today_count', 0)} 章")


def main() -> None:
    parser = argparse.ArgumentParser(description="自动生成并发布章节")
    parser.add_argument("--book", type=str, required=True, help="书籍名称")
    parser.add_argument("--book-id", type=str, default=None, help="番茄小说书籍 ID")
    parser.add_argument(
        "--count", type=int, default=10,
        help=f"本次目标发布章数（默认: {DAILY_LIMIT}）",
    )
    args = parser.parse_args()

    config = load_books_config()
    book_id = args.book_id or config.get(args.book, {}).get("book_id")
    if not book_id:
        print(f"未找到书籍 {args.book} 的 book_id，请使用 --book-id 指定")
        sys.exit(1)

    asyncio.run(run(args.book, book_id, target_chapters=args.count))


if __name__ == "__main__":
    main()

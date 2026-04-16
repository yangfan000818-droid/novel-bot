"""Batch publish chapters to Tomato Novel."""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from novel_bot.models import Chapter
from novel_bot.publisher.tomato import TomatoPublisher

BOOK_DIR = Path("/Users/yfan/work/xs/books/太初破灭")
CHAPTERS_DIR = BOOK_DIR / "chapters"
COOKIE_FILE = Path("data/cookies.json")
BOOK_ID = "7629145838731676697"

def parse_chapter_file(filepath: Path) -> tuple[str, str]:
    """Parse a chapter markdown file. Returns (title, content).

    Format:
      # 第N章 标题          ← title line
      <thinkering>...       ← AI notes (unclosed tag, no </thinkering>)
      (blank line)
      Story content...      ← actual chapter text
    """
    raw = filepath.read_text(encoding="utf-8")

    # Extract title from first line: # 第N章 标题
    title_match = re.match(r"^#\s+(.+)", raw)
    title = title_match.group(1).strip() if title_match else filepath.stem

    # Strip <thinkering> block (unclosed tag, no </thinkering>)
    # Tag bytes: 3c 74 68 69 6e 6b 3e = "<thinkering>" (5-letter tag name)
    think_tag = bytes([0x3c, 0x74, 0x68, 0x69, 0x6e, 0x6b, 0x3e]).decode("ascii")
    idx = raw.find(think_tag)
    if idx >= 0:
        after = raw[idx + len(think_tag) :]
        # Find story start: skip all AI note lines, then take narrative content.
        # Note lines contain keywords like 压缩/扩写/精简/etc or start with list markers.
        note_words = re.compile(r"压缩|扩写|修正|精简|保留|策略|核心|HOOK|减少|删除")
        lines = after.split("\n")
        story_start = len(lines)
        gap_found = False
        for i, line in enumerate(lines):
            if not line.strip():
                gap_found = True
                continue
            if gap_found and len(line.strip()) >= 10:
                if not re.match(r"^[\d\-•*]\s", line.strip()) and not note_words.search(line):
                    story_start = i
                    break
            gap_found = False
        content = "\n".join(lines[story_start:])
    else:
        # No think tag — just remove title line
        content = "\n".join(raw.split("\n")[1:])

    # Remove any remaining title line
    content = re.sub(r"^#\s+.+\n*", "", content)
    return title, content.strip()


def load_chapters(start: int = 1, end: int | None = None) -> list[Chapter]:
    """Load and parse chapter files from the book directory."""
    files = sorted(CHAPTERS_DIR.glob("*.md"))
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
            print(f"Warning: {filepath.name} has no content after parsing")
            continue

        chapters.append(Chapter(title=title, content=content, index=i))

    return chapters


async def publish_all(
    chapters: list[Chapter],
    delay_min: int = 3,
    delay_max: int = 8,
) -> None:
    """Publish all chapters sequentially."""
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
            print(
                f"\n[{i}/{len(chapters)}] "
                f"发布: {chapter.title} ({len(chapter.content)} 字)"
            )
            try:
                result = await publisher.publish_chapter(
                    page, book_id=BOOK_ID, chapter=chapter
                )
                if result:
                    success_count += 1
                    print("  -> 成功")
                else:
                    fail_count += 1
                    print("  -> 失败 (API 返回错误)，停止发布")
                    break
            except Exception as e:
                fail_count += 1
                print(f"  -> 错误: {e}，停止发布")
                break

        await browser.close()

    print(f"\n完成: {success_count} 成功, {fail_count} 失败")


def main() -> None:
    parser = argparse.ArgumentParser(description="批量发布章节到番茄小说")
    parser.add_argument("--start", type=int, default=1, help="起始章节号 (默认: 1)")
    parser.add_argument("--end", type=int, default=None, help="结束章节号 (默认: 全部)")
    parser.add_argument("--dry-run", action="store_true", help="仅解析不发布")
    parser.add_argument(
        "--delay-min", type=int, default=3, help="章节间最小延迟秒数"
    )
    parser.add_argument(
        "--delay-max", type=int, default=8, help="章节间最大延迟秒数"
    )
    args = parser.parse_args()

    chapters = load_chapters(args.start, args.end)

    if not chapters:
        print("没有可发布的章节")
        return

    print(f"共 {len(chapters)} 章:")
    for ch in chapters:
        print(f"  {ch.index}. {ch.title} ({len(ch.content)} 字)")

    if args.dry_run:
        print(f"\n--- 第一章内容预览 ({chapters[0].title}) ---")
        print(chapters[0].content[:500])
        if len(chapters[0].content) > 500:
            print("...")
        print(f"\n--- 最后一章内容预览 ({chapters[-1].title}) ---")
        print(chapters[-1].content[-200:])
        return

    print()
    asyncio.run(publish_all(chapters, args.delay_min, args.delay_max))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""交互式登录：使用持久化浏览器上下文，登录后所有状态自动保存。"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

USER_DATA_DIR = Path('/Users/yfan/work/xs/novel-bot/data/browser_data')
LOGIN_URL = 'https://fanqienovel.com/main/writer/'


async def main() -> None:
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=False,
            viewport={'width': 1280, 'height': 800},
            args=['--disable-blink-features=AutomationControlled'],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("正在打开浏览器，请手动登录...")
        await page.goto(LOGIN_URL)

        print("等待登录完成...")
        while True:
            login_input = await page.query_selector('input[placeholder="手机号"]')
            if login_input is None and 'writer' in page.url:
                print(f"检测到登录成功！URL: {page.url}")
                break
            await asyncio.sleep(2)

        await asyncio.sleep(3)
        print("登录状态已自动保存到持久化浏览器数据目录。")
        await context.close()


if __name__ == '__main__':
    asyncio.run(main())

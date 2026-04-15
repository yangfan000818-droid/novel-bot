"""Login manager for handling browser sessions and cookie persistence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

if TYPE_CHECKING:
    from collections.abc import Iterable

TOMATO_AUTHOR_URL = "https://writer.tomatofn.com"


class LoginManager:
    """Manages browser login sessions with cookie persistence."""

    def __init__(self, cookie_file: str = "data/cookies.json") -> None:
        """Initialize login manager with cookie file path.

        Args:
            cookie_file: Path to store/load cookies from.
        """
        self._cookie_file = Path(cookie_file)

    def has_cookies(self) -> bool:
        """Check if valid cookie file exists.

        Returns:
            True if cookie file exists and is non-empty.
        """
        return self._cookie_file.exists() and self._cookie_file.stat().st_size > 0

    def load_cookies(self) -> list[dict]:
        """Load cookies from storage.

        Returns:
            List of cookie dictionaries, or empty list if no cookies exist.
        """
        if not self.has_cookies():
            return []
        with open(self._cookie_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_cookies(self, cookies: Iterable[dict]) -> None:
        """Save cookies to storage.

        Args:
            cookies: Iterable of cookie dictionaries to save.
        """
        self._cookie_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cookie_file, "w", encoding="utf-8") as f:
            json.dump(list(cookies), f, ensure_ascii=False, indent=2)

    async def first_login(self) -> Page:
        """Open browser in headed mode for user to manually log in.

        This opens a Chromium browser window where the user can
        complete the login process manually. After pressing Enter,
        cookies are saved for future use.

        Returns:
            Authenticated Page object.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(TOMATO_AUTHOR_URL)

            print("请在浏览器中完成登录，登录完成后按 Enter...")
            input()

            cookies = await context.cookies()
            self.save_cookies(cookies)
            await browser.close()

        return await self.get_session()

    async def get_session(self, headless: bool = True) -> Page:
        """Get an authenticated page session.

        Attempts to load existing cookies. If none exist,
        triggers first_login flow. If cookies are invalid,
        prompts user to re-login.

        Args:
            headless: Whether to run browser in headless mode.

        Returns:
            Authenticated Page object.
        """
        cookies = self.load_cookies()
        if not cookies:
            return await self.first_login()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()
            await context.add_cookies(cookies)
            page = await context.new_page()
            await page.goto(TOMATO_AUTHOR_URL)

            # Check if redirected to login page
            current_url = page.url
            if "login" in current_url.lower():
                print("Cookie 已失效，请重新登录...")
                await browser.close()
                return await self.first_login()

            return page

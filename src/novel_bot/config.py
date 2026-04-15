"""Configuration management for novel-bot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Settings:
    """Application settings loaded from settings.yaml."""

    books_path: Path = Path("../books")
    publish_delay_min: int = 5
    publish_delay_max: int = 15
    headless: bool = True
    cookie_file: str = "data/cookies.json"
    progress_file: str = "data/progress.json"
    log_dir: str = "logs"
    project_root: Path | None = None

    @property
    def resolved_books_path(self) -> Path:
        """Resolve books_path relative to project root if not absolute."""
        if self.books_path.is_absolute():
            return self.books_path
        root = self.project_root or Path(__file__).resolve().parent.parent.parent.parent
        return (root / self.books_path).resolve()


def load_settings(
    path: Path | str | None = None,
    project_root: Path | None = None,
) -> Settings:
    """Load settings from a YAML file, falling back to defaults.

    Args:
        path: Path to settings.yaml. Defaults to config/settings.yaml relative to project.
        project_root: Override project root for resolving relative paths.

    Returns:
        Settings with YAML values merged over defaults.
    """
    if path is None:
        config_dir = Path(__file__).resolve().parent.parent.parent.parent / "config"
        path = config_dir / "settings.yaml"

    path = Path(path)
    if not path.exists():
        return Settings()

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    publish = data.get("publish", {})
    return Settings(
        books_path=Path(data.get("books_path", "../books")),
        publish_delay_min=publish.get("delay_min", 5),
        publish_delay_max=publish.get("delay_max", 15),
        headless=publish.get("headless", True),
        cookie_file=data.get("login", {}).get("cookie_file", "data/cookies.json"),
        progress_file=data.get("progress", {}).get("file", "data/progress.json"),
        log_dir=data.get("logging", {}).get("dir", "logs"),
        project_root=project_root,
    )

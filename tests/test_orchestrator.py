"""Tests for Orchestrator."""
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from novel_bot.orchestrator import Orchestrator
from novel_bot.models import Chapter, TaskState, PublishProgress


class TestOrchestrator:
    """Test cases for Orchestrator coordination and progress tracking."""

    def test_load_progress(self, tmp_path: Path) -> None:
        """Test loading progress from JSON file."""
        progress_file = tmp_path / "progress.json"
        progress_file.write_text('{"太初破灭": 5}', encoding="utf-8")

        orch = Orchestrator(progress_file=str(progress_file))
        assert orch._progress.get_last_published("太初破灭") == 5

    def test_load_progress_empty(self, tmp_path: Path) -> None:
        """Test loading progress when no file exists."""
        orch = Orchestrator(progress_file=str(tmp_path / "none.json"))
        assert orch._progress.get_last_published("任何书") == 0

    def test_save_progress(self, tmp_path: Path) -> None:
        """Test saving progress to JSON file."""
        progress_file = tmp_path / "progress.json"
        orch = Orchestrator(progress_file=str(progress_file))
        orch._save_progress({"太初破灭": 3})

        data = json.loads(progress_file.read_text(encoding="utf-8"))
        assert data == {"太初破灭": 3}

    def test_determine_resume_index(self, tmp_path: Path) -> None:
        """Test determining which chapters are pending based on progress."""
        progress_file = tmp_path / "progress.json"
        progress_file.write_text('{"太初破灭": 5}', encoding="utf-8")

        orch = Orchestrator(progress_file=str(progress_file))
        chapters = [Chapter(title=f"第{i}章", content="x", index=i) for i in range(10)]
        pending = orch._get_pending_chapters("太初破灭", chapters)
        assert len(pending) == 4  # chapters 6,7,8,9 (index 5 is last published, resume from 6)
        assert pending[0].index == 6

"""Tests for data models."""

import pytest
from novel_bot.models import Chapter, Book, TaskState, PublishProgress


class TestChapter:
    def test_create_chapter(self):
        ch = Chapter(title="第1章 测试", content="正文内容", index=1)
        assert ch.title == "第1章 测试"
        assert ch.content == "正文内容"
        assert ch.index == 1

    def test_chapter_word_count(self):
        ch = Chapter(title="第1章", content="这是一段测试正文内容", index=1)
        assert ch.word_count == 10

    def test_chapter_word_count_empty(self):
        ch = Chapter(title="第1章", content="", index=1)
        assert ch.word_count == 0

    def test_chapter_is_frozen(self):
        ch = Chapter(title="第1章", content="正文", index=1)
        with pytest.raises(AttributeError):
            ch.title = "新标题"


class TestBook:
    def test_create_from_json(self):
        data = {
            "id": "test-book",
            "title": "测试小说",
            "platform": "tomato",
            "genre": "xuanhuan",
            "status": "active",
            "targetChapters": 200,
            "chapterWordCount": 3000,
            "language": "zh",
        }
        book = Book.from_json(data)
        assert book.id == "test-book"
        assert book.title == "测试小说"
        assert book.platform == "tomato"
        assert book.target_chapters == 200

    def test_book_from_json_missing_fields(self):
        data = {"id": "test", "title": "T"}
        book = Book.from_json(data)
        assert book.platform == "tomato"
        assert book.genre == ""


class TestTaskState:
    def test_state_transitions(self):
        assert TaskState.PENDING.can_transition_to(TaskState.PARSING)
        assert not TaskState.PENDING.can_transition_to(TaskState.COMPLETED)
        assert TaskState.PARSING.can_transition_to(TaskState.LOGIN_CHECK)

    def test_invalid_transition_raises(self):
        with pytest.raises(ValueError):
            TaskState.PENDING.can_transition_to(TaskState.COMPLETED, raise_error=True)

    def test_all_states_defined(self):
        expected = {"PENDING", "PARSING", "LOGIN_CHECK", "PUBLISHING", "VERIFYING", "COMPLETED", "FAILED"}
        actual = {s.name for s in TaskState}
        assert actual == expected

    def test_failed_can_retry(self):
        assert TaskState.FAILED.can_transition_to(TaskState.PARSING)
        assert TaskState.FAILED.can_transition_to(TaskState.PENDING)


class TestPublishProgress:
    def test_update_progress(self):
        progress = PublishProgress()
        progress.update("太初破灭", 5)
        assert progress.get_last_published("太初破灭") == 5

    def test_update_increments(self):
        progress = PublishProgress()
        progress.update("太初破灭", 3)
        progress.update("太初破灭", 5)
        assert progress.get_last_published("太初破灭") == 5

    def test_update_cannot_decrement(self):
        progress = PublishProgress()
        progress.update("太初破灭", 5)
        with pytest.raises(ValueError):
            progress.update("太初破灭", 3)

    def test_new_book_returns_zero(self):
        progress = PublishProgress()
        assert progress.get_last_published("新书") == 0

    def test_to_dict_and_from_dict(self):
        progress = PublishProgress()
        progress.update("书A", 10)
        d = progress.to_dict()
        restored = PublishProgress.from_dict(d)
        assert restored.get_last_published("书A") == 10

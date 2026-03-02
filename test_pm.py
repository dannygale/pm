"""Tests for pm SQLite backend."""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

import pytest

import pm


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect all pm paths to a temp directory and reset DB state."""
    monkeypatch.setattr(pm, "ROOT", tmp_path)
    monkeypatch.setattr(pm, "TODO_PATH", tmp_path / "TODO.json")
    monkeypatch.setattr(pm, "FEATURES_PATH", tmp_path / "FEATURES.json")
    monkeypatch.setattr(pm, "DB_PATH", tmp_path / ".pm.db")
    monkeypatch.setattr(pm, "_db_ready", False)
    yield tmp_path


# ── Schema / init_db ────────────────────────────────────────────────────

class TestInitDb:
    def test_creates_db_file(self, isolated_db):
        pm._ensure_db()
        assert (isolated_db / ".pm.db").exists()

    def test_creates_tables(self, isolated_db):
        pm._ensure_db()
        conn = sqlite3.connect(isolated_db / ".pm.db")
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "todos" in tables
        assert "features" in tables

    def test_idempotent(self, isolated_db):
        pm._ensure_db()
        pm._db_ready = False
        pm._ensure_db()  # should not raise


# ── load/save todos ─────────────────────────────────────────────────────

class TestTodos:
    def test_empty_load(self):
        assert pm.load_todos() == []

    def test_save_and_load_roundtrip(self):
        items = [
            {"id": 1, "type": "task", "status": "open", "priority": "high",
             "title": "Test task", "description": "A test", "created": "2026-01-01"},
        ]
        pm.save_todos(items)
        loaded = pm.load_todos()
        assert len(loaded) == 1
        assert loaded[0]["title"] == "Test task"
        assert loaded[0]["id"] == 1

    def test_json_array_fields_roundtrip(self):
        items = [
            {"id": 1, "type": "bug", "status": "open", "priority": "medium",
             "title": "Bug", "description": "d", "created": "2026-01-01",
             "tags": ["a", "b"], "blocked_by": [2, 3], "blocks": [4],
             "notes": [{"ts": "2026-01-01", "msg": "hello"}]},
        ]
        pm.save_todos(items)
        loaded = pm.load_todos()
        assert loaded[0]["tags"] == ["a", "b"]
        assert loaded[0]["blocked_by"] == [2, 3]
        assert loaded[0]["blocks"] == [4]
        assert loaded[0]["notes"][0]["msg"] == "hello"

    def test_optional_fields_omitted_when_none(self):
        items = [
            {"id": 1, "type": "task", "status": "open", "priority": "low",
             "title": "Minimal", "description": "d", "created": "2026-01-01"},
        ]
        pm.save_todos(items)
        loaded = pm.load_todos()
        assert "package" not in loaded[0]
        assert "tags" not in loaded[0]
        assert "blocked_by" not in loaded[0]

    def test_save_replaces_all(self):
        pm.save_todos([
            {"id": 1, "type": "task", "status": "open", "priority": "low",
             "title": "First", "description": "d", "created": "2026-01-01"},
        ])
        pm.save_todos([
            {"id": 2, "type": "task", "status": "open", "priority": "low",
             "title": "Second", "description": "d", "created": "2026-01-01"},
        ])
        loaded = pm.load_todos()
        assert len(loaded) == 1
        assert loaded[0]["id"] == 2

    def test_ordering_by_id(self):
        items = [
            {"id": 3, "type": "task", "status": "open", "priority": "low",
             "title": "C", "description": "d", "created": "2026-01-01"},
            {"id": 1, "type": "task", "status": "open", "priority": "low",
             "title": "A", "description": "d", "created": "2026-01-01"},
        ]
        pm.save_todos(items)
        loaded = pm.load_todos()
        assert [i["id"] for i in loaded] == [1, 3]


# ── load/save features ──────────────────────────────────────────────────

class TestFeatures:
    def test_empty_load(self):
        assert pm.load_features() == []

    def test_save_and_load_roundtrip(self):
        feats = [
            {"id": "feat-1", "category": "core", "title": "Feature 1",
             "description": "desc", "status": "planned", "priority": "high"},
        ]
        pm.save_features(feats)
        loaded = pm.load_features()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "feat-1"
        assert loaded[0]["status"] == "planned"

    def test_requires_roundtrip(self):
        feats = [
            {"id": "a", "title": "A", "description": "d", "status": "planned",
             "requires": ["b", "c"], "required_by": ["d"]},
        ]
        pm.save_features(feats)
        loaded = pm.load_features()
        assert loaded[0]["requires"] == ["b", "c"]
        assert loaded[0]["required_by"] == ["d"]

    def test_save_replaces_all(self):
        pm.save_features([{"id": "a", "title": "A", "description": "d", "status": "planned"}])
        pm.save_features([{"id": "b", "title": "B", "description": "d", "status": "planned"}])
        loaded = pm.load_features()
        assert len(loaded) == 1
        assert loaded[0]["id"] == "b"


# ── JSON migration ──────────────────────────────────────────────────────

class TestMigration:
    def test_migrates_todo_json(self, isolated_db):
        todo_data = {"items": [
            {"id": 1, "type": "task", "status": "open", "priority": "high",
             "title": "From JSON", "description": "d", "created": "2026-01-01",
             "tags": ["migrated"]},
        ]}
        (isolated_db / "TODO.json").write_text(json.dumps(todo_data))
        pm._ensure_db()
        assert not (isolated_db / "TODO.json").exists()
        assert (isolated_db / "TODO.json.bak").exists()
        loaded = pm.load_todos()
        assert loaded[0]["title"] == "From JSON"
        assert loaded[0]["tags"] == ["migrated"]

    def test_migrates_features_json(self, isolated_db):
        feat_data = {"features": [
            {"id": "f1", "category": "core", "title": "F1",
             "description": "d", "status": "planned"},
        ]}
        (isolated_db / "FEATURES.json").write_text(json.dumps(feat_data))
        pm._ensure_db()
        assert not (isolated_db / "FEATURES.json").exists()
        assert (isolated_db / "FEATURES.json.bak").exists()
        loaded = pm.load_features()
        assert loaded[0]["id"] == "f1"

    def test_empty_json_files_still_renamed(self, isolated_db):
        (isolated_db / "TODO.json").write_text('{"items": []}')
        (isolated_db / "FEATURES.json").write_text('{"features": []}')
        pm._ensure_db()
        assert not (isolated_db / "TODO.json").exists()
        assert not (isolated_db / "FEATURES.json").exists()
        assert (isolated_db / "TODO.json.bak").exists()
        assert (isolated_db / "FEATURES.json.bak").exists()

    def test_no_json_no_migration(self, isolated_db):
        pm._ensure_db()
        assert not (isolated_db / "TODO.json.bak").exists()
        assert not (isolated_db / "FEATURES.json.bak").exists()


# ── next_id ──────────────────────────────────────────────────────────────

class TestNextId:
    def test_empty(self):
        assert pm.next_id([]) == 1

    def test_increments(self):
        assert pm.next_id([{"id": 3}, {"id": 7}]) == 8


# ── History ─────────────────────────────────────────────────────────────

class TestHistory:
    def test_history_table_created(self, isolated_db):
        pm._ensure_db()
        conn = sqlite3.connect(isolated_db / ".pm.db")
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "history" in tables

    def test_record_history_inserts_row(self):
        pm.record_history("todo add", "todo", 1, "Test task")
        conn = sqlite3.connect(pm.DB_PATH)
        rows = conn.execute("SELECT * FROM history").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][2] == "todo add"      # command
        assert rows[0][3] == "todo"           # entity_type
        assert rows[0][4] == "1"             # entity_id (stored as text)
        assert rows[0][5] == "Test task"     # detail

    def test_record_history_detail_optional(self):
        pm.record_history("todo resolve", "todo", 5)
        conn = sqlite3.connect(pm.DB_PATH)
        row = conn.execute("SELECT detail FROM history").fetchone()
        conn.close()
        assert row[0] is None

    def test_todo_add_records_history(self):
        args = mock.MagicMock(
            type="task", title="Hist test", priority="medium",
            description=None, package=None, feature=None,
            tags=None, blocked_by=None,
        )
        args.parent = None
        pm.todo_add(args)
        conn = sqlite3.connect(pm.DB_PATH)
        rows = conn.execute("SELECT command, entity_type, detail FROM history").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "todo add"
        assert rows[0][1] == "todo"
        assert rows[0][2] == "Hist test"

    def test_todo_resolve_records_history(self):
        pm.save_todos([
            {"id": 1, "type": "task", "status": "open", "priority": "low",
             "title": "T", "description": "d", "created": "2026-01-01"},
        ])
        args = mock.MagicMock(id=1)
        pm.todo_resolve(args)
        conn = sqlite3.connect(pm.DB_PATH)
        row = conn.execute("SELECT command, entity_id FROM history").fetchone()
        conn.close()
        assert row[0] == "todo resolve"
        assert row[1] == "1"

    def test_feature_add_records_history(self):
        args = mock.MagicMock(
            id="test-feat", title="Test Feature", priority="medium",
            description=None, category=None, package=None, requires=[],
        )
        pm.feature_add(args)
        conn = sqlite3.connect(pm.DB_PATH)
        row = conn.execute("SELECT command, entity_type, entity_id FROM history").fetchone()
        conn.close()
        assert row == ("feature add", "feature", "test-feat")

    def test_history_list_filters_by_item(self, capsys):
        pm.record_history("todo add", "todo", 1, "Task A")
        pm.record_history("todo add", "todo", 2, "Task B")
        args = mock.MagicMock(item=1, feature=None, since=None, until=None, limit=50)
        pm.history_list(args)
        out = capsys.readouterr().out
        assert "Task A" in out
        assert "Task B" not in out

    def test_history_list_filters_by_feature(self, capsys):
        pm.record_history("feature add", "feature", "gui", "GUI feature")
        pm.record_history("todo add", "todo", 1, "Task")
        args = mock.MagicMock(item=None, feature="gui", since=None, until=None, limit=50)
        pm.history_list(args)
        out = capsys.readouterr().out
        assert "GUI feature" in out
        assert "Task" not in out

    def test_history_list_empty(self, capsys):
        args = mock.MagicMock(item=None, feature=None, since=None, until=None, limit=50)
        pm.history_list(args)
        out = capsys.readouterr().out
        assert "No history entries found" in out

    def test_history_list_limit(self, capsys):
        for i in range(5):
            pm.record_history("todo add", "todo", i, f"Task {i}")
        args = mock.MagicMock(item=None, feature=None, since=None, until=None, limit=2)
        pm.history_list(args)
        out = capsys.readouterr().out
        # Should show only 2 entries (most recent: Task 4 and Task 3)
        assert "Task 4" in out
        assert "Task 3" in out
        assert "Task 0" not in out

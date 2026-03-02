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

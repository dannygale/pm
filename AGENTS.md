# AGENTS.md

## Project overview

pm is a lightweight CLI project management tool that tracks features and tasks in a SQLite database (.pm.db). It provides list, show, edit, and relationship management (blocking, dependencies) for both. It also has an autopilot mode that runs an AI agent in a loop until all work is done.

## Key files

```
pm/
├── pm.py                # All CLI logic: todo, feature, autopilot, dashboard
├── pm_tui.py            # Interactive TUI (textual-based)
├── test_pm.py           # Tests for SQLite backend
├── autopilot-prompt.md  # Default prompt for pm autopilot
├── pyproject.toml       # Package config, entry point: pm = pm:main
├── .pm.db               # SQLite database (todos + features)
└── CHANGELOG.md         # Version history
```

## Architecture

pm.py is a single-file CLI using argparse. Key patterns:
- `load_todos()` / `save_todos()` — read/write todos table in SQLite (.pm.db)
- `load_features()` / `save_features()` — read/write features table in SQLite (.pm.db)
- `_ensure_db()` — lazy init: creates tables on first access, auto-migrates JSON files
- `ROOT` — walks up to find `.git` directory, anchors DB path there
- `fmt_item_line()` / `fmt_feature_line()` — ANSI-colored formatted output
- All formatting pads text before applying ANSI codes for correct column alignment
- Array fields (tags, blocked_by, blocks, notes, requires, required_by) stored as JSON text in SQLite columns

## How to test

```bash
python -m pytest test_pm.py -v
```

## Conventions

- Single-file architecture — keep everything in pm.py unless it gets unwieldy
- ANSI colors via the `C` dict and `color()` helper
- Status values: features use `planned|in-progress|partial|implemented`, todos use `open|in-progress|resolved|wontfix`
- Priority values: `critical|high|medium|low`
- IDs: features use string IDs, todos use auto-incrementing integers

## Do not

- Break existing CLI behavior — all commands must continue to work
- Add heavy dependencies — stdlib + textual only
- Change JSON schema without migration support

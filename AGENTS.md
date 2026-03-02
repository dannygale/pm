# AGENTS.md

## Project overview

pm is a lightweight CLI project management tool that tracks features (FEATURES.json) and tasks (TODO.json). It provides list, show, edit, and relationship management (blocking, dependencies) for both. It also has an autopilot mode that runs an AI agent in a loop until all work is done.

## Key files

```
pm/
├── pm.py                # All CLI logic: todo, feature, autopilot, dashboard
├── pm_tui.py            # Interactive TUI (textual-based)
├── autopilot-prompt.md  # Default prompt for pm autopilot
├── pyproject.toml       # Package config, entry point: pm = pm:main
├── FEATURES.json        # Feature tracking (this project's own features)
├── TODO.json            # Task tracking (created when tasks are added)
└── CHANGELOG.md         # Version history
```

## Architecture

pm.py is a single-file CLI using argparse. Key patterns:
- `load_todos()` / `save_todos()` — read/write TODO.json
- `load_features()` / `save_features()` — read/write FEATURES.json
- `ROOT` — walks up to find `.git` directory, anchors JSON file paths there
- `fmt_item_line()` / `fmt_feature_line()` — ANSI-colored formatted output
- All formatting pads text before applying ANSI codes for correct column alignment

## How to test

```bash
# pm has no test suite yet — verify manually:
pm feature list
pm todo list
pm autopilot --max-iterations 1 --agent echo  # dry run
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

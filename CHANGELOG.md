# Changelog

## v0.2.0

### Added
- `pm autopilot` subcommand — runs an AI agent in a loop until all features are implemented and all tasks are resolved
  - `--agent` flag to override the default CLI (kiro-cli)
  - `--prompt` flag to use a custom prompt file
  - `--max-iterations` flag (default 50)
  - Injects AGENTS.md, README.md, feature list, and todo list into each prompt
- Default autopilot prompt in `autopilot-prompt.md` with pm workflow instructions and feature branch guidance
- Priority field on features: `pm feature edit <id> --priority critical|high|medium|low`
- Priority column in `pm feature list` with color coding
- Priority filter: `pm feature list --priority high`
- Requires (dependency) column in `pm feature list`
- Blocked-by column in `pm todo list`
- Column headers in both `pm feature list` and `pm todo list`

### Fixed
- Column alignment in feature and todo lists — text padded before ANSI coloring
- Fixed-width todo IDs for consistent alignment

## v0.1.0

### Added
- `pm todo` — add, list, show, edit, resolve, reopen, block, unblock, tree, note
- `pm feature` — list, show, edit
- `pm tui` — interactive terminal UI
- Dashboard view (default when no subcommand)
- Color-coded status and priority
- Blocking/dependency relationships for todos
- Feature-to-todo linking
- Hide resolved/wontfix items by default

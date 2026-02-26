# pm

Lightweight project management CLI that operates on two JSON files at your repo root:

- `TODO.json` — bugs, tasks, and work items with blocking relationships and parent/child hierarchy
- `FEATURES.json` — feature roadmap with dependency tracking

## Install

```bash
pip install -e .
```

## Usage

```bash
pm                                        # project dashboard
pm todo list --status open --type bug     # filter items
pm todo add --type bug --title "..." --priority high --feature gui
pm todo show 1                            # full details + children + blocks
pm todo resolve 1                         # reports newly unblocked items
pm todo block 24 1                        # #24 blocked by #1 (sets both sides)
pm todo tree                              # parent/child hierarchy
pm feature list --status planned
pm feature show gui                       # cross-references linked TODOs
```

## TODO.json schema

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Unique integer, monotonically increasing |
| `type` | yes | `bug`, `feature`, `task`, or `todo` |
| `status` | yes | `open`, `in-progress`, `resolved`, or `wontfix` |
| `priority` | yes | `critical`, `high`, `medium`, or `low` |
| `title` | yes | Short summary |
| `description` | yes | Full details |
| `package` | no | Which package/module this relates to |
| `file` | no | Specific file path |
| `created` | yes | Date in `YYYY-MM-DD` format |
| `tags` | no | Array of string labels |
| `feature` | no | FEATURES.json `id` this item supports |
| `parent` | no | Parent item `id` for hierarchical grouping |
| `blocked_by` | no | Array of item `id`s that must be resolved first |
| `blocks` | no | Array of item `id`s that this item is blocking |

## FEATURES.json schema

Each feature has: `id` (string), `category`, `title`, `description`, `status` (planned/partial/in-progress/implemented), `package`, `requires` (list of feature ids), `required_by` (list of feature ids).

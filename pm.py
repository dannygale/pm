#!/usr/bin/env python3
"""pm: Lightweight project management CLI for TODO.json and FEATURES.json."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path.cwd()
_p = ROOT
while _p != _p.parent:
    if (_p / ".git").exists():
        ROOT = _p
        break
    _p = _p.parent
TODO_PATH = ROOT / "TODO.json"
FEATURES_PATH = ROOT / "FEATURES.json"

# ── Palette (ANSI) ──────────────────────────────────────────────────────
C = {
    "r": "\033[0m", "b": "\033[1m", "dim": "\033[2m",
    "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
    "blue": "\033[34m", "magenta": "\033[35m", "cyan": "\033[36m",
}

STATUS_COLOR = {
    "open": "red", "in-progress": "yellow", "resolved": "green", "wontfix": "dim",
    "implemented": "green", "partial": "yellow", "planned": "red",
}
PRIORITY_COLOR = {"critical": "red", "high": "yellow", "medium": "cyan", "low": "dim"}
TYPE_SYMBOL = {"bug": "🐛", "feature": "✦", "task": "⚙", "todo": "☐"}


def color(text, name):
    return f"{C.get(name, '')}{text}{C['r']}"


# ── I/O ─────────────────────────────────────────────────────────────────
def load_todos():
    if not TODO_PATH.exists():
        return []
    return json.loads(TODO_PATH.read_text()).get("items", [])


def save_todos(items):
    TODO_PATH.write_text(json.dumps({"items": items}, indent=2) + "\n")


def load_features():
    if not FEATURES_PATH.exists():
        return []
    data = json.loads(FEATURES_PATH.read_text())
    return data.get("features", [])


def save_features(features):
    # Preserve existing file structure, only update features list
    data = {}
    if FEATURES_PATH.exists():
        data = json.loads(FEATURES_PATH.read_text())
    data["features"] = features
    FEATURES_PATH.write_text(json.dumps(data, indent=2) + "\n")


def next_id(items):
    return max((i["id"] for i in items), default=0) + 1


# ── Formatters ──────────────────────────────────────────────────────────
def fmt_status(s):
    return color(s, STATUS_COLOR.get(s, "r"))


def fmt_priority(p):
    return color(p, PRIORITY_COLOR.get(p, "r"))


def fmt_item_line(item):
    sym = TYPE_SYMBOL.get(item.get("type", ""), " ")
    sid = color(f"#{item['id']:>3}", "b")
    status = fmt_status(item["status"])
    pri = fmt_priority(item.get("priority", ""))
    title = item["title"]
    pkg = color(f"[{item['package']}]", "dim") if item.get("package") else ""
    feat = color(f"({item['feature']})", "magenta") if item.get("feature") else ""
    return f"  {sym} {sid}  {status:<22} {pri:<20} {title} {pkg} {feat}"


def fmt_feature_line(f):
    sid = color(f["id"], "b")
    status = fmt_status(f["status"])
    title = f["title"]
    pkg = color(f"[{f.get('package', '')}]", "dim")
    return f"  {sid:<28} {status:<22} {title} {pkg}"


# ── TODO commands ───────────────────────────────────────────────────────
def todo_list(args):
    items = load_todos()
    hide_closed = not args.status and not getattr(args, 'all', False)
    for item in items:
        if hide_closed and item["status"] in ("resolved", "wontfix"):
            continue
        if args.status and item["status"] != args.status:
            continue
        if args.type and item.get("type") != args.type:
            continue
        if args.priority and item.get("priority") != args.priority:
            continue
        if args.feature and item.get("feature") != args.feature:
            continue
        if args.tag and args.tag not in item.get("tags", []):
            continue
        if args.parent is not None:
            if args.parent == 0 and item.get("parent") is not None:
                continue
            if args.parent != 0 and item.get("parent") != args.parent:
                continue
        print(fmt_item_line(item))


def todo_add(args):
    items = load_todos()
    item = {
        "id": next_id(items),
        "type": args.type,
        "status": "open",
        "priority": args.priority,
        "title": args.title,
        "description": args.description or args.title,
        "created": date.today().isoformat(),
    }
    if args.package:
        item["package"] = args.package
    if args.feature:
        item["feature"] = args.feature
    if args.tags:
        item["tags"] = args.tags
    if args.parent:
        item["parent"] = args.parent
    if args.blocked_by:
        item["blocked_by"] = args.blocked_by
        for other in items:
            if other["id"] in args.blocked_by:
                other.setdefault("blocks", [])
                if item["id"] not in other["blocks"]:
                    other["blocks"].append(item["id"])
    items.append(item)
    save_todos(items)
    print(f"Created #{item['id']}: {item['title']}")


def todo_show(args):
    items = load_todos()
    item = next((i for i in items if i["id"] == args.id), None)
    if not item:
        print(f"Item #{args.id} not found", file=sys.stderr)
        return 1
    print(f"{color('ID:', 'b')}          #{item['id']}")
    print(f"{color('Type:', 'b')}        {item.get('type', '')}")
    print(f"{color('Status:', 'b')}      {fmt_status(item['status'])}")
    print(f"{color('Priority:', 'b')}    {fmt_priority(item.get('priority', ''))}")
    print(f"{color('Title:', 'b')}       {item['title']}")
    if item.get("description") and item["description"] != item["title"]:
        print(f"{color('Description:', 'b')} {item['description']}")
    if item.get("package"):
        print(f"{color('Package:', 'b')}     {item['package']}")
    if item.get("feature"):
        print(f"{color('Feature:', 'b')}     {item['feature']}")
    if item.get("file"):
        print(f"{color('File:', 'b')}        {item['file']}")
    if item.get("tags"):
        print(f"{color('Tags:', 'b')}        {', '.join(item['tags'])}")
    if item.get("parent"):
        parent = next((i for i in items if i["id"] == item["parent"]), None)
        label = f"#{item['parent']} ({parent['title']})" if parent else f"#{item['parent']}"
        print(f"{color('Parent:', 'b')}      {label}")
    children = [i for i in items if i.get("parent") == item["id"]]
    if children:
        print(f"{color('Children:', 'b')}")
        for c in children:
            print(f"  #{c['id']} {c['title']}")
    if item.get("blocked_by"):
        print(f"{color('Blocked by:', 'b')}")
        for bid in item["blocked_by"]:
            b = next((i for i in items if i["id"] == bid), None)
            label = f"#{bid} ({b['title']})" if b else f"#{bid}"
            print(f"  {label}")
    if item.get("blocks"):
        print(f"{color('Blocks:', 'b')}")
        for bid in item["blocks"]:
            b = next((i for i in items if i["id"] == bid), None)
            label = f"#{bid} ({b['title']})" if b else f"#{bid}"
            print(f"  {label}")
    print(f"{color('Created:', 'b')}     {item.get('created', '')}")


def todo_edit(args):
    items = load_todos()
    item = next((i for i in items if i["id"] == args.id), None)
    if not item:
        print(f"Item #{args.id} not found", file=sys.stderr)
        return 1
    changed = []
    for field in ("status", "priority", "title", "description", "package", "feature", "parent"):
        val = getattr(args, field, None)
        if val is not None:
            item[field] = val
            changed.append(field)
    if args.add_tag:
        item.setdefault("tags", [])
        for t in args.add_tag:
            if t not in item["tags"]:
                item["tags"].append(t)
                changed.append(f"+tag:{t}")
    save_todos(items)
    print(f"Updated #{args.id}: {', '.join(changed)}")


def todo_resolve(args):
    items = load_todos()
    item = next((i for i in items if i["id"] == args.id), None)
    if not item:
        print(f"Item #{args.id} not found", file=sys.stderr)
        return 1
    item["status"] = "resolved"
    save_todos(items)
    print(f"Resolved #{args.id}: {item['title']}")
    if item.get("blocks"):
        for bid in item["blocks"]:
            b = next((i for i in items if i["id"] == bid), None)
            if b and b["status"] == "open":
                still_blocked = [x for x in b.get("blocked_by", []) if x != args.id
                                 and next((i for i in items if i["id"] == x), {}).get("status") != "resolved"]
                if not still_blocked:
                    print(f"  → #{bid} ({b['title']}) is now unblocked")
                else:
                    print(f"  → #{bid} still blocked by {still_blocked}")


def todo_reopen(args):
    items = load_todos()
    item = next((i for i in items if i["id"] == args.id), None)
    if not item:
        print(f"Item #{args.id} not found", file=sys.stderr)
        return 1
    item["status"] = "open"
    save_todos(items)
    print(f"Reopened #{args.id}: {item['title']}")


def todo_block(args):
    items = load_todos()
    item = next((i for i in items if i["id"] == args.id), None)
    blocker = next((i for i in items if i["id"] == args.blocker_id), None)
    if not item:
        print(f"Item #{args.id} not found", file=sys.stderr)
        return 1
    if not blocker:
        print(f"Item #{args.blocker_id} not found", file=sys.stderr)
        return 1
    item.setdefault("blocked_by", [])
    if args.blocker_id not in item["blocked_by"]:
        item["blocked_by"].append(args.blocker_id)
    blocker.setdefault("blocks", [])
    if args.id not in blocker["blocks"]:
        blocker["blocks"].append(args.id)
    save_todos(items)
    print(f"#{args.id} is now blocked by #{args.blocker_id}")


def todo_unblock(args):
    items = load_todos()
    item = next((i for i in items if i["id"] == args.id), None)
    blocker = next((i for i in items if i["id"] == args.blocker_id), None)
    if not item:
        print(f"Item #{args.id} not found", file=sys.stderr)
        return 1
    if "blocked_by" in item and args.blocker_id in item["blocked_by"]:
        item["blocked_by"].remove(args.blocker_id)
    if blocker and "blocks" in blocker and args.id in blocker["blocks"]:
        blocker["blocks"].remove(args.id)
    save_todos(items)
    print(f"#{args.id} is no longer blocked by #{args.blocker_id}")


def todo_tree(args):
    items = load_todos()
    by_id = {i["id"]: i for i in items}
    children_of = {}
    roots = []
    for item in items:
        pid = item.get("parent")
        if pid and pid in by_id:
            children_of.setdefault(pid, []).append(item)
        else:
            roots.append(item)

    hide_closed = not args.status and not getattr(args, 'all', False)

    def print_tree(item, indent=0):
        if hide_closed and item["status"] in ("resolved", "wontfix"):
            return
        if args.status and item["status"] != args.status:
            return
        prefix = "  " * indent
        sym = TYPE_SYMBOL.get(item.get("type", ""), " ")
        sid = color(f"#{item['id']}", "b")
        status = fmt_status(item["status"])
        print(f"{prefix}{sym} {sid} {status} {item['title']}")
        for child in children_of.get(item["id"], []):
            print_tree(child, indent + 1)

    if args.root:
        root = by_id.get(args.root)
        if root:
            print_tree(root)
        else:
            print(f"Item #{args.root} not found", file=sys.stderr)
    else:
        for r in roots:
            print_tree(r)


# ── FEATURE commands ────────────────────────────────────────────────────
def feature_list(args):
    features = load_features()
    for f in features:
        if args.status and f["status"] != args.status:
            continue
        if args.category and f.get("category", "").lower() != args.category.lower():
            continue
        print(fmt_feature_line(f))


def feature_show(args):
    features = load_features()
    f = next((x for x in features if x["id"] == args.id), None)
    if not f:
        print(f"Feature '{args.id}' not found", file=sys.stderr)
        return 1
    print(f"{color('ID:', 'b')}          {f['id']}")
    print(f"{color('Category:', 'b')}    {f.get('category', '')}")
    print(f"{color('Status:', 'b')}      {fmt_status(f['status'])}")
    print(f"{color('Title:', 'b')}       {f['title']}")
    print(f"{color('Description:', 'b')} {f['description']}")
    if f.get("package"):
        print(f"{color('Package:', 'b')}     {f['package']}")
    if f.get("requires"):
        print(f"{color('Requires:', 'b')}    {', '.join(f['requires'])}")
    if f.get("required_by"):
        print(f"{color('Required by:', 'b')} {', '.join(f['required_by'])}")
    todos = load_todos()
    linked = [i for i in todos if i.get("feature") == f["id"]]
    if linked:
        print(f"{color('TODO items:', 'b')}")
        for item in linked:
            print(f"  {fmt_item_line(item)}")


def feature_edit(args):
    features = load_features()
    f = next((x for x in features if x["id"] == args.id), None)
    if not f:
        print(f"Feature '{args.id}' not found", file=sys.stderr)
        return 1
    changed = []
    for field in ("status", "title", "description", "package", "category"):
        val = getattr(args, field, None)
        if val is not None:
            f[field] = val
            changed.append(field)
    save_features(features)
    print(f"Updated {args.id}: {', '.join(changed)}")


# ── Dashboard ───────────────────────────────────────────────────────────
def dashboard():
    items = load_todos()
    features = load_features()
    work = [i for i in items if i.get("type") != "feature"]

    project = ROOT.name
    print(color(f"── {project} ──", "b"))

    # ── Features ──
    if features:
        feat_by_status = {}
        for f in features:
            feat_by_status.setdefault(f["status"], []).append(f)
        planned = feat_by_status.get("planned", [])
        partial = feat_by_status.get("partial", []) + feat_by_status.get("in-progress", [])
        implemented = feat_by_status.get("implemented", [])

        print(f"\n  {color('Features:', 'b')}  {color(len(planned), 'red')} planned  "
              f"{color(len(partial), 'yellow')} in-progress  "
              f"{color(len(implemented), 'green')} implemented  "
              f"{color(len(features), 'dim')} total")
        if partial:
            for f in partial:
                print(f"    {fmt_feature_line(f)}")

    # ── TODOs ──
    work_by_status = {}
    for i in work:
        work_by_status.setdefault(i["status"], []).append(i)
    w_open = work_by_status.get("open", [])
    w_prog = work_by_status.get("in-progress", [])
    w_done = work_by_status.get("resolved", [])

    print(f"\n  {color('TODO:', 'b')}      {color(len(w_open), 'red')} open  "
          f"{color(len(w_prog), 'yellow')} in-progress  "
          f"{color(len(w_done), 'green')} resolved  "
          f"{color(len(work), 'dim')} total")

    bugs = [i for i in w_open if i.get("type") == "bug"]
    if bugs:
        print(f"\n    {color('Bugs:', 'red')}")
        for b in bugs:
            print(f"  {fmt_item_line(b)}")

    if w_prog:
        print(f"\n    {color('In progress:', 'yellow')}")
        for i in w_prog:
            print(f"  {fmt_item_line(i)}")

    non_bug_open = [i for i in w_open if i.get("type") != "bug"]
    ready = [i for i in non_bug_open if not any(
        next((x for x in items if x["id"] == bid), {}).get("status") not in ("resolved", "wontfix")
        for bid in i.get("blocked_by", [])
    )]
    blocked = [i for i in non_bug_open if i not in ready]
    if ready:
        print(f"\n    {color('Ready:', 'green')}")
        for i in ready:
            print(f"  {fmt_item_line(i)}")
    if blocked:
        print(f"\n    {color('Blocked:', 'dim')}")
        for i in blocked:
            blockers = [f"#{bid}" for bid in i.get("blocked_by", [])
                        if next((x for x in items if x["id"] == bid), {}).get("status") not in ("resolved", "wontfix")]
            print(f"  {fmt_item_line(i)}  ← {', '.join(blockers)}")
    print()


# ── CLI ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(prog="pm", description="Lightweight project management for TODO.json and FEATURES.json")
    sub = parser.add_subparsers(dest="domain")

    # -- todo --
    todo = sub.add_parser("todo", help="Manage TODO items")
    todo_sub = todo.add_subparsers(dest="cmd")

    ls = todo_sub.add_parser("list", help="List items")
    ls.add_argument("--status", choices=["open", "in-progress", "resolved", "wontfix"])
    ls.add_argument("--type", choices=["bug", "feature", "task", "todo"])
    ls.add_argument("--priority", choices=["critical", "high", "medium", "low"])
    ls.add_argument("--feature")
    ls.add_argument("--tag")
    ls.add_argument("--parent", type=int, help="Filter by parent ID (0 = root items only)")
    ls.add_argument("--all", action="store_true", help="Include resolved/wontfix items")
    ls.set_defaults(func=todo_list)

    add = todo_sub.add_parser("add", help="Add item")
    add.add_argument("--type", required=True, choices=["bug", "feature", "task", "todo"])
    add.add_argument("--title", required=True)
    add.add_argument("--priority", default="medium", choices=["critical", "high", "medium", "low"])
    add.add_argument("--description")
    add.add_argument("--package")
    add.add_argument("--feature")
    add.add_argument("--tags", nargs="+")
    add.add_argument("--parent", type=int)
    add.add_argument("--blocked-by", dest="blocked_by", type=int, nargs="+")
    add.set_defaults(func=todo_add)

    show = todo_sub.add_parser("show", help="Show item details")
    show.add_argument("id", type=int)
    show.set_defaults(func=todo_show)

    edit = todo_sub.add_parser("edit", help="Edit item")
    edit.add_argument("id", type=int)
    edit.add_argument("--status", choices=["open", "in-progress", "resolved", "wontfix"])
    edit.add_argument("--priority", choices=["critical", "high", "medium", "low"])
    edit.add_argument("--title")
    edit.add_argument("--description")
    edit.add_argument("--package")
    edit.add_argument("--feature")
    edit.add_argument("--parent", type=int)
    edit.add_argument("--add-tag", nargs="+")
    edit.set_defaults(func=todo_edit)

    resolve = todo_sub.add_parser("resolve", help="Mark item resolved")
    resolve.add_argument("id", type=int)
    resolve.set_defaults(func=todo_resolve)

    reopen = todo_sub.add_parser("reopen", help="Reopen item")
    reopen.add_argument("id", type=int)
    reopen.set_defaults(func=todo_reopen)

    block = todo_sub.add_parser("block", help="Add blocking relationship")
    block.add_argument("id", type=int, help="Item that is blocked")
    block.add_argument("blocker_id", type=int, help="Item that blocks it")
    block.set_defaults(func=todo_block)

    unblock = todo_sub.add_parser("unblock", help="Remove blocking relationship")
    unblock.add_argument("id", type=int)
    unblock.add_argument("blocker_id", type=int)
    unblock.set_defaults(func=todo_unblock)

    tree = todo_sub.add_parser("tree", help="Show parent/child hierarchy")
    tree.add_argument("--root", type=int, help="Start from this item")
    tree.add_argument("--status", choices=["open", "in-progress", "resolved", "wontfix"])
    tree.add_argument("--all", action="store_true", help="Include resolved/wontfix items")
    tree.set_defaults(func=todo_tree)

    # -- feature --
    feat = sub.add_parser("feature", help="Manage features")
    feat_sub = feat.add_subparsers(dest="cmd")

    fls = feat_sub.add_parser("list", help="List features")
    fls.add_argument("--status", choices=["implemented", "partial", "planned", "in-progress"])
    fls.add_argument("--category")
    fls.set_defaults(func=feature_list)

    fshow = feat_sub.add_parser("show", help="Show feature details")
    fshow.add_argument("id")
    fshow.set_defaults(func=feature_show)

    fedit = feat_sub.add_parser("edit", help="Edit feature")
    fedit.add_argument("id")
    fedit.add_argument("--status", choices=["implemented", "partial", "planned", "in-progress"])
    fedit.add_argument("--title")
    fedit.add_argument("--description")
    fedit.add_argument("--package")
    fedit.add_argument("--category")
    fedit.set_defaults(func=feature_edit)

    args = parser.parse_args()
    if not args.domain:
        dashboard()
        return
    if not args.cmd:
        sub.choices[args.domain].print_help()
        return
    result = args.func(args)
    sys.exit(result or 0)


if __name__ == "__main__":
    main()

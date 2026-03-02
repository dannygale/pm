"""pm TUI: Textual-based terminal UI for project management."""

from datetime import date
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, Grid
from textual.screen import ModalScreen
from textual.widgets import (
    Header, Footer, Static, DataTable, Tree, TabbedContent, TabPane,
    Input, Select, Label, Button,
)

from pm import load_todos, load_features, save_todos, next_id, ROOT

# ── Helpers ──────────────────────────────────────────────────────────────

STATUS_STYLES = {
    "open": "bold red", "in-progress": "bold yellow",
    "resolved": "green", "wontfix": "dim",
    "implemented": "green", "partial": "yellow", "planned": "red",
}
PRIORITY_STYLES = {
    "critical": "bold red", "high": "yellow", "medium": "cyan", "low": "dim",
}
TYPE_SYMBOL = {"bug": "🐛", "feature": "✦", "task": "⚙", "todo": "☐"}

CLOSED = ("resolved", "wontfix")


def styled(text, style):
    return f"[{style}]{text}[/]"


def status_cell(s):
    return styled(s, STATUS_STYLES.get(s, ""))


def priority_cell(p):
    return styled(p, PRIORITY_STYLES.get(p, ""))


# ── Detail Screen ────────────────────────────────────────────────────────

class DetailScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", "Close")]
    DEFAULT_CSS = """
    DetailScreen { align: center middle; }
    #detail-box {
        width: 80; max-height: 80%; padding: 1 2;
        border: thick $accent; background: $surface;
    }
    """

    def __init__(self, item: dict):
        super().__init__()
        self.item = item

    def compose(self) -> ComposeResult:
        i = self.item
        sym = TYPE_SYMBOL.get(i.get("type", ""), " ")
        lines = [
            f"[bold]{sym} #{i['id']}  {i['title']}[/]",
            "",
            f"  Type: {i.get('type', '?')}    Status: {status_cell(i['status'])}    Priority: {priority_cell(i.get('priority', '?'))}",
            f"  Created: {i.get('created', '?')}    Feature: {i.get('feature', '—')}    Package: {i.get('package', '—')}",
        ]
        if i.get("description"):
            lines += ["", f"  {i['description']}"]
        if i.get("tags"):
            lines += ["", f"  Tags: {', '.join(i['tags'])}"]
        if i.get("blocked_by"):
            lines += [f"  Blocked by: {', '.join(f'#{b}' for b in i['blocked_by'])}"]
        if i.get("blocks"):
            lines += [f"  Blocks: {', '.join(f'#{b}' for b in i['blocks'])}"]
        if i.get("file"):
            lines += [f"  File: {i['file']}"]
        yield Vertical(Static("\n".join(lines)), id="detail-box")


# ── Add Screen ───────────────────────────────────────────────────────────

class AddScreen(ModalScreen[dict | None]):
    BINDINGS = [Binding("escape", "dismiss", "Cancel")]
    DEFAULT_CSS = """
    AddScreen { align: center middle; }
    #add-box {
        width: 70; height: auto; padding: 1 2;
        border: thick $accent; background: $surface;
    }
    #add-box Label { margin-top: 1; }
    #add-buttons { margin-top: 1; height: 3; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="add-box"):
            yield Static("[bold]Add TODO Item[/]")
            yield Label("Title")
            yield Input(id="title", placeholder="Short summary")
            yield Label("Type")
            yield Select(
                [(t, t) for t in ("bug", "task", "todo", "feature")],
                value="task", id="type",
            )
            yield Label("Priority")
            yield Select(
                [(p, p) for p in ("critical", "high", "medium", "low")],
                value="medium", id="priority",
            )
            yield Label("Description (optional)")
            yield Input(id="description", placeholder="Details")
            yield Label("Feature ID (optional)")
            yield Input(id="feature", placeholder="e.g. gui")
            with Horizontal(id="add-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "save":
            title = self.query_one("#title", Input).value.strip()
            if not title:
                self.notify("Title is required", severity="error")
                return
            self.dismiss({
                "type": self.query_one("#type", Select).value,
                "title": title,
                "priority": self.query_one("#priority", Select).value,
                "description": self.query_one("#description", Input).value.strip(),
                "feature": self.query_one("#feature", Input).value.strip() or None,
            })


# ── Main App ─────────────────────────────────────────────────────────────

class PmApp(App):
    TITLE = f"pm — {ROOT.name}"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "resolve", "Resolve", show=True),
        Binding("o", "reopen", "Reopen", show=True),
        Binding("a", "add", "Add", show=True),
        Binding("d", "detail", "Detail", show=True),
        Binding("A", "show_all", "Show all", show=True),
    ]
    CSS = """
    #dashboard { padding: 1 2; }
    DataTable { height: 1fr; }
    """

    show_closed = False

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent("Dashboard", "Todos", "Tree", "Features"):
            yield TabPane("Dashboard", Static(id="dash-content"), id="tab-dash")
            yield TabPane("Todos", DataTable(id="todo-table"), id="tab-todos")
            yield TabPane("Tree", Tree("Items", id="todo-tree"), id="tab-tree")
            yield TabPane("Features", DataTable(id="feat-table"), id="tab-feat")
        yield Footer()

    def on_mount(self):
        self._setup_todo_table()
        self._setup_feat_table()
        self.refresh_data()

    # ── Data loading ─────────────────────────────────────────────────

    def refresh_data(self):
        self._items = load_todos()
        self._features = load_features()
        self._by_id = {i["id"]: i for i in self._items}
        self._refresh_dashboard()
        self._refresh_todo_table()
        self._refresh_tree()
        self._refresh_feat_table()

    def _visible_items(self):
        if self.show_closed:
            return self._items
        return [i for i in self._items if i["status"] not in CLOSED]

    # ── Dashboard ────────────────────────────────────────────────────

    def _refresh_dashboard(self):
        items = self._items
        features = self._features
        work = [i for i in items if i.get("type") != "feature"]

        w_open = [i for i in work if i["status"] == "open"]
        w_prog = [i for i in work if i["status"] == "in-progress"]
        w_done = [i for i in work if i["status"] == "resolved"]
        bugs = [i for i in w_open if i.get("type") == "bug"]

        f_planned = [f for f in features if f["status"] == "planned"]
        f_prog = [f for f in features if f["status"] in ("partial", "in-progress")]
        f_done = [f for f in features if f["status"] == "implemented"]

        lines = [
            f"[bold]── {ROOT.name} ──[/]", "",
            f"  [bold]Features:[/]  [red]{len(f_planned)}[/] planned  "
            f"[yellow]{len(f_prog)}[/] in-progress  "
            f"[green]{len(f_done)}[/] implemented  "
            f"[dim]{len(features)}[/] total",
            "",
            f"  [bold]TODO:[/]      [red]{len(w_open)}[/] open  "
            f"[yellow]{len(w_prog)}[/] in-progress  "
            f"[green]{len(w_done)}[/] resolved  "
            f"[dim]{len(work)}[/] total",
        ]
        if bugs:
            lines += ["", "  [bold red]Bugs:[/]"]
            for b in bugs:
                lines.append(f"    🐛 #{b['id']}  {b['title']}")
        if w_prog:
            lines += ["", "  [bold yellow]In progress:[/]"]
            for i in w_prog:
                sym = TYPE_SYMBOL.get(i.get("type", ""), " ")
                lines.append(f"    {sym} #{i['id']}  {i['title']}")

        self.query_one("#dash-content", Static).update("\n".join(lines))

    # ── Todo table ───────────────────────────────────────────────────

    def _setup_todo_table(self):
        t = self.query_one("#todo-table", DataTable)
        t.cursor_type = "row"
        t.add_columns("ID", "Type", "Status", "Priority", "Title", "Feature")

    def _refresh_todo_table(self):
        t = self.query_one("#todo-table", DataTable)
        t.clear()
        for i in self._visible_items():
            sym = TYPE_SYMBOL.get(i.get("type", ""), " ")
            t.add_row(
                str(i["id"]), f"{sym} {i.get('type', '?')}",
                status_cell(i["status"]), priority_cell(i.get("priority", "?")),
                i["title"], i.get("feature", "—"),
                key=str(i["id"]),
            )

    # ── Tree ─────────────────────────────────────────────────────────

    def _refresh_tree(self):
        tree = self.query_one("#todo-tree", Tree)
        tree.clear()
        children_of = {}
        roots = []
        visible = set(i["id"] for i in self._visible_items())
        for i in self._items:
            if i["id"] not in visible:
                continue
            pid = i.get("parent")
            if pid and pid in self._by_id and pid in visible:
                children_of.setdefault(pid, []).append(i)
            else:
                roots.append(i)

        def add_nodes(parent_node, items):
            for i in items:
                sym = TYPE_SYMBOL.get(i.get("type", ""), " ")
                label = f"{sym} #{i['id']}  {status_cell(i['status'])}  {i['title']}"
                node = parent_node.add(label, data=i["id"])
                add_nodes(node, children_of.get(i["id"], []))

        add_nodes(tree.root, roots)
        tree.root.expand_all()

    # ── Features table ───────────────────────────────────────────────

    def _setup_feat_table(self):
        t = self.query_one("#feat-table", DataTable)
        t.cursor_type = "row"
        t.add_columns("ID", "Status", "Category", "Title")

    def _refresh_feat_table(self):
        t = self.query_one("#feat-table", DataTable)
        t.clear()
        for f in self._features:
            t.add_row(
                f["id"], status_cell(f["status"]),
                f.get("category", "—"), f["title"],
                key=f["id"],
            )

    # ── Selected item helper ─────────────────────────────────────────

    def _selected_item_id(self) -> int | None:
        t = self.query_one("#todo-table", DataTable)
        if t.row_count == 0:
            return None
        row_key, _ = t.coordinate_to_cell_key(t.cursor_coordinate)
        return int(row_key.value)

    # ── Actions ──────────────────────────────────────────────────────

    def action_resolve(self):
        iid = self._selected_item_id()
        if iid is None:
            return
        item = self._by_id.get(iid)
        if not item or item["status"] in CLOSED:
            return
        item["status"] = "resolved"
        save_todos(self._items)
        self.refresh_data()
        self.notify(f"#{iid} resolved")

    def action_reopen(self):
        iid = self._selected_item_id()
        if iid is None:
            return
        item = self._by_id.get(iid)
        if not item or item["status"] not in CLOSED:
            return
        item["status"] = "open"
        save_todos(self._items)
        self.refresh_data()
        self.notify(f"#{iid} reopened")

    def action_detail(self):
        iid = self._selected_item_id()
        if iid is None:
            return
        item = self._by_id.get(iid)
        if item:
            self.push_screen(DetailScreen(item))

    def action_add(self):
        def on_result(result: dict | None):
            if result is None:
                return
            items = load_todos()
            items.append({
                "id": next_id(items),
                "type": result["type"],
                "status": "open",
                "priority": result["priority"],
                "title": result["title"],
                "description": result.get("description", ""),
                "created": str(date.today()),
                **({"feature": result["feature"]} if result.get("feature") else {}),
            })
            save_todos(items)
            self.refresh_data()
            self.notify(f"Added: {result['title']}")

        self.push_screen(AddScreen(), callback=on_result)

    def action_show_all(self):
        self.show_closed = not self.show_closed
        self._refresh_todo_table()
        self._refresh_tree()
        label = "all" if self.show_closed else "open"
        self.notify(f"Showing {label} items")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        iid = int(event.row_key.value)
        item = self._by_id.get(iid)
        if item:
            self.push_screen(DetailScreen(item))


def run():
    PmApp().run()

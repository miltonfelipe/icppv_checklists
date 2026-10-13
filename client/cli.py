from typing import Optional

import requests
import typer
from rich import box
from rich.console import Console
from rich.table import Table

from .api import ChecklistClient

app = typer.Typer(help="ICPPV Checklists — command-line client")
console = Console()


def _client(url: Optional[str]) -> ChecklistClient:
    return ChecklistClient(base_url=url)


def _item_table(items: list[dict]) -> Table:
    table = Table(box=box.SIMPLE_HEAD, show_lines=False)
    for col in ("id", "type", "group", "description", "active", "activated", "time"):
        table.add_column(col, overflow="fold")
    for item in items:
        table.add_row(
            str(item.get("id", "")),
            item.get("type", ""),
            item.get("group", ""),
            item.get("description", ""),
            str(item.get("active", "")),
            str(item.get("activated", "")),
            str(item.get("time") or ""),
        )
    return table


def _abort(exc: requests.HTTPError) -> None:
    try:
        detail = exc.response.json().get("detail", exc.response.text)
    except Exception:
        detail = str(exc)
    console.print(f"[red]Error {exc.response.status_code}:[/red] {detail}")
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@app.command("list")
def list_items(
    url: Optional[str] = typer.Option(None, "--url", "-u", envvar="ICPPV_SERVER_URL", help="Server base URL"),
    type: Optional[str] = typer.Option(None, help="Filter by type"),
    group: Optional[str] = typer.Option(None, help="Filter by group"),
    active: Optional[bool] = typer.Option(None, help="Filter by active flag"),
    activated: Optional[bool] = typer.Option(None, help="Filter by activated flag"),
):
    """List checklist items (with optional filters)."""
    try:
        items = _client(url).list_items(type=type, group=group, active=active, activated=activated)
    except requests.HTTPError as e:
        _abort(e)
    if not items:
        console.print("[yellow]No items found.[/yellow]")
        return
    console.print(_item_table(items))
    console.print(f"[dim]{len(items)} item(s)[/dim]")


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

@app.command("get")
def get_item(
    item_id: int = typer.Argument(..., help="Item ID"),
    url: Optional[str] = typer.Option(None, "--url", "-u", envvar="ICPPV_SERVER_URL"),
):
    """Fetch a single item by ID."""
    try:
        item = _client(url).get_item(item_id)
    except requests.HTTPError as e:
        _abort(e)
    console.print(_item_table([item]))


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

@app.command("create")
def create_item(
    type: str = typer.Option(..., prompt=True, help="Item type"),
    group: str = typer.Option(..., prompt=True, help="Item group"),
    description: str = typer.Option(..., prompt=True, help="Description"),
    active: bool = typer.Option(True, help="Active flag"),
    activated: bool = typer.Option(False, help="Activated flag"),
    time: Optional[str] = typer.Option(None, help="Time of day the task must be performed (HH:MM)"),
    url: Optional[str] = typer.Option(None, "--url", "-u", envvar="ICPPV_SERVER_URL"),
):
    """Create a new checklist item."""
    try:
        item = _client(url).create_item(
            type=type,
            group=group,
            description=description,
            active=active,
            activated=activated,
            time=time,
        )
    except requests.HTTPError as e:
        _abort(e)
    console.print(f"[green]Created item id={item['id']}[/green]")
    console.print(_item_table([item]))


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

@app.command("update")
def update_item(
    item_id: int = typer.Argument(..., help="Item ID to update"),
    type: Optional[str] = typer.Option(None, help="New type"),
    group: Optional[str] = typer.Option(None, help="New group"),
    description: Optional[str] = typer.Option(None, help="New description"),
    active: Optional[bool] = typer.Option(None, help="New active flag"),
    activated: Optional[bool] = typer.Option(None, help="New activated flag"),
    time: Optional[str] = typer.Option(None, help="New time of day (HH:MM)"),
    url: Optional[str] = typer.Option(None, "--url", "-u", envvar="ICPPV_SERVER_URL"),
):
    """Update fields of an existing item (only supplied fields are changed)."""
    fields = {}
    if type is not None:
        fields["type"] = type
    if group is not None:
        fields["group"] = group
    if description is not None:
        fields["description"] = description
    if active is not None:
        fields["active"] = active
    if activated is not None:
        fields["activated"] = activated
    if time is not None:
        fields["time"] = time

    if not fields:
        console.print("[yellow]No fields to update — pass at least one option.[/yellow]")
        raise typer.Exit(1)

    try:
        item = _client(url).update_item(item_id, **fields)
    except requests.HTTPError as e:
        _abort(e)
    console.print(f"[green]Updated item id={item['id']}[/green]")
    console.print(_item_table([item]))


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

@app.command("delete")
def delete_item(
    item_id: int = typer.Argument(..., help="Item ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    url: Optional[str] = typer.Option(None, "--url", "-u", envvar="ICPPV_SERVER_URL"),
):
    """Delete an item by ID."""
    if not yes:
        typer.confirm(f"Delete item {item_id}?", abort=True)
    try:
        _client(url).delete_item(item_id)
    except requests.HTTPError as e:
        _abort(e)
    console.print(f"[green]Deleted item id={item_id}[/green]")


if __name__ == "__main__":
    app()

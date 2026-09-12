"""Compare cost, latency, and error rate across prompt versions."""

import sqlite3
import statistics

import click
from rich.console import Console
from rich.table import Table
from rich import box

from tracer import DB_PATH

console = Console()


def get_versions_for_function(function_name):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT version, cost, latency_ms, status FROM calls WHERE function_name = ?", (function_name,)).fetchall()
    conn.close()
    return rows


@click.command()
@click.option("--function", "function_name", "-f", prompt="Function name to compare")
def main(function_name):
    rows = get_versions_for_function(function_name)
    if not rows:
        console.print(f"\n[red]No calls found for function '{function_name}'.[/red]")
        return
    by_version = {}
    for row in rows:
        key = row["version"] or "(no version tag)"
        bucket = by_version.setdefault(key, {"costs": [], "latencies": [], "total": 0, "errors": 0})
        bucket["total"] += 1
        bucket["errors"] += row["status"] == "error"
        if row["cost"] is not None:
            bucket["costs"].append(row["cost"])
        if row["latency_ms"] is not None:
            bucket["latencies"].append(row["latency_ms"])
    table = Table(box=box.ROUNDED, border_style="dim", title=f"{function_name} - version comparison", title_style="bold purple")
    for column in ("version", "calls", "avg cost", "avg latency", "error rate"):
        table.add_column(column, justify="right" if column != "version" else "left")
    for version, stats in sorted(by_version.items()):
        avg_cost = statistics.mean(stats["costs"]) if stats["costs"] else None
        avg_latency = statistics.mean(stats["latencies"]) if stats["latencies"] else None
        error_rate = stats["errors"] / stats["total"] * 100
        table.add_row(version, str(stats["total"]), f"${avg_cost:.4f}" if avg_cost is not None else "-",
                      f"{avg_latency:.0f}ms" if avg_latency is not None else "-", f"{error_rate:.1f}%")
    console.print(table)
    if len(by_version) < 2:
        console.print("\n[dim]Only one version tagged so far - tag a new version to compare it.[/dim]")


if __name__ == "__main__":
    main()

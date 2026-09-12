"""Display recent GlassBox calls and live anomaly flags."""

import time
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box

from tracer import recent_calls

console = Console()


def build_table():
    rows = recent_calls(limit=15)
    table = Table(box=box.ROUNDED, border_style="dim", title="GlassBox - live", title_style="bold purple")
    for column in ("time", "function", "model", "tokens", "cost", "latency", "status", "flag"):
        table.add_column(column)

    for row in rows:
        time_str = datetime.fromisoformat(row["timestamp"]).strftime("%H:%M:%S")
        tokens = (f"{row['input_tokens'] + row['output_tokens']:,}"
                  if row["input_tokens"] is not None and row["output_tokens"] is not None else "-")
        cost = f"${row['cost']:.4f}" if row["cost"] is not None else "-"
        latency = f"{row['latency_ms']}ms" if row["latency_ms"] is not None else "-"
        if row["is_anomaly"]:
            cost = f"[magenta]{cost}[/magenta]"
            latency = f"[magenta]{latency}[/magenta]"
        elif row["latency_ms"] is not None and row["latency_ms"] > 2000:
            latency = f"[yellow]{latency}[/yellow]"
        status = "[green]ok[/green]" if row["status"] == "ok" else "[red]error[/red]"
        flag = "[magenta]WARNING[/magenta]" if row["is_anomaly"] else ""
        table.add_row(time_str, row["function_name"], row["model"] or "-", tokens, cost, latency, status, flag)

    if not rows:
        table.caption = "No calls logged yet. Wrap a function with @track() and run it."
    return table


def main():
    console.print("\n[purple bold]GlassBox is watching...[/purple bold] [dim](Ctrl+C to stop)[/dim]\n")
    try:
        with Live(build_table(), refresh_per_second=2, console=console) as live:
            while True:
                time.sleep(0.5)
                live.update(build_table())
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped watching.[/dim]\n")


if __name__ == "__main__":
    main()

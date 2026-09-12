"""Display recent Glassbox calls in a live terminal dashboard."""

import time
from datetime import datetime

from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table

from tracer import recent_calls

console = Console()


def build_table():
    table = Table(box=box.ROUNDED, title="Glassbox - live")
    for column in ("time", "function", "model", "tokens", "cost", "latency", "status"):
        table.add_column(column)
    for row in recent_calls(limit=15):
        timestamp, function_name, model, input_tokens, output_tokens, cost, latency, status = row
        tokens = f"{input_tokens + output_tokens:,}" if input_tokens is not None and output_tokens is not None else "-"
        cost_text = f"${cost:.4f}" if cost is not None else "-"
        table.add_row(datetime.fromisoformat(timestamp).strftime("%H:%M:%S"),
                      function_name, model or "-", tokens, cost_text, f"{latency}ms", status)
    return table


if __name__ == "__main__":
    console.print("Glassbox is watching... (Ctrl+C to stop)")
    try:
        with Live(build_table(), refresh_per_second=2, console=console) as live:
            while True:
                time.sleep(0.5)
                live.update(build_table())
    except KeyboardInterrupt:
        console.print("Stopped watching.")
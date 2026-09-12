import os
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))


def main() -> None:
    project_name = os.getenv("APP_NAME", "glassbox")
    env_mode = os.getenv("APP_ENV", "development")

    console.print(
        Panel.fit(
            f"[bold cyan]{project_name}[/bold cyan]\n[green]Environment:[/] [yellow]{env_mode}[/yellow]",
            title="Glassbox",
        )
    )

    table = Table(title="Project status")
    table.add_column("Item")
    table.add_column("Status")
    table.add_row("Python", "Ready")
    table.add_row("Virtual environment", "Ready")
    table.add_row("Dependencies", "Installed")

    console.print(table)


if __name__ == "__main__":
    main()

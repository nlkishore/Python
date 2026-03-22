"""Typer CLI entry point."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from pr_review import __version__
from pr_review.config.loader import load_settings
from pr_review.pipeline import run_pipeline

app = typer.Typer(
    name="pr-review",
    help="Bitbucket Server PR workspace, diff line report, Maven compile, static analyzers.",
    no_args_is_help=True,
)


@app.callback()
def main_callback() -> None:
    pass


@app.command("run")
def cmd_run(
    config: Path = typer.Option(
        Path("config/settings.yaml"),
        "--config",
        "-c",
        help="Path to YAML settings (copy from config/settings.example.yaml).",
    ),
) -> None:
    """Execute full pipeline for the configured Bitbucket PR."""
    console = Console()
    settings = load_settings(config)
    run_pipeline(settings, console=console)


@app.command("version")
def cmd_version() -> None:
    """Print package version."""
    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

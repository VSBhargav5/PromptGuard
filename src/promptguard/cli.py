from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .runner import load_suite, run_suite
from .store import RunStore

app = typer.Typer(
    help="PromptGuard – regression testing for LLM apps",
    no_args_is_help=True,
)
console = Console()


@app.command("run")
def run_cmd(
    suite_path: Path = typer.Argument(..., help="Path to suite YAML/JSON"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override suite model"),
    temperature: Optional[float] = typer.Option(None, "--temperature", "-t"),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="OpenAI-compatible base URL"
    ),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write run history"),
):
    """Run a golden suite and print a pass/fail report."""
    if not suite_path.exists():
        console.print(f"[red]Suite not found: {suite_path}[/red]")
        raise typer.Exit(1)

    try:
        suite = load_suite(suite_path)
    except Exception as e:
        console.print(f"[red]Failed to load suite:[/red] {e}")
        raise typer.Exit(1) from e

    if not suite.cases:
        console.print("[yellow]Suite has no cases.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold]Running suite[/bold] {suite.name} ({len(suite.cases)} cases)...")

    try:
        result = run_suite(
            suite,
            model=model,
            temperature=temperature,
            base_url=base_url,
        )
    except Exception as e:
        msg = str(e).lower()
        if "api_key" in msg or "authentication" in msg or "401" in msg:
            console.print(
                "[red]API key missing or invalid.[/red]\n"
                "Set OPENAI_API_KEY (or your provider key) and retry.\n"
                "Use --base-url for OpenAI-compatible endpoints."
            )
        else:
            console.print(f"[red]Run failed:[/red] {e}")
        raise typer.Exit(1) from e

    if not no_save:
        path = RunStore().save(result)
        console.print(f"[dim]Saved run {result.id[:8]}… → {path}[/dim]")

    # Report
    console.print()
    console.print(f"Suite : {result.suite_name}")
    console.print(f"Model : {result.model}  (temp={result.temperature})")
    console.print(f"Result: [bold]{result.passed}/{result.total} passed[/bold]")
    console.print()

    for cr in result.case_results:
        if cr.passed:
            console.print(f"[green]PASS[/green]  {cr.case_id}")
        else:
            console.print(f"[red]FAIL[/red]  {cr.case_id}")
            for f in cr.failures:
                console.print(f"       {f}")
            # short preview of output
            preview = cr.output.replace("\n", " ")[:120]
            if preview:
                console.print(f"       got: {preview}{'…' if len(cr.output) > 120 else ''}")

    raise typer.Exit(0 if result.failed == 0 else 1)


@app.command("list-runs")
def list_runs_cmd(
    limit: int = typer.Option(15, "--limit", "-n"),
):
    """List recent local runs."""
    rows = RunStore().list_runs(limit=limit)
    if not rows:
        console.print("[dim]No runs yet.[/dim]")
        return

    table = Table(title="Recent runs")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Suite")
    table.add_column("Model")
    table.add_column("Pass")
    table.add_column("Fail")
    table.add_column("Started")
    for r in rows:
        table.add_row(
            str(r["id"])[:8],
            str(r.get("suite_name") or ""),
            str(r.get("model") or ""),
            str(r.get("passed", 0)),
            str(r.get("failed", 0)),
            str(r.get("started_at") or "")[:19],
        )
    console.print(table)


@app.command("show-run")
def show_run_cmd(
    run_id: str = typer.Argument(..., help="Full or short run ID"),
):
    """Show details of a past run."""
    run = RunStore().get(run_id)
    if not run:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Run {run.id}[/bold]")
    console.print(f"Suite : {run.suite_name}")
    console.print(f"Model : {run.model}  temp={run.temperature}")
    console.print(f"Result: {run.passed}/{run.total} passed")
    console.print()

    for cr in run.case_results:
        mark = "[green]PASS[/green]" if cr.passed else "[red]FAIL[/red]"
        console.print(f"{mark}  {cr.case_id}")
        if not cr.passed:
            for f in cr.failures:
                console.print(f"       {f}")


def main():
    app()


if __name__ == "__main__":
    main()

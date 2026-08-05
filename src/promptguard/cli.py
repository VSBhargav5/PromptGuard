from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import CaseResult, RunResult
from .runner import load_suite, run_suite
from .store import RunStore

app = typer.Typer(
    help="PromptGuard – regression testing for LLM apps",
    no_args_is_help=True,
)
console = Console()


def _render_failure_block(cr: CaseResult) -> None:
    """Print structured expected vs got for a failed case."""
    for f in cr.failures:
        # Support both new Failure objects and legacy string failures from old runs
        if isinstance(f, str):
            console.print(f"  [red]•[/red] {f}")
            continue

        console.print(f"  [red]•[/red] [{f.check}] {f.message}")
        if f.expected is not None:
            console.print(f"      [dim]expected[/dim]  {f.expected}")
        if f.got is not None:
            console.print(f"      [dim]got[/dim]       {f.got}")

    if cr.output and not any(
        (not isinstance(f, str) and f.got) for f in cr.failures
    ):
        preview = " ".join(cr.output.split())[:200]
        console.print(f"      [dim]output[/dim]    {preview}{'…' if len(cr.output) > 200 else ''}")


def _print_report(result: RunResult, *,
                  verbose: bool = False,
                  show_header: bool = True) -> None:
    if show_header:
        status = (
            f"[bold green]{result.passed}/{result.total} passed[/bold green]"
            if result.failed == 0
            else f"[bold yellow]{result.passed}/{result.total} passed[/bold yellow]"
            f"  [bold red]{result.failed} failed[/bold red]"
        )
        console.print()
        console.print(f"Suite  : [bold]{result.suite_name}[/bold]")
        console.print(f"Model  : {result.model}  (temp={result.temperature})")
        console.print(f"Result : {status}")
        console.print()

    # Summary table
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("", width=4)
    table.add_column("Case")
    table.add_column("Latency", justify="right")
    table.add_column("Issues", justify="right")

    for cr in result.case_results:
        mark = Text("PASS", style="green") if cr.passed else Text("FAIL", style="bold red")
        latency = f"{cr.latency_ms:.0f}ms" if cr.latency_ms is not None else "—"
        issues = "—" if cr.passed else str(len(cr.failures))
        table.add_row(mark, cr.case_id, latency, issues)

    console.print(table)
    console.print()

    # Detailed failures
    failed_cases = [cr for cr in result.case_results if not cr.passed]
    if failed_cases:
        console.print("[bold]Failures[/bold]")
        for cr in failed_cases:
            console.print()
            console.print(f"[red bold]FAIL[/red bold]  {cr.case_id}")
            _render_failure_block(cr)
            if verbose and cr.output:
                console.print(
                    Panel(
                        cr.output[:2000] + ("…" if len(cr.output) > 2000 else ""),
                        title="full output",
                        border_style="dim",
                        expand=False,
                    )
                )

    if verbose:
        passed_cases = [cr for cr in result.case_results if cr.passed]
        if passed_cases:
            console.print()
            console.print("[bold]Passed (verbose)[/bold]")
            for cr in passed_cases:
                preview = " ".join(cr.output.split())[:120] if cr.output else "(empty)"
                console.print(f"  [green]PASS[/green]  {cr.case_id}")
                console.print(f"         {preview}{'…' if cr.output and len(cr.output) > 120 else ''}")


@app.command("run")
def run_cmd(
    suite_path: Path = typer.Argument(..., help="Path to suite YAML/JSON"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override suite model"),
    temperature: Optional[float] = typer.Option(None, "--temperature", "-t"),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="OpenAI-compatible base URL"
    ),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write run history"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full outputs and passed-case previews"
    ),
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

    console.print(
        f"[bold]Running suite[/bold] {suite.name} "
        f"([cyan]{len(suite.cases)}[/cyan] cases)..."
    )

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

    _print_report(result, verbose=verbose)

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
    table.add_column("Pass", justify="right")
    table.add_column("Fail", justify="right")
    table.add_column("Started")
    for r in rows:
        fail_style = "red" if (r.get("failed") or 0) > 0 else "green"
        table.add_row(
            str(r["id"])[:8],
            str(r.get("suite_name") or ""),
            str(r.get("model") or ""),
            str(r.get("passed", 0)),
            Text(str(r.get("failed", 0)), style=fail_style),
            str(r.get("started_at") or "")[:19],
        )
    console.print(table)


@app.command("show-run")
def show_run_cmd(
    run_id: str = typer.Argument(..., help="Full or short run ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Show details of a past run."""
    run = RunStore().get(run_id)
    if not run:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Run {run.id}[/bold]")
    _print_report(run, verbose=verbose, show_header=True)


def main():
    app()


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .compare import compare_runs
from .junit import write_junit
from .models import CaseResult, RunResult
from .runner import load_suite, run_suite
from .store import RunStore

app = typer.Typer(
    help="PromptGuard – regression testing for LLM apps",
    no_args_is_help=True,
)
console = Console()


def _render_failure_block(cr: CaseResult) -> None:
    for f in cr.failures:
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
        console.print(
            f"      [dim]output[/dim]    {preview}{'…' if len(cr.output) > 200 else ''}"
        )


def _print_report(
    result: RunResult,
    *,
    verbose: bool = False,
    show_header: bool = True,
) -> None:
    if show_header:
        status = (
            f"[bold green]{result.passed}/{result.total} passed[/bold green]"
            if result.failed == 0
            else (
                f"[bold yellow]{result.passed}/{result.total} passed[/bold yellow]"
                f"  [bold red]{result.failed} failed[/bold red]"
            )
        )
        console.print()
        console.print(f"Suite  : [bold]{result.suite_name}[/bold]")
        console.print(f"Model  : {result.model}  (temp={result.temperature})")
        if result.system_prompt:
            snap = result.system_prompt.replace("\n", " ")[:80]
            console.print(
                f"Prompt : [dim]{snap}{'…' if len(result.system_prompt) > 80 else ''}[/dim]"
            )
        console.print(f"Result : {status}")
        console.print()

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

    failed_cases = [cr for cr in result.case_results if not cr.passed]
    if failed_cases:
        console.print("[bold]Failures[/bold]")
        for cr in failed_cases:
            console.print()
            console.print(f"[red bold]FAIL[/red bold]  {cr.case_id}")
            if cr.rendered_input and verbose:
                console.print(f"  [dim]input[/dim]  {cr.rendered_input[:150]}")
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
                console.print(
                    f"         {preview}{'…' if cr.output and len(cr.output) > 120 else ''}"
                )


def _print_compare(cmp) -> None:
    console.print()
    console.print(
        f"Compare  [bold]{cmp.baseline.id[:8]}[/bold] → [bold]{cmp.current.id[:8]}[/bold]"
    )
    console.print(
        f"Suite    {cmp.current.suite_name}  |  "
        f"baseline {cmp.baseline.passed}/{cmp.baseline.total}  →  "
        f"current {cmp.current.passed}/{cmp.current.total}"
    )
    console.print()

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Case")
    table.add_column("Baseline")
    table.add_column("Current")
    table.add_column("Delta")

    style_for = {
        "regressed": "bold red",
        "fixed": "bold green",
        "still_fail": "yellow",
        "still_pass": "dim",
        "new": "cyan",
        "removed": "dim",
    }

    for d in cmp.deltas:
        b = "—" if d.baseline_passed is None else ("PASS" if d.baseline_passed else "FAIL")
        c = "—" if d.current_passed is None else ("PASS" if d.current_passed else "FAIL")
        table.add_row(
            d.case_id,
            b,
            c,
            Text(d.kind, style=style_for.get(d.kind, "")),
        )

    console.print(table)
    console.print()

    if cmp.regressed:
        console.print(
            f"[bold red]{len(cmp.regressed)} regressed[/bold red]: "
            + ", ".join(d.case_id for d in cmp.regressed)
        )
    if cmp.fixed:
        console.print(
            f"[bold green]{len(cmp.fixed)} fixed[/bold green]: "
            + ", ".join(d.case_id for d in cmp.fixed)
        )
    if not cmp.regressed and not cmp.fixed:
        console.print("[dim]No pass/fail changes between runs.[/dim]")


@app.command("run")
def run_cmd(
    suite_path: Path = typer.Argument(..., help="Path to suite YAML/JSON"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override suite model"),
    temperature: Optional[float] = typer.Option(None, "--temperature", "-t"),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="OpenAI-compatible base URL"
    ),
    case: Optional[List[str]] = typer.Option(
        None, "--case", "-c", help="Run only these case ids (repeatable)"
    ),
    baseline: Optional[str] = typer.Option(
        None,
        "--baseline",
        help="Compare against run id, or 'last' / 'last-pass' for this suite",
    ),
    no_save: bool = typer.Option(False, "--no-save", help="Do not write run history"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full outputs and passed-case previews"
    ),
    junit: Optional[Path] = typer.Option(
        None, "--junit", help="Write JUnit XML report to this path (CI)"
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

    case_ids = case or None
    n = len(case_ids) if case_ids else len(suite.cases)
    console.print(
        f"[bold]Running suite[/bold] {suite.name} "
        f"([cyan]{n}[/cyan] case{'s' if n != 1 else ''})..."
    )

    try:
        result = run_suite(
            suite,
            model=model,
            temperature=temperature,
            base_url=base_url,
            case_ids=case_ids,
        )
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e
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

    store = RunStore()
    if not no_save:
        path = store.save(result)
        console.print(f"[dim]Saved run {result.id[:8]}… → {path}[/dim]")

    if junit:
        out = write_junit(result, junit)
        console.print(f"[dim]JUnit XML → {out}[/dim]")

    _print_report(result, verbose=verbose)

    # Optional baseline compare
    if baseline:
        base_run = None
        if baseline in ("last", "latest"):
            base_run = store.latest_for_suite(
                suite.name, exclude_id=result.id
            )
        elif baseline in ("last-pass", "last-passing", "green"):
            base_run = store.latest_for_suite(
                suite.name, only_passing=True, exclude_id=result.id
            )
        else:
            base_run = store.get(baseline)

        if not base_run:
            console.print(
                f"[yellow]No baseline run found for '{baseline}' — skip compare.[/yellow]"
            )
        else:
            cmp = compare_runs(base_run, result)
            _print_compare(cmp)
            if cmp.regressed:
                raise typer.Exit(1)

    raise typer.Exit(0 if result.failed == 0 else 1)


@app.command("compare")
def compare_cmd(
    baseline_id: str = typer.Argument(..., help="Baseline run id (or prefix)"),
    current_id: str = typer.Argument(..., help="Current run id (or prefix)"),
):
    """Diff two saved runs: regressions, fixes, unchanged."""
    store = RunStore()
    baseline = store.get(baseline_id)
    current = store.get(current_id)
    if not baseline:
        console.print(f"[red]Baseline run not found: {baseline_id}[/red]")
        raise typer.Exit(1)
    if not current:
        console.print(f"[red]Current run not found: {current_id}[/red]")
        raise typer.Exit(1)

    cmp = compare_runs(baseline, current)
    _print_compare(cmp)
    raise typer.Exit(1 if cmp.regressed else 0)


@app.command("list-runs")
def list_runs_cmd(
    limit: int = typer.Option(15, "--limit", "-n"),
    suite: Optional[str] = typer.Option(None, "--suite", "-s", help="Filter by suite name"),
):
    """List recent local runs."""
    rows = RunStore().list_runs(limit=limit, suite=suite)
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


@app.command("init")
def init_cmd(
    name: str = typer.Argument("my-suite", help="Suite name"),
    output: Path = typer.Option(
        Path("suite.yaml"), "--output", "-o", help="Where to write the suite file"
    ),
):
    """Scaffold a starter suite YAML."""
    if output.exists():
        console.print(f"[red]Refusing to overwrite existing file: {output}[/red]")
        raise typer.Exit(1)

    content = f"""name: {name}
system_prompt: |
  You are a helpful assistant. Be concise and accurate.
  Never invent policies or facts you were not given.
model: gpt-4o-mini
temperature: 0
vars:
  product: Acme

cases:
  - id: greeting
    input: "Hi"
    expect:
      contains:
        - "help"
      max_chars: 400

  - id: product_mention
    input: "What product do you support?"
    expect:
      contains:
        - "{{{{product}}}}"

  - id: multi_turn_example
    messages:
      - role: user
        content: "My order id is {{{{order_id}}}}"
      - role: assistant
        content: "Thanks, I have order {{{{order_id}}}}. What do you need?"
      - role: user
        content: "What's the status?"
    vars:
      order_id: "A-100"
    expect:
      not_contains:
        - "I don't know your order"
      max_chars: 600
"""
    output.write_text(content, encoding="utf-8")
    console.print(f"[green]Wrote[/green] {output}")
    console.print("Edit the cases, then:  python -m promptguard run " + str(output))


def main():
    app()


if __name__ == "__main__":
    main()

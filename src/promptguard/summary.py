"""Compact, paste-ready summaries for PRs and chat."""

from __future__ import annotations

from pathlib import Path

from .compare import CompareResult
from .models import RunResult
from .stats import latency_summary


def _fail_line(cr) -> str:
    if not cr.failures:
        return f"- `{cr.case_id}` — failed"
    first = cr.failures[0]
    if isinstance(first, str):
        msg = first
    else:
        msg = f"[{first.check}] {first.message}"
    return f"- `{cr.case_id}` — {msg}"


def to_pr_summary(result: RunResult) -> str:
    """Short Markdown meant for a PR comment body."""
    status = "✅ all passed" if result.failed == 0 else f"❌ {result.failed} failed"
    lines = [
        f"### PromptGuard · {result.suite_name}",
        "",
        f"**{result.passed}/{result.total}** passed · {status}",
        f"Model `{result.model}` (temp={result.temperature}) · run `{result.id[:8]}`",
    ]
    lat = latency_summary(result)
    if lat:
        lines.append(
            f"Latency avg {lat['avg_ms']:.0f}ms · p95 {lat['p95_ms']:.0f}ms"
        )

    failed = [c for c in result.case_results if not c.passed]
    if failed:
        lines.extend(["", "**Failures**"])
        for cr in failed[:20]:
            lines.append(_fail_line(cr))
        if len(failed) > 20:
            lines.append(f"- …and {len(failed) - 20} more")
    else:
        lines.extend(["", "_No failing cases._"])

    lines.append("")
    return "\n".join(lines)


def to_compare_pr_summary(cmp: CompareResult) -> str:
    """Baseline → current, focused on regressions."""
    cur = cmp.current
    base = cmp.baseline
    lines = [
        f"### PromptGuard compare · {cur.suite_name}",
        "",
        f"`{base.id[:8]}` ({base.passed}/{base.total}) → "
        f"`{cur.id[:8]}` ({cur.passed}/{cur.total})",
    ]
    if cmp.prompt_changed:
        lines.append("_System prompt changed_")
    if cmp.model_changed:
        lines.append(
            f"_Model/temp: {base.model}@{base.temperature} → {cur.model}@{cur.temperature}_"
        )

    if cmp.regressed:
        lines.extend(["", f"**Regressed ({len(cmp.regressed)})**"])
        for d in cmp.regressed:
            lines.append(f"- `{d.case_id}`")
    if cmp.fixed:
        lines.extend(["", f"**Fixed ({len(cmp.fixed)})**"])
        for d in cmp.fixed:
            lines.append(f"- `{d.case_id}`")
    if not cmp.regressed and not cmp.fixed:
        lines.extend(["", "_No pass/fail changes._"])

    lines.append("")
    return "\n".join(lines)


def write_pr_summary(result: RunResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_pr_summary(result), encoding="utf-8")
    return path


def write_compare_pr_summary(cmp: CompareResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_compare_pr_summary(cmp), encoding="utf-8")
    return path

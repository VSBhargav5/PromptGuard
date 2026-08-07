from __future__ import annotations

from pathlib import Path

from .models import RunResult


def to_markdown(result: RunResult) -> str:
    lines = [
        f"# PromptGuard Report: {result.suite_name}",
        "",
        f"- **Run id:** `{result.id}`",
        f"- **Model:** `{result.model}` (temp={result.temperature})",
        f"- **Result:** {result.passed}/{result.total} passed",
        f"- **Started:** {result.started_at}",
    ]
    if result.finished_at:
        lines.append(f"- **Finished:** {result.finished_at}")
    if result.system_prompt:
        lines.extend(["", "## System prompt snapshot", "", "```", result.system_prompt.strip(), "```"])

    lines.extend(["", "## Cases", ""])
    for cr in result.case_results:
        mark = "PASS" if cr.passed else "FAIL"
        lat = f"{cr.latency_ms:.0f}ms" if cr.latency_ms is not None else "—"
        lines.append(f"### {mark} `{cr.case_id}` ({lat})")
        if cr.rendered_input:
            lines.append(f"- **Input:** {cr.rendered_input[:300]}")
        if not cr.passed:
            for f in cr.failures:
                if isinstance(f, str):
                    lines.append(f"- {f}")
                else:
                    lines.append(f"- **[{f.check}]** {f.message}")
                    if f.expected is not None:
                        lines.append(f"  - expected: {f.expected}")
                    if f.got is not None:
                        lines.append(f"  - got: {f.got}")
            if cr.output:
                lines.extend(["", "```", cr.output[:1500], "```"])
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_markdown(result: RunResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_markdown(result), encoding="utf-8")
    return path

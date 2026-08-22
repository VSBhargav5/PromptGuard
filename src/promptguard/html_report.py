"""Self-contained HTML report for humans (no JS required)."""

from __future__ import annotations

import html
from pathlib import Path

from .models import RunResult
from .stats import latency_summary


def _esc(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def to_html(result: RunResult) -> str:
    lat = latency_summary(result)
    lat_row = ""
    if lat:
        lat_row = (
            f"<p class='meta'>Latency avg {lat['avg_ms']:.0f}ms · "
            f"p50 {lat['p50_ms']:.0f}ms · p95 {lat['p95_ms']:.0f}ms</p>"
        )

    status_cls = "ok" if result.failed == 0 else "bad"
    rows = []
    for cr in result.case_results:
        mark = "PASS" if cr.passed else "FAIL"
        cls = "pass" if cr.passed else "fail"
        lat_s = f"{cr.latency_ms:.0f}ms" if cr.latency_ms is not None else "—"
        detail = ""
        if not cr.passed and cr.failures:
            bits = []
            for f in cr.failures:
                if isinstance(f, str):
                    bits.append(_esc(f))
                else:
                    bits.append(_esc(f"[{f.check}] {f.message}"))
            detail = "<ul>" + "".join(f"<li>{b}</li>" for b in bits) + "</ul>"
        rows.append(
            f"<tr class='{cls}'><td><span class='badge'>{mark}</span></td>"
            f"<td><code>{_esc(cr.case_id)}</code></td>"
            f"<td>{lat_s}</td><td>{detail}</td></tr>"
        )

    prompt_block = ""
    if result.system_prompt:
        prompt_block = (
            "<h2>System prompt snapshot</h2>"
            f"<pre>{_esc(result.system_prompt)}</pre>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>PromptGuard · {_esc(result.suite_name)}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; line-height: 1.45; }}
  h1 {{ margin-bottom: 0.2rem; }}
  .meta {{ color: #64748b; }}
  .badge {{ font-family: ui-monospace, monospace; font-size: 0.8rem; font-weight: 700; }}
  tr.pass .badge {{ color: #16a34a; }}
  tr.fail .badge {{ color: #dc2626; }}
  .ok {{ color: #16a34a; }} .bad {{ color: #dc2626; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
  pre {{ background: #0f172a; color: #e2e8f0; padding: 1rem; border-radius: 8px; overflow: auto; }}
  code {{ font-family: ui-monospace, monospace; }}
</style>
</head>
<body>
  <h1>PromptGuard · {_esc(result.suite_name)}</h1>
  <p class="meta">Run <code>{_esc(result.id)}</code> · model <code>{_esc(result.model)}</code> (temp={result.temperature})</p>
  <p class="{status_cls}"><strong>{result.passed}/{result.total}</strong> passed
     {"· no failures" if result.failed == 0 else f"· {result.failed} failed"}</p>
  {lat_row}
  {prompt_block}
  <h2>Cases</h2>
  <table>
    <thead><tr><th></th><th>Case</th><th>Latency</th><th>Issues</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""


def write_html(result: RunResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_html(result), encoding="utf-8")
    return path

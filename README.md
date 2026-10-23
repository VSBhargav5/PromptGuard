# PromptGuard

**Regression testing for LLM applications.**

Change a prompt or model → re-run the suite → see **what regressed** before users do — and paste a short summary into the PR.

**Current version: 0.6.0**

---

## Features

| Area | Capability |
|------|------------|
| Suites | YAML cases, tags, `{{vars}}`, multi-turn, `system_prompt_file` |
| Scoring | contains / not_contains / regex / exact / json / similar_to / min_chars / max_chars |
| Runs | parallel, retries, timeout, fail-fast, `--from-failed`, `--tag` |
| Artifacts | **PR summary** (paste into GitHub), **HTML report**, Markdown, JUnit, JSON |
| History | Prompt snapshot, local store, baseline compare + output-change flags |
| Coverage | Added/removed cases in PR summaries; optional `--fail-on-removed` CI gate |
| CI | Offline unit tests always; live suite when `OPENAI_API_KEY` is set |

---

## Quick Start

```bash
pip install -e ".[dev]"
pytest -q

python -m promptguard validate examples/support_bot_suite.yaml
python -m promptguard run examples/support_bot_suite.yaml --tag smoke --timeout 45 \
  --pr-summary pr.md --html report.html --baseline last
```

Paste `pr.md` into the PR description or as a bot comment.

---

## CLI

```bash
python -m promptguard validate <suite.yaml>
python -m promptguard run <suite.yaml> \
  [-c CASE]... [--tag TAG]... [--from-failed last] \
  [-w N] [--retries N] [--timeout S] [--fail-fast] \
  [--baseline last|last-pass] [--fail-on-removed] \
  [--junit path] [--report path] [--pr-summary path] [--html path] [--json path] [-v]
python -m promptguard compare <baseline_id> <current_id> [--pr-summary path] [--fail-on-removed]
python -m promptguard list-runs | show-run <id> [--pr-summary path] [--html path]
python -m promptguard init [name]
```

---

## Keep test coverage visible

A run can go from **8/10 passing to 8/8 passing** because two failing cases
were excluded. That does not demonstrate that the prompt improved.

Compare summaries list added and removed case IDs with their pass/fail status.
Unchanged results refer only to shared cases; disjoint runs explicitly say that
pass/fail changes cannot be assessed.

For a CI job that must retain every baseline case:

```bash
python -m promptguard run examples/support_bot_suite.yaml --baseline last-pass --fail-on-removed
python -m promptguard compare <baseline_id> <current_id> --fail-on-removed --pr-summary comparison.md
```

The flag exits with code 1 when a baseline case is absent, even if all current
cases pass. On `run`, it requires `--baseline` and also fails if that baseline
cannot be found. It is opt-in because tag filters, fail-fast, and focused reruns
can intentionally evaluate fewer cases. Without it, the existing exit behavior
is preserved. Case IDs establish coverage, not equivalence of inputs or assertions.

An offline [first-principles exercise](docs/coverage-gates.md) explains the failure
mode and how to reproduce the behavior without an API key.

---

## Status

**v0.6.0** — PR-comment summary + self-contained HTML report  
**v0.5.0** — tags, validate, latency stats, JSON export, CI  
**v0.4.x** — baseline compare, retries, timeout, fail-fast

---

## License

MIT

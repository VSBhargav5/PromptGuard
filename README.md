# PromptGuard

**Regression testing for LLM applications.**

Change a prompt or model → re-run the suite → see **what regressed** before users do.

**Current version: 0.5.0**

---

## Features

| Area | Capability |
|------|------------|
| Suites | YAML cases, tags, `{{vars}}`, multi-turn, `system_prompt_file` |
| Scoring | contains / not_contains / regex / exact / json / similar_to / min_chars / max_chars |
| Runs | parallel, retries, timeout, fail-fast, `--from-failed`, **`--tag`** |
| DX | **`validate`** (no API), **`--json`**, latency avg/p50/p95 |
| History | Prompt snapshot, local store, baseline compare + output-change flags |
| CI | Offline unit tests always; live suite when `OPENAI_API_KEY` is set |

---

## Quick Start

```bash
pip install -e ".[dev]"
pytest -q

python -m promptguard validate examples/support_bot_suite.yaml
python -m promptguard run examples/support_bot_suite.yaml --tag smoke --timeout 45
python -m promptguard run examples/support_bot_suite.yaml --json out.json --baseline last
```

---

## CLI

```bash
python -m promptguard validate <suite.yaml>
python -m promptguard run <suite.yaml> \
  [-c CASE]... [--tag TAG]... [--from-failed last] \
  [-w N] [--retries N] [--timeout S] [--fail-fast] \
  [--baseline last|last-pass] [--junit path] [--report path] [--json path] [-v]
python -m promptguard compare <baseline_id> <current_id>
python -m promptguard list-runs | show-run <id> | init [name]
```

---

## License

MIT

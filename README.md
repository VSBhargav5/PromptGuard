# PromptGuard

**Regression testing for LLM applications.**

Change a prompt or model → re-run the suite → see **what regressed** before users do.

**Current version: 0.4.0**

---

## Features

| Area | Capability |
|------|------------|
| Suites | YAML cases, `{{vars}}`, multi-turn, `system_prompt_file` |
| Scoring | contains / not_contains / regex / exact / json / similar_to / min_chars / max_chars |
| Runs | parallel workers, retries, **timeout**, fail-fast, **`--from-failed`** |
| History | Prompt snapshot, local store |
| Compare | baseline last/last-pass, **output text change** flags |
| CI | **offline unit tests**, JUnit, Markdown, GitHub Action |
| DX | `init`, OpenAI-compatible `--base-url` |

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/PromptGuard.git
cd PromptGuard
pip install -e ".[dev]"
export OPENAI_API_KEY="sk-..."

pytest -q   # offline, no API key needed

python -m promptguard run examples/support_bot_suite.yaml --workers 4 --timeout 45
python -m promptguard run examples/support_bot_suite.yaml --baseline last
python -m promptguard run examples/support_bot_suite.yaml --from-failed last
```

---

## CLI

```bash
python -m promptguard run <suite.yaml> \
  [-c CASE]... [--from-failed last|<id>] \
  [-w WORKERS] [--retries N] [--timeout SECS] [--fail-fast] \
  [--baseline last|last-pass|<id>] \
  [--junit path] [--report path] [-v]

python -m promptguard compare <baseline_id> <current_id>
python -m promptguard list-runs [--suite name]
python -m promptguard show-run <id> [-v]
python -m promptguard init [name] [-o suite.yaml]
```

---

## GitHub Actions

[`.github/workflows/promptguard.yml`](.github/workflows/promptguard.yml) always runs **pytest**.  
Live suite runs only when `OPENAI_API_KEY` is set as a repo secret.

---

## License

MIT

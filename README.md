# PromptGuard

**Regression testing for LLM applications.**

Change a prompt or model → re-run the suite → see **what regressed** before users do.

**Current version: 0.3.0**

---

## Why

LLM features almost never have real regression tests. Prompt tweaks and model upgrades silently break behavior. PromptGuard is a focused suite you run on every change — with baseline compare, parallel execution, and CI artifacts.

---

## Features

| Area | Capability |
|------|------------|
| Suites | YAML golden cases, `{{vars}}`, multi-turn `messages` |
| Scoring | contains / not_contains / regex / exact / json / similar_to / max_chars |
| Runs | **parallel workers**, **retries**, **fail-fast**, case filter |
| History | Prompt snapshot, local run store |
| Compare | `--baseline last\|last-pass`, `compare` cmd, prompt/model change flags |
| CI | JUnit XML, Markdown report, **GitHub Action** example |
| DX | `init`, `system_prompt_file`, OpenAI-compatible `--base-url` |

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/PromptGuard.git
cd PromptGuard
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."

python -m promptguard run examples/support_bot_suite.yaml --workers 4
python -m promptguard run examples/support_bot_suite.yaml --baseline last
python -m promptguard run examples/sql_assistant_suite.yaml -c refuse_destructive -v
```

CI-style:

```bash
python -m promptguard run examples/support_bot_suite.yaml \
  --workers 4 --retries 1 \
  --junit junit.xml --report report.md \
  --baseline last-pass
```

---

## CLI

```bash
python -m promptguard run <suite.yaml> \
  [-c CASE]... [-w WORKERS] [--retries N] [--fail-fast] \
  [--baseline last|last-pass|<id>] \
  [--junit path] [--report path] [-v] \
  [--model ...] [--base-url ...]

python -m promptguard compare <baseline_id> <current_id>
python -m promptguard list-runs [--suite name]
python -m promptguard show-run <id> [-v]
python -m promptguard init [name] [-o suite.yaml]
```

Exit code `1` on failures or regressions.

---

## Suite tips (v0.3)

```yaml
name: my-bot
system_prompt_file: prompts/system.txt   # optional; merged with system_prompt
system_prompt: |
  Short overrides here.
model: gpt-4o-mini
temperature: 0
vars:
  shop: Acme
cases:
  - id: refund
    input: "Refund policy for {{shop}}?"
    expect:
      contains: ["refund"]
```

---

## GitHub Actions

See [`.github/workflows/promptguard.yml`](.github/workflows/promptguard.yml).

Set repository secret `OPENAI_API_KEY` (and optionally point at another OpenAI-compatible API).

---

## Architecture

```
Suite YAML (+ prompt file / vars / multi-turn)
        │
        ▼
 Runner (filter · template · parallel · retries · fail-fast · snapshot)
        │
        ▼
 Scorer → Failure{check, expected, got}
        │
        ├─ Terminal report
        ├─ History (~/.promptguard/runs/)
        ├─ compare (regressions + prompt/model flags)
        ├─ JUnit + Markdown
        └─ GitHub Action
```

---

## Roadmap

**0.3 (current)** — parallel · retries · fail-fast · markdown · GHA · prompt file  
**Later** — embedding similarity · multi-suite workspaces · shared registry

---

## Tech

Python 3.11+ · Pydantic · PyYAML · OpenAI-compatible APIs · Typer · Rich

## License

MIT

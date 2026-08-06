# PromptGuard

**Regression testing for LLM applications.**

You change a prompt, a model, or a temperature.  
Something that used to work now fails — and nobody notices until a user complains.

PromptGuard records golden behaviors, re-runs them after every change, and tells you **what regressed**.

**Current version: 0.2.0**

---

## The Real Pain

Teams shipping LLM features almost never have real regression tests.

- Prompt tweaks silently change tone, format, or correctness
- Model upgrades break edge cases that used to pass
- “Vibe checks” don’t scale
- There is no CI signal for “this prompt change is safe”

**PromptGuard is the missing middle**: a focused regression suite you run every time you touch a prompt — with **baseline compare**, not just a one-off score.

---

## What’s in v0.2

| Capability | Why it matters |
|------------|----------------|
| Golden suites (YAML) | Repeatable cases |
| Deterministic scorers | Readable failures in seconds |
| **Prompt snapshot** on every run | History stays meaningful after edits |
| **`--baseline last` / `last-pass`** | “What broke vs last green?” |
| **`compare` command** | Diff any two runs |
| **`--case` filter** | Re-run one failing case |
| **`{{vars}}` templating** | One suite, many fixtures |
| **Multi-turn `messages`** | Real chat flows |
| **`init`** | Scaffold a suite in one command |
| JUnit XML | Drop into CI |

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/PromptGuard.git
cd PromptGuard
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."

# Scaffold or use examples
python -m promptguard init my-bot -o suite.yaml
python -m promptguard run examples/support_bot_suite.yaml

# After you edit the system prompt — see what regressed
python -m promptguard run examples/support_bot_suite.yaml --baseline last

# One case only
python -m promptguard run examples/support_bot_suite.yaml -c refund_policy -v

# CI
python -m promptguard run examples/support_bot_suite.yaml --junit junit.xml --baseline last-pass
```

---

## Baseline compare (the product moment)

```bash
python -m promptguard run suite.yaml --baseline last
# or
python -m promptguard compare <old_run_id> <new_run_id>
```

Example output:

```text
Compare  a1b2c3d4 → e5f6g7h8
Suite    support-bot  |  baseline 5/5  →  current 4/5

Case                 Baseline  Current  Delta
refund_policy        PASS      PASS     still_pass
order_status_json    PASS      FAIL     regressed

1 regressed: order_status_json
```

Exit code `1` if anything **regressed** (or failed, on a normal run).

---

## Suite format

```yaml
name: support-bot
system_prompt: |
  You are support for {{shop_name}}.
  Refunds within {{refund_days}} days.
model: gpt-4o-mini
temperature: 0
vars:
  shop_name: Acme Shop
  refund_days: "30"

cases:
  - id: refund_policy
    input: "What is your refund policy?"
    expect:
      contains: ["{{refund_days}} days", "refund"]

  - id: multi_turn
    messages:
      - role: user
        content: "Order {{order_id}} please"
      - role: assistant
        content: "I have order {{order_id}}."
      - role: user
        content: "Status?"
    vars:
      order_id: "A-100"
    expect:
      max_chars: 500
```

**Checks:** `contains`, `not_contains`, `regex`, `exact`, `json_valid`, `json_keys`, `similar_to` + `min_similarity`, `max_chars`.

---

## CLI

```bash
python -m promptguard run <suite.yaml> \
  [--model ...] [--base-url ...] [-c CASE]... \
  [--baseline last|last-pass|<id>] [-v] [--junit path]

python -m promptguard compare <baseline_id> <current_id>
python -m promptguard list-runs [--suite name]
python -m promptguard show-run <id> [-v]
python -m promptguard init [name] [-o suite.yaml]
```

---

## Architecture

```
Suite YAML (+ vars / multi-turn)
        │
        ▼
   Runner (filter · template · snapshot prompt)
        │
        ▼
   Scorer → structured Failure{check, expected, got}
        │
        ├─ Report (table + diffs)
        ├─ History (~/.promptguard/runs/)
        ├─ compare (regressions / fixes)
        └─ JUnit XML
```

---

## Roadmap

**Done (0.2)**  
Baseline compare · prompt snapshot · case filter · templating · multi-turn · init · JUnit

**Later**  
Embedding similarity · parallel runs · GitHub Action · shared suite registry

---

## Tech Stack

Python 3.11+ · Pydantic · PyYAML · OpenAI-compatible APIs · Typer · Rich

## License

MIT

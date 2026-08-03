# PromptGuard

**Regression testing for LLM applications.**

You change a prompt, a model, or a temperature.  
Something that used to work now fails — and nobody notices until a user complains.

PromptGuard lets you record *golden behaviors*, re-run them after every change, and see exactly what broke.

---

## The Real Pain

Teams shipping LLM features almost never have real regression tests.

- Prompt tweaks silently change tone, format, or correctness
- Model upgrades break edge cases that used to pass
- “Vibe checks” in the chat UI don’t scale past a handful of examples
- There is no CI signal for “this prompt change is safe”

Existing eval tools are either heavy research frameworks or one-off notebooks.  
**PromptGuard is the missing middle**: a small, focused regression suite you actually run every time you touch a prompt.

---

## What it does (v0.1)

1. Define **golden cases** (input + expected behavior)
2. Group them into a **suite** (YAML/JSON)
3. **Run** the suite against your current model + system prompt
4. Score each case with simple, reliable checks:
   - `contains` / `not_contains`
   - `regex`
   - `exact` (normalized)
   - `json_valid` + optional key presence
5. Get a clear **pass/fail report** with diffs
6. Store run history locally so you can compare over time

No agents. No giant eval platform. Just regression tests for prompts.

---

## Why this can become a product

- Every team with an LLM feature in production feels this pain weekly
- High willingness to pay for “don’t break what already works”
- Natural expansion: CI action → shared suite repo → semantic scoring → prompt versioning
- The hard part is *discipline + clear failure signals*, not fancy ML

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/PromptGuard.git
cd PromptGuard
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."
```

### 1. Write a suite

See `examples/support_bot_suite.yaml`.

### 2. Run it

```bash
python -m promptguard run examples/support_bot_suite.yaml
```

### 3. Read the report

```text
Suite: support-bot
Model: gpt-4o-mini
Passed: 4/5

FAIL  refund_policy_tone
  expected contains: "refund"
  got: "I can help you with your order status..."
```

---

## Suite format (minimal)

```yaml
name: support-bot
system_prompt: |
  You are a helpful support agent for Acme Shop.
  Be concise. Never invent policies.
model: gpt-4o-mini
temperature: 0

cases:
  - id: greeting
    input: "Hi"
    expect:
      contains: ["help", "assist"]

  - id: refund_policy
    input: "What is your refund policy?"
    expect:
      contains: ["30 days", "refund"]
      not_contains: ["I don't know"]

  - id: json_order_status
    input: "Return order status for #12345 as JSON with keys status and eta"
    expect:
      json_valid: true
      json_keys: ["status", "eta"]
```

---

## Architecture

```
Suite (YAML)
    │
    ▼
┌─────────────────────┐
│  Runner             │  calls model once per case
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Scorer             │  contains / regex / exact / json checks
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Report + History   │  local JSON runs under ~/.promptguard/
└─────────────────────┘
```

Design principles:
- Deterministic checks first (semantic scoring can come later)
- One case = one clear expectation
- Failures must be readable in 5 seconds
- Local-first, CI-friendly exit codes

---

## CLI

```bash
python -m promptguard run <suite.yaml> [--model ...] [--base-url ...]
python -m promptguard list-runs
python -m promptguard show-run <run_id>
```

Exit code `1` if any case fails → drop straight into CI.

---

## Project Structure

```
src/promptguard/
├── cli.py          # run / list-runs / show-run
├── models.py       # Suite, Case, Expect, RunResult
├── runner.py       # execute suite against LLM
├── scorer.py       # expectation checks
└── store.py        # local run history
examples/
└── support_bot_suite.yaml
```

---

## Roadmap

**v0.1 (this)**  
Suite format · deterministic scorers · CLI run · local history · CI exit codes

**v0.2**  
Semantic similarity option · prompt snapshotting · richer diffs · JUnit XML

**Later**  
GitHub Action · shared suite registry · multi-turn cases

---

## Tech Stack

Python 3.11+ · Pydantic · PyYAML · OpenAI-compatible APIs · Typer · Rich

## License

MIT

Built as a real tool for people who ship LLM features — not a research demo.

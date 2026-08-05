# PromptGuard

**Regression testing for LLM applications.**

You change a prompt, a model, or a temperature.  
Something that used to work now fails — and nobody notices until a user complains.

PromptGuard lets you record *golden behaviors*, re-run them after every change, and see exactly what broke.

**Current version: 0.1.1**

---

## The Real Pain

Teams shipping LLM features almost never have real regression tests.

- Prompt tweaks silently change tone, format, or correctness
- Model upgrades break edge cases that used to pass
- “Vibe checks” in the chat UI don’t scale past a handful of examples
- There is no CI signal for “this prompt change is safe”

**PromptGuard is the missing middle**: a small, focused regression suite you actually run every time you touch a prompt.

---

## What it does

1. Define **golden cases** (input + expected behavior)
2. Group them into a **suite** (YAML)
3. **Run** against your current model + system prompt
4. Score with deterministic checks: `contains`, `not_contains`, `regex`, `exact`, `json_valid`, `json_keys`
5. Get a **readable report** with summary table, latency, and expected-vs-got diffs
6. Store run history locally (`~/.promptguard/runs/`)

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/PromptGuard.git
cd PromptGuard
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."

python -m promptguard run examples/support_bot_suite.yaml
python -m promptguard run examples/support_bot_suite.yaml -v   # verbose
```

Other providers:

```bash
python -m promptguard run examples/support_bot_suite.yaml \
  --base-url https://api.groq.com/openai/v1 \
  --model llama-3.3-70b-versatile
```

### Example report

```text
Suite  : support-bot
Model  : gpt-4o-mini  (temp=0.0)
Result : 4/5 passed  1 failed

 PASS  greeting          420ms   —
 PASS  refund_policy     510ms   —
 FAIL  order_status_json 380ms   1

Failures

FAIL  order_status_json
  • [json_key] Missing JSON key: "eta"
      expected  key "eta" present
      got       keys: ['status']
```

---

## Suite format

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
      contains: ["help"]

  - id: refund_policy
    input: "What is your refund policy?"
    expect:
      contains: ["30 days", "refund"]
      not_contains: ["I don't know"]

  - id: order_status_json
    input: "Return ONLY JSON with keys status and eta for order #12345"
    expect:
      json_valid: true
      json_keys: ["status", "eta"]
```

---

## CLI

```bash
python -m promptguard run <suite.yaml> [--model ...] [--base-url ...] [-v]
python -m promptguard list-runs
python -m promptguard show-run <run_id> [-v]
```

Exit code `1` if any case fails → CI-ready.

---

## Architecture

```
Suite (YAML)
    │
    ▼
┌─────────────────────┐
│  Runner             │  one model call per case
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Scorer             │  structured Failure{check, expected, got}
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Report + History   │  table + diffs + ~/.promptguard/runs/
└─────────────────────┘
```

---

## Roadmap

**v0.1.1 (current)**  
Structured failures · expected-vs-got diffs · summary table · latency · verbose mode

**Next**  
Second example suite · optional semantic similarity · JUnit XML

**Later**  
GitHub Action · multi-turn cases · prompt snapshotting

---

## Tech Stack

Python 3.11+ · Pydantic · PyYAML · OpenAI-compatible APIs · Typer · Rich

## License

MIT

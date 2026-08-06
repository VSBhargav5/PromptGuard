# PromptGuard

**Regression testing for LLM applications.**

You change a prompt, a model, or a temperature.  
Something that used to work now fails — and nobody notices until a user complains.

PromptGuard lets you record *golden behaviors*, re-run them after every change, and see exactly what broke.

**Current version: 0.1.2**

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
4. Score with checks: `contains`, `not_contains`, `regex`, `exact`, `json_*`, `similar_to`, `max_chars`
5. Readable report: summary table, latency, expected-vs-got diffs
6. **JUnit XML** export for CI
7. Local run history (`~/.promptguard/runs/`)

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/PromptGuard.git
cd PromptGuard
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."

python -m promptguard run examples/support_bot_suite.yaml
python -m promptguard run examples/sql_assistant_suite.yaml -v
python -m promptguard run examples/support_bot_suite.yaml --junit junit.xml
```

Other providers:

```bash
python -m promptguard run examples/support_bot_suite.yaml \
  --base-url https://api.groq.com/openai/v1 \
  --model llama-3.3-70b-versatile
```

---

## Expectations

| Check | Purpose |
|-------|---------|
| `contains` / `not_contains` | Required / forbidden phrases |
| `regex` | Pattern match |
| `exact` | Whitespace-normalized full match |
| `json_valid` / `json_keys` | Structured output |
| `similar_to` + `min_similarity` | Lexical (token Jaccard) similarity — no embeddings |
| `max_chars` | Soft length guard |

---

## Suite format

```yaml
name: support-bot
system_prompt: |
  You are a helpful support agent...
model: gpt-4o-mini
temperature: 0

cases:
  - id: refund_policy
    input: "What is your refund policy?"
    expect:
      contains: ["30 days", "refund"]
      not_contains: ["I don't know"]
      max_chars: 1000
```

Examples: `examples/support_bot_suite.yaml`, `examples/sql_assistant_suite.yaml`.

---

## CLI

```bash
python -m promptguard run <suite.yaml> [--model ...] [--base-url ...] [-v] [--junit path]
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
 Runner  →  Scorer (structured Failure)  →  Report + History + optional JUnit
```

---

## Roadmap

**v0.1.2 (current)**  
JUnit XML · `similar_to` / `max_chars` · second example suite (SQL assistant)

**Later**  
Embedding-based similarity · GitHub Action · multi-turn cases

---

## Tech Stack

Python 3.11+ · Pydantic · PyYAML · OpenAI-compatible APIs · Typer · Rich

## License

MIT

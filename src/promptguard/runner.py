from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

import yaml
from openai import OpenAI

from .models import Case, CaseResult, Failure, RunResult, Suite
from .scorer import score
from .template import render


def load_suite(path: Path) -> Suite:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Suite.model_validate(raw)


def filter_cases(suite: Suite, case_ids: Optional[Sequence[str]] = None) -> list[Case]:
    if not case_ids:
        return list(suite.cases)
    wanted = set(case_ids)
    selected = [c for c in suite.cases if c.id in wanted]
    missing = wanted - {c.id for c in selected}
    if missing:
        raise ValueError(f"Unknown case id(s): {', '.join(sorted(missing))}")
    return selected


def _build_messages(suite: Suite, case: Case) -> tuple[list[dict], str]:
    """Return (chat messages, rendered user input preview)."""
    vars_map = {**(suite.vars or {}), **(case.vars or {})}

    system = suite.system_prompt or ""
    if case.system_extra:
        system = (system + "\n" + case.system_extra).strip()
    system = render(system, vars_map)

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})

    rendered_preview = ""

    if case.messages:
        for m in case.messages:
            content = render(m.content, vars_map)
            messages.append({"role": m.role, "content": content})
            if m.role == "user":
                rendered_preview = content
    else:
        user_text = render(case.input or "", vars_map)
        messages.append({"role": "user", "content": user_text})
        rendered_preview = user_text

    return messages, rendered_preview


def run_suite(
    suite: Suite,
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    case_ids: Optional[Sequence[str]] = None,
) -> RunResult:
    """Execute cases and return a full RunResult with prompt snapshot."""
    client_kwargs = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    use_model = model or suite.model
    use_temp = suite.temperature if temperature is None else temperature
    cases = filter_cases(suite, case_ids)

    result = RunResult(
        suite_name=suite.name,
        model=use_model,
        temperature=use_temp,
        system_prompt=suite.system_prompt or "",
        total=len(cases),
        meta={"case_filter": list(case_ids) if case_ids else None},
    )

    for case in cases:
        messages, rendered_input = _build_messages(suite, case)

        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=use_temp,
            )
            output = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            case_result = CaseResult(
                case_id=case.id,
                passed=False,
                output="",
                failures=[
                    Failure(
                        check="model_call",
                        message=f"Model call failed: {e}",
                        expected="successful model response",
                        got=str(e),
                    )
                ],
                latency_ms=round(latency, 1),
                rendered_input=rendered_input,
            )
            result.case_results.append(case_result)
            result.failed += 1
            continue

        latency = (time.perf_counter() - t0) * 1000
        # Also template expect.similar_to / exact if they use vars
        expect = case.expect.model_copy(deep=True)
        vars_map = {**(suite.vars or {}), **(case.vars or {})}
        if expect.similar_to:
            expect.similar_to = render(expect.similar_to, vars_map)
        if expect.exact:
            expect.exact = render(expect.exact, vars_map)
        expect.contains = [render(x, vars_map) for x in expect.contains]
        expect.not_contains = [render(x, vars_map) for x in expect.not_contains]

        failures = score(output, expect)
        passed = len(failures) == 0

        case_result = CaseResult(
            case_id=case.id,
            passed=passed,
            output=output,
            failures=failures,
            latency_ms=round(latency, 1),
            rendered_input=rendered_input,
        )
        result.case_results.append(case_result)
        if passed:
            result.passed += 1
        else:
            result.failed += 1

    result.finished_at = datetime.utcnow()
    return result

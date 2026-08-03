from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from openai import OpenAI

from .models import CaseResult, RunResult, Suite
from .scorer import score


def load_suite(path: Path) -> Suite:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Suite.model_validate(raw)


def run_suite(
    suite: Suite,
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> RunResult:
    """Execute every case and return a full RunResult."""
    client_kwargs = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    use_model = model or suite.model
    use_temp = suite.temperature if temperature is None else temperature

    result = RunResult(
        suite_name=suite.name,
        model=use_model,
        temperature=use_temp,
        total=len(suite.cases),
    )

    for case in suite.cases:
        system = suite.system_prompt or ""
        if case.system_extra:
            system = (system + "\n" + case.system_extra).strip()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": case.input})

        t0 = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=use_temp,
            )
            output = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            output = ""
            failures = [f"model call failed: {e}"]
            latency = (time.perf_counter() - t0) * 1000
            case_result = CaseResult(
                case_id=case.id,
                passed=False,
                output=output,
                failures=failures,
                latency_ms=latency,
            )
            result.case_results.append(case_result)
            result.failed += 1
            continue

        latency = (time.perf_counter() - t0) * 1000
        failures = score(output, case.expect)
        passed = len(failures) == 0

        case_result = CaseResult(
            case_id=case.id,
            passed=passed,
            output=output,
            failures=failures,
            latency_ms=round(latency, 1),
        )
        result.case_results.append(case_result)
        if passed:
            result.passed += 1
        else:
            result.failed += 1

    result.finished_at = datetime.utcnow()
    return result

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

import yaml
from openai import OpenAI

from .models import Case, CaseResult, Failure, RunResult, Suite
from .scorer import score
from .template import render


def load_suite(path: Path) -> Suite:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    suite = Suite.model_validate(raw)

    if suite.system_prompt_file:
        prompt_path = Path(suite.system_prompt_file)
        if not prompt_path.is_absolute():
            prompt_path = path.parent / prompt_path
        if not prompt_path.exists():
            raise FileNotFoundError(f"system_prompt_file not found: {prompt_path}")
        file_text = prompt_path.read_text(encoding="utf-8").strip()
        if suite.system_prompt:
            suite.system_prompt = (suite.system_prompt.rstrip() + "\n\n" + file_text).strip()
        else:
            suite.system_prompt = file_text

    return suite


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


def _call_model(
    client: OpenAI,
    *,
    model: str,
    messages: list[dict],
    temperature: float,
) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()


def _run_one_case(
    client: OpenAI,
    suite: Suite,
    case: Case,
    *,
    model: str,
    temperature: float,
    retries: int = 0,
    timeout: Optional[float] = None,
) -> CaseResult:
    messages, rendered_input = _build_messages(suite, case)
    attempts = max(0, retries) + 1
    last_error: Optional[Exception] = None
    output = ""
    t0 = time.perf_counter()

    for attempt in range(attempts):
        try:
            if timeout and timeout > 0:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(
                        _call_model,
                        client,
                        model=model,
                        messages=messages,
                        temperature=temperature,
                    )
                    output = fut.result(timeout=timeout)
            else:
                output = _call_model(
                    client,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
            last_error = None
            break
        except FuturesTimeout as e:
            last_error = TimeoutError(f"case timed out after {timeout}s")
            break
        except Exception as e:
            last_error = e
            if attempt + 1 < attempts:
                time.sleep(0.4 * (attempt + 1))

    latency = (time.perf_counter() - t0) * 1000

    if last_error is not None:
        check = "timeout" if isinstance(last_error, TimeoutError) else "model_call"
        return CaseResult(
            case_id=case.id,
            passed=False,
            output="",
            failures=[
                Failure(
                    check=check,
                    message=f"Model call failed after {attempts} attempt(s): {last_error}",
                    expected="successful model response",
                    got=str(last_error),
                )
            ],
            latency_ms=round(latency, 1),
            rendered_input=rendered_input,
        )

    expect = case.expect.model_copy(deep=True)
    vars_map = {**(suite.vars or {}), **(case.vars or {})}
    if expect.similar_to:
        expect.similar_to = render(expect.similar_to, vars_map)
    if expect.exact:
        expect.exact = render(expect.exact, vars_map)
    expect.contains = [render(x, vars_map) for x in expect.contains]
    expect.not_contains = [render(x, vars_map) for x in expect.not_contains]

    failures = score(output, expect)
    return CaseResult(
        case_id=case.id,
        passed=len(failures) == 0,
        output=output,
        failures=failures,
        latency_ms=round(latency, 1),
        rendered_input=rendered_input,
    )


def run_suite(
    suite: Suite,
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    case_ids: Optional[Sequence[str]] = None,
    workers: int = 1,
    retries: int = 0,
    fail_fast: bool = False,
    timeout: Optional[float] = None,
) -> RunResult:
    """Execute cases (optionally in parallel) and return a RunResult."""
    client_kwargs = {}
    if api_key:
        client_kwargs["api_key"] = api_key
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    use_model = model or suite.model
    use_temp = suite.temperature if temperature is None else temperature
    cases = filter_cases(suite, case_ids)
    workers = max(1, workers)

    result = RunResult(
        suite_name=suite.name,
        model=use_model,
        temperature=use_temp,
        system_prompt=suite.system_prompt or "",
        total=len(cases),
        meta={
            "case_filter": list(case_ids) if case_ids else None,
            "workers": workers,
            "retries": retries,
            "fail_fast": fail_fast,
            "timeout": timeout,
        },
    )

    case_results: list[CaseResult] = []

    if workers == 1 or fail_fast:
        for case in cases:
            cr = _run_one_case(
                client,
                suite,
                case,
                model=use_model,
                temperature=use_temp,
                retries=retries,
                timeout=timeout,
            )
            case_results.append(cr)
            if fail_fast and not cr.passed:
                break
    else:
        by_id: dict[str, CaseResult] = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _run_one_case,
                    client,
                    suite,
                    case,
                    model=use_model,
                    temperature=use_temp,
                    retries=retries,
                    timeout=timeout,
                ): case.id
                for case in cases
            }
            for fut in as_completed(futures):
                cr = fut.result()
                by_id[cr.case_id] = cr
        case_results = [by_id[c.id] for c in cases if c.id in by_id]

    result.case_results = case_results
    result.passed = sum(1 for c in case_results if c.passed)
    result.failed = sum(1 for c in case_results if not c.passed)
    result.total = len(case_results)
    result.finished_at = datetime.utcnow()
    return result

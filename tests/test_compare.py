from promptguard.compare import compare_runs
from promptguard.models import CaseResult, RunResult


def _run(name, cases, prompt="p", model="m"):
    results = [
        CaseResult(case_id=cid, passed=passed, output=out)
        for cid, passed, out in cases
    ]
    passed = sum(1 for c in results if c.passed)
    return RunResult(
        suite_name=name,
        model=model,
        temperature=0.0,
        system_prompt=prompt,
        passed=passed,
        failed=len(results) - passed,
        total=len(results),
        case_results=results,
    )


def test_regression_and_fix():
    base = _run("s", [("a", True, "ok"), ("b", False, "bad")])
    cur = _run("s", [("a", False, "broke"), ("b", True, "fixed")])
    cmp = compare_runs(base, cur)
    kinds = {d.case_id: d.kind for d in cmp.deltas}
    assert kinds["a"] == "regressed"
    assert kinds["b"] == "fixed"
    assert cmp.regressed and cmp.fixed


def test_output_changed():
    base = _run("s", [("a", True, "version-1")])
    cur = _run("s", [("a", True, "version-2")])
    cmp = compare_runs(base, cur)
    assert cmp.deltas[0].output_changed is True
    assert cmp.deltas[0].kind == "still_pass"


def test_prompt_model_flags():
    base = _run("s", [("a", True, "x")], prompt="old", model="gpt-a")
    cur = _run("s", [("a", True, "x")], prompt="new", model="gpt-b")
    cmp = compare_runs(base, cur)
    assert cmp.prompt_changed
    assert cmp.model_changed

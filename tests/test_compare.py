import pytest

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


def test_new_and_removed_cases_are_not_regressions():
    base = _run("s", [("shared", True, "ok"), ("removed", False, "bad")])
    cur = _run("s", [("shared", True, "ok"), ("new", False, "bad")])
    cmp = compare_runs(base, cur)
    assert [d.case_id for d in cmp.new_cases] == ["new"]
    assert [d.case_id for d in cmp.removed_cases] == ["removed"]
    assert cmp.removed_cases[0].baseline_passed is False
    assert cmp.removed_cases[0].current_passed is None
    assert cmp.regressed == []
    assert cmp.fixed == []


def test_comparison_rejects_different_suites_with_matching_case_ids():
    base = _run("refund-policy", [("shared", True, "allowed")])
    cur = _run("ranking-policy", [("shared", False, "different task")])
    with pytest.raises(ValueError, match="Cannot compare different suites"):
        compare_runs(base, cur)

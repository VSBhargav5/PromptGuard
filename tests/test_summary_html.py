from promptguard.compare import compare_runs
from promptguard.html_report import to_html
from promptguard.models import CaseResult, Failure, RunResult
from promptguard.summary import to_compare_pr_summary, to_pr_summary


def _run(failed=False):
    cases = [
        CaseResult(case_id="ok", passed=True, output="hello", latency_ms=12),
    ]
    if failed:
        cases.append(
            CaseResult(
                case_id="broken",
                passed=False,
                output="nope",
                latency_ms=20,
                failures=[Failure(check="contains", message="missing help")],
            )
        )
    passed = sum(1 for c in cases if c.passed)
    return RunResult(
        suite_name="demo",
        model="gpt-x",
        temperature=0.0,
        system_prompt="Be helpful.",
        passed=passed,
        failed=len(cases) - passed,
        total=len(cases),
        case_results=cases,
    )


def test_pr_summary_pass():
    text = to_pr_summary(_run(failed=False))
    assert "PromptGuard" in text
    assert "1/1" in text
    assert "No failing" in text


def test_pr_summary_fail_lists_case():
    text = to_pr_summary(_run(failed=True))
    assert "broken" in text
    assert "contains" in text
    assert "failed" in text.lower()


def test_compare_pr_summary_regressed():
    base = _run(failed=False)
    cur = _run(failed=True)
    # make same case id regress: rewrite ids
    base.case_results = [CaseResult(case_id="a", passed=True, output="ok")]
    cur.case_results = [
        CaseResult(
            case_id="a",
            passed=False,
            output="bad",
            failures=[Failure(check="exact", message="mismatch")],
        )
    ]
    base.passed, base.failed, base.total = 1, 0, 1
    cur.passed, cur.failed, cur.total = 0, 1, 1
    text = to_compare_pr_summary(compare_runs(base, cur))
    assert "Regressed" in text
    assert "`a`" in text


def test_html_contains_suite_and_fail():
    html = to_html(_run(failed=True))
    assert "demo" in html
    assert "broken" in html
    assert "FAIL" in html
    assert "<!DOCTYPE html>" in html

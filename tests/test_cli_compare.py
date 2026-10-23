import pytest
from typer.testing import CliRunner

from promptguard import cli
from promptguard.models import CaseResult, RunResult
from promptguard.store import RunStore


def _run(cases):
    results = [
        CaseResult(case_id=case_id, passed=passed, output="fixture")
        for case_id, passed in cases
    ]
    passed = sum(c.passed for c in results)
    return RunResult(
        suite_name="coverage-demo",
        model="offline-fixture",
        temperature=0,
        total=len(results),
        passed=passed,
        failed=len(results) - passed,
        case_results=results,
    )


@pytest.fixture
def store(tmp_path, monkeypatch):
    store = RunStore(tmp_path / "runs")
    monkeypatch.setattr(cli, "RunStore", lambda: store)
    return store


@pytest.mark.parametrize("removed_passed", [True, False])
@pytest.mark.parametrize("strict,expected", [(False, 0), (True, 1)])
def test_compare_removed_coverage_gate(store, removed_passed, strict, expected, tmp_path):
    base = _run([("shared", True), ("removed", removed_passed)])
    cur = _run([("shared", True)])
    store.save(base)
    store.save(cur)
    report = tmp_path / "comparison.md"
    args = ["compare", base.id, cur.id, "--pr-summary", str(report)]
    if strict:
        args.append("--fail-on-removed")
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == expected, result.output
    assert "not evaluated in current run" in result.output
    assert "**Removed cases (1)**" in report.read_text(encoding="utf-8")


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("passed,expected", [(True, 0), (False, 1)])
def test_compare_shared_case_exit_status(store, strict, passed, expected):
    base = _run([("shared", True)])
    cur = _run([("shared", passed)])
    store.save(base)
    store.save(cur)
    args = ["compare", base.id, cur.id]
    if strict:
        args.append("--fail-on-removed")
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == expected, result.output


def test_compare_disjoint_coverage_warns(store):
    base = _run([("original", True)])
    cur = _run([("replacement", True)])
    store.save(base)
    store.save(cur)
    result = CliRunner().invoke(cli.app, ["compare", base.id, cur.id, "--fail-on-removed"])
    assert result.exit_code == 1, result.output
    assert "No shared cases" in result.output
    assert "No pass/fail changes" not in result.output


def test_run_coverage_gate_requires_baseline():
    result = CliRunner().invoke(cli.app, ["run", "unused.yaml", "--fail-on-removed"])
    assert result.exit_code == 1, result.output
    assert "--fail-on-removed requires --baseline" in result.output


@pytest.mark.parametrize("strict,expected", [(False, 0), (True, 1)])
@pytest.mark.parametrize("baseline_exists", [True, False])
def test_run_coverage_gate(store, monkeypatch, tmp_path, strict, expected, baseline_exists):
    base = _run([("shared", True), ("removed", False)])
    cur = _run([("shared", True)])
    if baseline_exists:
        store.save(base)
    suite = tmp_path / "suite.yaml"
    suite.write_text(
        "name: coverage-demo\ncases:\n  - id: shared\n    input: hello\n",
        encoding="utf-8",
    )
    # Replace only the model execution boundary; parsing, storage, comparison,
    # report writing, and exit codes use their normal implementations.
    monkeypatch.setattr(cli, "run_suite", lambda *args, **kwargs: cur)
    args = ["run", str(suite), "--baseline", "last"]
    if strict:
        args.append("--fail-on-removed")
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == expected, result.output
    if strict and not baseline_exists:
        assert "cannot verify case coverage" in result.output


def test_from_failed_empty_intersection_does_not_run_entire_suite(store, monkeypatch, tmp_path):
    from promptguard import runner

    previous = _run([("failed", False), ("passed", True)])
    store.save(previous)
    suite = tmp_path / "suite.yaml"
    suite.write_text(
        "name: coverage-demo\ncases:\n  - id: failed\n    input: help\n"
        "  - id: passed\n    input: hello\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "OpenAI", lambda **kwargs: pytest.fail("Unexpected client"))
    result = CliRunner().invoke(
        cli.app, ["run", str(suite), "--from-failed", previous.id, "--case", "passed"]
    )
    assert result.exit_code == 1, result.output
    assert "No cases selected" in result.output
    assert len(list(store.root.glob("*.json"))) == 1


@pytest.mark.parametrize("command", [["show-run", "common"], ["compare", "common", "common-one"]])
def test_ambiguous_run_id_has_a_clear_cli_error(store, command):
    for run_id in ("common-one", "common-two"):
        run = _run([("shared", True)])
        run.id = run_id
        store.save(run)
    result = CliRunner().invoke(cli.app, command)
    assert result.exit_code == 1, result.output
    assert "Ambiguous run ID prefix" in result.output


def test_path_run_id_has_a_clear_cli_error(store):
    result = CliRunner().invoke(cli.app, ["show-run", "../outside"])
    assert result.exit_code == 1, result.output
    assert "Run ID" in result.output

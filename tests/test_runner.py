import pytest

from promptguard import runner
from promptguard.models import Case, Suite


@pytest.mark.parametrize("case_ids", [[], ["missing"]])
def test_invalid_selection_fails_before_creating_client(monkeypatch, case_ids):
    def unexpected_client(**kwargs):
        pytest.fail("Invalid selection must not initialize a model client")

    monkeypatch.setattr(runner, "OpenAI", unexpected_client)
    suite = Suite(name="demo", cases=[Case(id="refund", input="help")])
    with pytest.raises(ValueError):
        runner.run_suite(suite, case_ids=case_ids)


def test_empty_suite_cannot_produce_a_passing_run(monkeypatch):
    monkeypatch.setattr(runner, "OpenAI", lambda **kwargs: pytest.fail("Unexpected client"))
    with pytest.raises(ValueError, match="No cases selected"):
        runner.run_suite(Suite(name="empty"))


def test_absent_filter_still_selects_all_cases():
    suite = Suite(name="demo", cases=[Case(id="a"), Case(id="b")])
    assert [case.id for case in runner.filter_cases(suite)] == ["a", "b"]

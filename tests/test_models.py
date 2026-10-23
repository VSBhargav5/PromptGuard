import pytest
from pydantic import ValidationError

from promptguard.models import Case, Expect, Suite


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan"), float("inf")])
def test_similarity_threshold_must_be_a_probability(threshold):
    with pytest.raises(ValidationError):
        Expect(min_similarity=threshold)


@pytest.mark.parametrize("field", ["min_chars", "max_chars"])
def test_negative_length_limits_are_rejected(field):
    with pytest.raises(ValidationError):
        Expect(**{field: -1})


def test_inverted_length_range_is_rejected():
    with pytest.raises(ValidationError, match="min_chars must not exceed max_chars"):
        Expect(min_chars=10, max_chars=5)


def test_length_and_similarity_boundaries_remain_valid():
    assert Expect(min_chars=0, max_chars=0, min_similarity=0).max_chars == 0
    assert Expect(min_chars=5, max_chars=5, min_similarity=1).min_similarity == 1


@pytest.mark.parametrize("case_id", ["", " ", "\t\n"])
def test_blank_case_ids_are_rejected(case_id):
    with pytest.raises(ValidationError, match="Case id must not be blank"):
        Case(id=case_id)


def test_direct_suite_construction_rejects_duplicate_ids():
    with pytest.raises(ValidationError, match="Duplicate case id"):
        Suite(name="demo", cases=[Case(id="refund"), Case(id="refund")])


def test_suite_preserves_distinct_case_identity_and_order():
    suite = Suite(name="demo", cases=[Case(id="refund"), Case(id="refund-followup")])
    assert [case.id for case in suite.cases] == ["refund", "refund-followup"]


@pytest.mark.parametrize("pattern", ["[", "(", "*", r"\k"])
def test_malformed_regex_is_rejected_before_execution(pattern):
    with pytest.raises(ValidationError, match="Invalid expectation regex"):
        Expect(regex=[pattern])


def test_valid_regex_patterns_are_preserved():
    patterns = [r"order #\d+", "(?i)refund", ""]
    assert Expect(regex=patterns).regex == patterns

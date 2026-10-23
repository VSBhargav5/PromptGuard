import pytest
from pydantic import ValidationError

from promptguard.models import Expect


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

from pathlib import Path

import pytest

from promptguard.models import Case, Expect, Suite
from promptguard.runner import filter_cases
from promptguard.validate import validate_suite


def test_filter_by_tag():
    suite = Suite(
        name="t",
        cases=[
            Case(id="a", input="x", tags=["smoke"], expect=Expect(contains=["x"])),
            Case(id="b", input="y", tags=["policy"], expect=Expect(contains=["y"])),
            Case(id="c", input="z", tags=["smoke", "policy"], expect=Expect()),
        ],
    )
    ids = [c.id for c in filter_cases(suite, tags=["smoke"])]
    assert ids == ["a", "c"]


def test_filter_tag_none_match():
    suite = Suite(
        name="t",
        cases=[Case(id="a", input="x", tags=["smoke"])],
    )
    with pytest.raises(ValueError, match="No cases match"):
        filter_cases(suite, tags=["missing"])


def test_validate_ok(tmp_path: Path):
    p = tmp_path / "s.yaml"
    p.write_text(
        """name: demo
system_prompt: You are helpful.
cases:
  - id: a
    input: hi
    expect:
      contains: [hello]
""",
        encoding="utf-8",
    )
    suite, warnings = validate_suite(p)
    assert suite.name == "demo"
    assert warnings == []


def test_validate_duplicate_ids(tmp_path: Path):
    p = tmp_path / "s.yaml"
    p.write_text(
        """name: demo
cases:
  - id: a
    input: hi
  - id: a
    input: bye
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate"):
        validate_suite(p)

from __future__ import annotations

from pathlib import Path

from .models import Suite
from .runner import load_suite


def validate_suite(path: Path) -> tuple[Suite, list[str]]:
    """Load and lint a suite. Returns (suite, warnings). Raises on hard errors."""
    suite = load_suite(path)
    warnings: list[str] = []

    if not suite.cases:
        raise ValueError("Suite has no cases")

    ids = [c.id for c in suite.cases]
    if len(ids) != len(set(ids)):
        seen: set[str] = set()
        dups = []
        for i in ids:
            if i in seen:
                dups.append(i)
            seen.add(i)
        raise ValueError(f"Duplicate case id(s): {', '.join(sorted(set(dups)))}")

    for case in suite.cases:
        if not case.input and not case.messages:
            warnings.append(f"{case.id}: no input and no messages")
        if case.input and case.messages:
            warnings.append(f"{case.id}: both input and messages set; messages win at runtime")
        for m in case.messages:
            if m.role not in ("system", "user", "assistant"):
                warnings.append(f"{case.id}: unusual message role '{m.role}'")
        exp = case.expect
        if (
            not exp.contains
            and not exp.not_contains
            and not exp.regex
            and exp.exact is None
            and not exp.json_valid
            and not exp.json_keys
            and exp.similar_to is None
            and exp.max_chars is None
            and exp.min_chars is None
        ):
            warnings.append(f"{case.id}: no expectations defined (will always pass)")

    if not suite.system_prompt and not suite.system_prompt_file:
        warnings.append("no system_prompt or system_prompt_file")

    return suite, warnings

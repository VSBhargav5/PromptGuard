from __future__ import annotations

import json
import re
from typing import List

from .models import Expect


def score(output: str, expect: Expect) -> List[str]:
    """Return list of failure messages. Empty list means pass."""
    failures: list[str] = []
    text = output or ""

    for needle in expect.contains:
        if needle.lower() not in text.lower():
            failures.append(f'expected contains: "{needle}"')

    for needle in expect.not_contains:
        if needle.lower() in text.lower():
            failures.append(f'expected not_contains: "{needle}"')

    for pattern in expect.regex:
        if not re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            failures.append(f'expected regex: /{pattern}/')

    if expect.exact is not None:
        got = " ".join(text.split())
        want = " ".join(expect.exact.split())
        if got != want:
            failures.append(f'expected exact match (normalized)')

    if expect.json_valid or expect.json_keys:
        try:
            # Allow fenced code blocks
            candidate = text.strip()
            if candidate.startswith("```"):
                lines = candidate.split("\n")
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                candidate = "\n".join(lines)
            data = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            failures.append("expected valid JSON")
            return failures

        if not isinstance(data, dict):
            failures.append("expected JSON object")
            return failures

        for key in expect.json_keys:
            if key not in data:
                failures.append(f'expected json key: "{key}"')

    return failures

from __future__ import annotations

import json
import re
from typing import List, Optional

from .models import Expect, Failure


def _preview(text: str, limit: int = 160) -> str:
    one_line = " ".join((text or "").split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1] + "…"


def _fail(
    check: str,
    message: str,
    *,
    expected: Optional[str] = None,
    got: Optional[str] = None,
) -> Failure:
    return Failure(check=check, message=message, expected=expected, got=got)


def score(output: str, expect: Expect) -> List[Failure]:
    """Return structured failures. Empty list means pass."""
    failures: list[Failure] = []
    text = output or ""
    got_preview = _preview(text)

    for needle in expect.contains:
        if needle.lower() not in text.lower():
            failures.append(
                _fail(
                    "contains",
                    f'Missing required phrase: "{needle}"',
                    expected=needle,
                    got=got_preview or "(empty output)",
                )
            )

    for needle in expect.not_contains:
        if needle.lower() in text.lower():
            failures.append(
                _fail(
                    "not_contains",
                    f'Forbidden phrase present: "{needle}"',
                    expected=f'not present: "{needle}"',
                    got=got_preview,
                )
            )

    for pattern in expect.regex:
        if not re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            failures.append(
                _fail(
                    "regex",
                    f"No match for regex /{pattern}/",
                    expected=f"/{pattern}/",
                    got=got_preview or "(empty output)",
                )
            )

    if expect.exact is not None:
        got_norm = " ".join(text.split())
        want_norm = " ".join(expect.exact.split())
        if got_norm != want_norm:
            failures.append(
                _fail(
                    "exact",
                    "Output does not match expected text (whitespace-normalized)",
                    expected=_preview(want_norm, 200),
                    got=_preview(got_norm, 200) or "(empty output)",
                )
            )

    if expect.json_valid or expect.json_keys:
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            candidate = "\n".join(lines)

        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, TypeError) as e:
            failures.append(
                _fail(
                    "json_valid",
                    f"Expected valid JSON ({e})",
                    expected="valid JSON object",
                    got=got_preview or "(empty output)",
                )
            )
            return failures

        if not isinstance(data, dict):
            failures.append(
                _fail(
                    "json_valid",
                    f"Expected JSON object, got {type(data).__name__}",
                    expected="JSON object {{...}}",
                    got=_preview(str(data)),
                )
            )
            return failures

        for key in expect.json_keys:
            if key not in data:
                failures.append(
                    _fail(
                        "json_key",
                        f'Missing JSON key: "{key}"',
                        expected=f'key "{key}" present',
                        got=f"keys: {list(data.keys())}",
                    )
                )

    return failures

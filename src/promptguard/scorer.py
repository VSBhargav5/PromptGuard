from __future__ import annotations

import json
import re
from typing import List, Optional, Set

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


def _tokens(text: str) -> Set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def token_jaccard(a: str, b: str) -> float:
    """Lexical similarity in [0, 1]. Empty vs empty is 1.0."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


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

    if expect.similar_to is not None:
        sim = token_jaccard(text, expect.similar_to)
        if sim < expect.min_similarity:
            failures.append(
                _fail(
                    "similar_to",
                    f"Lexical similarity {sim:.2f} < min {expect.min_similarity:.2f}",
                    expected=_preview(expect.similar_to, 120),
                    got=got_preview or "(empty output)",
                )
            )

    if expect.max_chars is not None and len(text) > expect.max_chars:
        failures.append(
            _fail(
                "max_chars",
                f"Output length {len(text)} exceeds max_chars {expect.max_chars}",
                expected=f"<= {expect.max_chars} chars",
                got=f"{len(text)} chars",
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

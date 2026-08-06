from __future__ import annotations

import re
from typing import Any


_VAR = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def render(text: str, variables: dict[str, Any] | None = None) -> str:
    """Replace {{name}} placeholders. Unknown vars are left unchanged."""
    if not text or not variables:
        return text or ""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in variables:
            return str(variables[key])
        return match.group(0)

    return _VAR.sub(repl, text)

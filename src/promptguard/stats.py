from __future__ import annotations

from typing import Optional

from .models import RunResult


def latency_summary(result: RunResult) -> Optional[dict[str, float]]:
    vals = sorted(
        c.latency_ms for c in result.case_results if c.latency_ms is not None
    )
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    if n % 2:
        p50 = vals[mid]
    else:
        p50 = (vals[mid - 1] + vals[mid]) / 2
    p95_idx = min(n - 1, max(0, int(round(0.95 * (n - 1)))))
    return {
        "count": float(n),
        "avg_ms": round(sum(vals) / n, 1),
        "p50_ms": round(p50, 1),
        "p95_ms": round(vals[p95_idx], 1),
        "max_ms": round(vals[-1], 1),
        "min_ms": round(vals[0], 1),
    }

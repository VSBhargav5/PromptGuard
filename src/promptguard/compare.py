from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import CaseResult, RunResult


@dataclass
class CaseDelta:
    case_id: str
    baseline_passed: Optional[bool]
    current_passed: Optional[bool]

    @property
    def kind(self) -> str:
        if self.baseline_passed is None:
            return "new"
        if self.current_passed is None:
            return "removed"
        if self.baseline_passed and not self.current_passed:
            return "regressed"
        if not self.baseline_passed and self.current_passed:
            return "fixed"
        if self.current_passed:
            return "still_pass"
        return "still_fail"


@dataclass
class CompareResult:
    baseline: RunResult
    current: RunResult
    deltas: list[CaseDelta] = field(default_factory=list)

    @property
    def regressed(self) -> list[CaseDelta]:
        return [d for d in self.deltas if d.kind == "regressed"]

    @property
    def fixed(self) -> list[CaseDelta]:
        return [d for d in self.deltas if d.kind == "fixed"]

    @property
    def still_fail(self) -> list[CaseDelta]:
        return [d for d in self.deltas if d.kind == "still_fail"]

    @property
    def new_cases(self) -> list[CaseDelta]:
        return [d for d in self.deltas if d.kind == "new"]


def compare_runs(baseline: RunResult, current: RunResult) -> CompareResult:
    base_map = {c.case_id: c for c in baseline.case_results}
    cur_map = {c.case_id: c for c in current.case_results}
    ids = sorted(set(base_map) | set(cur_map))

    deltas: list[CaseDelta] = []
    for cid in ids:
        b: Optional[CaseResult] = base_map.get(cid)
        c: Optional[CaseResult] = cur_map.get(cid)
        deltas.append(
            CaseDelta(
                case_id=cid,
                baseline_passed=None if b is None else b.passed,
                current_passed=None if c is None else c.passed,
            )
        )

    return CompareResult(baseline=baseline, current=current, deltas=deltas)

from __future__ import annotations

import re
from tempfile import NamedTemporaryFile
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .models import RunResult


DEFAULT_DIR = Path.home() / ".promptguard" / "runs"


def _validate_run_id(run_id: str) -> None:
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        raise ValueError("Run ID must contain only letters, digits, underscores, or hyphens")


class RunStore:
    def __init__(self, root: Path | str = DEFAULT_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, run: RunResult) -> Path:
        _validate_run_id(run.id)
        path = self.root / f"{run.id}.json"
        content = run.model_dump_json(indent=2)
        temporary: Optional[Path] = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.root, prefix=".run-", suffix=".tmp", delete=False
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return path

    def list_runs(self, limit: int = 20, suite: Optional[str] = None) -> list[dict]:
        files = sorted(
            self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        out = []
        for f in files:
            if len(out) >= limit:
                break
            try:
                run = RunResult.model_validate_json(f.read_text(encoding="utf-8"))
                if suite and run.suite_name != suite:
                    continue
                out.append(
                    {
                        "id": run.id,
                        "suite_name": run.suite_name,
                        "model": run.model,
                        "passed": run.passed,
                        "failed": run.failed,
                        "total": run.total,
                        "started_at": run.started_at.isoformat(),
                    }
                )
            except (ValidationError, OSError):
                continue
        return out

    def get(self, run_id: str) -> Optional[RunResult]:
        _validate_run_id(run_id)
        path = self.root / f"{run_id}.json"
        if path.exists():
            return RunResult.model_validate_json(path.read_text(encoding="utf-8"))
        matches = sorted(f for f in self.root.glob("*.json") if f.stem.startswith(run_id))
        if len(matches) > 1:
            raise ValueError(f"Ambiguous run ID prefix '{run_id}'; use a longer ID")
        if not matches:
            return None
        return RunResult.model_validate_json(matches[0].read_text(encoding="utf-8"))

    def latest_for_suite(
        self, suite_name: str, *,
        only_passing: bool = False,
        exclude_id: Optional[str] = None,
    ) -> Optional[RunResult]:
        """Most recent run for a suite (optionally last fully-passing)."""
        files = sorted(
            self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        for f in files:
            try:
                run = RunResult.model_validate_json(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if run.suite_name != suite_name:
                continue
            if exclude_id and (
                run.id == exclude_id or run.id.startswith(exclude_id)
            ):
                continue
            if only_passing and run.failed != 0:
                continue
            return run
        return None

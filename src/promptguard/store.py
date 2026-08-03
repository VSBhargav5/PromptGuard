from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import RunResult


DEFAULT_DIR = Path.home() / ".promptguard" / "runs"


class RunStore:
    def __init__(self, root: Path | str = DEFAULT_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, run: RunResult) -> Path:
        path = self.root / f"{run.id}.json"
        path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        return path

    def list_runs(self, limit: int = 20) -> list[dict]:
        files = sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        out = []
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                out.append(
                    {
                        "id": data.get("id", f.stem),
                        "suite_name": data.get("suite_name"),
                        "model": data.get("model"),
                        "passed": data.get("passed"),
                        "failed": data.get("failed"),
                        "total": data.get("total"),
                        "started_at": data.get("started_at"),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        return out

    def get(self, run_id: str) -> Optional[RunResult]:
        # full id or prefix
        path = self.root / f"{run_id}.json"
        if path.exists():
            return RunResult.model_validate_json(path.read_text(encoding="utf-8"))
        for f in self.root.glob("*.json"):
            if f.stem.startswith(run_id):
                return RunResult.model_validate_json(f.read_text(encoding="utf-8"))
        return None

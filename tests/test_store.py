from pathlib import Path

import pytest

from promptguard.models import RunResult
from promptguard.store import RunStore


def _run(run_id="run-one"):
    return RunResult(id=run_id, suite_name="demo", model="offline", temperature=0)


@pytest.mark.parametrize("run_id", ["", "..", "../outside", r"..\outside", "/outside", "run:stream"])
def test_get_rejects_paths_and_empty_prefixes(tmp_path, run_id):
    outside = tmp_path / "outside.json"
    outside.write_text(_run().model_dump_json(), encoding="utf-8")
    store = RunStore(tmp_path / "runs")
    with pytest.raises(ValueError, match="Run ID"):
        store.get(run_id)
    assert outside.exists()


@pytest.mark.parametrize("run_id", ["../outside", r"..\outside", "/outside", "run:stream"])
def test_save_rejects_path_ids_without_writing(tmp_path, run_id):
    store = RunStore(tmp_path / "runs")
    with pytest.raises(ValueError, match="Run ID"):
        store.save(_run(run_id))
    assert list(store.root.iterdir()) == []
    assert not (tmp_path / "outside.json").exists()


def test_save_and_get_uuid_and_named_ids(tmp_path):
    store = RunStore(tmp_path)
    for run_id in ("alpha_1-test", "da62302d-5b37-4ad3-b9a2-706b0c10f7ce"):
        run = _run(run_id)
        assert store.save(run).parent == tmp_path
        assert store.get(run_id) == run


def test_ambiguous_prefix_is_not_resolved_arbitrarily(tmp_path):
    store = RunStore(tmp_path)
    store.save(_run("alpha-one"))
    store.save(_run("alpha-two"))
    with pytest.raises(ValueError, match="Ambiguous run ID prefix"):
        store.get("alpha")
    assert store.get("alpha-o").id == "alpha-one"
    assert store.get("missing") is None


def test_exact_id_takes_precedence_over_prefix_matches(tmp_path):
    store = RunStore(tmp_path)
    for run_id in ("alpha", "alpha-one", "alpha-two"):
        store.save(_run(run_id))
    assert store.get("alpha").id == "alpha"


def test_failed_atomic_replace_preserves_previous_run_and_cleans_temporary_file(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    original = _run()
    destination = store.save(original)
    original_bytes = destination.read_bytes()
    updated = original.model_copy(update={"model": "changed"})

    def fail_replace(self, target):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replacement failure"):
        store.save(updated)
    assert destination.read_bytes() == original_bytes
    assert store.get(original.id) == original
    assert list(tmp_path.glob("*.tmp")) == []


def test_atomic_save_can_replace_existing_run_without_leftover_files(tmp_path):
    store = RunStore(tmp_path)
    run = _run()
    store.save(run)
    updated = run.model_copy(update={"model": "changed"})
    store.save(updated)
    assert store.get(run.id) == updated
    assert [path.name for path in tmp_path.iterdir()] == [f"{run.id}.json"]


@pytest.mark.parametrize("content", ["[]", "null", "1", "{}", '{"passed": "many"}', "{broken"])
def test_list_runs_skips_invalid_history_without_losing_valid_runs(tmp_path, content):
    store = RunStore(tmp_path)
    valid = _run("valid-run")
    store.save(valid)
    (tmp_path / "bad.json").write_text(content, encoding="utf-8")
    rows = store.list_runs(limit=1)
    assert len(rows) == 1
    assert rows[0]["id"] == valid.id
    assert rows[0]["started_at"] == valid.started_at.isoformat()


def test_list_runs_filters_valid_history_by_suite(tmp_path):
    store = RunStore(tmp_path)
    store.save(_run("demo-run"))
    other = _run("other-run").model_copy(update={"suite_name": "other"})
    store.save(other)
    assert [row["id"] for row in store.list_runs(suite="other")] == [other.id]

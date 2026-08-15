from __future__ import annotations

import pytest

from taskpin import TaskPinError, normalize_snapshot, snapshot
from tests.conftest import BASE, INSTRUCTION, ROOT_A, ROOT_B, sample_snapshot


def test_default_allowed_paths_is_dot() -> None:
    built = snapshot(repo_id=ROOT_A, base_commit=BASE)
    assert built["allowed_paths"] == ["."]
    assert built["instruction_digest"] is None
    assert built["worktree_key"] == ""


def test_null_instruction_digest_distinct_from_digest() -> None:
    null_snap = normalize_snapshot(sample_snapshot())
    hashed = normalize_snapshot(sample_snapshot(instruction_digest=INSTRUCTION))
    assert null_snap["instruction_digest"] is None
    assert hashed["instruction_digest"] == INSTRUCTION
    assert null_snap != hashed


def test_malformed_instruction_digest_rejected() -> None:
    with pytest.raises(TaskPinError) as exc:
        normalize_snapshot(sample_snapshot(instruction_digest="not-a-digest"))
    assert exc.value.code == "INVALID_INSTRUCTION_DIGEST"


def test_uppercase_instruction_digest_rejected() -> None:
    with pytest.raises(TaskPinError) as exc:
        normalize_snapshot(sample_snapshot(instruction_digest=INSTRUCTION.upper()))
    assert exc.value.code == "INVALID_INSTRUCTION_DIGEST"


def test_malformed_base_commit_rejected() -> None:
    with pytest.raises(TaskPinError) as exc:
        normalize_snapshot(sample_snapshot(base_commit="HEAD"))
    assert exc.value.code == "INVALID_BASE_COMMIT"
    with pytest.raises(TaskPinError) as exc:
        normalize_snapshot(sample_snapshot(base_commit=BASE.upper()))
    assert exc.value.code == "INVALID_BASE_COMMIT"
    with pytest.raises(TaskPinError) as exc:
        normalize_snapshot(sample_snapshot(base_commit=BASE[:-1]))
    assert exc.value.code == "INVALID_BASE_COMMIT"


def test_unknown_snapshot_fields_rejected() -> None:
    raw = sample_snapshot()
    raw["task_id"] = "nope"
    with pytest.raises(TaskPinError) as exc:
        normalize_snapshot(raw)
    assert exc.value.code == "UNKNOWN_FIELD"


def test_missing_required_fields_rejected() -> None:
    raw = sample_snapshot()
    del raw["base_commit"]
    with pytest.raises(TaskPinError) as exc:
        normalize_snapshot(raw)
    assert exc.value.code == "MISSING_FIELD"


def test_allowed_paths_sort_and_dedupe() -> None:
    normalized = normalize_snapshot(
        sample_snapshot(allowed_paths=["src/b", "src/a", "src/a/", "src/b"])
    )
    assert normalized["allowed_paths"] == ["src/a", "src/b"]


def test_allowed_paths_rejects_glob_absolute_and_dotdot() -> None:
    for bad in ("src/**", "/etc", "../escape", "foo/../bar", r"src\win"):
        with pytest.raises(TaskPinError) as exc:
            normalize_snapshot(sample_snapshot(allowed_paths=[bad]))
        assert exc.value.code == "INVALID_ALLOWED_PATHS"


def test_repo_id_sort_and_dedupe() -> None:
    normalized = normalize_snapshot(
        sample_snapshot(repo_id=f"{ROOT_B},{ROOT_A},{ROOT_A}")
    )
    assert normalized["repo_id"] == f"{ROOT_A},{ROOT_B}"


def test_worktree_key_main_and_linked() -> None:
    assert normalize_snapshot(sample_snapshot(worktree_key=""))["worktree_key"] == ""
    linked = normalize_snapshot(sample_snapshot(worktree_key="worktrees/agent-b/"))
    assert linked["worktree_key"] == "worktrees/agent-b"
    with pytest.raises(TaskPinError) as exc:
        normalize_snapshot(sample_snapshot(worktree_key="/abs"))
    assert exc.value.code == "INVALID_WORKTREE_KEY"

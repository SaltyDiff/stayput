from __future__ import annotations

import json
from pathlib import Path

import pytest

from stayput import (
    DEFAULT_APPROVAL_PATH,
    StayPutError,
    check,
    digest_instruction,
    save,
    verify_approval,
)
from tests.gitutil import commit_file, init_repo


def test_save_creates_valid_approval(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    result = save(repo)
    target = repo / DEFAULT_APPROVAL_PATH
    assert result["ok"] is True
    assert Path(result["path"]) == target
    assert target.is_file()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert set(loaded) == {"schema_version", "snapshot", "record_digest"}
    assert loaded["schema_version"] == "stayput.approval.v0.1"
    assert set(loaded["snapshot"]) == {
        "schema_version",
        "instruction_digest",
        "repo_id",
        "worktree_key",
        "base_commit",
        "allowed_paths",
    }
    verify_approval(loaded)
    leftover = list((repo / ".stayput").glob(".approval-*.tmp"))
    assert leftover == []


def test_save_default_allowed_paths(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    approval = save(repo)["approval"]
    assert approval["snapshot"]["allowed_paths"] == ["."]


def test_save_explicit_allowed_paths_canonical(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    approval = save(repo, allowed_paths=["src/z", "src/a", "src/a"])["approval"]
    assert approval["snapshot"]["allowed_paths"] == ["src/a", "src/z"]


def test_save_null_instruction(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    approval = save(repo)["approval"]
    assert approval["snapshot"]["instruction_digest"] is None


def test_save_supplied_bytes_seal_digest(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    approval = save(repo, instruction_bytes=b"abc")["approval"]
    assert approval["snapshot"]["instruction_digest"] == digest_instruction(b"abc")


def test_second_save_without_replace_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    first = save(repo)
    with pytest.raises(StayPutError) as exc:
        save(repo)
    assert exc.value.code == "APPROVAL_ALREADY_EXISTS"
    assert json.loads((repo / DEFAULT_APPROVAL_PATH).read_text(encoding="utf-8"))[
        "record_digest"
    ] == first["approval"]["record_digest"]


def test_explicit_replace_changes_digest(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    first = save(repo)
    commit_file(repo, "a.txt", "a\nb\n", "second")
    second = save(repo, replace=True)
    assert second["approval"]["record_digest"] != first["approval"]["record_digest"]
    assert second["approval"]["snapshot"]["base_commit"] != first["approval"][
        "snapshot"
    ]["base_commit"]
    assert check(repo)["status"] == "MATCH"


def test_save_does_not_add_host_metadata(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    raw = (repo / DEFAULT_APPROVAL_PATH).read_text(encoding="utf-8")
    for banned in ("timestamp", "user", "email", "branch", "host", "HOME"):
        assert banned not in raw

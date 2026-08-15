from __future__ import annotations

import json
from pathlib import Path

import pytest

from taskpin import (
    BASE_COMMIT_MISMATCH,
    DEFAULT_APPROVAL_PATH,
    INSTRUCTION_DRIFT,
    PATH_OUTSIDE_ALLOWLIST,
    REPOSITORY_MISMATCH,
    WORKTREE_MISMATCH,
    TaskPinError,
    check,
    save,
)
from tests.gitutil import commit_file, git, init_repo, write_file


def _write_exec(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_check_match_unchanged(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    result = check(repo)
    assert result["status"] == "MATCH"
    assert result["mismatches"] == []
    assert result["delivered_paths"] == []


def test_check_match_head_advance(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    commit_file(repo, "a.txt", "a\nb\n", "second")
    result = check(repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["a.txt"]


def test_check_match_in_scope_dirty(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    save(repo, allowed_paths=["src/auth"])
    write_file(repo, "src/auth/a.py", "dirty\n")
    assert check(repo)["status"] == "MATCH"


def test_check_match_exact_instruction_bytes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo, instruction_bytes=b"do this")
    result = check(repo, instruction_bytes=b"do this")
    assert result["status"] == "MATCH"


def test_check_match_null_instruction_without_bytes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    assert check(repo)["status"] == "MATCH"


def test_check_wrong_repository(tmp_path: Path) -> None:
    a = init_repo(tmp_path / "a")
    b = init_repo(tmp_path / "b")
    commit_file(a, "a.txt", "a\n", "a")
    commit_file(b, "b.txt", "b\n", "b")
    save(a)
    result = check(b, path=a / DEFAULT_APPROVAL_PATH)
    assert result["status"] == "MISMATCH"
    assert result["mismatches"][0]["class"] == REPOSITORY_MISMATCH


def test_check_wrong_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", str(linked), "-b", "feat")
    save(linked)
    result = check(repo, path=linked / DEFAULT_APPROVAL_PATH)
    assert WORKTREE_MISMATCH in [m["class"] for m in result["mismatches"]]


def test_check_invalid_base_lineage(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    git(repo, "checkout", "--orphan", "other")
    commit_file(repo, "o.txt", "o\n", "orphan")
    result = check(repo)
    assert BASE_COMMIT_MISMATCH in [m["class"] for m in result["mismatches"]]


def test_check_out_of_scope_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    save(repo, allowed_paths=["src/auth"])
    write_file(repo, "docs/out.md", "x\n")
    result = check(repo)
    assert [m["class"] for m in result["mismatches"]] == [PATH_OUTSIDE_ALLOWLIST]


def test_check_instruction_drift(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo, instruction_bytes=b"abc")
    result = check(repo, instruction_bytes=b"abd")
    assert [m["class"] for m in result["mismatches"]] == [INSTRUCTION_DRIFT]


def test_check_missing_approval(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "APPROVAL_MISSING"
    assert not (repo / DEFAULT_APPROVAL_PATH).exists()


def test_check_malformed_json(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    target = repo / DEFAULT_APPROVAL_PATH
    target.parent.mkdir()
    target.write_text("{not json", encoding="utf-8")
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "INVALID_APPROVAL"


def test_check_wrong_wrapper_schema(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    target = repo / DEFAULT_APPROVAL_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["schema_version"] = "taskpin.approval.v9.9"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "UNSUPPORTED_SCHEMA"


def test_check_unknown_wrapper_field(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    target = repo / DEFAULT_APPROVAL_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["extra"] = True
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "UNKNOWN_FIELD"


def test_check_malformed_snapshot(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    target = repo / DEFAULT_APPROVAL_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["snapshot"]["base_commit"] = "not-a-sha"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "INVALID_BASE_COMMIT"


def test_check_altered_snapshot_stale_digest(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    target = repo / DEFAULT_APPROVAL_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["snapshot"]["allowed_paths"] = ["src/auth"]
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "DIGEST_MISMATCH"


def test_check_altered_record_digest(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    target = repo / DEFAULT_APPROVAL_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["record_digest"] = "0" * 64
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "DIGEST_MISMATCH"


def test_check_sealed_instruction_without_bytes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo, instruction_bytes=b"need me")
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "INSTRUCTION_REQUIRED"


def test_check_unreadable_approval(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    target = repo / DEFAULT_APPROVAL_PATH
    target.parent.mkdir()
    target.mkdir()
    with pytest.raises(TaskPinError) as exc:
        check(repo)
    assert exc.value.code == "APPROVAL_UNREADABLE"


def test_check_git_failure_fails_closed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    save(repo)
    fake = _write_exec(
        tmp_path / "nope",
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo "git version 2.30.0"; exit 0; fi\n'
        "exit 128\n",
    )
    with pytest.raises(TaskPinError) as exc:
        check(repo, git_bin=str(fake))
    assert exc.value.code == "GIT_TOO_OLD"


def test_check_does_not_create_or_repair(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    with pytest.raises(TaskPinError):
        check(repo)
    assert not (repo / ".taskpin").exists()


def test_check_excludes_only_the_approval_artifact(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    save(repo, allowed_paths=["src/auth"])
    write_file(repo, ".taskpin/notes.txt", "not the seal\n")
    result = check(repo)
    assert result["status"] == "MISMATCH"
    assert ".taskpin/approval.json" not in result["delivered_paths"]
    assert ".taskpin/notes.txt" in result["delivered_paths"]
    assert PATH_OUTSIDE_ALLOWLIST in [m["class"] for m in result["mismatches"]]


def test_mismatch_does_not_reapprove(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    first = save(repo, allowed_paths=["src/auth"])
    write_file(repo, "docs/out.md", "x\n")
    result = check(repo)
    assert result["status"] == "MISMATCH"
    after = json.loads((repo / DEFAULT_APPROVAL_PATH).read_text(encoding="utf-8"))
    assert after["record_digest"] == first["approval"]["record_digest"]

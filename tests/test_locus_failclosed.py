from __future__ import annotations

from pathlib import Path

import pytest

from taskpin import TaskPinError, compare_locus, project_locus, project_snapshot
from taskpin.gitops import merge_base_is_ancestor
from tests.gitutil import commit_file, git, init_repo


def _write_exec(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_shallow_clone_fails_closed(tmp_path: Path) -> None:
    full = init_repo(tmp_path / "full")
    commit_file(full, "a.txt", "1\n", "r1")
    commit_file(full, "a.txt", "1\n2\n", "r2")
    commit_file(full, "a.txt", "1\n2\n3\n", "r3")
    shallow = tmp_path / "shallow"
    git(tmp_path, "clone", "--depth", "1", f"file://{full}", str(shallow))
    with pytest.raises(TaskPinError) as exc:
        project_locus(shallow)
    assert exc.value.code == "SHALLOW_REPOSITORY"


def test_grafts_fail_closed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    grafts = repo / ".git" / "info" / "grafts"
    grafts.parent.mkdir(parents=True, exist_ok=True)
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    grafts.write_text(f"{head}\n", encoding="utf-8")
    with pytest.raises(TaskPinError) as exc:
        project_locus(repo)
    assert exc.value.code == "GRAFTS_PRESENT"


def test_replace_refs_do_not_alter_identity(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    first = commit_file(repo, "a.txt", "1\n", "r1")
    commit_file(repo, "a.txt", "1\n2\n", "r2")
    third = commit_file(repo, "a.txt", "1\n2\n3\n", "r3")
    before = project_locus(repo)
    git(repo, "replace", "--graft", third)
    visible = git(repo, "rev-list", "--max-parents=0", "HEAD").stdout.strip()
    assert visible == third
    after = project_locus(repo)
    assert after["repo_id"] == before["repo_id"]
    assert after["repo_id"] == first
    assert after["repo_id"] != third


def test_bare_repository_fails_closed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    bare = tmp_path / "bare.git"
    git(tmp_path, "clone", "--bare", str(repo), str(bare))
    with pytest.raises(TaskPinError) as exc:
        project_locus(bare)
    assert exc.value.code == "BARE_REPOSITORY"


def test_not_a_repository(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(TaskPinError) as exc:
        project_locus(empty)
    assert exc.value.code == "NOT_A_REPOSITORY"


def test_unsupported_git_version(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    fake = _write_exec(
        tmp_path / "old-git",
        "#!/bin/sh\n"
        'if [ "$1" = "--version" ]; then echo "git version 2.30.0"; exit 0; fi\n'
        "exec git \"$@\"\n",
    )
    with pytest.raises(TaskPinError) as exc:
        project_locus(repo, git_bin=str(fake))
    assert exc.value.code == "GIT_TOO_OLD"


def test_merge_base_exit_128_is_operational(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    fake = _write_exec(
        tmp_path / "weird-git",
        "#!/bin/sh\n"
        'for arg in "$@"; do\n'
        '  if [ "$arg" = "merge-base" ]; then exit 128; fi\n'
        "done\n"
        "exec git \"$@\"\n",
    )
    with pytest.raises(TaskPinError) as exc:
        compare_locus(sealed, repo, git_bin=str(fake))
    assert exc.value.code == "CANNOT_PROVE_ANCESTRY"
    assert merge_base_is_ancestor(repo, sealed["base_commit"], git_bin=str(fake)) == 128


def test_missing_git_binary(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    with pytest.raises(TaskPinError) as exc:
        project_locus(repo, git_bin=str(tmp_path / "no-such-git"))
    assert exc.value.code == "GIT_NOT_FOUND"


def test_corrupt_object_fails_closed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    sha = commit_file(repo, "a.txt", "a\n", "first")
    obj = repo / ".git" / "objects" / sha[:2] / sha[2:]
    assert obj.is_file()
    obj.chmod(0o644)
    obj.write_bytes(b"not-a-git-object")
    with pytest.raises(TaskPinError) as exc:
        project_locus(repo)
    assert exc.value.code in {"GIT_INCOMPLETE", "GIT_FAILURE"}


def test_t1_schema_unchanged_by_projection(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    snap = project_snapshot(repo)
    assert set(snap) == {
        "schema_version",
        "instruction_digest",
        "repo_id",
        "worktree_key",
        "base_commit",
        "allowed_paths",
    }
    assert snap["schema_version"] == "taskpin.snapshot.v0.1"
    assert snap["instruction_digest"] is None
    assert snap["allowed_paths"] == ["."]

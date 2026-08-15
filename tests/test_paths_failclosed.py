from __future__ import annotations

from pathlib import Path

import pytest

from taskpin import (
    PATH_OUTSIDE_ALLOWLIST,
    REPOSITORY_MISMATCH,
    TaskPinError,
    compare_locus,
    project_paths,
    project_snapshot,
)
from taskpin.gitops import parse_name_status_z
from taskpin.paths import canonicalize_git_path
from tests.gitutil import commit_file, git, init_repo, write_file


def _write_exec(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_ignored_file_not_in_delivered_set(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    write_file(repo, ".gitignore", "*.log\n")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-m", "ignore")
    sealed = project_snapshot(repo, allowed_paths=["."])
    write_file(repo, "noise.log", "ignored\n")
    write_file(repo, "src/auth/ok.py", "ok\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/ok.py"]
    assert "noise.log" not in result["delivered_paths"]


def test_spaces_and_unicode_filenames(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    write_file(repo, "src/auth/my file.py", "s\n")
    write_file(repo, "src/auth/café.py", "u\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/café.py", "src/auth/my file.py"]


def test_unusual_legal_git_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    write_file(repo, "src/auth/file@1#ok.txt", "x\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/file@1#ok.txt"]


def test_deleted_symlink_is_observable_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    (repo / "src/auth/link").symlink_to("a.py")
    git(repo, "add", "src/auth/link")
    git(repo, "commit", "-m", "link")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    git(repo, "rm", "src/auth/link")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/link"]


def test_broken_symlink_inside_repo(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    (repo / "src/auth/broken").symlink_to("missing-inside")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/broken"]


def test_gitlink_is_one_path(tmp_path: Path) -> None:
    parent = init_repo(tmp_path / "parent")
    commit_file(parent, "src/auth/a.py", "a\n", "first")
    sub = init_repo(tmp_path / "sub")
    sha1 = commit_file(sub, "inner.txt", "i\n", "sub1")
    sha2 = commit_file(sub, "inner.txt", "i2\n", "sub2")
    git(parent, "update-index", "--add", "--cacheinfo", f"160000,{sha1},vendor/lib")
    git(parent, "commit", "-m", "gitlink")
    sealed = project_snapshot(parent, allowed_paths=["."])
    git(parent, "update-index", "--cacheinfo", f"160000,{sha2},vendor/lib")
    result = compare_locus(sealed, parent)
    assert result["delivered_paths"] == ["vendor/lib"]
    assert result["status"] == "MATCH"


def test_nested_git_is_outer_visible_path_only(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed_dot = project_snapshot(repo, allowed_paths=["."])
    sealed_auth = {**sealed_dot, "allowed_paths": ["src/auth"]}
    nested = init_repo(repo / "nested")
    commit_file(nested, "inner.txt", "i\n", "nested")
    assert project_paths(repo, sealed_dot["base_commit"]) == ["nested"]
    assert compare_locus(sealed_dot, repo)["status"] == "MATCH"
    result = compare_locus(sealed_auth, repo)
    assert [m["class"] for m in result["mismatches"]] == [PATH_OUTSIDE_ALLOWLIST]
    assert result["delivered_paths"] == ["nested"]


def test_repository_mismatch_skips_path_projection(tmp_path: Path) -> None:
    a = init_repo(tmp_path / "a")
    b = init_repo(tmp_path / "b")
    commit_file(a, "src/auth/a.py", "a\n", "a")
    commit_file(b, "src/other.py", "b\n", "b")
    sealed = project_snapshot(a, allowed_paths=["src/auth"])
    result = compare_locus(sealed, b)
    assert [m["class"] for m in result["mismatches"]] == [REPOSITORY_MISMATCH]
    assert result["delivered_paths"] == []


def test_git_path_listing_failure(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    fake = _write_exec(
        tmp_path / "bad-git",
        "#!/bin/sh\n"
        'for arg in "$@"; do\n'
        '  if [ "$arg" = "ls-files" ]; then exit 128; fi\n'
        "done\n"
        'exec git "$@"\n',
    )
    with pytest.raises(TaskPinError) as exc:
        compare_locus(sealed, repo, git_bin=str(fake))
    assert exc.value.code == "CANNOT_PROJECT_PATHS"


def test_unrepresentable_path_never_silently_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    monkeypatch.setattr(
        "taskpin.gitops.changed_paths_since",
        lambda *args, **kwargs: ["../escape"],
    )
    with pytest.raises(TaskPinError) as exc:
        project_paths(repo, sealed["base_commit"])
    assert exc.value.code == "UNCANONICAL_PATH"
    with pytest.raises(TaskPinError) as exc:
        compare_locus(sealed, repo)
    assert exc.value.code == "UNCANONICAL_PATH"
    with pytest.raises(TaskPinError) as exc:
        canonicalize_git_path("../escape")
    assert exc.value.code == "UNCANONICAL_PATH"


def test_malformed_name_status_fails_closed() -> None:
    with pytest.raises(TaskPinError) as exc:
        parse_name_status_z(b"R100\x00only-old\x00")
    assert exc.value.code == "CANNOT_PROJECT_PATHS"


def test_schema_still_six_fields(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    snap = project_snapshot(repo, allowed_paths=["src/auth"])
    assert set(snap) == {
        "schema_version",
        "instruction_digest",
        "repo_id",
        "worktree_key",
        "base_commit",
        "allowed_paths",
    }
    assert "delivered_paths" not in snap

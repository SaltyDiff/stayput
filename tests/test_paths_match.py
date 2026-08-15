from __future__ import annotations

from pathlib import Path

from stayput import compare_locus, project_paths, project_snapshot
from tests.gitutil import commit_file, git, init_repo, write_file


def _seal(repo: Path, allowed: list[str] | None = None) -> dict:
    return project_snapshot(repo, allowed_paths=allowed)


def test_no_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == []


def test_committed_in_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    commit_file(repo, "src/auth/b.py", "b\n", "second")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/b.py"]


def test_staged_in_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    write_file(repo, "src/auth/staged.py", "s\n")
    git(repo, "add", "src/auth/staged.py")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert "src/auth/staged.py" in result["delivered_paths"]


def test_unstaged_in_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    write_file(repo, "src/auth/a.py", "dirty\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/a.py"]


def test_untracked_non_ignored_in_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    write_file(repo, "src/auth/new.py", "n\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/new.py"]


def test_multiple_in_scope_mutations(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    commit_file(repo, "src/auth/b.py", "b\n", "second")
    write_file(repo, "src/auth/a.py", "dirty\n")
    write_file(repo, "src/auth/c.py", "c\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == [
        "src/auth/a.py",
        "src/auth/b.py",
        "src/auth/c.py",
    ]


def test_dot_allows_in_repo_mutations(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal(repo, ["."])
    write_file(repo, "other/dir/file.py", "x\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["other/dir/file.py"]


def test_nested_allowed_prefix_is_literal(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    write_file(repo, "src/auth/nested/ok.py", "ok\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/nested/ok.py"]


def test_deletion_inside_allowed_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    git(repo, "rm", "src/auth/a.py")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/a.py"]


def test_rename_both_sides_allowed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/old.py", "same\n" * 20, "first")
    sealed = _seal(repo, ["src/auth"])
    git(repo, "mv", "src/auth/old.py", "src/auth/new.py")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_paths"] == ["src/auth/new.py", "src/auth/old.py"]


def test_base_equals_head_with_dirty_changes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    write_file(repo, "src/auth/a.py", "dirty\n")
    write_file(repo, "src/auth/untracked.py", "u\n")
    assert sealed["base_commit"] == git(repo, "rev-parse", "HEAD").stdout.strip()
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert set(result["delivered_paths"]) == {"src/auth/a.py", "src/auth/untracked.py"}


def test_detached_head_in_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    first = commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    git(repo, "checkout", "--detach", first)
    write_file(repo, "src/auth/a.py", "detached\n")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"


def test_project_paths_sorts_and_dedupes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal(repo, ["src/auth"])
    write_file(repo, "src/auth/a.py", "dirty\n")
    git(repo, "add", "src/auth/a.py")
    write_file(repo, "src/auth/a.py", "dirty2\n")
    paths = project_paths(repo, sealed["base_commit"])
    assert paths == ["src/auth/a.py"]

from __future__ import annotations

from pathlib import Path

from taskpin import (
    BASE_COMMIT_MISMATCH,
    REPOSITORY_MISMATCH,
    WORKTREE_MISMATCH,
    compare_locus,
    project_snapshot,
)
from tests.gitutil import commit_file, git, init_repo


def test_different_repository(tmp_path: Path) -> None:
    a = init_repo(tmp_path / "a")
    b = init_repo(tmp_path / "b")
    commit_file(a, "a.txt", "a\n", "a")
    commit_file(b, "b.txt", "b\n", "b")
    sealed = project_snapshot(a)
    result = compare_locus(sealed, b)
    assert result["status"] == "MISMATCH"
    assert result["mismatches"][0]["class"] == REPOSITORY_MISMATCH
    assert len(result["mismatches"]) == 1


def test_sealed_base_absent(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    sealed = {
        **sealed,
        "base_commit": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "repo_id": sealed["repo_id"],
    }
    result = compare_locus(sealed, repo)
    assert result["status"] == "MISMATCH"
    assert result["mismatches"][0]["class"] == REPOSITORY_MISMATCH
    assert result["mismatches"][0]["delivered"] is None


def test_linked_approved_checked_from_main(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", str(linked), "-b", "feat")
    sealed = project_snapshot(linked)
    result = compare_locus(sealed, repo)
    assert result["status"] == "MISMATCH"
    classes = [m["class"] for m in result["mismatches"]]
    assert WORKTREE_MISMATCH in classes
    assert REPOSITORY_MISMATCH not in classes


def test_one_linked_worktree_vs_another(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    left = tmp_path / "wt-a"
    right = tmp_path / "wt-b"
    git(repo, "worktree", "add", str(left), "-b", "a")
    git(repo, "worktree", "add", str(right), "-b", "b")
    sealed = project_snapshot(left)
    result = compare_locus(sealed, right)
    assert [m["class"] for m in result["mismatches"]] == [WORKTREE_MISMATCH]


def test_gitdir_rewrite_to_main(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", str(linked), "-b", "feat")
    sealed = project_snapshot(linked)
    common = git(linked, "rev-parse", "--path-format=absolute", "--git-common-dir")
    (linked / ".git").write_text(f"gitdir: {common.stdout.strip()}\n", encoding="utf-8")
    result = compare_locus(sealed, linked)
    assert result["status"] == "MISMATCH"
    assert any(m["class"] == WORKTREE_MISMATCH for m in result["mismatches"])


def test_reset_drops_sealed_base(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    git(repo, "checkout", "--orphan", "drop")
    commit_file(repo, "d.txt", "d\n", "drop")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MISMATCH"
    classes = [m["class"] for m in result["mismatches"]]
    assert BASE_COMMIT_MISMATCH in classes
    assert REPOSITORY_MISMATCH not in classes


def test_orphan_head_does_not_redefine_repo_id(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    git(repo, "checkout", "--orphan", "orphan")
    commit_file(repo, "o.txt", "o\n", "orphan")
    result = compare_locus(sealed, repo)
    assert REPOSITORY_MISMATCH not in [m["class"] for m in result["mismatches"]]
    assert result["delivered_locus"]["repo_id"] == sealed["repo_id"]
    assert any(m["class"] == BASE_COMMIT_MISMATCH for m in result["mismatches"])

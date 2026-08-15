from __future__ import annotations

from pathlib import Path

from stayput import compare_locus, project_locus, project_snapshot
from tests.gitutil import commit_file, git, init_repo


def test_same_repo_same_main_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["mismatches"] == []
    assert sealed["worktree_key"] == ""
    assert len(sealed["base_commit"]) == 40


def test_head_advance_is_match(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    commit_file(repo, "a.txt", "a\nb\n", "second")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_locus"]["head"] != sealed["base_commit"]


def test_dirty_worktree_does_not_fail_ancestry(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    (repo / "a.txt").write_text("dirty\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("u\n", encoding="utf-8")
    assert compare_locus(sealed, repo)["status"] == "MATCH"


def test_detached_head_on_descendant(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    second = commit_file(repo, "a.txt", "a\nb\n", "second")
    git(repo, "checkout", "--detach", second)
    assert compare_locus(sealed, repo)["status"] == "MATCH"


def test_same_linked_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", str(linked), "-b", "feat")
    sealed = project_snapshot(linked)
    assert sealed["worktree_key"].startswith("worktrees/")
    commit_file(linked, "a.txt", "feat\n", "feat commit")
    assert compare_locus(sealed, linked)["status"] == "MATCH"


def test_repository_relocated_keeps_identity(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    moved = tmp_path / "repo-moved"
    repo.rename(moved)
    delivered = project_locus(moved)
    assert delivered["repo_id"] == sealed["repo_id"]
    assert delivered["worktree_key"] == ""
    assert compare_locus(sealed, moved)["status"] == "MATCH"


def test_worktree_move_keeps_key(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    linked = tmp_path / "linked"
    moved = tmp_path / "linked-moved"
    git(repo, "worktree", "add", str(linked), "-b", "feat")
    sealed = project_snapshot(linked)
    git(repo, "worktree", "move", str(linked), str(moved))
    delivered = project_locus(moved)
    assert delivered["worktree_key"] == sealed["worktree_key"]
    assert compare_locus(sealed, moved)["status"] == "MATCH"


def test_unrelated_merge_does_not_redefine_repo_id_from_head(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    git(repo, "checkout", "--orphan", "other")
    git(repo, "rm", "-rf", "--ignore-unmatch", ".")
    commit_file(repo, "o.txt", "o\n", "orphan-root")
    git(repo, "checkout", "main")
    git(repo, "merge", "--allow-unrelated-histories", "-m", "join", "other")
    head_locus = project_locus(repo)
    assert "," in head_locus["repo_id"]
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"
    assert result["delivered_locus"]["repo_id"] == sealed["repo_id"]
    assert result["delivered_locus"]["repo_id"] != head_locus["repo_id"]


def test_multiple_roots_at_save(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    git(repo, "checkout", "--orphan", "other")
    git(repo, "rm", "-rf", "--ignore-unmatch", ".")
    commit_file(repo, "o.txt", "o\n", "orphan-root")
    git(repo, "checkout", "main")
    git(repo, "merge", "--allow-unrelated-histories", "-m", "join", "other")
    sealed = project_locus(repo)
    assert len(sealed["repo_id"].split(",")) == 2
    assert sealed["repo_id"] == ",".join(sorted(sealed["repo_id"].split(",")))
    assert compare_locus(project_snapshot(repo), repo)["status"] == "MATCH"

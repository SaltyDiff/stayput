from __future__ import annotations

from pathlib import Path

from stayput import PATH_OUTSIDE_ALLOWLIST, compare_locus, project_snapshot
from tests.gitutil import commit_file, git, init_repo, write_file


def _classes(result: dict) -> list[str]:
    return [m["class"] for m in result["mismatches"]]


def _path_hits(result: dict) -> list[str]:
    return [
        str(m["delivered"])
        for m in result["mismatches"]
        if m["class"] == PATH_OUTSIDE_ALLOWLIST
    ]


def test_committed_out_of_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    commit_file(repo, "src/other.py", "o\n", "other")
    result = compare_locus(sealed, repo)
    assert result["status"] == "MISMATCH"
    assert _path_hits(result) == ["src/other.py"]


def test_staged_out_of_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    write_file(repo, "docs/note.md", "n\n")
    git(repo, "add", "docs/note.md")
    result = compare_locus(sealed, repo)
    assert _path_hits(result) == ["docs/note.md"]


def test_unstaged_out_of_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    commit_file(repo, "README.md", "r\n", "readme")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    write_file(repo, "README.md", "dirty\n")
    result = compare_locus(sealed, repo)
    assert _path_hits(result) == ["README.md"]


def test_untracked_out_of_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    write_file(repo, "tmp/out.py", "x\n")
    result = compare_locus(sealed, repo)
    assert _path_hits(result) == ["tmp/out.py"]


def test_rename_allowed_to_disallowed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "same\n" * 20, "first")
    write_file(repo, "lib/.keep", "")
    git(repo, "add", "lib/.keep")
    git(repo, "commit", "-m", "keep")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    git(repo, "mv", "src/auth/a.py", "lib/a.py")
    result = compare_locus(sealed, repo)
    assert "lib/a.py" in _path_hits(result)
    assert "src/auth/a.py" not in _path_hits(result)
    assert "src/auth/a.py" in result["delivered_paths"]
    assert "lib/a.py" in result["delivered_paths"]


def test_rename_disallowed_to_allowed(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "auth")
    commit_file(repo, "lib/x.py", "same\n" * 20, "lib")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    git(repo, "mv", "lib/x.py", "src/auth/x.py")
    result = compare_locus(sealed, repo)
    assert _path_hits(result) == ["lib/x.py"]
    assert "src/auth/x.py" in result["delivered_paths"]


def test_rename_either_side_out_of_scope(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "left/a.py", "same\n" * 20, "left")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    (repo / "right").mkdir()
    git(repo, "mv", "left/a.py", "right/a.py")
    hits = _path_hits(compare_locus(sealed, repo))
    assert hits == ["left/a.py", "right/a.py"]


def test_symlink_target_escapes_repository(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = project_snapshot(repo, allowed_paths=["."])
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")
    (repo / "escape").symlink_to(outside)
    result = compare_locus(sealed, repo)
    assert result["status"] == "MISMATCH"
    assert _path_hits(result) == ["escape"]
    assert PATH_OUTSIDE_ALLOWLIST in _classes(result)


def test_src_auth_does_not_match_auth_backup(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = project_snapshot(repo, allowed_paths=["src/auth"])
    write_file(repo, "src/auth_backup/file.py", "nope\n")
    result = compare_locus(sealed, repo)
    assert _path_hits(result) == ["src/auth_backup/file.py"]

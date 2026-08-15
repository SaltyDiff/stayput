from pathlib import Path

import pytest

from stayput.errors import StayPutError
from stayput.paths import canonicalize_git_path, path_allowed, path_escapes_repository


def test_canonicalize_strips_trailing_slash_and_dot_slash() -> None:
    assert canonicalize_git_path("nested/") == "nested"
    assert canonicalize_git_path("./src/auth.py") == "src/auth.py"


def test_canonicalize_rejects_traversal_and_absolute() -> None:
    for raw in ("", ".", "..", "../x", "src/../x", "/abs", "C:/win", "a\\b", "a//b"):
        with pytest.raises(StayPutError) as exc:
            canonicalize_git_path(raw)
        assert exc.value.code == "UNCANONICAL_PATH"


def test_src_auth_does_not_match_src_auth_backup() -> None:
    assert path_allowed("src/auth", ["src/auth"])
    assert path_allowed("src/auth/login.py", ["src/auth"])
    assert not path_allowed("src/auth_backup/file.py", ["src/auth"])
    assert not path_allowed("src/other.py", ["src/auth"])


def test_dot_allows_any_in_repo_path() -> None:
    assert path_allowed("anything/here.py", ["."])
    assert path_allowed("src/auth_backup/file.py", ["."])


def test_symlink_escape_is_outside(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x\n", encoding="utf-8")
    link = repo / "link"
    link.symlink_to(outside)
    assert path_escapes_repository(repo, "link") is True


def test_broken_in_repo_symlink_does_not_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "broken").symlink_to("missing-inside")
    assert path_escapes_repository(repo, "broken") is False


def test_deleted_path_does_not_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert path_escapes_repository(repo, "gone.txt") is False

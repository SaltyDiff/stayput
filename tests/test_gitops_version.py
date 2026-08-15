from taskpin.gitops import parse_git_version


def test_parse_git_version() -> None:
    assert parse_git_version("git version 2.43.0") == (2, 43)
    assert parse_git_version("git version 2.31.1.windows.1") == (2, 31)
    assert parse_git_version("not git") is None

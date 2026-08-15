from __future__ import annotations

import subprocess
from pathlib import Path


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def init_repo(path: Path, *, branch: str = "main") -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", branch)
    git(path, "config", "user.email", "taskpin@example.test")
    git(path, "config", "user.name", "taskpin")
    git(path, "config", "commit.gpgsign", "false")
    return path


def commit_file(path: Path, name: str, content: str, message: str) -> str:
    (path / name).write_text(content, encoding="utf-8")
    git(path, "add", name)
    git(path, "commit", "-m", message)
    return git(path, "rev-parse", "HEAD").stdout.strip()

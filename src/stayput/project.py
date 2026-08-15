"""Project Git locus and delivered path set. No instruction scrape."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from stayput import gitops
from stayput.paths import canonicalize_git_path
from stayput.schema import snapshot


def _cwd(cwd: Path | str | None) -> Path:
    return Path(cwd) if cwd is not None else Path.cwd()


def project_locus(
    cwd: Path | str | None = None,
    *,
    git_bin: str = "git",
) -> dict[str, str]:
    """SAVE projection: repo_id and base_commit from current HEAD."""
    root = _cwd(cwd)
    inspected = gitops.inspect_repository(root, git_bin=git_bin)
    head = gitops.read_head(root, git_bin=git_bin)
    return {
        "repo_id": gitops.roots_of(root, head, git_bin=git_bin),
        "worktree_key": gitops.worktree_key(
            Path(str(inspected["git_dir"])),
            Path(str(inspected["common_dir"])),
        ),
        "base_commit": head,
    }


def project_check_repo_id(
    cwd: Path | str | None,
    sealed_base_commit: str,
    *,
    git_bin: str = "git",
) -> str | None:
    """CHECK repo_id from the sealed base commit, or None if the object is absent."""
    root = _cwd(cwd)
    gitops.inspect_repository(root, git_bin=git_bin)
    if not gitops.commit_exists(root, sealed_base_commit, git_bin=git_bin):
        return None
    return gitops.roots_of(root, sealed_base_commit, git_bin=git_bin)


def project_paths(
    cwd: Path | str | None,
    sealed_base_commit: str,
    *,
    exclude_paths: Sequence[str] = (),
    git_bin: str = "git",
) -> list[str]:
    """Sorted unique Git-visible delivered paths since the sealed base."""
    root = _cwd(cwd)
    inspected = gitops.inspect_repository(root, git_bin=git_bin)
    toplevel = Path(str(inspected["toplevel"]))
    raw_paths = gitops.changed_paths_since(
        toplevel,
        sealed_base_commit,
        git_bin=git_bin,
    )
    excluded = set(exclude_paths)
    return sorted(
        {
            path
            for path in (canonicalize_git_path(raw) for raw in raw_paths)
            if path not in excluded
        }
    )


def project_snapshot(
    cwd: Path | str | None = None,
    *,
    instruction_digest: str | None = None,
    allowed_paths: list[str] | None = None,
    git_bin: str = "git",
) -> dict[str, Any]:
    """Build a T1 snapshot from live Git locus.

    Instruction digest and allowed_paths are caller-supplied.
    """
    locus = project_locus(cwd, git_bin=git_bin)
    return snapshot(
        instruction_digest=instruction_digest,
        repo_id=locus["repo_id"],
        worktree_key=locus["worktree_key"],
        base_commit=locus["base_commit"],
        allowed_paths=allowed_paths,
    )

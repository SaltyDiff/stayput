"""Compare sealed vs delivered Git locus. Path and instruction axes are T3+."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from taskpin import gitops
from taskpin.errors import TaskPinError
from taskpin.project import project_check_repo_id, project_locus
from taskpin.schema import normalize_snapshot

REPOSITORY_MISMATCH = "REPOSITORY_MISMATCH"
WORKTREE_MISMATCH = "WORKTREE_MISMATCH"
BASE_COMMIT_MISMATCH = "BASE_COMMIT_MISMATCH"

_LOCUS_KEYS = ("repo_id", "worktree_key", "base_commit")


def _locus_from_snapshot(sealed: Mapping[str, Any]) -> dict[str, str]:
    snap = normalize_snapshot(sealed)
    return {key: str(snap[key]) for key in _LOCUS_KEYS}


def _mismatch(cls: str, sealed: object, delivered: object) -> dict[str, object]:
    return {"class": cls, "sealed": sealed, "delivered": delivered}


def compare_locus(
    sealed: Mapping[str, Any],
    cwd: Path | str | None = None,
    *,
    git_bin: str = "git",
) -> dict[str, Any]:
    """Compare sealed snapshot locus to live Git state.

    Short-circuits after ``REPOSITORY_MISMATCH``. Does not grade paths or
    instruction bytes. Operational inability to prove raises ``TaskPinError``.
    """
    sealed_locus = _locus_from_snapshot(sealed)
    root = Path(cwd) if cwd is not None else Path.cwd()
    delivered = project_locus(root, git_bin=git_bin)
    check_repo_id = project_check_repo_id(
        root,
        sealed_locus["base_commit"],
        git_bin=git_bin,
    )
    delivered_for_compare = {
        "repo_id": check_repo_id,
        "worktree_key": delivered["worktree_key"],
        "head": delivered["base_commit"],
    }

    if check_repo_id is None or check_repo_id != sealed_locus["repo_id"]:
        return {
            "ok": True,
            "status": "MISMATCH",
            "mismatches": [
                _mismatch(
                    REPOSITORY_MISMATCH,
                    sealed_locus["repo_id"],
                    check_repo_id,
                )
            ],
            "sealed_locus": sealed_locus,
            "delivered_locus": delivered_for_compare,
        }

    mismatches: list[dict[str, object]] = []
    if delivered["worktree_key"] != sealed_locus["worktree_key"]:
        mismatches.append(
            _mismatch(
                WORKTREE_MISMATCH,
                sealed_locus["worktree_key"],
                delivered["worktree_key"],
            )
        )

    ancestry = gitops.merge_base_is_ancestor(
        root,
        sealed_locus["base_commit"],
        git_bin=git_bin,
    )
    if ancestry == 0:
        pass
    elif ancestry == 1:
        mismatches.append(
            _mismatch(
                BASE_COMMIT_MISMATCH,
                sealed_locus["base_commit"],
                delivered["base_commit"],
            )
        )
    else:
        raise TaskPinError(
            "CANNOT_PROVE_ANCESTRY",
            f"merge-base --is-ancestor exited {ancestry}",
        )

    status = "MATCH" if not mismatches else "MISMATCH"
    return {
        "ok": True,
        "status": status,
        "mismatches": mismatches,
        "sealed_locus": sealed_locus,
        "delivered_locus": delivered_for_compare,
    }

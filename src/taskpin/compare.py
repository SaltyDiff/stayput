"""Compare sealed vs delivered Git locus, changed paths, and instruction bytes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from taskpin import gitops
from taskpin.errors import TaskPinError
from taskpin.instruction import digest_instruction
from taskpin.paths import violating_paths
from taskpin.project import project_check_repo_id, project_locus, project_paths
from taskpin.schema import normalize_snapshot

REPOSITORY_MISMATCH = "REPOSITORY_MISMATCH"
WORKTREE_MISMATCH = "WORKTREE_MISMATCH"
BASE_COMMIT_MISMATCH = "BASE_COMMIT_MISMATCH"
PATH_OUTSIDE_ALLOWLIST = "PATH_OUTSIDE_ALLOWLIST"
INSTRUCTION_DRIFT = "INSTRUCTION_DRIFT"

_LOCUS_KEYS = ("repo_id", "worktree_key", "base_commit")


def _mismatch(cls: str, sealed: object, delivered: object) -> dict[str, object]:
    return {"class": cls, "sealed": sealed, "delivered": delivered}


def compare_locus(
    sealed: Mapping[str, Any],
    cwd: Path | str | None = None,
    *,
    instruction_bytes: bytes | None = None,
    exclude_paths: Sequence[str] = (),
    git_bin: str = "git",
) -> dict[str, Any]:
    """Compare sealed snapshot locus, paths, and optional instruction bytes.

    Short-circuits after ``REPOSITORY_MISMATCH``. A sealed instruction digest
    with omitted bytes raises ``INSTRUCTION_REQUIRED`` after Git/path axes
    are collected. Operational inability to prove raises ``TaskPinError``.
    """
    snap = normalize_snapshot(sealed)
    sealed_locus = {key: str(snap[key]) for key in _LOCUS_KEYS}
    allowed = list(snap["allowed_paths"])
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
            "delivered_paths": [],
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

    inspected = gitops.inspect_repository(root, git_bin=git_bin)
    toplevel = Path(str(inspected["toplevel"]))
    delivered_paths = project_paths(
        root,
        sealed_locus["base_commit"],
        exclude_paths=exclude_paths,
        git_bin=git_bin,
    )
    for path in violating_paths(delivered_paths, allowed, toplevel):
        mismatches.append(_mismatch(PATH_OUTSIDE_ALLOWLIST, allowed, path))

    sealed_instruction = snap["instruction_digest"]
    if sealed_instruction is not None:
        if instruction_bytes is None:
            raise TaskPinError(
                "INSTRUCTION_REQUIRED",
                "sealed instruction_digest requires explicit instruction bytes",
                details={
                    "mismatches": mismatches,
                    "delivered_paths": delivered_paths,
                },
            )
        if type(instruction_bytes) is not bytes:
            raise TaskPinError(
                "INVALID_INSTRUCTION",
                "instruction_bytes must be bytes when supplied",
                details={
                    "mismatches": mismatches,
                    "delivered_paths": delivered_paths,
                },
            )
        try:
            delivered_digest = digest_instruction(instruction_bytes)
        except TaskPinError as exc:
            raise TaskPinError(
                exc.code,
                exc.message,
                details={
                    "mismatches": mismatches,
                    "delivered_paths": delivered_paths,
                    **exc.details,
                },
            ) from exc
        if delivered_digest != sealed_instruction:
            mismatches.append(
                _mismatch(
                    INSTRUCTION_DRIFT,
                    sealed_instruction,
                    delivered_digest,
                )
            )

    status = "MATCH" if not mismatches else "MISMATCH"
    return {
        "ok": True,
        "status": status,
        "mismatches": mismatches,
        "sealed_locus": sealed_locus,
        "delivered_locus": delivered_for_compare,
        "delivered_paths": delivered_paths,
    }

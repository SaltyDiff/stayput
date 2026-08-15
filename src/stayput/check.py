"""Library check of an explicitly sealed approval artifact.

Does not create, repair, or overwrite approvals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stayput import gitops
from stayput.canonicalize import verify_approval
from stayput.compare import compare_locus
from stayput.errors import StayPutError
from stayput.paths import canonicalize_git_path
from stayput.save import resolve_approval_path


def _read_approval_text(path: Path) -> str:
    if not path.exists():
        raise StayPutError(
            "APPROVAL_MISSING",
            f"approval artifact is missing: {path}",
        )
    if not path.is_file():
        raise StayPutError(
            "APPROVAL_UNREADABLE",
            f"approval path is not a file: {path}",
        )
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise StayPutError(
            "INVALID_APPROVAL",
            "approval artifact is not valid UTF-8",
        ) from exc
    except OSError as exc:
        raise StayPutError(
            "APPROVAL_UNREADABLE",
            f"approval artifact cannot be read: {path}",
        ) from exc


def check(
    cwd: Path | str | None = None,
    *,
    path: Path | str | None = None,
    instruction_bytes: bytes | None = None,
    git_bin: str = "git",
) -> dict[str, Any]:
    """Verify artifact integrity, then compare sealed vs delivered locus.

    ``record_digest`` is verified before the snapshot is trusted.
    Integrity failures raise ``StayPutError`` (ERROR), not MISMATCH.
    """
    target = resolve_approval_path(cwd, path)
    text = _read_approval_text(target)
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StayPutError(
            "INVALID_APPROVAL",
            "approval JSON is not parseable",
        ) from exc
    verified = verify_approval(loaded)
    exclude = _approval_relpath(cwd, target, git_bin=git_bin)
    result = compare_locus(
        verified["approval"]["snapshot"],
        cwd,
        instruction_bytes=instruction_bytes,
        exclude_paths=exclude,
        git_bin=git_bin,
    )
    result["approval_path"] = str(target)
    return result


def _approval_relpath(
    cwd: Path | str | None,
    target: Path,
    *,
    git_bin: str,
) -> tuple[str, ...]:
    """The approval file is the seal, not a delivered mutation of the sealed work."""
    root = Path(cwd) if cwd is not None else Path.cwd()
    inspected = gitops.inspect_repository(root, git_bin=git_bin)
    toplevel = Path(str(inspected["toplevel"]))
    try:
        rel = target.resolve().relative_to(toplevel.resolve())
    except (OSError, ValueError):
        return ()
    try:
        return (canonicalize_git_path(str(rel).replace("\\", "/")),)
    except StayPutError:
        return ()

"""Library save of an explicitly sealed approval artifact.

Never infers approval from cwd, session, or first-run presence.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from taskpin.canonicalize import build_approval, serialize_approval
from taskpin.errors import TaskPinError
from taskpin.instruction import digest_instruction
from taskpin.project import project_snapshot
from taskpin.schema import DEFAULT_APPROVAL_PATH


def resolve_approval_path(
    cwd: Path | str | None = None,
    path: Path | str | None = None,
) -> Path:
    """Resolve the approval file path. Default is ``<cwd>/.taskpin/approval.json``."""
    root = Path(cwd) if cwd is not None else Path.cwd()
    target = Path(path) if path is not None else Path(DEFAULT_APPROVAL_PATH)
    if not target.is_absolute():
        target = root / target
    return target


def _write_atomic(path: Path, text: str) -> None:
    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TaskPinError(
            "APPROVAL_WRITE_FAILED",
            f"cannot create approval directory {parent}",
        ) from exc
    payload = text if text.endswith("\n") else f"{text}\n"
    tmp_path: Path | None = None
    try:
        fd, raw = tempfile.mkstemp(prefix=".approval-", suffix=".tmp", dir=parent)
        tmp_path = Path(raw)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        tmp_path = None
    except OSError as exc:
        raise TaskPinError(
            "APPROVAL_WRITE_FAILED",
            f"cannot write approval artifact {path}",
        ) from exc
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def save(
    cwd: Path | str | None = None,
    *,
    path: Path | str | None = None,
    instruction_bytes: bytes | None = None,
    allowed_paths: list[str] | None = None,
    replace: bool = False,
    git_bin: str = "git",
) -> dict[str, Any]:
    """Seal the current Git locus into ``taskpin.approval.v0.1``.

    ``replace`` must be True to overwrite an existing artifact. Default is
    fail-closed ``APPROVAL_ALREADY_EXISTS``.
    """
    if instruction_bytes is None:
        instruction_digest = None
    elif type(instruction_bytes) is not bytes:
        raise TaskPinError(
            "INVALID_INSTRUCTION",
            "instruction_bytes must be bytes when supplied",
        )
    else:
        instruction_digest = digest_instruction(instruction_bytes)

    snapshot = project_snapshot(
        cwd,
        instruction_digest=instruction_digest,
        allowed_paths=allowed_paths,
        git_bin=git_bin,
    )
    approval = build_approval(snapshot)
    target = resolve_approval_path(cwd, path)
    if target.exists() and not replace:
        raise TaskPinError(
            "APPROVAL_ALREADY_EXISTS",
            f"approval artifact already exists: {target}",
        )
    _write_atomic(target, serialize_approval(approval))
    return {
        "ok": True,
        "path": str(target),
        "approval": approval,
    }

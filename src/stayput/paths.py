"""Path canonicalization, allowlist prefix match, and symlink containment.

Not a sandbox. Not a policy language. No globbing.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from stayput.errors import StayPutError


def canonicalize_git_path(raw: str) -> str:
    """Normalize one Git-emitted path to a repo-relative POSIX path.

    Rejects absolute paths, backslashes, ``//``, and ``.`` / ``..`` segments.
    Does not silently repair unrepresentable paths.
    """
    if not isinstance(raw, str) or raw == "":
        raise StayPutError("UNCANONICAL_PATH", "git path must be a non-empty string")
    if "\x00" in raw:
        raise StayPutError("UNCANONICAL_PATH", "git path contains a NUL")
    if raw.startswith("/") or (len(raw) >= 2 and raw[1] == ":"):
        raise StayPutError("UNCANONICAL_PATH", "git path must be repository-relative")
    if "\\" in raw or "//" in raw:
        raise StayPutError(
            "UNCANONICAL_PATH",
            "git path must be POSIX without backslash or empty segments",
        )
    text = raw.removeprefix("./")
    text = text.rstrip("/")
    if text == "" or text == ".":
        raise StayPutError("UNCANONICAL_PATH", "git path collapsed to empty or '.'")
    segments = text.split("/")
    if any(seg in {"", ".", ".."} for seg in segments):
        raise StayPutError(
            "UNCANONICAL_PATH",
            "git path must not contain '.', '..', or empty segments",
        )
    return text


def path_allowed(path: str, allowed: Sequence[str]) -> bool:
    """Literal prefix match. ``.`` means any in-repo Git-visible path."""
    for entry in allowed:
        if entry == ".":
            return True
        if path == entry or path.startswith(f"{entry}/"):
            return True
    return False


def _normalize_fs(path: Path) -> str:
    return str(path).replace("\\", "/").rstrip("/")


def _contained(path: Path, root: Path) -> bool:
    path_n = _normalize_fs(path)
    root_n = _normalize_fs(root)
    if os.name == "nt":
        path_n = path_n.casefold()
        root_n = root_n.casefold()
    return path_n == root_n or path_n.startswith(f"{root_n}/")


def path_escapes_repository(toplevel: Path, rel: str) -> bool:
    """True when a Git-visible path resolves outside the approved work tree.

    Resolves existing symlink prefixes and the path itself when it exists.
    Does not walk or read escaped target content.
    """
    try:
        top = toplevel.resolve(strict=True)
    except OSError as exc:
        raise StayPutError(
            "WORKTREE_UNRESOLVABLE",
            f"cannot realpath repository toplevel: {toplevel}",
        ) from exc

    current = top
    parts = rel.split("/")
    for index, part in enumerate(parts):
        current = current / part
        try:
            present = current.is_symlink() or current.exists()
        except OSError as exc:
            raise StayPutError(
                "UNCANONICAL_PATH",
                f"cannot stat delivered path {rel!r}",
            ) from exc
        if not present:
            return False
        if current.is_symlink() or index == len(parts) - 1:
            try:
                resolved = Path(os.path.realpath(current))
            except OSError as exc:
                raise StayPutError(
                    "UNCANONICAL_PATH",
                    f"cannot realpath delivered path {rel!r}",
                ) from exc
            if not _contained(resolved, top):
                return True
    return False


def violating_paths(
    paths: Sequence[str],
    allowed: Sequence[str],
    toplevel: Path,
) -> list[str]:
    """Sorted unique delivered paths that miss the allowlist or escape toplevel."""
    violations: list[str] = []
    for path in paths:
        if not path_allowed(path, allowed) or path_escapes_repository(toplevel, path):
            violations.append(path)
    return sorted(set(violations))

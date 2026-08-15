"""Closed StayPut V0 snapshot and approval-wrapper schemas.

T1 validates and normalizes representation only. No Git derivation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from stayput.errors import StayPutError

SNAPSHOT_SCHEMA_VERSION = "stayput.snapshot.v0.1"
APPROVAL_SCHEMA_VERSION = "stayput.approval.v0.1"
DEFAULT_APPROVAL_PATH = ".stayput/approval.json"
DEFAULT_ALLOWED_PATHS: tuple[str, ...] = (".",)

SNAPSHOT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "instruction_digest",
    "repo_id",
    "worktree_key",
    "base_commit",
    "allowed_paths",
)
APPROVAL_FIELDS: tuple[str, ...] = (
    "schema_version",
    "snapshot",
    "record_digest",
)

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_GLOB_CHARS = frozenset("*?[{}")


def _require_mapping(value: object, *, code: str, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StayPutError(code, f"{what} must be an object")
    return value


def _reject_unknown(keys: object, allowed: tuple[str, ...], *, code: str) -> None:
    try:
        present = frozenset(keys)  # type: ignore[arg-type]
    except TypeError as exc:
        raise StayPutError(code, "object keys must be strings") from exc
    extra = sorted(str(k) for k in present if k not in allowed)
    if extra:
        raise StayPutError(code, f"unknown fields: {', '.join(extra)}")


def _require_keys(keys: object, required: tuple[str, ...], *, code: str) -> None:
    try:
        present = frozenset(keys)  # type: ignore[arg-type]
    except TypeError as exc:
        raise StayPutError(code, "object keys must be strings") from exc
    missing = [k for k in required if k not in present]
    if missing:
        raise StayPutError(code, f"missing required fields: {', '.join(missing)}")


def _normalize_instruction_digest(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise StayPutError(
            "INVALID_INSTRUCTION_DIGEST",
            "instruction_digest must be null or 64 lowercase hex characters",
        )
    return value


def _normalize_repo_id(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise StayPutError(
            "INVALID_REPO_ID",
            "repo_id must be a non-empty comma-separated list of 40-hex commits",
        )
    if " " in value or value.startswith(",") or value.endswith(",") or ",," in value:
        raise StayPutError(
            "INVALID_REPO_ID",
            "repo_id must be comma-separated 40-hex SHAs with no spaces",
        )
    parts = value.split(",")
    for part in parts:
        if not _HEX40.fullmatch(part):
            raise StayPutError(
                "INVALID_REPO_ID",
                "each repo_id component must be a 40-character lowercase hex SHA",
            )
    canonical = ",".join(sorted(set(parts)))
    return canonical


def _normalize_worktree_key(value: object) -> str:
    if not isinstance(value, str):
        raise StayPutError("INVALID_WORKTREE_KEY", "worktree_key must be a string")
    if value == "":
        return ""
    if "\\" in value or value.startswith("/") or "//" in value:
        raise StayPutError(
            "INVALID_WORKTREE_KEY",
            "worktree_key must be a POSIX path relative to git common-dir",
        )
    if value.startswith("./"):
        raise StayPutError(
            "INVALID_WORKTREE_KEY",
            "worktree_key must not start with ./",
        )
    stripped = value.rstrip("/")
    if not stripped:
        raise StayPutError("INVALID_WORKTREE_KEY", "worktree_key must not be '/'")
    segments = stripped.split("/")
    if any(seg in {"", ".", ".."} for seg in segments):
        raise StayPutError(
            "INVALID_WORKTREE_KEY",
            "worktree_key must not contain empty, '.', or '..' segments",
        )
    return stripped


def _normalize_base_commit(value: object) -> str:
    if not isinstance(value, str) or not _HEX40.fullmatch(value):
        raise StayPutError(
            "INVALID_BASE_COMMIT",
            "base_commit must be a 40-character lowercase hex SHA",
        )
    return value


def _normalize_one_allowed_path(value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise StayPutError(
            "INVALID_ALLOWED_PATHS",
            "each allowed_paths entry must be a non-empty string",
        )
    if value.startswith("/") or "\\" in value or "//" in value:
        raise StayPutError(
            "INVALID_ALLOWED_PATHS",
            "allowed_paths entries must be repository-relative POSIX prefixes",
        )
    if len(value) >= 2 and value[1] == ":":
        raise StayPutError(
            "INVALID_ALLOWED_PATHS",
            "allowed_paths entries must not be absolute Windows paths",
        )
    if any(ch in value for ch in _GLOB_CHARS):
        raise StayPutError(
            "INVALID_ALLOWED_PATHS",
            "allowed_paths does not accept glob or regex syntax",
        )
    if value == ".":
        return "."
    stripped = value.rstrip("/")
    if stripped == "." or stripped == "":
        raise StayPutError("INVALID_ALLOWED_PATHS", "invalid allowed_paths entry")
    segments = stripped.split("/")
    if any(seg in {"", ".", ".."} for seg in segments):
        raise StayPutError(
            "INVALID_ALLOWED_PATHS",
            "allowed_paths entries must not contain '.', '..', or empty segments",
        )
    return stripped


def _normalize_allowed_paths(value: object) -> list[str]:
    if not isinstance(value, list):
        raise StayPutError("INVALID_ALLOWED_PATHS", "allowed_paths must be a list")
    if not value:
        raise StayPutError("INVALID_ALLOWED_PATHS", "allowed_paths must be non-empty")
    normalized = [_normalize_one_allowed_path(item) for item in value]
    return sorted(set(normalized))


def normalize_snapshot(raw: object) -> dict[str, Any]:
    """Validate and return the closed six-field snapshot.

    ``allowed_paths`` is a set of literal prefixes: sorted and deduplicated.
    ``repo_id`` components are likewise sorted and deduplicated.
    Caller mappings are not mutated.
    """
    mapping = _require_mapping(raw, code="INVALID_SNAPSHOT", what="snapshot")
    _reject_unknown(mapping.keys(), SNAPSHOT_FIELDS, code="UNKNOWN_FIELD")
    _require_keys(mapping.keys(), SNAPSHOT_FIELDS, code="MISSING_FIELD")
    if mapping["schema_version"] != SNAPSHOT_SCHEMA_VERSION:
        raise StayPutError(
            "UNSUPPORTED_SCHEMA",
            f"schema_version must be {SNAPSHOT_SCHEMA_VERSION}",
        )
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "instruction_digest": _normalize_instruction_digest(
            mapping["instruction_digest"]
        ),
        "repo_id": _normalize_repo_id(mapping["repo_id"]),
        "worktree_key": _normalize_worktree_key(mapping["worktree_key"]),
        "base_commit": _normalize_base_commit(mapping["base_commit"]),
        "allowed_paths": _normalize_allowed_paths(mapping["allowed_paths"]),
    }


def snapshot(
    *,
    instruction_digest: str | None = None,
    repo_id: str,
    worktree_key: str = "",
    base_commit: str,
    allowed_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Build a normalized snapshot. Default ``allowed_paths`` is ``["."]``."""
    return normalize_snapshot(
        {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "instruction_digest": instruction_digest,
            "repo_id": repo_id,
            "worktree_key": worktree_key,
            "base_commit": base_commit,
            "allowed_paths": list(DEFAULT_ALLOWED_PATHS)
            if allowed_paths is None
            else allowed_paths,
        }
    )


def serialize_snapshot(normalized: Mapping[str, Any]) -> str:
    """Stable JSON text of a normalized snapshot (not the identity digest)."""
    closed = normalize_snapshot(normalized)
    return json.dumps(closed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def parse_snapshot(text: str) -> dict[str, Any]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StayPutError(
            "INVALID_SNAPSHOT",
            "snapshot JSON is not parseable",
        ) from exc
    return normalize_snapshot(loaded)

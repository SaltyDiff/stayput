"""Canonical bytes and record_digest via public salt-grain 0.1.0 only."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from foundation_bytes_digest import digest_bytes
from foundation_json_canonicalize import canonicalize_json

from stayput.errors import StayPutError
from stayput.schema import (
    APPROVAL_FIELDS,
    APPROVAL_SCHEMA_VERSION,
    normalize_snapshot,
    serialize_snapshot,
)

_CANON_SCHEMA = "foundation.json_canonicalize.request.v0.1"
_DIGEST_SCHEMA = "foundation.bytes_digest.request.v0.1"


def canonical_snapshot_bytes(raw: object) -> bytes:
    """Return salt-grain canonical UTF-8 bytes of the normalized six-field snapshot."""
    snapshot = normalize_snapshot(raw)
    result = canonicalize_json(
        {
            "schema_version": _CANON_SCHEMA,
            "value": snapshot,
        }
    )
    if not result.get("ok"):
        failure = result.get("failure") or {}
        raise StayPutError(
            "CANONICALIZE_FAILED",
            str(failure.get("message") or "canonicalize_json failed"),
        )
    canonical = result.get("canonical")
    if type(canonical) is not bytes:
        raise StayPutError("CANONICALIZE_FAILED", "canonicalize_json returned no bytes")
    return canonical


def digest_snapshot(raw: object) -> str:
    """SHA-256 (lowercase hex) of ``canonical_snapshot_bytes``."""
    canonical = canonical_snapshot_bytes(raw)
    result = digest_bytes(
        {
            "schema_version": _DIGEST_SCHEMA,
            "data": canonical,
        }
    )
    if not result.get("ok") or not isinstance(result.get("digest"), str):
        failure = result.get("failure") or {}
        raise StayPutError(
            "CANONICALIZE_FAILED",
            str(failure.get("message") or "digest_bytes failed"),
        )
    return result["digest"]


def build_approval(raw_snapshot: object) -> dict[str, Any]:
    """Wrap a snapshot with ``stayput.approval.v0.1`` and ``record_digest``."""
    snapshot = normalize_snapshot(raw_snapshot)
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "snapshot": snapshot,
        "record_digest": digest_snapshot(snapshot),
    }


def normalize_approval(raw: object) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise StayPutError("INVALID_APPROVAL", "approval must be an object")
    try:
        keys = frozenset(raw.keys())
    except TypeError as exc:
        raise StayPutError("INVALID_APPROVAL", "approval keys must be strings") from exc
    extra = sorted(str(k) for k in keys if k not in APPROVAL_FIELDS)
    if extra:
        raise StayPutError(
            "UNKNOWN_FIELD",
            f"unknown approval fields: {', '.join(extra)}",
        )
    missing = [k for k in APPROVAL_FIELDS if k not in keys]
    if missing:
        raise StayPutError(
            "MISSING_FIELD",
            f"missing required approval fields: {', '.join(missing)}",
        )
    if raw["schema_version"] != APPROVAL_SCHEMA_VERSION:
        raise StayPutError(
            "UNSUPPORTED_SCHEMA",
            f"approval schema_version must be {APPROVAL_SCHEMA_VERSION}",
        )
    digest = raw["record_digest"]
    if not isinstance(digest, str) or len(digest) != 64 or any(
        ch not in "0123456789abcdef" for ch in digest
    ):
        raise StayPutError(
            "INVALID_APPROVAL",
            "record_digest must be 64 lowercase hex characters",
        )
    snapshot = normalize_snapshot(raw["snapshot"])
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "snapshot": snapshot,
        "record_digest": digest,
    }


def verify_approval(raw: object) -> dict[str, Any]:
    """Recompute ``record_digest`` over the canonical snapshot.

    Returns ``{"ok": True, "approval": ...}`` or raises ``StayPutError``.
    A digest mismatch is ``DIGEST_MISMATCH`` (not MATCH/MISMATCH locus classes).
    """
    approval = normalize_approval(raw)
    expected = digest_snapshot(approval["snapshot"])
    if expected != approval["record_digest"]:
        raise StayPutError(
            "DIGEST_MISMATCH",
            "record_digest does not match the canonical snapshot",
        )
    return {"ok": True, "approval": approval}


def serialize_approval(raw: object) -> str:
    approval = normalize_approval(raw)
    payload = {
        "schema_version": approval["schema_version"],
        "snapshot": approval["snapshot"],
        "record_digest": approval["record_digest"],
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def parse_approval(text: str) -> dict[str, Any]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StayPutError(
            "INVALID_APPROVAL",
            "approval JSON is not parseable",
        ) from exc
    return normalize_approval(loaded)


# Re-export for callers that only import canonicalize.
__all__ = [
    "build_approval",
    "canonical_snapshot_bytes",
    "digest_snapshot",
    "normalize_approval",
    "parse_approval",
    "serialize_approval",
    "serialize_snapshot",
    "verify_approval",
]

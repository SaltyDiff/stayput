"""Exact-byte instruction digest via public salt-grain 0.1.0.

No normalization. No prompt models. Bytes are authority.
"""

from __future__ import annotations

from foundation_bytes_digest import digest_bytes

from taskpin.errors import TaskPinError

_DIGEST_SCHEMA = "foundation.bytes_digest.request.v0.1"


def digest_instruction(data: bytes) -> str:
    """SHA-256 (lowercase hex) of the exact instruction bytes.

    Empty bytes are a real digest, not null. Failures raise ``TaskPinError``
    and must not be treated as MATCH.
    """
    if type(data) is not bytes:
        raise TaskPinError(
            "INVALID_INSTRUCTION",
            "instruction digest input must be bytes",
        )
    result = digest_bytes(
        {
            "schema_version": _DIGEST_SCHEMA,
            "data": data,
        }
    )
    digest = result.get("digest")
    if not result.get("ok") or not isinstance(digest, str):
        failure = result.get("failure") or {}
        raise TaskPinError(
            "DIGEST_FAILED",
            str(failure.get("message") or "digest_bytes failed"),
        )
    return digest


def digest_instruction_text(text: str) -> str:
    """Digest ``text`` after explicit UTF-8 encoding.

    Encoding is UTF-8 with no BOM, no newline translation, and no Unicode
    normalization. Prefer ``digest_instruction`` when bytes are already known.
    """
    if type(text) is not str:
        raise TaskPinError(
            "INVALID_INSTRUCTION",
            "instruction text helper requires a str",
        )
    return digest_instruction(text.encode("utf-8"))

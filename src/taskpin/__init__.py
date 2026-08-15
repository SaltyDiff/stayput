"""TaskPin — SaltyDiff git-locus integrity primitive.

T1 public surface is the closed six-field snapshot, salt-grain
canonicalization, and approval ``record_digest``. No Git, CLI, or host
adapters in this release.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from taskpin.canonicalize import (
    build_approval,
    canonical_snapshot_bytes,
    digest_snapshot,
    normalize_approval,
    parse_approval,
    serialize_approval,
    verify_approval,
)
from taskpin.errors import TaskPinError
from taskpin.schema import (
    APPROVAL_SCHEMA_VERSION,
    DEFAULT_APPROVAL_PATH,
    SNAPSHOT_SCHEMA_VERSION,
    normalize_snapshot,
    parse_snapshot,
    serialize_snapshot,
    snapshot,
)

PRODUCT_FAMILY = "SaltyDiff"
CAPABILITY_ID = "taskpin"
CAPABILITY_VERSION = "0.1.0"

try:
    __version__ = version("taskpin")
except PackageNotFoundError:  # pragma: no cover - editable/source tree fallback
    __version__ = CAPABILITY_VERSION

__all__ = [
    "APPROVAL_SCHEMA_VERSION",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "DEFAULT_APPROVAL_PATH",
    "PRODUCT_FAMILY",
    "SNAPSHOT_SCHEMA_VERSION",
    "TaskPinError",
    "__version__",
    "build_approval",
    "canonical_snapshot_bytes",
    "digest_snapshot",
    "normalize_approval",
    "normalize_snapshot",
    "parse_approval",
    "parse_snapshot",
    "serialize_approval",
    "serialize_snapshot",
    "snapshot",
    "verify_approval",
]

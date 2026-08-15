"""StayPut — SaltyDiff git-locus integrity primitive.

Host-neutral library and CLI. Thin host examples live under examples/.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from stayput.canonicalize import (
    build_approval,
    canonical_snapshot_bytes,
    digest_snapshot,
    normalize_approval,
    parse_approval,
    serialize_approval,
    verify_approval,
)
from stayput.check import check
from stayput.compare import (
    BASE_COMMIT_MISMATCH,
    INSTRUCTION_DRIFT,
    PATH_OUTSIDE_ALLOWLIST,
    REPOSITORY_MISMATCH,
    WORKTREE_MISMATCH,
    compare_locus,
)
from stayput.errors import StayPutError
from stayput.instruction import digest_instruction, digest_instruction_text
from stayput.project import project_locus, project_paths, project_snapshot
from stayput.save import save
from stayput.schema import (
    APPROVAL_SCHEMA_VERSION,
    DEFAULT_APPROVAL_PATH,
    SNAPSHOT_SCHEMA_VERSION,
    normalize_snapshot,
    parse_snapshot,
    serialize_snapshot,
    snapshot,
)

PRODUCT_FAMILY = "SaltyDiff"
CAPABILITY_ID = "stayput"
CAPABILITY_VERSION = "0.1.0"

try:
    __version__ = version("stayput")
except PackageNotFoundError:  # pragma: no cover - editable/source tree fallback
    __version__ = CAPABILITY_VERSION

__all__ = [
    "APPROVAL_SCHEMA_VERSION",
    "BASE_COMMIT_MISMATCH",
    "CAPABILITY_ID",
    "CAPABILITY_VERSION",
    "DEFAULT_APPROVAL_PATH",
    "INSTRUCTION_DRIFT",
    "PATH_OUTSIDE_ALLOWLIST",
    "PRODUCT_FAMILY",
    "REPOSITORY_MISMATCH",
    "SNAPSHOT_SCHEMA_VERSION",
    "WORKTREE_MISMATCH",
    "StayPutError",
    "__version__",
    "build_approval",
    "canonical_snapshot_bytes",
    "check",
    "compare_locus",
    "digest_instruction",
    "digest_instruction_text",
    "digest_snapshot",
    "normalize_approval",
    "normalize_snapshot",
    "parse_approval",
    "parse_snapshot",
    "project_locus",
    "project_paths",
    "project_snapshot",
    "save",
    "serialize_approval",
    "serialize_snapshot",
    "snapshot",
    "verify_approval",
]

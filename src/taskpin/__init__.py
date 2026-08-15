"""TaskPin — SaltyDiff git-locus integrity primitive.

T1: closed six-field snapshot, salt-grain canonicalization, record_digest.
T2: Git locus projection for repo_id, worktree_key, and base ancestry.
T3: changed-path projection and PATH_OUTSIDE_ALLOWLIST.
T4: optional instruction-byte verification and INSTRUCTION_DRIFT.
No CLI, hooks, save/check workflow, or host integration in this release.
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
from taskpin.compare import (
    BASE_COMMIT_MISMATCH,
    INSTRUCTION_DRIFT,
    PATH_OUTSIDE_ALLOWLIST,
    REPOSITORY_MISMATCH,
    WORKTREE_MISMATCH,
    compare_locus,
)
from taskpin.errors import TaskPinError
from taskpin.instruction import digest_instruction, digest_instruction_text
from taskpin.project import project_locus, project_paths, project_snapshot
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
    "TaskPinError",
    "__version__",
    "build_approval",
    "canonical_snapshot_bytes",
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
    "serialize_approval",
    "serialize_snapshot",
    "snapshot",
    "verify_approval",
]

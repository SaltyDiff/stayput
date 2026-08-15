from __future__ import annotations

import json
from pathlib import Path

import pytest

from stayput import (
    StayPutError,
    build_approval,
    canonical_snapshot_bytes,
    digest_snapshot,
    normalize_snapshot,
    parse_approval,
    parse_snapshot,
    serialize_approval,
    serialize_snapshot,
    verify_approval,
)
from tests.conftest import GOLDENS, INSTRUCTION, sample_snapshot

VECTOR = GOLDENS / "v0_1_null_instruction.json"


def _load_vector() -> dict[str, object]:
    return json.loads(VECTOR.read_text(encoding="utf-8"))


def test_identical_snapshot_identical_canonical_bytes() -> None:
    left = canonical_snapshot_bytes(sample_snapshot())
    right = canonical_snapshot_bytes(sample_snapshot())
    assert left == right
    assert isinstance(left, bytes)


def test_identical_snapshot_identical_digest() -> None:
    assert digest_snapshot(sample_snapshot()) == digest_snapshot(sample_snapshot())
    assert len(digest_snapshot(sample_snapshot())) == 64


def test_input_field_order_does_not_change_canonical_result() -> None:
    ordered = sample_snapshot()
    shuffled = {
        "allowed_paths": ["."],
        "base_commit": ordered["base_commit"],
        "worktree_key": "",
        "repo_id": ordered["repo_id"],
        "instruction_digest": None,
        "schema_version": "stayput.snapshot.v0.1",
    }
    assert canonical_snapshot_bytes(ordered) == canonical_snapshot_bytes(shuffled)
    assert digest_snapshot(ordered) == digest_snapshot(shuffled)


def test_allowed_paths_order_canonicalizes_to_sorted_set() -> None:
    a = sample_snapshot(allowed_paths=["z", "a"])
    b = sample_snapshot(allowed_paths=["a", "z", "a"])
    assert canonical_snapshot_bytes(a) == canonical_snapshot_bytes(b)
    assert normalize_snapshot(a)["allowed_paths"] == ["a", "z"]


def test_null_instruction_changes_digest_vs_real_digest() -> None:
    null_digest = digest_snapshot(sample_snapshot())
    hashed = digest_snapshot(sample_snapshot(instruction_digest=INSTRUCTION))
    assert null_digest != hashed


def test_canonical_serialize_parse_serialize_stable() -> None:
    first = serialize_snapshot(sample_snapshot())
    second = serialize_snapshot(parse_snapshot(first))
    assert first == second
    approval = build_approval(sample_snapshot())
    text = serialize_approval(approval)
    assert serialize_approval(parse_approval(text)) == text


def test_no_timestamp_random_or_environment_in_canonical_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USER", "should-not-appear")
    monkeypatch.setenv("HOME", "/tmp/should-not-appear")
    payload = canonical_snapshot_bytes(sample_snapshot())
    assert b"should-not-appear" not in payload
    assert b"timestamp" not in payload
    assert b"random" not in payload
    decoded = json.loads(payload.decode("utf-8"))
    assert set(decoded) == {
        "schema_version",
        "instruction_digest",
        "repo_id",
        "worktree_key",
        "base_commit",
        "allowed_paths",
    }


def test_golden_canonical_bytes_and_digest() -> None:
    vector = _load_vector()
    snapshot = vector["snapshot"]
    assert isinstance(snapshot, dict)
    canonical = canonical_snapshot_bytes(snapshot)
    assert canonical.hex() == vector["canonical_hex"]
    assert canonical.decode("utf-8") == vector["canonical_utf8"]
    assert digest_snapshot(snapshot) == vector["record_digest"]


def test_altered_snapshot_fails_record_digest_verification() -> None:
    approval = build_approval(sample_snapshot())
    tampered = {
        **approval,
        "snapshot": {**approval["snapshot"], "worktree_key": "worktrees/other"},
    }
    with pytest.raises(StayPutError) as exc:
        verify_approval(tampered)
    assert exc.value.code == "DIGEST_MISMATCH"


def test_altered_record_digest_fails_verification() -> None:
    approval = build_approval(sample_snapshot())
    other = "0" * 64
    assert other != approval["record_digest"]
    with pytest.raises(StayPutError) as exc:
        verify_approval({**approval, "record_digest": other})
    assert exc.value.code == "DIGEST_MISMATCH"


def test_unknown_approval_wrapper_fields_rejected() -> None:
    approval = build_approval(sample_snapshot())
    with pytest.raises(StayPutError) as exc:
        verify_approval({**approval, "campaign_id": "nope"})
    assert exc.value.code == "UNKNOWN_FIELD"


def test_verify_approval_accepts_matching_digest() -> None:
    approval = build_approval(sample_snapshot())
    checked = verify_approval(approval)
    assert checked["ok"] is True
    assert checked["approval"]["record_digest"] == approval["record_digest"]


def test_golden_file_exists() -> None:
    assert Path(VECTOR).is_file()

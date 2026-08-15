from __future__ import annotations

import json
from pathlib import Path

import pytest

from stayput import (
    INSTRUCTION_DRIFT,
    PATH_OUTSIDE_ALLOWLIST,
    StayPutError,
    compare_locus,
    digest_instruction,
    digest_instruction_text,
    normalize_snapshot,
    project_snapshot,
)
from tests.conftest import GOLDENS, INSTRUCTION, sample_snapshot
from tests.gitutil import commit_file, init_repo, write_file

VECTOR = GOLDENS / "v0_1_instruction_bytes.json"


def _load_vectors() -> list[dict[str, str]]:
    payload = json.loads(VECTOR.read_text(encoding="utf-8"))
    return list(payload["vectors"])


def test_golden_instruction_digests() -> None:
    for row in _load_vectors():
        data = bytes.fromhex(row["data_hex"])
        assert digest_instruction(data) == row["digest"]


def test_empty_bytes_are_not_null() -> None:
    digest = digest_instruction(b"")
    assert digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    snap = sample_snapshot(instruction_digest=digest)
    assert normalize_snapshot(snap)["instruction_digest"] == digest
    assert sample_snapshot()["instruction_digest"] is None


def test_abc_matches_known_sha256() -> None:
    assert digest_instruction(b"abc") == INSTRUCTION


def test_binary_and_utf8_are_deterministic() -> None:
    blob = bytes(range(256))
    assert digest_instruction(blob) == digest_instruction(blob)
    text = "café"
    assert digest_instruction(text.encode("utf-8")) == digest_instruction_text(text)


def test_text_helper_is_explicit_utf8() -> None:
    assert digest_instruction_text("abc") == digest_instruction(b"abc")
    with pytest.raises(StayPutError) as exc:
        digest_instruction_text(b"abc")  # type: ignore[arg-type]
    assert exc.value.code == "INVALID_INSTRUCTION"


def test_non_bytes_input_rejected() -> None:
    with pytest.raises(StayPutError) as exc:
        digest_instruction("abc")  # type: ignore[arg-type]
    assert exc.value.code == "INVALID_INSTRUCTION"


def test_digest_failure_is_not_match(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_payload: object) -> dict[str, object]:
        return {"ok": False, "failure": {"message": "forced"}}

    monkeypatch.setattr("stayput.instruction.digest_bytes", boom)
    with pytest.raises(StayPutError) as exc:
        digest_instruction(b"abc")
    assert exc.value.code == "DIGEST_FAILED"


def _seal_with_bytes(repo: Path, data: bytes, allowed: list[str] | None = None) -> dict:
    return project_snapshot(
        repo,
        instruction_digest=digest_instruction(data),
        allowed_paths=allowed,
    )


def test_sealed_bytes_match(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"do the task")
    result = compare_locus(sealed, repo, instruction_bytes=b"do the task")
    assert result["status"] == "MATCH"
    assert result["mismatches"] == []


def test_null_digest_no_bytes_is_match(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    assert sealed["instruction_digest"] is None
    result = compare_locus(sealed, repo)
    assert result["status"] == "MATCH"


def test_null_digest_with_bytes_makes_no_claim(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    result = compare_locus(sealed, repo, instruction_bytes=b"ignored")
    assert result["status"] == "MATCH"
    assert all(m["class"] != INSTRUCTION_DRIFT for m in result["mismatches"])


def test_empty_bytes_can_be_sealed_and_matched(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"")
    assert sealed["instruction_digest"] == digest_instruction(b"")
    assert compare_locus(sealed, repo, instruction_bytes=b"")["status"] == "MATCH"
    result = compare_locus(sealed, repo, instruction_bytes=b"x")
    assert [m["class"] for m in result["mismatches"]] == [INSTRUCTION_DRIFT]


def test_one_byte_change_is_drift(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"abc")
    result = compare_locus(sealed, repo, instruction_bytes=b"abd")
    assert result["status"] == "MISMATCH"
    assert [m["class"] for m in result["mismatches"]] == [INSTRUCTION_DRIFT]


def test_whitespace_change_is_drift(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"hello world")
    result = compare_locus(sealed, repo, instruction_bytes=b"hello  world")
    assert [m["class"] for m in result["mismatches"]] == [INSTRUCTION_DRIFT]


def test_lf_vs_crlf_is_drift(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"hello\n")
    result = compare_locus(sealed, repo, instruction_bytes=b"hello\r\n")
    assert [m["class"] for m in result["mismatches"]] == [INSTRUCTION_DRIFT]
    assert digest_instruction(b"hello\n") != digest_instruction(b"hello\r\n")


def test_unicode_byte_difference_is_drift(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    nfc = "café".encode("utf-8")  # noqa: UP012 — encoding is the claim
    nfd = "cafe\u0301".encode("utf-8")  # noqa: UP012, RUF100 — encoding is the claim
    assert nfc != nfd
    sealed = _seal_with_bytes(repo, nfc)
    result = compare_locus(sealed, repo, instruction_bytes=nfd)
    assert [m["class"] for m in result["mismatches"]] == [INSTRUCTION_DRIFT]


def test_same_semantic_text_different_bytes_is_drift(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"Task: fix the bug.")
    result = compare_locus(sealed, repo, instruction_bytes=b"task: fix the bug.")
    assert [m["class"] for m in result["mismatches"]] == [INSTRUCTION_DRIFT]


def test_sealed_digest_without_bytes_is_required(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"need me")
    with pytest.raises(StayPutError) as exc:
        compare_locus(sealed, repo)
    assert exc.value.code == "INSTRUCTION_REQUIRED"
    assert INSTRUCTION_DRIFT not in [
        m["class"] for m in exc.value.details.get("mismatches", [])
    ]


def test_instruction_required_does_not_suppress_path_mismatches(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"scope", allowed=["src/auth"])
    write_file(repo, "docs/out.md", "x\n")
    with pytest.raises(StayPutError) as exc:
        compare_locus(sealed, repo)
    assert exc.value.code == "INSTRUCTION_REQUIRED"
    classes = [m["class"] for m in exc.value.details["mismatches"]]
    assert PATH_OUTSIDE_ALLOWLIST in classes


def test_instruction_drift_collects_with_path_mismatch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"scope", allowed=["src/auth"])
    write_file(repo, "docs/out.md", "x\n")
    result = compare_locus(sealed, repo, instruction_bytes=b"other")
    assert [m["class"] for m in result["mismatches"]] == [
        PATH_OUTSIDE_ALLOWLIST,
        INSTRUCTION_DRIFT,
    ]


def test_digest_failure_does_not_become_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = _seal_with_bytes(repo, b"abc")

    def boom(_payload: object) -> dict[str, object]:
        return {"ok": False, "failure": {"message": "forced"}}

    monkeypatch.setattr("stayput.instruction.digest_bytes", boom)
    with pytest.raises(StayPutError) as exc:
        compare_locus(sealed, repo, instruction_bytes=b"abc")
    assert exc.value.code == "DIGEST_FAILED"
    assert exc.value.details["mismatches"] == []


def test_malformed_sealed_digest_still_rejected_by_schema(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    sealed = project_snapshot(repo)
    sealed = {**sealed, "instruction_digest": "not-a-digest"}
    with pytest.raises(StayPutError) as exc:
        compare_locus(sealed, repo, instruction_bytes=b"abc")
    assert exc.value.code == "INVALID_INSTRUCTION_DIGEST"


def test_schema_still_six_fields(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    snap = _seal_with_bytes(repo, b"abc")
    assert set(snap) == {
        "schema_version",
        "instruction_digest",
        "repo_id",
        "worktree_key",
        "base_commit",
        "allowed_paths",
    }
    assert snap["instruction_digest"] == INSTRUCTION

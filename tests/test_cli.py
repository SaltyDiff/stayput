from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from taskpin import DEFAULT_APPROVAL_PATH, digest_instruction
from tests.gitutil import commit_file, git, init_repo, write_file


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "taskpin", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_project_default_snapshot(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    proc = run_cli("project", "--cwd", str(repo), cwd=repo)
    assert proc.returncode == 0
    snap = json.loads(proc.stdout)
    assert snap["schema_version"] == "taskpin.snapshot.v0.1"
    assert snap["allowed_paths"] == ["."]
    assert snap["instruction_digest"] is None
    assert not (repo / DEFAULT_APPROVAL_PATH).exists()


def test_project_json_is_single_document(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    proc = run_cli("project", "--cwd", str(repo), "--json", cwd=repo)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert set(payload["snapshot"]) == {
        "schema_version",
        "instruction_digest",
        "repo_id",
        "worktree_key",
        "base_commit",
        "allowed_paths",
    }
    assert "MATCH" not in proc.stdout
    assert "ERROR" not in proc.stdout


def test_project_instruction_file_exact_bytes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    inst = tmp_path / "inst.bin"
    inst.write_bytes(b"hello\r\n")
    proc = run_cli(
        "project",
        "--cwd",
        str(repo),
        "--instruction-file",
        str(inst),
        "--json",
        cwd=repo,
    )
    assert proc.returncode == 0
    digest = json.loads(proc.stdout)["snapshot"]["instruction_digest"]
    assert digest == digest_instruction(b"hello\r\n")
    assert digest != digest_instruction(b"hello\n")


def test_project_allowed_path_repeats_canonicalize(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/a.py", "a\n", "first")
    proc = run_cli(
        "project",
        "--cwd",
        str(repo),
        "--allowed-path",
        "src/z",
        "--allowed-path",
        "src/a",
        "--allowed-path",
        "src/a",
        "--json",
        cwd=repo,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["snapshot"]["allowed_paths"] == ["src/a", "src/z"]


def test_save_default_path_and_json(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    proc = run_cli("save", "--cwd", str(repo), "--json", cwd=repo)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert (repo / DEFAULT_APPROVAL_PATH).is_file()
    assert payload["approval"]["snapshot"]["allowed_paths"] == ["."]


def test_save_custom_path(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    dest = repo / "sealed.json"
    proc = run_cli("save", "--cwd", str(repo), "--path", str(dest), cwd=repo)
    assert proc.returncode == 0
    assert dest.is_file()
    assert "SAVED" in proc.stdout
    assert not (repo / DEFAULT_APPROVAL_PATH).exists()


def test_save_without_replace_fails(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    assert run_cli("save", "--cwd", str(repo), cwd=repo).returncode == 0
    proc = run_cli("save", "--cwd", str(repo), cwd=repo)
    assert proc.returncode == 1
    assert "ERROR: APPROVAL_ALREADY_EXISTS" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert "Traceback" not in proc.stdout


def test_save_replace_succeeds(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    first = run_cli("save", "--cwd", str(repo), "--json", cwd=repo)
    commit_file(repo, "a.txt", "a\nb\n", "second")
    second = run_cli("save", "--cwd", str(repo), "--replace", "--json", cwd=repo)
    assert second.returncode == 0
    left = json.loads(first.stdout)["approval"]["record_digest"]
    right = json.loads(second.stdout)["approval"]["record_digest"]
    assert left != right


def test_save_instruction_file_and_operational_failure(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    inst = tmp_path / "task.bin"
    inst.write_bytes(b"abc")
    proc = run_cli(
        "save",
        "--cwd",
        str(repo),
        "--instruction-file",
        str(inst),
        "--json",
        cwd=repo,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["approval"]["snapshot"][
        "instruction_digest"
    ] == digest_instruction(b"abc")
    missing = run_cli(
        "save",
        "--cwd",
        str(repo),
        "--instruction-file",
        str(tmp_path / "nope.bin"),
        "--json",
        cwd=repo,
    )
    assert missing.returncode == 1
    err = json.loads(missing.stdout)
    assert err["ok"] is False
    assert err["error"] == "INSTRUCTION_UNREADABLE"


def test_check_match_exit_0(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    run_cli("save", "--cwd", str(repo), cwd=repo)
    proc = run_cli("check", "--cwd", str(repo), cwd=repo)
    assert proc.returncode == 0
    assert proc.stdout == "MATCH\n"


def test_check_mismatch_exit_2(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    run_cli(
        "save",
        "--cwd",
        str(repo),
        "--allowed-path",
        "src/auth",
        cwd=repo,
    )
    write_file(repo, "docs/out.md", "x\n")
    before = (repo / DEFAULT_APPROVAL_PATH).read_bytes()
    proc = run_cli("check", "--cwd", str(repo), cwd=repo)
    assert proc.returncode == 2
    assert proc.stdout.startswith("MISMATCH\n")
    assert "PATH_OUTSIDE_ALLOWLIST: docs/out.md" in proc.stdout
    assert (repo / DEFAULT_APPROVAL_PATH).read_bytes() == before


def test_check_wrong_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    linked = tmp_path / "linked"
    git(repo, "worktree", "add", str(linked), "-b", "feat")
    run_cli("save", "--cwd", str(linked), cwd=linked)
    proc = run_cli(
        "check",
        "--cwd",
        str(repo),
        "--path",
        str(linked / DEFAULT_APPROVAL_PATH),
        cwd=repo,
    )
    assert proc.returncode == 2
    assert "WORKTREE_MISMATCH" in proc.stdout


def test_check_instruction_drift_and_required(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    inst = tmp_path / "inst.txt"
    inst.write_bytes(b"abc")
    run_cli(
        "save",
        "--cwd",
        str(repo),
        "--instruction-file",
        str(inst),
        cwd=repo,
    )
    other = tmp_path / "other.txt"
    other.write_bytes(b"abd")
    drift = run_cli(
        "check",
        "--cwd",
        str(repo),
        "--instruction-file",
        str(other),
        cwd=repo,
    )
    assert drift.returncode == 2
    assert "INSTRUCTION_DRIFT" in drift.stdout
    required = run_cli("check", "--cwd", str(repo), "--json", cwd=repo)
    assert required.returncode == 1
    payload = json.loads(required.stdout)
    assert payload["ok"] is False
    assert payload["error"] == "INSTRUCTION_REQUIRED"


def test_check_missing_and_tampered_exit_1(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    missing = run_cli("check", "--cwd", str(repo), cwd=repo)
    assert missing.returncode == 1
    assert "ERROR: APPROVAL_MISSING" in missing.stderr
    run_cli("save", "--cwd", str(repo), cwd=repo)
    target = repo / DEFAULT_APPROVAL_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["record_digest"] = "0" * 64
    target.write_text(json.dumps(payload), encoding="utf-8")
    tampered = run_cli("check", "--cwd", str(repo), "--json", cwd=repo)
    assert tampered.returncode == 1
    assert json.loads(tampered.stdout)["error"] == "DIGEST_MISMATCH"


def test_check_json_preserves_structured_fields(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/auth/a.py", "a\n", "first")
    run_cli("save", "--cwd", str(repo), "--allowed-path", "src/auth", cwd=repo)
    write_file(repo, "docs/out.md", "x\n")
    proc = run_cli("check", "--cwd", str(repo), "--json", cwd=repo)
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["status"] == "MISMATCH"
    assert payload["mismatches"][0]["class"] == "PATH_OUTSIDE_ALLOWLIST"
    assert payload["delivered_paths"] == ["docs/out.md"]
    assert "ok" in payload


def test_cli_usage_is_exit_1_not_mismatch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    proc = run_cli("--json", cwd=repo)
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["error"] == "CLI_USAGE"

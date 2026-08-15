from __future__ import annotations

from pathlib import Path

GOLDENS = Path(__file__).resolve().parent / "goldens"

ROOT_A = "3073f9a9961e954de80ca5ae1239813d1e3e7e36"
ROOT_B = "ad9d8d14eec4fefd3bdfe19315bee0ac28e8fa1b"
BASE = "1a09b140a9c21ec2d47dd07ce385a348bf78820d"
INSTRUCTION = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def sample_snapshot(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "taskpin.snapshot.v0.1",
        "instruction_digest": None,
        "repo_id": ROOT_A,
        "worktree_key": "",
        "base_commit": BASE,
        "allowed_paths": ["."],
    }
    payload.update(overrides)
    return payload

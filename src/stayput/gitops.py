"""Narrow Git CLI adapter. No host types. No business comparison."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from stayput.errors import StayPutError

MIN_GIT_VERSION = (2, 31)
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_VERSION_RE = re.compile(r"git version (\d+)\.(\d+)")
_REPLACE_OFF = ("-c", "core.useReplaceRefs=false")


def parse_git_version(text: str) -> tuple[int, int] | None:
    match = _VERSION_RE.search(text)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)))


def _run(
    cwd: Path,
    args: list[str],
    *,
    git_bin: str,
    replace_off: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = [git_bin]
    if replace_off:
        cmd.extend(_REPLACE_OFF)
    cmd.extend(args)
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise StayPutError(
            "GIT_NOT_FOUND",
            f"git executable not found: {git_bin}",
        ) from exc
    except OSError as exc:
        raise StayPutError("GIT_FAILURE", f"git could not be executed: {exc}") from exc


def require_git(cwd: Path, *, git_bin: str) -> tuple[int, int]:
    proc = _run(cwd, ["--version"], git_bin=git_bin, replace_off=False)
    if proc.returncode != 0:
        raise StayPutError("GIT_FAILURE", "git --version failed")
    version = parse_git_version(proc.stdout or "")
    if version is None:
        raise StayPutError("GIT_FAILURE", "could not parse git --version")
    if version < MIN_GIT_VERSION:
        raise StayPutError(
            "GIT_TOO_OLD",
            f"git {version[0]}.{version[1]} is unsupported; require >= 2.31",
        )
    return version


def _truthy(proc: subprocess.CompletedProcess[str], *, code: str, what: str) -> bool:
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        if "not a git repository" in err.lower():
            raise StayPutError("NOT_A_REPOSITORY", f"{what}: not a git repository")
        raise StayPutError(code, f"{what} failed")
    return proc.stdout.strip() == "true"


def inspect_repository(cwd: Path, *, git_bin: str) -> dict[str, Path | bool]:
    """Fail-closed repository preconditions. Returns resolved git-dir and common-dir."""
    require_git(cwd, git_bin=git_bin)
    if not cwd.is_dir():
        raise StayPutError("NOT_A_REPOSITORY", f"cwd is not a directory: {cwd}")

    inside = _run(cwd, ["rev-parse", "--is-inside-work-tree"], git_bin=git_bin)
    bare = _run(cwd, ["rev-parse", "--is-bare-repository"], git_bin=git_bin)
    if bare.returncode == 0 and bare.stdout.strip() == "true":
        raise StayPutError("BARE_REPOSITORY", "bare repositories are out of V0")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise StayPutError("NOT_A_REPOSITORY", "cwd is not a git work tree")

    shallow = _run(cwd, ["rev-parse", "--is-shallow-repository"], git_bin=git_bin)
    if _truthy(shallow, code="GIT_FAILURE", what="rev-parse --is-shallow-repository"):
        raise StayPutError("SHALLOW_REPOSITORY", "shallow repositories fail closed")

    common = _absolute_git_path(cwd, "--git-common-dir", git_bin=git_bin)
    gitdir = _absolute_git_path(cwd, "--git-dir", git_bin=git_bin)
    toplevel = _absolute_git_path(cwd, "--show-toplevel", git_bin=git_bin)
    grafts = common / "info" / "grafts"
    if grafts.is_file():
        raise StayPutError(
            "GRAFTS_PRESENT",
            "info/grafts rewrites ancestry and fails closed",
        )
    return {"common_dir": common, "git_dir": gitdir, "toplevel": toplevel}


def _absolute_git_path(cwd: Path, flag: str, *, git_bin: str) -> Path:
    proc = _run(
        cwd,
        ["rev-parse", "--path-format=absolute", flag],
        git_bin=git_bin,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        if "unknown option" in err.lower() or "path-format" in err.lower():
            raise StayPutError(
                "GIT_TOO_OLD",
                "git does not support --path-format=absolute",
            )
        raise StayPutError("GIT_FAILURE", f"rev-parse {flag} failed")
    raw = proc.stdout.strip()
    if not raw:
        raise StayPutError("GIT_FAILURE", f"rev-parse {flag} returned empty")
    try:
        return Path(raw).resolve(strict=True)
    except OSError as exc:
        raise StayPutError(
            "WORKTREE_UNRESOLVABLE",
            f"cannot realpath {flag}: {raw}",
        ) from exc


def read_head(cwd: Path, *, git_bin: str) -> str:
    proc = _run(cwd, ["rev-parse", "HEAD"], git_bin=git_bin)
    if proc.returncode != 0:
        raise StayPutError("GIT_FAILURE", "rev-parse HEAD failed")
    sha = proc.stdout.strip().lower()
    if not _HEX40.fullmatch(sha):
        raise StayPutError("GIT_FAILURE", "HEAD is not a 40-hex commit")
    return sha


def commit_exists(cwd: Path, sha: str, *, git_bin: str) -> bool:
    if not _HEX40.fullmatch(sha):
        raise StayPutError(
            "INVALID_BASE_COMMIT",
            "commit identity must be a 40-character lowercase hex SHA",
        )
    proc = _run(cwd, ["cat-file", "-e", f"{sha}^{{commit}}"], git_bin=git_bin)
    if proc.returncode == 0:
        return True
    err = (proc.stderr or proc.stdout or "").strip().lower()
    if proc.returncode == 1 or "not a valid object" in err or "does not exist" in err:
        return False
    raise StayPutError("GIT_INCOMPLETE", f"cat-file -e {sha} failed unexpectedly")


def roots_of(cwd: Path, commit: str, *, git_bin: str) -> str:
    if not _HEX40.fullmatch(commit):
        raise StayPutError(
            "INVALID_BASE_COMMIT",
            "commit identity must be a 40-character lowercase hex SHA",
        )
    proc = _run(cwd, ["rev-list", "--max-parents=0", commit], git_bin=git_bin)
    if proc.returncode != 0:
        raise StayPutError(
            "GIT_INCOMPLETE",
            f"rev-list --max-parents=0 {commit} failed",
        )
    lines = [line.strip().lower() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise StayPutError("GIT_INCOMPLETE", "rev-list returned no roots")
    for line in lines:
        if not _HEX40.fullmatch(line):
            raise StayPutError("GIT_INCOMPLETE", "rev-list returned a non-40-hex root")
    return ",".join(sorted(set(lines)))


def merge_base_is_ancestor(cwd: Path, ancestor: str, *, git_bin: str) -> int:
    """Return the raw merge-base --is-ancestor exit code (0, 1, or other)."""
    if not _HEX40.fullmatch(ancestor):
        raise StayPutError(
            "INVALID_BASE_COMMIT",
            "sealed base_commit must be a 40-character lowercase hex SHA",
        )
    proc = _run(
        cwd,
        ["merge-base", "--is-ancestor", ancestor, "HEAD"],
        git_bin=git_bin,
    )
    return proc.returncode


def worktree_key(git_dir: Path, common_dir: Path) -> str:
    git_n = _normalize_fs_path(git_dir)
    common_n = _normalize_fs_path(common_dir)
    if _paths_equal(git_n, common_n):
        return ""
    rel = os.path.relpath(git_n, common_n).replace("\\", "/")
    if rel == ".":
        return ""
    if rel == ".." or rel.startswith("../"):
        raise StayPutError(
            "WORKTREE_UNRESOLVABLE",
            "git-dir is not inside common-dir",
        )
    return rel


def _normalize_fs_path(path: Path) -> str:
    text = str(path).replace("\\", "/").rstrip("/")
    return text


def _paths_equal(left: str, right: str) -> bool:
    if os.name == "nt":
        return left.casefold() == right.casefold()
    return left == right


def _run_bytes(
    cwd: Path,
    args: list[str],
    *,
    git_bin: str,
) -> subprocess.CompletedProcess[bytes]:
    cmd = [git_bin, *_REPLACE_OFF, *args]
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise StayPutError(
            "GIT_NOT_FOUND",
            f"git executable not found: {git_bin}",
        ) from exc
    except OSError as exc:
        raise StayPutError("GIT_FAILURE", f"git could not be executed: {exc}") from exc


def _decode_git_path(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StayPutError(
            "UNCANONICAL_PATH",
            "git emitted a path that is not valid UTF-8",
        ) from exc


def parse_name_status_z(data: bytes) -> list[str]:
    """Expand ``diff -z --name-status`` records into raw Git path strings."""
    if not data:
        return []
    tokens = data.split(b"\0")
    if tokens and tokens[-1] == b"":
        tokens.pop()
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            raise StayPutError("CANNOT_PROJECT_PATHS", "empty name-status token")
        kind = chr(status[0])
        if kind in {"R", "C"}:
            if index + 1 >= len(tokens):
                raise StayPutError(
                    "CANNOT_PROJECT_PATHS",
                    "rename/copy status is missing old or new path",
                )
            paths.append(_decode_git_path(tokens[index]))
            paths.append(_decode_git_path(tokens[index + 1]))
            index += 2
        else:
            if index >= len(tokens):
                raise StayPutError(
                    "CANNOT_PROJECT_PATHS",
                    "name-status record is missing a path",
                )
            paths.append(_decode_git_path(tokens[index]))
            index += 1
    return paths


def parse_ls_files_z(data: bytes) -> list[str]:
    if not data:
        return []
    tokens = data.split(b"\0")
    if tokens and tokens[-1] == b"":
        tokens.pop()
    return [_decode_git_path(token) for token in tokens if token]


def _require_path_listing(
    proc: subprocess.CompletedProcess[bytes],
    *,
    what: str,
) -> bytes:
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace")
        raise StayPutError(
            "CANNOT_PROJECT_PATHS",
            f"{what} failed ({proc.returncode}): {err.strip()}",
        )
    return proc.stdout


def name_status_paths(
    cwd: Path,
    extra: list[str],
    *,
    git_bin: str,
) -> list[str]:
    """``git diff -z --name-status -M`` plus extra args, from ``cwd``."""
    proc = _run_bytes(
        cwd,
        ["diff", "-z", "--name-status", "-M", *extra, "--"],
        git_bin=git_bin,
    )
    payload = _require_path_listing(
        proc,
        what="git diff -z --name-status -M",
    )
    return parse_name_status_z(payload)


def untracked_paths(cwd: Path, *, git_bin: str) -> list[str]:
    proc = _run_bytes(
        cwd,
        ["ls-files", "-z", "--others", "--exclude-standard", "--"],
        git_bin=git_bin,
    )
    payload = _require_path_listing(
        proc,
        what="git ls-files -z --others --exclude-standard",
    )
    return parse_ls_files_z(payload)


def changed_paths_since(
    cwd: Path,
    base_commit: str,
    *,
    git_bin: str,
) -> list[str]:
    """Union of committed, staged, unstaged, and untracked-not-ignored paths."""
    if not _HEX40.fullmatch(base_commit):
        raise StayPutError(
            "INVALID_BASE_COMMIT",
            "sealed base_commit must be a 40-character lowercase hex SHA",
        )
    collected: list[str] = []
    collected.extend(
        name_status_paths(cwd, [base_commit, "HEAD"], git_bin=git_bin)
    )
    collected.extend(name_status_paths(cwd, ["--cached"], git_bin=git_bin))
    collected.extend(name_status_paths(cwd, [], git_bin=git_bin))
    collected.extend(untracked_paths(cwd, git_bin=git_bin))
    return collected

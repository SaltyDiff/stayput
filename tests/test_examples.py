from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from tests.gitutil import commit_file, init_repo, write_file

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SRC = ROOT / "src"
HOOK_CONFIGS = (
    EXAMPLES / "claude-code" / "settings.json",
    EXAMPLES / "cursor" / "hooks.json",
    EXAMPLES / "openhands" / "hooks.json",
)
MACHINE_SUFFIXES = {".json", ".yml", ".yaml", ".sh"}
FORBIDDEN_IMPORTS = (
    "from factory",
    "import factory",
    "from saltmine",
    "import saltmine",
    "from arsenal",
    "import arsenal",
)


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    )
    return env


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "stayput", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=_cli_env(),
    )


def _stayput_shim_dir(tmp_path: Path) -> Path:
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    shim = shim_dir / "stayput"
    shim.write_text(
        "#!/bin/sh\n"
        f'export PYTHONPATH="{SRC}${{PYTHONPATH:+:$PYTHONPATH}}"\n'
        f'exec "{sys.executable}" -m stayput "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    return shim_dir


def _run_check_sh(
    *,
    cwd: Path,
    shim_dir: Path,
    extra_env: dict[str, str] | None = None,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = _cli_env()
    env["PATH"] = f"{shim_dir}{os.pathsep}{env.get('PATH', '')}"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["sh", str(EXAMPLES / "check.sh")],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
        input=stdin,
    )


def test_hook_json_parses_and_is_check_only() -> None:
    claude = json.loads(HOOK_CONFIGS[0].read_text(encoding="utf-8"))
    cursor = json.loads(HOOK_CONFIGS[1].read_text(encoding="utf-8"))
    openhands = json.loads(HOOK_CONFIGS[2].read_text(encoding="utf-8"))

    assert set(claude["hooks"]) == {"Stop"}
    assert claude["hooks"]["Stop"][0]["hooks"][0]["type"] == "command"
    assert "save" not in claude["hooks"]["Stop"][0]["hooks"][0]["command"]

    assert cursor["version"] == 1
    assert list(cursor["hooks"]) == ["stop"]
    assert "save" not in cursor["hooks"]["stop"][0]["command"]

    assert openhands["hooks"]["stop"][0]["matcher"] == "*"
    assert "save" not in openhands["hooks"]["stop"][0]["command"]


def test_check_sh_is_thin_check_wrapper() -> None:
    text = (EXAMPLES / "check.sh").read_text(encoding="utf-8")
    assert "exec stayput check --json" in text
    assert "stayput save" not in text
    assert "taskpin save" not in text
    assert "factory" not in text.lower()
    assert "saltmine" not in text.lower()


def test_machine_examples_never_invoke_save() -> None:
    for path in EXAMPLES.rglob("*"):
        if not path.is_file() or path.suffix not in MACHINE_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        assert "stayput save" not in text
        assert "taskpin save" not in text
        lower = text.lower()
        for needle in FORBIDDEN_IMPORTS:
            assert needle not in lower


def test_example_docs_do_not_depend_on_factory() -> None:
    for path in EXAMPLES.rglob("*"):
        if not path.is_file():
            continue
        lower = path.read_text(encoding="utf-8").lower()
        for needle in FORBIDDEN_IMPORTS:
            assert needle not in lower
        assert "saltmine" not in lower
        assert "factory qualification" not in lower


def test_ci_yaml_is_ordinary_cli_with_full_history() -> None:
    text = (EXAMPLES / "ci" / "github-actions-check.yml").read_text(encoding="utf-8")
    assert "fetch-depth: 0" in text
    assert "stayput check --json" in text
    assert "stayput save" not in text
    assert "taskpin save" not in text
    assert "uses: saltydiff/" not in text.lower()
    assert "docker://" not in text


def test_documented_cli_commands_work(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/a.py", "a\n", "first")
    inst = tmp_path / "PLAN.md"
    inst.write_bytes(b"do the work\n")

    project = _run_cli("project", "--cwd", str(repo), "--json", cwd=repo)
    assert project.returncode == 0
    assert json.loads(project.stdout)["ok"] is True

    saved = _run_cli(
        "save",
        "--cwd",
        str(repo),
        "--instruction-file",
        str(inst),
        "--allowed-path",
        "src",
        "--json",
        cwd=repo,
    )
    assert saved.returncode == 0

    checked = _run_cli(
        "check",
        "--cwd",
        str(repo),
        "--instruction-file",
        str(inst),
        "--json",
        cwd=repo,
    )
    assert checked.returncode == 0
    assert json.loads(checked.stdout)["status"] == "MATCH"


def test_check_sh_honors_match_error_mismatch(tmp_path: Path) -> None:
    shim_dir = _stayput_shim_dir(tmp_path)
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "src/a.py", "a\n", "first")

    missing = _run_check_sh(cwd=repo, shim_dir=shim_dir)
    assert missing.returncode == 1
    assert json.loads(missing.stdout)["ok"] is False

    saved = _run_cli(
        "save",
        "--cwd",
        str(repo),
        "--allowed-path",
        "src",
        "--json",
        cwd=repo,
    )
    assert saved.returncode == 0

    matched = _run_check_sh(cwd=repo, shim_dir=shim_dir)
    assert matched.returncode == 0
    assert json.loads(matched.stdout)["status"] == "MATCH"

    write_file(repo, "docs/out.md", "nope\n")
    mismatched = _run_check_sh(cwd=repo, shim_dir=shim_dir)
    assert mismatched.returncode == 2
    assert json.loads(mismatched.stdout)["status"] == "MISMATCH"


def test_check_sh_uses_stayput_cwd_and_discards_stdin(tmp_path: Path) -> None:
    shim_dir = _stayput_shim_dir(tmp_path)
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    saved = _run_cli("save", "--cwd", str(repo), "--json", cwd=repo)
    assert saved.returncode == 0

    other = tmp_path / "other"
    other.mkdir()
    proc = _run_check_sh(
        cwd=other,
        shim_dir=shim_dir,
        extra_env={"STAYPUT_CWD": str(repo)},
        stdin='{"branch":"agent-reported","worktree":"/tmp/lie"}\n',
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["status"] == "MATCH"


def test_examples_do_not_require_host_modules_in_core() -> None:
    names = {path.stem for path in (SRC / "stayput").glob("*.py")}
    assert names.isdisjoint({"claude", "cursor", "openhands", "hooks", "ci"})

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from stayput import CAPABILITY_VERSION, __version__
from tests.gitutil import commit_file, init_repo, write_file

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SRC = ROOT / "src"
CLAUDE_SETTINGS = EXAMPLES / "claude-code" / "settings.json"
CURSOR_HOOKS = EXAMPLES / "cursor" / "hooks.json"
OPENHANDS_HOOKS = EXAMPLES / "openhands" / "hooks.json"
CHECK_SH = EXAMPLES / "check.sh"
COPIED_HOOK_SCRIPTS = (
    EXAMPLES / "claude-code" / "stayput-check.sh",
    EXAMPLES / "cursor" / "stayput-check.sh",
    EXAMPLES / "openhands" / "stayput-check.sh",
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
OBSOLETE_CURSOR_WRAPPERS = ("stayput-stop.sh", "stayput-stop")


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
        ["sh", str(CHECK_SH)],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
        input=stdin,
    )


def test_claude_settings_are_project_stop_command() -> None:
    claude = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    assert set(claude["hooks"]) == {"Stop"}
    command = claude["hooks"]["Stop"][0]["hooks"][0]
    assert command["type"] == "command"
    assert command["command"] == ".claude/hooks/stayput-check.sh"
    assert "save" not in command["command"]


def test_cursor_hooks_use_native_stop_contract() -> None:
    cursor = json.loads(CURSOR_HOOKS.read_text(encoding="utf-8"))
    assert cursor["version"] == 1
    assert list(cursor["hooks"]) == ["stop"]
    command = cursor["hooks"]["stop"][0]["command"]
    assert command == ".cursor/hooks/stayput-check.sh"
    assert "save" not in command
    assert "followup_message" not in json.dumps(cursor)


def test_openhands_hooks_use_native_top_level_stop() -> None:
    openhands = json.loads(OPENHANDS_HOOKS.read_text(encoding="utf-8"))
    assert list(openhands) == ["stop"]
    matcher = openhands["stop"][0]
    assert matcher["matcher"] == "*"
    assert "command" not in matcher
    command = matcher["hooks"][0]["command"]
    assert command == ".openhands/hooks/stayput-check.sh"
    assert "save" not in command


def test_copied_hook_scripts_match_check_sh() -> None:
    canonical = CHECK_SH.read_bytes()
    assert b"exec stayput check --json" in canonical
    assert b"CLAUDE_PROJECT_DIR" in canonical
    assert b"OPENHANDS_PROJECT_DIR" in canonical
    for path in COPIED_HOOK_SCRIPTS:
        assert path.is_file()
        assert path.read_bytes() == canonical
        assert path.stat().st_mode & stat.S_IXUSR


def test_no_obsolete_cursor_stop_wrapper() -> None:
    found = [
        path
        for path in EXAMPLES.rglob("*")
        if path.is_file() and path.name in OBSOLETE_CURSOR_WRAPPERS
    ]
    assert found == []
    for path in EXAMPLES.rglob("*.sh"):
        text = path.read_text(encoding="utf-8")
        assert "followup_message" not in text
        assert "stayput-stop" not in text
        assert "exit 2" not in text or "exec stayput check --json" in text


def test_package_version_remains_0_1_0() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "stayput"' in pyproject
    assert 'version = "0.1.0"' in pyproject
    assert CAPABILITY_VERSION == "0.1.0"
    assert __version__ == "0.1.0"


def test_failure_docs_cover_v0_1_contract() -> None:
    text = (ROOT / "docs" / "failures.md").read_text(encoding="utf-8")
    for needle in (
        "REPOSITORY_MISMATCH",
        "WORKTREE_MISMATCH",
        "BASE_COMMIT_MISMATCH",
        "PATH_OUTSIDE_ALLOWLIST",
        "SHALLOW_REPOSITORY",
        "CANNOT_PROVE_ANCESTRY",
        '"ok": true',
        '"ok": false',
    ):
        assert needle in text
    lower = text.lower()
    assert "does not check branch names" in lower
    assert "mismatch" in lower
    assert "error" in lower


def test_check_sh_is_thin_check_wrapper() -> None:
    text = CHECK_SH.read_text(encoding="utf-8")
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
    assert "uses: actions/checkout@v4" in text
    assert "fetch-depth: 0" in text
    assert "pip install stayput" in text
    assert "stayput check --json" in text
    assert "stayput save" not in text
    assert "taskpin save" not in text
    assert "uses: saltydiff/" not in text.lower()
    assert "docker://" not in text
    assert '"ok": true' in text
    assert "Do not gate on JSON" in text
    assert "if " not in text
    assert ".ok" not in text
    assert "jq" not in text


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


def test_ci_readme_documents_shallow_fail_closed() -> None:
    text = (EXAMPLES / "ci" / "README.md").read_text(encoding="utf-8")
    assert "SHALLOW_REPOSITORY" in text
    assert "fetch-depth: 0" in text
    assert '"ok": true' in text
    assert "process exit code" in text.lower()


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


def test_check_sh_uses_host_project_dir_env(tmp_path: Path) -> None:
    shim_dir = _stayput_shim_dir(tmp_path)
    repo = init_repo(tmp_path / "repo")
    commit_file(repo, "a.txt", "a\n", "first")
    saved = _run_cli("save", "--cwd", str(repo), "--json", cwd=repo)
    assert saved.returncode == 0
    other = tmp_path / "other"
    other.mkdir()
    for key in ("CLAUDE_PROJECT_DIR", "OPENHANDS_PROJECT_DIR"):
        proc = _run_check_sh(
            cwd=other,
            shim_dir=shim_dir,
            extra_env={key: str(repo)},
        )
        assert proc.returncode == 0, key
        assert json.loads(proc.stdout)["status"] == "MATCH"


def test_examples_do_not_require_host_modules_in_core() -> None:
    names = {path.stem for path in (SRC / "stayput").glob("*.py")}
    assert names.isdisjoint({"claude", "cursor", "openhands", "hooks", "ci"})

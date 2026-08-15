"""Thin TaskPin CLI. All semantics stay in the library."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

from taskpin.check import check
from taskpin.errors import TaskPinError
from taskpin.instruction import digest_instruction
from taskpin.project import project_snapshot
from taskpin.save import save
from taskpin.schema import serialize_snapshot

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_MISMATCH = 2


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise TaskPinError("CLI_USAGE", message)


def _json_dump(payload: object) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _read_instruction_file(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise TaskPinError(
            "INSTRUCTION_UNREADABLE",
            f"instruction file cannot be read: {path}",
        ) from exc


def _instruction_bytes(path: Path | None) -> bytes | None:
    if path is None:
        return None
    return _read_instruction_file(path)


def _allowed_paths(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    return values


def _emit(text: str, *, stream: Any = sys.stdout) -> None:
    stream.write(text if text.endswith("\n") else f"{text}\n")


def _error_payload(exc: TaskPinError) -> dict[str, object]:
    details = dict(exc.details)
    details.setdefault("message", exc.message)
    return {"ok": False, "error": exc.code, "details": details}


def _render_error(exc: TaskPinError, *, json_mode: bool) -> int:
    if json_mode:
        _emit(_json_dump(_error_payload(exc)))
    else:
        _emit(f"ERROR: {exc.code}", stream=sys.stderr)
    return EXIT_ERROR


def _render_mismatch_line(item: dict[str, object]) -> str:
    cls = str(item.get("class", "MISMATCH"))
    delivered = item.get("delivered")
    if isinstance(delivered, str) and delivered:
        return f"{cls}: {delivered}"
    return cls


def _cmd_project(args: argparse.Namespace) -> int:
    raw = _instruction_bytes(args.instruction_file)
    digest = None if raw is None else digest_instruction(raw)
    snapshot = project_snapshot(
        args.cwd,
        instruction_digest=digest,
        allowed_paths=_allowed_paths(args.allowed_path),
    )
    if args.json:
        _emit(_json_dump({"ok": True, "snapshot": snapshot}))
    else:
        _emit(serialize_snapshot(snapshot))
    return EXIT_OK


def _cmd_save(args: argparse.Namespace) -> int:
    result = save(
        args.cwd,
        path=args.path,
        instruction_bytes=_instruction_bytes(args.instruction_file),
        allowed_paths=_allowed_paths(args.allowed_path),
        replace=args.replace,
    )
    if args.json:
        _emit(_json_dump(result))
    else:
        _emit("SAVED")
        _emit(str(result["path"]))
    return EXIT_OK


def _cmd_check(args: argparse.Namespace) -> int:
    result = check(
        args.cwd,
        path=args.path,
        instruction_bytes=_instruction_bytes(args.instruction_file),
    )
    if args.json:
        _emit(_json_dump(result))
    elif result["status"] == "MATCH":
        _emit("MATCH")
    else:
        _emit("MISMATCH")
        for item in result["mismatches"]:
            if isinstance(item, dict):
                _emit(_render_mismatch_line(item))
    if result["status"] == "MATCH":
        return EXIT_OK
    return EXIT_MISMATCH


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="taskpin")
    sub = parser.add_subparsers(dest="command", required=True)

    project = sub.add_parser("project", help="project the current six-field snapshot")
    project.add_argument("--cwd", type=Path)
    project.add_argument("--json", action="store_true")
    project.add_argument("--instruction-file", type=Path)
    project.add_argument("--allowed-path", action="append")
    project.set_defaults(func=_cmd_project)

    save_p = sub.add_parser("save", help="write an explicit approval artifact")
    save_p.add_argument("--cwd", type=Path)
    save_p.add_argument("--json", action="store_true")
    save_p.add_argument("--path", type=Path)
    save_p.add_argument("--instruction-file", type=Path)
    save_p.add_argument("--allowed-path", action="append")
    save_p.add_argument("--replace", action="store_true")
    save_p.set_defaults(func=_cmd_save)

    check_p = sub.add_parser("check", help="verify a sealed approval artifact")
    check_p.add_argument("--cwd", type=Path)
    check_p.add_argument("--json", action="store_true")
    check_p.add_argument("--path", type=Path)
    check_p.add_argument("--instruction-file", type=Path)
    check_p.set_defaults(func=_cmd_check)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in args_list
    try:
        parsed = _build_parser().parse_args(args_list)
        return int(parsed.func(parsed))
    except TaskPinError as exc:
        return _render_error(exc, json_mode=json_mode)

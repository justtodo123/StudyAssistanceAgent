#!/usr/bin/env python3
"""Run the closed M8 v3 S1 prerequisite oracle or historical replay.

The default command is a candidate-local Builder self-check. Historical replay
is an explicit, commit-bound, non-gating mode. Neither mode grants S1 or any
execution authority.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, NoReturn

TOOLS = Path(__file__).resolve().parent
if os.fspath(TOOLS) not in sys.path:
    sys.path.insert(0, os.fspath(TOOLS))

from m8_freeze_s1_prerequisites_v3 import (
    FreezeError,
    ORACLE_MANIFEST_PATH,
    canonical,
    derive_gating_closure,
    inspect_path_components,
    parse_oracle_manifest,
    validate_logical_path,
)
from m8_replay_historical_regressions_v3 import (
    FORMAT as HISTORICAL_FORMAT,
    PURPOSE as HISTORICAL_PURPOSE,
    run_bounded_process,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
GATING_SUCCESS_LINE = (
    "GATING PASS: M8 v3 S1 prerequisite closed oracle"
)
HISTORICAL_SUCCESS_LINE = (
    "HISTORICAL NON-GATING PASS: "
    "88/88 and 77/77 via isolated replay"
)
FULL_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_CONSOLE_LINE = 2400


class CheckFailure(AssertionError):
    """A deterministic, user-facing prerequisite failure."""


class ControlledArgumentParser(argparse.ArgumentParser):
    """Turn parser exits into controlled prerequisite failures."""

    def error(self, message: str) -> NoReturn:
        raise CheckFailure(message)


@dataclass(frozen=True)
class Check:
    name: str
    function: Callable[[], None]


@dataclass(frozen=True)
class SubprocessSpec:
    path: str
    success_oracle: dict[str, object]


@dataclass(frozen=True)
class OracleContext:
    """Validated manifest-derived authority for repository access."""

    root: Path
    manifest: dict[str, object]
    closure: tuple[str, ...]
    subprocess_specs: tuple[SubprocessSpec, ...]

    @classmethod
    def load(cls, root: Path) -> OracleContext:
        manifest_path = root.joinpath(*ORACLE_MANIFEST_PATH.split("/"))
        try:
            raw = manifest_path.read_bytes()
        except OSError as exc:
            raise CheckFailure(
                f"cannot read oracle manifest: {exc}"
            ) from exc
        try:
            manifest = parse_oracle_manifest(raw)
            closure = derive_gating_closure(manifest)
        except FreezeError as exc:
            raise CheckFailure(f"invalid oracle manifest: {exc}") from exc
        gating = _object(manifest.get("gating"), "gating")
        subprocesses = gating.get("allowed_subprocesses")
        if not isinstance(subprocesses, list):
            raise CheckFailure("gating.allowed_subprocesses is not a list")
        specs: list[SubprocessSpec] = []
        for raw_item in subprocesses:
            item = _object(raw_item, "allowed subprocess")
            path = item.get("path")
            oracle = item.get("success_oracle")
            if not isinstance(path, str):
                raise CheckFailure("allowed subprocess path is invalid")
            specs.append(
                SubprocessSpec(
                    path=path,
                    success_oracle=_object(
                        oracle,
                        "allowed subprocess success_oracle",
                    ),
                )
            )
        return cls(root, manifest, closure, tuple(specs))

    @property
    def allowed_subprocesses(self) -> frozenset[str]:
        return frozenset(spec.path for spec in self.subprocess_specs)

    def path(self, logical_path: str) -> Path:
        """Authorize one normalized closure member before touching it."""
        try:
            normalized = validate_logical_path(logical_path)
        except FreezeError as exc:
            raise CheckFailure(str(exc)) from exc
        if normalized not in self.closure:
            raise CheckFailure(
                "undeclared repository read refused: " + normalized
            )
        candidate = self.root.joinpath(*normalized.split("/"))
        try:
            return inspect_path_components(
                candidate,
                f"declared repository path {normalized}",
            )
        except FreezeError as exc:
            raise CheckFailure(str(exc)) from exc

    def read_bytes(self, logical_path: str) -> bytes:
        path = self.path(logical_path)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise CheckFailure(
                f"cannot read declared repository path {logical_path}: {exc}"
            ) from exc

    def read_text(self, logical_path: str) -> str:
        raw = self.read_bytes(logical_path)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CheckFailure(
                f"declared repository path is not UTF-8: {logical_path}"
            ) from exc

    def require_subprocess(self, logical_path: str) -> SubprocessSpec:
        """Return the exact manifest declaration for one gating child."""
        try:
            normalized = validate_logical_path(logical_path)
        except FreezeError as exc:
            raise CheckFailure(str(exc)) from exc
        for spec in self.subprocess_specs:
            if spec.path == normalized:
                self.path(normalized)
                return spec
        raise CheckFailure(
            "undeclared gating subprocess refused: " + normalized
        )

    def materialize_closure(self, destination: Path) -> Path:
        """Copy only declared closure bytes into a fresh external tree."""
        materialized = inspect_path_components(
            destination,
            "gating closure materialization root",
        )
        source_root = self.root.resolve()
        target_root = materialized.resolve()
        if target_root == source_root or source_root in target_root.parents:
            raise CheckFailure(
                "gating closure materialization must be repository-external"
            )
        if any(materialized.iterdir()):
            raise CheckFailure(
                "gating closure materialization root must be empty"
            )
        for logical_path in self.closure:
            target = materialized.joinpath(*logical_path.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.read_bytes(logical_path))
        return materialized


_CONTEXT: OracleContext | None = None


def _context() -> OracleContext:
    if _CONTEXT is None:
        raise CheckFailure("oracle context has not been initialized")
    return _CONTEXT


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise CheckFailure(f"{label} must be an object")
    return value


def _safe_console_line(text: object, *, limit: int = MAX_CONSOLE_LINE) -> None:
    """Write one bounded line without assuming console Unicode coverage."""
    rendered = str(text).replace("\r", "\\r").replace("\n", "\\n")
    if len(rendered) > limit:
        rendered = "..." + rendered[-limit:]
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe = rendered.encode(
        encoding,
        errors="backslashreplace",
    ).decode(encoding)
    sys.stdout.write(safe + "\n")


def _call_name(node: ast.AST) -> str | None:
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def _source_subprocess_paths() -> frozenset[str]:
    """Return closure members allowed to contain process-control source."""
    context = _context()
    gating = _object(context.manifest["gating"], "gating")
    support = gating.get("support_modules")
    if not isinstance(support, list):
        raise CheckFailure("gating.support_modules is not a list")
    special_support = {
        "tools/m8_freeze_minimal_1k_v3_review.py",
        "tools/m8_freeze_s1_prerequisites_v3.py",
        "tools/m8_replay_historical_regressions_v3.py",
    }
    if not special_support.issubset(set(support)):
        raise CheckFailure(
            "manifest omits a process-control support module"
        )
    return frozenset(
        {
            str(gating["entrypoint"]),
            *context.allowed_subprocesses,
            *special_support,
        }
    )


def _enclosing_symbol_names(
    tree: ast.AST,
) -> dict[ast.AST, tuple[str, ...]]:
    """Map each AST node to its lexical function or method path."""
    names: dict[ast.AST, tuple[str, ...]] = {}

    def visit(node: ast.AST, enclosing: tuple[str, ...]) -> None:
        names[node] = enclosing
        next_enclosing = enclosing
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            next_enclosing = (*enclosing, node.name)
        elif isinstance(node, ast.ClassDef):
            next_enclosing = (*enclosing, node.name)
        for child in ast.iter_child_nodes(node):
            visit(child, next_enclosing)

    visit(tree, ())
    return names


def _list_call_parts(argument: ast.AST) -> tuple[ast.AST, ...] | None:
    """Return an explicit argv literal for destination validation."""
    if not isinstance(argument, (ast.List, ast.Tuple)):
        return None
    return tuple(argument.elts)


def _literal_string(node: ast.AST, expected: str | None = None) -> bool:
    """Return whether a node is a literal string, optionally exact."""
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        return False
    return expected is None or node.value == expected


def _call_of(node: ast.AST, name: str, argument: str | None = None) -> bool:
    """Recognize one simple call used in a destination expression."""
    if not isinstance(node, ast.Call) or _call_name(node.func) != name:
        return False
    if len(node.args) != 1 or node.keywords:
        return False
    return argument is None or (
        isinstance(node.args[0], ast.Name) and node.args[0].id == argument
    )


def _is_sys_executable(node: ast.AST) -> bool:
    return _call_name(node) == "sys.executable"


def _is_str_name(node: ast.AST, name: str) -> bool:
    return _call_of(node, "str", name)


def _is_exact_taskkill(parts: tuple[ast.AST, ...]) -> bool:
    """Recognize the fixed Windows process-tree cleanup argv."""
    return (
        len(parts) == 5
        and _is_str_name(parts[0], "taskkill")
        and _literal_string(parts[1], "/PID")
        and isinstance(parts[2], ast.Call)
        and _call_name(parts[2].func) == "str"
        and len(parts[2].args) == 1
        and not parts[2].keywords
        and _call_name(parts[2].args[0]) in {"pid", "process.pid"}
        and _literal_string(parts[3], "/T")
        and _literal_string(parts[4], "/F")
    )


def _is_exact_mklink(parts: tuple[ast.AST, ...]) -> bool:
    """Recognize only the test-only Windows junction command family."""
    return (
        len(parts) == 7
        and _literal_string(parts[0], "cmd.exe")
        and all(
            _literal_string(parts[index], value)
            for index, value in enumerate(
                ("/d", "/c", "mklink", "/J"),
                start=1,
            )
        )
        and all(
            isinstance(part, ast.Call)
            and _call_name(part.func) == "str"
            and len(part.args) == 1
            and not part.keywords
            for part in parts[5:]
        )
    )


def _module_assignment_values(
    tree: ast.Module,
    name: str,
) -> tuple[ast.AST, ...]:
    """Return values assigned directly to one module-level name."""
    values: list[ast.AST] = []
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in statement.targets
            ):
                values.append(statement.value)
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == name
            and statement.value is not None
        ):
            values.append(statement.value)
    return tuple(values)


def _is_script_constant(node: ast.AST, filename: str) -> bool:
    """Recognize Path(__file__).with_name(<fixed filename>)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "with_name"
        and isinstance(node.func.value, ast.Call)
        and _call_name(node.func.value.func) == "Path"
        and len(node.func.value.args) == 1
        and not node.func.value.keywords
        and isinstance(node.func.value.args[0], ast.Name)
        and node.func.value.args[0].id == "__file__"
        and len(node.args) == 1
        and not node.keywords
        and _literal_string(node.args[0], filename)
    )


def _is_graph_generator_constant(node: ast.AST) -> bool:
    """Recognize ROOT / the fixed tools fixture-generator path."""
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and _literal_string(
            node.right,
            "tools/m8_generate_minimal_1k_v3_fixtures.py",
        )
        and isinstance(node.left, ast.Name)
        and node.left.id == "ROOT"
    )


def _validate_process_path_constants(
    logical_path: str,
    tree: ast.Module,
) -> None:
    """Bind path constants referenced by subprocess argv expressions."""
    referenced_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) not in {
            "subprocess.Popen",
            "subprocess.run",
        }:
            continue
        if not node.args:
            continue
        for candidate in ast.walk(node.args[0]):
            if (
                isinstance(candidate, ast.Call)
                and _call_name(candidate.func) == "str"
                and len(candidate.args) == 1
                and not candidate.keywords
                and isinstance(candidate.args[0], ast.Name)
            ):
                referenced_names.add(candidate.args[0].id)

    expected_scripts = {
        "tools/m8_test_freeze_minimal_1k_v3_review.py": (
            "m8_freeze_minimal_1k_v3_review.py"
        ),
        "tools/m8_test_freeze_s1_prerequisites_v3.py": (
            "m8_freeze_s1_prerequisites_v3.py"
        ),
        "tools/m8_test_replay_historical_regressions_v3.py": (
            "m8_replay_historical_regressions_v3.py"
        ),
    }
    expected_script = expected_scripts.get(logical_path)
    if expected_script is not None and "SCRIPT" in referenced_names:
        values = _module_assignment_values(tree, "SCRIPT")
        if len(values) != 1 or not _is_script_constant(
            values[0],
            expected_script,
        ):
            raise CheckFailure(
                f"{logical_path}: SCRIPT subprocess destination is not bound"
            )

    if (
        logical_path == "tools/m8_test_minimal_1k_graph_v3.py"
        and "GENERATOR" in referenced_names
    ):
        values = _module_assignment_values(tree, "GENERATOR")
        if len(values) != 1 or not _is_graph_generator_constant(values[0]):
            raise CheckFailure(
                f"{logical_path}: GENERATOR subprocess destination is not bound"
            )


def _validate_subprocess_destination(
    logical_path: str,
    node: ast.Call,
    enclosing: tuple[str, ...],
) -> None:
    """Bind each process launch to a narrow source-specific family."""
    if len(node.args) != 1:
        raise CheckFailure(
            f"{logical_path}:{node.lineno}: subprocess argv must be explicit"
        )
    argument = node.args[0]
    function = enclosing[-1] if enclosing else ""

    hardened_git_helpers = {
        "tools/m8_freeze_minimal_1k_v3_review.py": {"run_git_process"},
        "tools/m8_freeze_s1_prerequisites_v3.py": {"run_git_process"},
    }
    if (
        function in hardened_git_helpers.get(logical_path, set())
        and isinstance(argument, ast.Name)
        and argument.id == "command"
    ):
        return

    if logical_path == "tools/m8_replay_historical_regressions_v3.py":
        if (
            function == "run_bounded_process"
            and isinstance(argument, ast.Name)
            and argument.id == "command"
        ):
            return

    parts = _list_call_parts(argument)
    if parts is None:
        raise CheckFailure(
            f"{logical_path}:{node.lineno}: subprocess destination is not bound"
        )
    starred = tuple(item for item in parts if isinstance(item, ast.Starred))

    if function in {"terminate_process_tree", "_terminate_process_tree"}:
        if not starred and _is_exact_taskkill(parts):
            return
        raise CheckFailure(
            f"{logical_path}:{node.lineno}: taskkill destination is not bound"
        )

    git_test_sources = {
        "tools/m8_test_freeze_minimal_1k_v3_review.py",
        "tools/m8_test_freeze_s1_prerequisites_v3.py",
        "tools/m8_test_replay_historical_regressions_v3.py",
    }
    if logical_path in git_test_sources and function in {
        "run_git",
        "explicit_git",
    }:
        if (
            parts
            and _is_str_name(parts[0], "executable")
            and len(starred) == 1
            and isinstance(starred[0].value, ast.Name)
            and starred[0].value.id == "args"
        ):
            return

    if (
        logical_path in {
            "tools/m8_test_freeze_minimal_1k_v3_review.py",
            "tools/m8_test_freeze_s1_prerequisites_v3.py",
        }
        and function == "clone_replay_tests"
        and not starred
        and len(parts) == 9
        and _is_str_name(parts[0], "executable")
        and all(
            _literal_string(part, literal)
            for part, literal in zip(
                parts[1:7],
                (
                    "--no-replace-objects",
                    "--no-lazy-fetch",
                    "clone",
                    "--no-local",
                    "--no-hardlinks",
                    "--no-checkout",
                ),
            )
        )
        and _is_str_name(parts[7], "repo")
        and _is_str_name(parts[8], "clone")
    ):
        return

    freeze_script = {
        "tools/m8_test_freeze_minimal_1k_v3_review.py": (
            "tools/m8_freeze_minimal_1k_v3_review.py"
        ),
        "tools/m8_test_freeze_s1_prerequisites_v3.py": (
            "tools/m8_freeze_s1_prerequisites_v3.py"
        ),
    }
    if logical_path in freeze_script and parts:
        cli_starred_args = (
            function == "cli"
            and len(starred) == 1
            and isinstance(starred[0].value, ast.Name)
            and starred[0].value.id == "args"
        )
        if (
            (not starred or cli_starred_args)
            and len(parts) >= 2
            and _is_sys_executable(parts[0])
            and _is_str_name(parts[1], "SCRIPT")
        ):
            return

    if logical_path == "tools/m8_test_s1_prerequisites_v3.py":
        if (
            not starred
            and function == "_run_declared_tool"
            and len(parts) == 4
            and _is_sys_executable(parts[0])
            and _literal_string(parts[1], "-I")
            and _literal_string(parts[2], "-c")
            and isinstance(parts[3], ast.Name)
            and parts[3].id == "launcher"
        ):
            return

    if logical_path == "tools/m8_test_minimal_1k_graph_v3.py":
        if (
            not starred
            and function == "run"
            and len(parts) == 3
            and _is_sys_executable(parts[0])
            and _is_str_name(parts[1], "validator")
            and _is_str_name(parts[2], "path")
        ):
            return
        if (
            not starred
            and len(parts) >= 2
            and _is_sys_executable(parts[0])
            and _is_str_name(parts[1], "GENERATOR")
        ):
            return
        if not starred and _is_exact_mklink(parts):
            return

    if logical_path == "tools/m8_test_observe_minimal_1k_v3.py":
        if (
            not starred
            and function == "test_publication_rejects_junction_in_evidence_ancestor"
            and _is_exact_mklink(parts)
        ):
            return

    if logical_path == "tools/m8_test_replay_historical_regressions_v3.py":
        if (
            not starred
            and function == "test_descendant_pipe_cleanup"
            and len(parts) == 3
            and _is_sys_executable(parts[0])
            and _literal_string(parts[1], "-I")
            and _is_str_name(parts[2], "child")
        ):
            return
        if (
            not starred
            and len(parts) >= 2
            and _is_sys_executable(parts[0])
            and _is_str_name(parts[1], "SCRIPT")
        ):
            return

    raise CheckFailure(
        f"{logical_path}:{node.lineno}: subprocess destination is not bound"
    )


def _validate_execution_policy(logical_path: str, source: str) -> None:
    """Reject network/install APIs and ambiguous process invocation."""
    try:
        tree = ast.parse(source, filename=logical_path)
    except SyntaxError as exc:
        raise CheckFailure(
            f"{logical_path}: invalid Python: {exc}"
        ) from exc
    forbidden_modules = {
        "httpx",
        "pip",
        "requests",
        "socket",
        "urllib",
        "venv",
    }
    process_source_allowed = logical_path in _source_subprocess_paths()
    subprocess_aliases: set[str] = set()
    enclosing_names = _enclosing_symbol_names(tree)
    _validate_process_path_constants(logical_path, tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in forbidden_modules:
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: "
                        f"forbidden import {root}"
                    )
                if root == "subprocess":
                    if alias.asname:
                        raise CheckFailure(
                            f"{logical_path}:{node.lineno}: "
                            "aliased subprocess imports are forbidden"
                        )
                    if not process_source_allowed:
                        raise CheckFailure(
                            f"{logical_path}:{node.lineno}: "
                            "subprocess source role is undeclared"
                        )
                    subprocess_aliases.add("subprocess")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in forbidden_modules:
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: "
                    f"forbidden import {root}"
                )
            if root == "subprocess":
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: "
                    "from-subprocess imports are forbidden"
                )
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            if node.value is None:
                continue
            call_name = _call_name(node.value)
            if call_name in {
                "subprocess.Popen",
                "subprocess.run",
            }:
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: "
                    "subprocess callable aliases are forbidden"
                )
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name in {
                "__import__",
                "breakpoint",
                "eval",
                "exec",
            }:
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: "
                    f"forbidden dynamic call {call_name}()"
                )
            if call_name == "importlib.import_module":
                if any(
                    isinstance(argument, ast.Constant)
                    and argument.value == "subprocess"
                    for argument in node.args
                ):
                    raise CheckFailure(
                        f"{logical_path}:{node.lineno}: "
                        "dynamic subprocess imports are forbidden"
                    )
            if call_name == "getattr" and node.args:
                if _call_name(node.args[0]) in subprocess_aliases:
                    attribute = (
                        node.args[1].value
                        if len(node.args) > 1
                        and isinstance(node.args[1], ast.Constant)
                        and isinstance(node.args[1].value, str)
                        else None
                    )
                    if attribute in {"Popen", "run"} or attribute is None:
                        raise CheckFailure(
                            f"{logical_path}:{node.lineno}: "
                            "indirect subprocess invocation is forbidden"
                        )
            if call_name not in {
                "subprocess.Popen",
                "subprocess.run",
            }:
                continue
            if not process_source_allowed:
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: "
                    "subprocess call is not allowed for this source role"
                )
            keywords = {
                keyword.arg: keyword.value
                for keyword in node.keywords
                if keyword.arg
            }
            if any(keyword.arg is None for keyword in node.keywords):
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: "
                    "expanded subprocess keywords are forbidden"
                )
            shell = keywords.get("shell")
            if shell is not None and not (
                isinstance(shell, ast.Constant)
                and shell.value is False
            ):
                raise CheckFailure(
                    f"{logical_path}:{node.lineno}: "
                    "shell must be omitted or literal False"
                )
            _validate_subprocess_destination(
                logical_path,
                node,
                enclosing_names[node],
            )


def _child_environment(temp_root: Path) -> dict[str, str]:
    """Build a bounded environment without inherited Python/Git controls."""
    env: dict[str, str] = {
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPYCACHEPREFIX": str(temp_root / "pycache"),
        "PYTHONUTF8": "1",
        "TEMP": str(temp_root),
        "TMP": str(temp_root),
        "TMPDIR": str(temp_root),
    }
    for name in (
        "COMSPEC",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
    ):
        value = os.environ.get(name)
        if value:
            env[name] = value
    if os.name != "nt":
        env["LANG"] = "C.UTF-8"
        env["LC_ALL"] = "C.UTF-8"
    return env


def _validate_subprocess_output(
    spec: SubprocessSpec,
    stdout: bytes,
    stderr: bytes,
) -> None:
    """Require the manifest-declared success facts exactly once."""
    try:
        combined = (stdout + b"\n" + stderr).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CheckFailure(
            f"{spec.path} emitted non-UTF-8 output"
        ) from exc
    lines = combined.splitlines()
    oracle = spec.success_oracle
    kind = oracle.get("kind")
    success_line = oracle.get("success_line")
    if not isinstance(success_line, str):
        raise CheckFailure(f"{spec.path}: invalid success oracle")
    if lines.count(success_line) != 1:
        raise CheckFailure(
            f"{spec.path}: expected exactly one {success_line!r} line"
        )
    if kind == "exact-line":
        return
    if kind != "unittest":
        raise CheckFailure(
            f"{spec.path}: unsupported success oracle {kind!r}"
        )
    expected = oracle.get("expected_test_count")
    summaries = [
        match
        for line in lines
        if (
            match := re.fullmatch(
                r"Ran (0|[1-9][0-9]*) tests in .+",
                line,
            )
        )
    ]
    if len(summaries) != 1:
        raise CheckFailure(
            f"{spec.path}: expected exactly one unittest summary"
        )
    observed = int(summaries[0].group(1))
    if observed != expected:
        raise CheckFailure(
            f"{spec.path}: expected {expected} tests, observed {observed}"
        )


def check_subprocess_output_regressions() -> None:
    """Prove output oracles reject false and ambiguous success."""
    exact = SubprocessSpec(
        path="tools/exact.py",
        success_oracle={
            "kind": "exact-line",
            "success_line": "EXACT PASS",
        },
    )
    unittest = SubprocessSpec(
        path="tools/unittest.py",
        success_oracle={
            "expected_test_count": 2,
            "kind": "unittest",
            "success_line": "OK",
        },
    )
    accepted = (
        (exact, b"EXACT PASS\n", b""),
        (unittest, b"", b"Ran 2 tests in 0.001s\n\nOK\n"),
    )
    for spec, stdout, stderr in accepted:
        _validate_subprocess_output(spec, stdout, stderr)
    rejected = (
        (exact, b"", b"", "expected exactly one"),
        (
            exact,
            b"EXACT PASS\nEXACT PASS\n",
            b"",
            "expected exactly one",
        ),
        (unittest, b"", b"Ran 0 tests in 0.001s\nOK\n", "observed 0"),
        (unittest, b"", b"Ran 3 tests in 0.001s\nOK\n", "observed 3"),
        (unittest, b"", b"Ran 2 tests in 0.001s\n", "exactly one 'OK'"),
        (
            unittest,
            b"",
            b"Ran 2 tests in 0.001s\nRan 2 tests in 0.002s\nOK\n",
            "exactly one unittest summary",
        ),
        (unittest, b"", b"Ran 2 tests in 0.001s\nOK\nOK\n", "exactly one 'OK'"),
    )
    for spec, stdout, stderr, expected in rejected:
        try:
            _validate_subprocess_output(spec, stdout, stderr)
        except CheckFailure as exc:
            if expected not in str(exc):
                raise CheckFailure(
                    "subprocess-output regression failed incorrectly: "
                    + str(exc)
                ) from exc
        else:
            raise CheckFailure(
                "invalid subprocess success output was accepted"
            )
    try:
        _validate_subprocess_output(unittest, b"\xff", b"")
    except CheckFailure as exc:
        if "non-UTF-8 output" not in str(exc):
            raise CheckFailure(
                "non-UTF-8 output regression failed incorrectly: "
                + str(exc)
            ) from exc
    else:
        raise CheckFailure("non-UTF-8 subprocess output was accepted")


def _verify_materialized_closure(
    context: OracleContext,
    materialized_root: Path,
) -> None:
    """Require the external tree to contain unchanged closure bytes only."""
    observed = tuple(
        sorted(
            (
                path.relative_to(materialized_root).as_posix()
                for path in materialized_root.rglob("*")
                if path.is_file()
            ),
            key=lambda item: item.encode("utf-8"),
        )
    )
    if observed != context.closure:
        missing = tuple(path for path in context.closure if path not in observed)
        added = tuple(path for path in observed if path not in context.closure)
        raise CheckFailure(
            "materialized gating closure inventory changed: "
            f"missing={missing!r}, added={added!r}"
        )
    for logical_path in context.closure:
        copied = materialized_root.joinpath(*logical_path.split("/"))
        copied_bytes = copied.read_bytes()
        source_bytes = context.read_bytes(logical_path)
        if copied_bytes != source_bytes:
            differing_offset = next(
                (
                    index
                    for index, (copied_byte, source_byte) in enumerate(
                        zip(copied_bytes, source_bytes)
                    )
                    if copied_byte != source_byte
                ),
                min(len(copied_bytes), len(source_bytes)),
            )
            raise CheckFailure(
                "materialized gating closure bytes changed: "
                f"{logical_path}; copied_bytes={len(copied_bytes)}, "
                f"source_bytes={len(source_bytes)}, "
                f"first_difference={differing_offset}"
            )


def check_materialized_closure_regressions() -> None:
    """Prove external materialization excludes undeclared source bytes."""
    with tempfile.TemporaryDirectory(
        prefix="m8-s1-materialization-regression-"
    ) as directory:
        temp_root = Path(directory)
        source_root = temp_root / "source"
        source_root.mkdir()
        (source_root / "declared.txt").write_bytes(b"declared\n")
        (source_root / "undeclared.txt").write_bytes(b"ambient\n")
        context = OracleContext(
            root=source_root,
            manifest={},
            closure=("declared.txt",),
            subprocess_specs=(),
        )
        materialized_root = temp_root / "materialized"
        materialized_root.mkdir()
        context.materialize_closure(materialized_root)
        _verify_materialized_closure(context, materialized_root)
        if (materialized_root / "undeclared.txt").exists():
            raise CheckFailure(
                "undeclared source bytes entered materialized closure"
            )
        (materialized_root / "extra.txt").write_bytes(b"extra\n")
        try:
            _verify_materialized_closure(context, materialized_root)
        except CheckFailure as exc:
            if "inventory changed" not in str(exc):
                raise CheckFailure(
                    "extra-file regression failed incorrectly: " + str(exc)
                ) from exc
        else:
            raise CheckFailure(
                "extra materialized closure file was accepted"
            )
        (materialized_root / "extra.txt").unlink()
        (materialized_root / "declared.txt").write_bytes(b"changed\n")
        try:
            _verify_materialized_closure(context, materialized_root)
        except CheckFailure as exc:
            if "bytes changed" not in str(exc):
                raise CheckFailure(
                    "changed-byte regression failed incorrectly: " + str(exc)
                ) from exc
        else:
            raise CheckFailure(
                "changed materialized closure bytes were accepted"
            )


def _run_declared_tool(
    spec: SubprocessSpec,
    materialized_root: Path,
    temp_root: Path,
) -> None:
    """Run one declared test only from the external closure tree."""
    declared = _context().require_subprocess(spec.path)
    if declared != spec:
        raise CheckFailure(
            f"subprocess declaration changed for {spec.path}"
        )
    tool = inspect_path_components(
        materialized_root.joinpath(*spec.path.split("/")),
        f"materialized gating subprocess {spec.path}",
    )
    materialized_tools = inspect_path_components(
        materialized_root / "tools",
        "materialized gating tools directory",
    )
    cwd = temp_root / "unrelated-cwd"
    cwd.mkdir(exist_ok=True)
    child_temp_root = temp_root / "child-runtime"
    child_temp_root.mkdir(exist_ok=True)
    pycache_root = child_temp_root / "pycache"
    launcher = (
        "import runpy,sys;"
        f"sys.pycache_prefix={os.fspath(pycache_root)!r};"
        f"sys.path.insert(0,{os.fspath(materialized_tools)!r});"
        f"runpy.run_path({os.fspath(tool)!r},run_name='__main__')"
    )
    return_code, stdout, stderr = run_bounded_process(
        [sys.executable, "-I", "-c", launcher],
        cwd,
        allowed_isolated_code=launcher,
        environment=_child_environment(child_temp_root),
        timeout_seconds=600,
    )
    if return_code != 0:
        combined = (stdout + b"\n" + stderr).decode(
            "utf-8",
            errors="replace",
        )
        raise CheckFailure(
            f"{spec.path} exited {return_code}: {combined[-2000:]}"
        )
    _validate_subprocess_output(spec, stdout, stderr)


def check_repository_contract() -> None:
    """Require every mechanically derived closure member to be readable."""
    context = _context()
    if not context.closure:
        raise CheckFailure("manifest-derived gating closure is empty")
    if tuple(sorted(
        context.closure,
        key=lambda item: item.encode("utf-8"),
    )) != context.closure:
        raise CheckFailure("gating closure is not UTF-8-byte sorted")
    if len(context.closure) != len(set(context.closure)):
        raise CheckFailure("gating closure contains duplicate paths")
    for logical_path in context.closure:
        context.read_bytes(logical_path)


def check_s1_tool_syntax() -> None:
    """Compile every Python member without writing repository bytecode."""
    for logical_path in _context().closure:
        if not logical_path.endswith(".py"):
            continue
        source = _context().read_text(logical_path)
        try:
            compile(source, logical_path, "exec")
        except SyntaxError as exc:
            raise CheckFailure(
                f"syntax error in {logical_path}: {exc}"
            ) from exc


def check_execution_policy() -> None:
    """Scan all closure-bound Python source under manifest-aware roles."""
    python_paths = tuple(
        path
        for path in _context().closure
        if path.endswith(".py")
    )
    if not python_paths:
        raise CheckFailure("gating closure contains no Python source")
    for logical_path in python_paths:
        _validate_execution_policy(
            logical_path,
            _context().read_text(logical_path),
        )


def check_execution_policy_regressions() -> None:
    """Prove process-source and destination bypasses fail closed."""
    graph_path = "tools/m8_test_minimal_1k_graph_v3.py"
    freeze_test_path = "tools/m8_test_freeze_s1_prerequisites_v3.py"
    rejected = (
        (
            graph_path,
            "import subprocess as sp\nsp.run(['tool'])\n",
            "aliased subprocess imports are forbidden",
        ),
        (
            graph_path,
            "from subprocess import run\nrun(['tool'])\n",
            "from-subprocess imports are forbidden",
        ),
        (
            graph_path,
            "import subprocess\nrunner = subprocess.run\nrunner(['tool'])\n",
            "subprocess callable aliases are forbidden",
        ),
        (
            graph_path,
            "import subprocess\ngetattr(subprocess, 'run')(['tool'])\n",
            "indirect subprocess invocation is forbidden",
        ),
        (
            graph_path,
            "import importlib\nimportlib.import_module('subprocess').run(['tool'])\n",
            "dynamic subprocess imports are forbidden",
        ),
        (
            graph_path,
            "import subprocess\nenabled = True\n"
            "subprocess.run(['tool'], shell=enabled)\n",
            "shell must be omitted or literal False",
        ),
        (
            graph_path,
            "import subprocess\noptions = {'shell': False}\n"
            "subprocess.run(['tool'], **options)\n",
            "expanded subprocess keywords are forbidden",
        ),
        (
            graph_path,
            "import subprocess\nsubprocess.run(['tool'], shell=False)\n",
            "subprocess destination is not bound",
        ),
        (
            graph_path,
            "import subprocess, sys\n"
            "subprocess.run([sys.executable, 'other.py'])\n",
            "subprocess destination is not bound",
        ),
        (
            graph_path,
            "import subprocess\n"
            "subprocess.run(['cmd.exe', '/d', '/c', 'del', 'x'])\n",
            "subprocess destination is not bound",
        ),
        (
            graph_path,
            "import subprocess\ncommand = ['tool']\n"
            "subprocess.run(command)\n",
            "subprocess destination is not bound",
        ),
        (
            graph_path,
            "import subprocess, sys\nfrom pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[1]\n"
            "GENERATOR = ROOT / 'tools' / "
            "'m8_generate_minimal_1k_v3_fixtures.py'\n"
            "extra = ['--escape']\n"
            "subprocess.run([sys.executable, str(GENERATOR), *extra])\n",
            "subprocess destination is not bound",
        ),
        (
            freeze_test_path,
            "import subprocess, sys\nfrom pathlib import Path\n"
            "SCRIPT = Path('other.py')\n"
            "subprocess.run([sys.executable, str(SCRIPT)])\n",
            "SCRIPT subprocess destination is not bound",
        ),
        (
            graph_path,
            "import subprocess\n"
            "from pathlib import Path\n"
            "def _terminate_process_tree(process):\n"
            "    taskkill = Path('other.exe')\n"
            "    subprocess.run([str(taskkill), '/PID', "
            "str(process.pid), '/F'])\n",
            "taskkill destination is not bound",
        ),
    )
    for logical_path, source, expected in rejected:
        try:
            _validate_execution_policy(logical_path, source)
        except CheckFailure as exc:
            if expected not in str(exc):
                raise CheckFailure(
                    "execution-policy regression failed incorrectly: "
                    + str(exc)
                ) from exc
        else:
            raise CheckFailure(
                "execution-policy bypass was accepted: " + expected
            )

    _validate_execution_policy(
        graph_path,
        "import subprocess, sys\n"
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "GENERATOR = ROOT / "
        "'tools/m8_generate_minimal_1k_v3_fixtures.py'\n"
        "subprocess.run([sys.executable, str(GENERATOR), "
        "'--output-root', 'fixture'])\n",
    )
    _validate_execution_policy(
        graph_path,
        "import subprocess\n"
        "from pathlib import Path\n"
        "def test_link(parent, external):\n"
        "    subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', "
        "str(parent), str(external)])\n",
    )
    try:
        _validate_execution_policy(
            "tools/m8_generate_minimal_1k_v3_fixtures.py",
            "import subprocess\nsubprocess.run(['tool'])\n",
        )
    except CheckFailure as exc:
        if "subprocess source role is undeclared" not in str(exc):
            raise CheckFailure(
                "source-role regression failed incorrectly: " + str(exc)
            ) from exc
    else:
        raise CheckFailure("undeclared process-control source was accepted")


def check_oracle_enforcement_regressions() -> None:
    """Prove undeclared reads/processes fail before filesystem access."""
    missing = "definitely-not-declared/does-not-exist.txt"
    try:
        _context().read_bytes(missing)
    except CheckFailure as exc:
        if "undeclared repository read refused" not in str(exc):
            raise CheckFailure(
                f"undeclared-read regression failed incorrectly: {exc}"
            ) from exc
    else:
        raise CheckFailure("undeclared repository read was accepted")
    try:
        _context().require_subprocess(
            "tools/m8_replay_historical_regressions_v3.py"
        )
    except CheckFailure as exc:
        if "undeclared gating subprocess refused" not in str(exc):
            raise CheckFailure(
                f"historical-dispatch regression failed incorrectly: {exc}"
            ) from exc
    else:
        raise CheckFailure(
            "default gating can dispatch the historical replay helper"
        )
    try:
        _context().require_subprocess(
            "tools/definitely-not-declared.py"
        )
    except CheckFailure as exc:
        if "undeclared gating subprocess refused" not in str(exc):
            raise CheckFailure(
                f"undeclared-process regression failed incorrectly: {exc}"
            ) from exc
    else:
        raise CheckFailure("undeclared gating subprocess was accepted")


def _validate_dispatch_sequence(
    declared: tuple[SubprocessSpec, ...],
    observed: tuple[str, ...],
) -> None:
    """Require one successful dispatch in exact manifest order per child."""
    expected = tuple(spec.path for spec in declared)
    if observed != expected:
        raise CheckFailure(
            "gating child dispatch sequence differs from manifest"
        )


def check_dispatch_sequence_regressions() -> None:
    """Prove missing, duplicate, reordered, or extra dispatches fail."""
    declared = (
        SubprocessSpec("tools/a.py", {}),
        SubprocessSpec("tools/b.py", {}),
    )
    _validate_dispatch_sequence(
        declared,
        ("tools/a.py", "tools/b.py"),
    )
    rejected = (
        ("tools/a.py",),
        ("tools/a.py", "tools/a.py", "tools/b.py"),
        ("tools/b.py", "tools/a.py"),
        ("tools/a.py", "tools/b.py", "tools/c.py"),
    )
    for observed in rejected:
        try:
            _validate_dispatch_sequence(declared, observed)
        except CheckFailure as exc:
            if "differs from manifest" not in str(exc):
                raise CheckFailure(
                    "dispatch-sequence regression failed incorrectly: "
                    + str(exc)
                ) from exc
        else:
            raise CheckFailure(
                "invalid gating child dispatch sequence was accepted"
            )


def check_declared_child_suites() -> None:
    """Run every manifest-declared child exactly once from one closed tree."""
    context = _context()
    if len(context.subprocess_specs) != len(
        {spec.path for spec in context.subprocess_specs}
    ):
        raise CheckFailure("manifest declares duplicate gating subprocesses")
    completed: list[str] = []
    with tempfile.TemporaryDirectory(
        prefix="m8-s1-gating-"
    ) as directory:
        temp_root = inspect_path_components(
            Path(directory),
            "gating temporary directory",
        )
        materialized_root = temp_root / "closure"
        materialized_root.mkdir()
        context.materialize_closure(materialized_root)
        _verify_materialized_closure(context, materialized_root)
        for spec in context.subprocess_specs:
            _verify_materialized_closure(context, materialized_root)
            _run_declared_tool(spec, materialized_root, temp_root)
            completed.append(spec.path)
            _verify_materialized_closure(context, materialized_root)
    _validate_dispatch_sequence(
        context.subprocess_specs,
        tuple(completed),
    )


def gating_checks() -> Iterable[Check]:
    return (
        Check("manifest-derived repository contract", check_repository_contract),
        Check("closure-bound Python syntax", check_s1_tool_syntax),
        Check("manifest-aware execution policy", check_execution_policy),
        Check(
            "execution-policy fail-closed regressions",
            check_execution_policy_regressions,
        ),
        Check(
            "declared read and subprocess enforcement",
            check_oracle_enforcement_regressions,
        ),
        Check(
            "subprocess output-oracle regressions",
            check_subprocess_output_regressions,
        ),
        Check(
            "external closure materialization regressions",
            check_materialized_closure_regressions,
        ),
        Check(
            "manifest dispatch exact-once regressions",
            check_dispatch_sequence_regressions,
        ),
        Check(
            "manifest-declared closed child suites",
            check_declared_child_suites,
        ),
    )


def run_gating() -> int:
    _safe_console_line("GATING_SUITE_ONLY")
    all_passed = True
    for check in gating_checks():
        try:
            check.function()
        except (
            CheckFailure,
            FreezeError,
            OSError,
            RuntimeError,
            TypeError,
            UnicodeError,
            ValueError,
        ) as exc:
            all_passed = False
            _safe_console_line(f"FAIL: {check.name} -- {exc}")
        else:
            _safe_console_line(f"PASS: {check.name}")
    if all_passed:
        _safe_console_line(GATING_SUCCESS_LINE)
        return 0
    _safe_console_line("GATING_FAILED")
    return 1


def _strict_canonical_json(data: bytes) -> dict[str, object]:
    if data.startswith(b"\xef\xbb\xbf") or b"\r" in data:
        raise CheckFailure("historical report has invalid byte framing")

    def reject_pairs(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise CheckFailure(
                    f"historical report has duplicate key: {key}"
                )
            result[key] = value
        return result

    def reject_constant(value: str) -> NoReturn:
        raise CheckFailure(
            f"historical report has invalid JSON constant: {value}"
        )

    try:
        parsed = json.loads(
            data,
            object_pairs_hook=reject_pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CheckFailure(
            f"historical report is not strict JSON: {exc}"
        ) from exc
    report = _object(parsed, "historical report")
    if canonical(report) != data:
        raise CheckFailure("historical report is not canonical")
    return report


def _validate_historical_report(
    report: dict[str, object],
    commit: str,
) -> None:
    expected_keys = {
        "canonicalization_id",
        "format",
        "inventory",
        "inventory_file_count",
        "mismatches",
        "purpose",
        "source_commit",
        "status",
        "validators",
    }
    if set(report) != expected_keys:
        raise CheckFailure("historical report keys are not exact")
    if report["canonicalization_id"] != "sa-json-c14n-v1":
        raise CheckFailure("historical canonicalization ID mismatch")
    if report["format"] != HISTORICAL_FORMAT:
        raise CheckFailure("historical report format mismatch")
    if report["purpose"] != HISTORICAL_PURPOSE:
        raise CheckFailure("historical report purpose mismatch")
    if report["source_commit"] != commit:
        raise CheckFailure("historical report source commit mismatch")
    if report["status"] != "PASS" or report["mismatches"] != []:
        raise CheckFailure("historical replay did not report PASS")

    historical = _object(
        _context().manifest["historical_replay"],
        "historical_replay",
    )
    objects = historical.get("objects")
    if not isinstance(objects, list):
        raise CheckFailure("historical manifest objects are invalid")
    inventory = report["inventory"]
    if not isinstance(inventory, list) or len(inventory) != len(objects):
        raise CheckFailure("historical inventory count mismatch")
    if report["inventory_file_count"] != len(objects):
        raise CheckFailure("historical inventory_file_count mismatch")
    inventory_keys = {
        "byte_count",
        "git_blob_oid",
        "git_mode",
        "path",
        "sha256",
    }
    observed_paths: list[str] = []
    for raw in inventory:
        item = _object(raw, "historical inventory item")
        if set(item) != inventory_keys:
            raise CheckFailure("historical inventory item keys mismatch")
        path = item["path"]
        if not isinstance(path, str):
            raise CheckFailure("historical inventory path is invalid")
        observed_paths.append(path)
        if item["git_mode"] != "100644":
            raise CheckFailure("historical inventory mode mismatch")
        if not isinstance(item["byte_count"], int) or item["byte_count"] < 0:
            raise CheckFailure("historical inventory byte_count is invalid")
        for key, length in (("git_blob_oid", 40), ("sha256", 64)):
            value = item[key]
            if not isinstance(value, str) or not re.fullmatch(
                rf"[0-9a-f]{{{length}}}",
                value,
            ):
                raise CheckFailure(
                    f"historical inventory {key} is invalid"
                )
    expected_paths = sorted(
        (str(path) for path in objects),
        key=lambda item: item.encode("utf-8"),
    )
    if observed_paths != expected_paths:
        raise CheckFailure("historical inventory paths mismatch")

    runtime_oracles = historical.get("runtime_oracles")
    if not isinstance(runtime_oracles, list):
        raise CheckFailure("historical runtime oracles are invalid")
    expected_oracles: dict[str, int] = {}
    for raw_oracle in runtime_oracles:
        oracle = _object(raw_oracle, "runtime oracle")
        path = oracle.get("path")
        expected_passed = oracle.get("expected_passed")
        if not isinstance(path, str) or path in expected_oracles:
            raise CheckFailure("historical runtime oracle path is invalid")
        if (
            not isinstance(expected_passed, int)
            or isinstance(expected_passed, bool)
            or expected_passed <= 0
        ):
            raise CheckFailure(
                "historical runtime oracle expected_passed is invalid"
            )
        expected_oracles[path] = expected_passed
    validators = report["validators"]
    if not isinstance(validators, list) or len(validators) != 2:
        raise CheckFailure("historical validator report count mismatch")
    validator_keys = {
        "all_checks_pass_marker_count",
        "checks",
        "expected_checks",
        "failed",
        "passed",
        "path",
        "return_code",
        "stderr_byte_count",
        "stderr_sha256",
        "stdout_byte_count",
        "stdout_sha256",
    }
    observed_validators: dict[str, dict[str, object]] = {}
    for raw in validators:
        item = _object(raw, "historical validator report")
        if set(item) != validator_keys:
            raise CheckFailure("historical validator keys mismatch")
        path = item["path"]
        if not isinstance(path, str) or path in observed_validators:
            raise CheckFailure("historical validator path is invalid")
        observed_validators[path] = item
    if set(observed_validators) != set(expected_oracles):
        raise CheckFailure("historical validator paths mismatch")
    empty_sha256 = (
        "e3b0c44298fc1c149afbf4c8996fb924"
        "27ae41e4649b934ca495991b7852b855"
    )
    for path, expected in expected_oracles.items():
        item = observed_validators[path]
        if (
            item["expected_checks"] != expected
            or item["checks"] != expected
            or item["passed"] != expected
            or item["failed"] != 0
            or item["return_code"] != 0
            or item["all_checks_pass_marker_count"] != 1
            or item["stderr_byte_count"] != 0
            or item["stderr_sha256"] != empty_sha256
        ):
            raise CheckFailure(
                f"historical runtime oracle mismatch: {path}"
            )
        if (
            not isinstance(item["stdout_byte_count"], int)
            or item["stdout_byte_count"] <= 0
            or not isinstance(item["stdout_sha256"], str)
            or not re.fullmatch(
                r"[0-9a-f]{64}",
                item["stdout_sha256"],
            )
        ):
            raise CheckFailure(
                f"historical stdout facts are invalid: {path}"
            )


def run_historical(repo: Path, commit: str) -> int:
    try:
        if not repo.is_absolute():
            raise CheckFailure("historical repository must be absolute")
        if FULL_COMMIT_RE.fullmatch(commit) is None:
            raise CheckFailure(
                "historical commit must be full lowercase 40-hex"
            )
        historical = _object(
            _context().manifest["historical_replay"],
            "historical_replay",
        )
        entrypoint = historical.get("entrypoint")
        if not isinstance(entrypoint, str):
            raise CheckFailure("historical entrypoint is invalid")
        if entrypoint in _context().allowed_subprocesses:
            raise CheckFailure(
                "historical entrypoint entered gating subprocess authority"
            )
        if entrypoint not in _context().closure:
            raise CheckFailure(
                "historical entrypoint is not closure-bound support source"
            )
        helper = _context().path(entrypoint)
        with tempfile.TemporaryDirectory(
            prefix="m8-s1-historical-dispatch-"
        ) as directory:
            temp_root = inspect_path_components(
                Path(directory),
                "historical dispatch temporary directory",
            )
            cwd = temp_root / "unrelated-cwd"
            cwd.mkdir()
            launcher = (
                "import runpy,sys;"
                f"sys.path.insert(0,{os.fspath(TOOLS)!r});"
                f"sys.argv={[os.fspath(helper), '--repo', str(repo), '--commit', commit]!r};"
                f"runpy.run_path({os.fspath(helper)!r},run_name='__main__')"
            )
            return_code, stdout, stderr = run_bounded_process(
                [sys.executable, "-I", "-c", launcher],
                cwd,
                allowed_isolated_code=launcher,
                environment=_child_environment(temp_root),
                timeout_seconds=120,
            )
        if return_code != 0:
            detail = (stdout + b"\n" + stderr).decode(
                "utf-8",
                errors="replace",
            )
            raise CheckFailure(
                f"historical helper exited {return_code}: {detail[-2000:]}"
            )
        if stderr:
            raise CheckFailure("historical helper wrote stderr")
        report = _strict_canonical_json(stdout)
        _validate_historical_report(report, commit)
    except (
        CheckFailure,
        FreezeError,
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        _safe_console_line(f"historical replay failure: {exc}")
        _safe_console_line("HISTORICAL_REGRESSION_FAILED")
        return 1
    _safe_console_line(HISTORICAL_SUCCESS_LINE)
    return 0


def _parse_arguments() -> argparse.Namespace:
    parser = ControlledArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--gating-only",
        action="store_true",
        help="run only the closed candidate-local gating suite",
    )
    modes.add_argument(
        "--historical-regressions",
        action="store_true",
        help="run only explicit commit-bound historical replay",
    )
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--commit")
    args = parser.parse_args()
    if args.historical_regressions:
        if args.repo is None or args.commit is None:
            raise CheckFailure(
                "historical mode requires --repo and --commit"
            )
    elif args.repo is not None or args.commit is not None:
        raise CheckFailure(
            "--repo and --commit are valid only with "
            "--historical-regressions"
        )
    return args


def main() -> int:
    global _CONTEXT
    try:
        args = _parse_arguments()
    except (
        CheckFailure,
        FreezeError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        _safe_console_line(f"prerequisite oracle setup failure: {exc}")
        _safe_console_line("GATING_FAILED")
        return 2
    try:
        _CONTEXT = OracleContext.load(REPO_ROOT)
    except (
        CheckFailure,
        FreezeError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        _safe_console_line(f"prerequisite oracle setup failure: {exc}")
        _safe_console_line(
            "HISTORICAL_REGRESSION_FAILED"
            if args.historical_regressions
            else "GATING_FAILED"
        )
        return 2
    if args.historical_regressions:
        return run_historical(args.repo, args.commit)
    return run_gating()


if __name__ == "__main__":
    raise SystemExit(main())

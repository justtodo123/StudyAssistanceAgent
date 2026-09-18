#!/usr/bin/env python3
"""Run the closed M8 v3 S1 prerequisite oracle or historical replay.

The default command is a candidate-local Builder self-check. Historical replay
is an explicit, commit-bound, non-gating mode. Neither mode grants S1 or any
execution authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
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
    ALLOWED_GATING_SUBPROCESSES,
    PROCESS_CONTROL_SUPPORT_MODULES,
    FreezeError,
    ORACLE_MANIFEST_PATH,
    canonical,
    derive_gating_closure,
    inspect_path_components,
    parse_oracle_manifest,
    read_blob,
    validate_commit,
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
HISTORICAL_HELPER_SHA256 = (
    "cab4075464e9febd1a36241d13265c77279f3a37571b1dc04160708ef4348c61"
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
    """Validated manifest-derived authority for immutable repository bytes."""

    root: Path
    manifest: dict[str, object]
    closure: tuple[str, ...]
    subprocess_specs: tuple[SubprocessSpec, ...]
    snapshot: dict[str, bytes]

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
        snapshot: dict[str, bytes] = {}
        for logical_path in closure:
            path = root.joinpath(*logical_path.split("/"))
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(root.resolve(strict=True))
                snapshot[logical_path] = path.read_bytes()
            except (OSError, ValueError) as exc:
                raise CheckFailure(
                    f"cannot capture closure member {logical_path}: {exc}"
                ) from exc
        if snapshot.get(ORACLE_MANIFEST_PATH) != raw:
            raise CheckFailure("oracle manifest changed during snapshot capture")
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
        return cls(root, manifest, closure, tuple(specs), snapshot)

    @property
    def allowed_subprocesses(self) -> frozenset[str]:
        return frozenset(spec.path for spec in self.subprocess_specs)

    def path(self, logical_path: str) -> Path:
        normalized = validate_logical_path(logical_path)
        if normalized not in self.closure:
            raise CheckFailure(
                f"undeclared repository read refused: {normalized}"
            )
        path = self.root.joinpath(*normalized.split("/"))
        try:
            path.resolve(strict=True).relative_to(self.root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise CheckFailure(
                f"declared path escaped repository: {normalized}"
            ) from exc
        return path

    def read_bytes(self, logical_path: str) -> bytes:
        normalized = validate_logical_path(logical_path)
        if normalized not in self.closure:
            raise CheckFailure(
                f"undeclared repository read refused: {normalized}"
            )
        try:
            return self.snapshot[normalized]
        except KeyError as exc:
            raise CheckFailure(
                f"closure snapshot omits declared path: {normalized}"
            ) from exc

    def read_text(self, logical_path: str) -> str:
        try:
            return self.read_bytes(logical_path).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CheckFailure(
                f"declared text is not UTF-8: {logical_path}"
            ) from exc

    def require_subprocess(self, logical_path: str) -> SubprocessSpec:
        normalized = validate_logical_path(logical_path)
        matches = tuple(
            spec for spec in self.subprocess_specs if spec.path == normalized
        )
        if len(matches) != 1:
            raise CheckFailure(
                f"undeclared gating subprocess refused: {normalized}"
            )
        return matches[0]

    def materialize_closure(self, destination: Path) -> Path:
        """Copy only captured closure bytes into a fresh external tree."""
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
    """Return only validated manifest roles allowed process-control source."""
    context = _context()
    gating = _object(context.manifest["gating"], "gating")
    support = gating.get("support_modules")
    if not isinstance(support, list):
        raise CheckFailure("gating.support_modules is not a list")
    missing = sorted(set(PROCESS_CONTROL_SUPPORT_MODULES) - set(support))
    if missing:
        raise CheckFailure(
            "manifest omits a process-control support module: " + missing[0]
        )
    return frozenset(
        {
            str(gating["entrypoint"]),
            *context.allowed_subprocesses,
            *PROCESS_CONTROL_SUPPORT_MODULES,
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
    process_modules = {"asyncio", "multiprocessing", "os", "subprocess"}
    process_terminals = {
        "Popen",
        "Pool",
        "Process",
        "call",
        "check_call",
        "check_output",
        "create_subprocess_exec",
        "create_subprocess_shell",
        "popen",
        "run",
        "startfile",
        "system",
    }
    windows_process_terminals = {
        "CreateProcess",
        "CreateProcessA",
        "CreateProcessW",
        "ShellExecute",
        "ShellExecuteA",
        "ShellExecuteW",
        "WinExec",
    }
    process_source_allowed = logical_path in _source_subprocess_paths()
    enclosing_names = _enclosing_symbol_names(tree)
    _validate_process_path_constants(logical_path, tree)
    imported_modules: dict[str, str] = {}

    def bound_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return imported_modules.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            parent = bound_name(node.value)
            return f"{parent}.{node.attr}" if parent else None
        return None

    def process_callable(name: str | None) -> bool:
        if not name:
            return False
        root, separator, remainder = name.partition(".")
        if not separator:
            return False
        terminal = remainder.rsplit(".", 1)[-1]
        return root in process_modules and (
            root == "multiprocessing"
            or terminal in process_terminals
            or terminal.startswith("spawn")
            or terminal.startswith("exec")
        )

    def reject(node: ast.AST, message: str) -> NoReturn:
        raise CheckFailure(
            f"{logical_path}:{getattr(node, 'lineno', 0)}: {message}"
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                imported_modules[alias.asname or root] = alias.name
                if root in forbidden_modules:
                    reject(node, f"forbidden import {root}")
                if root == "subprocess" and alias.asname:
                    reject(node, "aliased subprocess imports are forbidden")
                if root == "subprocess" and not process_source_allowed:
                    reject(node, "subprocess source role is undeclared")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".", 1)[0]
            if root in forbidden_modules:
                reject(node, f"forbidden import {root}")
            if root == "subprocess":
                reject(node, "from-subprocess imports are forbidden")
            if root in {"asyncio", "multiprocessing", "os"}:
                for alias in node.names:
                    candidate = f"{root}.{alias.name}"
                    if process_callable(candidate):
                        reject(node, f"from-{root} process imports are forbidden")
            for alias in node.names:
                if alias.name == "*":
                    reject(node, "star imports are forbidden")
                if root == "importlib" and alias.name == "import_module":
                    imported_modules[alias.asname or alias.name] = (
                        "importlib.import_module"
                    )
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            value = node.value
            if value is None:
                continue
            value_name = bound_name(value)
            if value_name == "subprocess":
                reject(node, "subprocess module aliases are forbidden")
            if process_callable(value_name):
                reject(node, "process callable aliases are forbidden")
        elif isinstance(node, ast.Call):
            call_name = bound_name(node.func)
            if call_name in {"__import__", "breakpoint", "eval", "exec"}:
                reject(node, f"forbidden dynamic call {call_name}()")
            if call_name == "importlib.import_module":
                if (
                    len(node.args) != 1
                    or node.keywords
                    or not isinstance(node.args[0], ast.Constant)
                    or not isinstance(node.args[0].value, str)
                ):
                    reject(node, "dynamic imports require one literal module name")
                imported_root = node.args[0].value.split(".", 1)[0]
                if imported_root == "subprocess":
                    reject(node, "dynamic subprocess imports are forbidden")
                if imported_root in forbidden_modules:
                    reject(node, f"dynamic import of forbidden module {imported_root}")
                reject(node, "dynamic imports are forbidden")
            if (
                isinstance(node.func, ast.Subscript)
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "__dict__"
            ):
                target = bound_name(node.func.value.value)
                if target and target.split(".", 1)[0] in process_modules:
                    reject(node, "process module dictionary access is forbidden")
            if call_name == "getattr" and node.args:
                target = bound_name(node.args[0])
                if target and target.split(".", 1)[0] in (
                    process_modules | {"importlib"}
                ):
                    attribute = (
                        node.args[1].value
                        if len(node.args) >= 2
                        and isinstance(node.args[1], ast.Constant)
                        and isinstance(node.args[1].value, str)
                        else None
                    )
                    if (
                        target == "importlib"
                        or attribute is None
                        or attribute in process_terminals
                        or attribute in windows_process_terminals
                        or attribute.startswith("spawn")
                        or attribute.startswith("exec")
                    ):
                        reject(
                            node,
                            "indirect process or import invocation is forbidden",
                        )
            terminal = call_name.rsplit(".", 1)[-1] if call_name else ""
            if terminal in windows_process_terminals:
                reject(node, "alternate process invocation is forbidden")
            if not process_callable(call_name):
                continue
            if call_name not in {"subprocess.Popen", "subprocess.run"}:
                reject(node, "alternate process invocation is forbidden")
            if not process_source_allowed:
                reject(node, "subprocess call is not allowed for this source role")
            keywords = {
                keyword.arg: keyword.value
                for keyword in node.keywords
                if keyword.arg
            }
            if any(keyword.arg is None for keyword in node.keywords):
                reject(node, "expanded subprocess keywords are forbidden")
            shell = keywords.get("shell")
            if shell is not None and not (
                isinstance(shell, ast.Constant) and shell.value is False
            ):
                reject(node, "shell must be omitted or literal False")
            _validate_subprocess_destination(
                logical_path,
                node,
                enclosing_names[node],
            )


def _child_environment(temp_root: Path) -> dict[str, str]:
    """Build a bounded environment without inherited Python/Git controls."""
    env: dict[str, str] = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
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
    """Prove materialization uses one immutable captured byte snapshot."""
    with tempfile.TemporaryDirectory(
        prefix="m8-s1-materialization-regression-"
    ) as directory:
        temp_root = Path(directory)
        source_root = temp_root / "source"
        source_root.mkdir()
        declared = source_root / "declared.txt"
        declared.write_bytes(b"declared\n")
        (source_root / "undeclared.txt").write_bytes(b"ambient\n")
        context = OracleContext(
            root=source_root,
            manifest={},
            closure=("declared.txt",),
            subprocess_specs=(),
            snapshot={"declared.txt": b"declared\n"},
        )
        declared.write_bytes(b"post-snapshot mutation\n")
        materialized_root = temp_root / "materialized"
        materialized_root.mkdir()
        context.materialize_closure(materialized_root)
        _verify_materialized_closure(context, materialized_root)
        if (materialized_root / "declared.txt").read_bytes() != b"declared\n":
            raise CheckFailure("post-snapshot source mutation entered closure")
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


def check_child_runtime_isolation_regressions() -> None:
    """Prove separate child processes cannot observe each other's writable roots."""
    with tempfile.TemporaryDirectory(
        prefix="m8-s1-child-isolation-regression-"
    ) as directory:
        temp_root = Path(directory)
        probe = temp_root / "probe.py"
        probe.write_text(
            "import os, pathlib, sys\n"
            "root = pathlib.Path(os.environ['CHILD_ROOT'])\n"
            "mode = os.environ['CHILD_MODE']\n"
            "locations = ('closure', 'cwd', 'runtime', 'runtime/pycache')\n"
            "if mode == 'write':\n"
            "    for location in locations:\n"
            "        root.joinpath(*location.split('/'), 'sentinel').write_text('child-a\\n')\n"
            "else:\n"
            "    leaked = [location for location in locations if root.joinpath(*location.split('/'), 'sentinel').exists()]\n"
            "    if leaked:\n"
            "        print('leaked:' + ','.join(leaked))\n"
            "        sys.exit(1)\n"
            "    print('isolated')\n",
            encoding="utf-8",
            newline="\n",
        )
        child_a = temp_root / "child-a"
        child_b = temp_root / "child-b"
        locations = ("closure", "cwd", "runtime", "runtime/pycache")
        for child_root in (child_a, child_b):
            for location in locations:
                child_root.joinpath(*location.split("/")).mkdir(
                    parents=True,
                    exist_ok=True,
                )
        environment_a = _child_environment(temp_root / "runtime-a")
        environment_a["CHILD_ROOT"] = str(child_a)
        environment_a["CHILD_MODE"] = "write"
        return_code, stdout, stderr = run_bounded_process(
            [sys.executable, "-I", "-B", str(probe)],
            child_a / "cwd",
            allowed_python_script=probe,
            environment=environment_a,
            timeout_seconds=30,
        )
        if return_code != 0 or stdout != b"" or stderr != b"":
            raise CheckFailure("child A isolation probe failed")
        for location in locations:
            sentinel = child_a.joinpath(*location.split("/"), "sentinel")
            if not sentinel.is_file():
                raise CheckFailure(
                    "child A did not write isolation sentinel: " + location
                )
        environment_b = _child_environment(temp_root / "runtime-b")
        environment_b["CHILD_ROOT"] = str(child_b)
        environment_b["CHILD_MODE"] = "read"
        return_code, stdout, stderr = run_bounded_process(
            [sys.executable, "-I", "-B", str(probe)],
            child_b / "cwd",
            allowed_python_script=probe,
            environment=environment_b,
            timeout_seconds=30,
        )
        if (
            return_code != 0
            or _normalize_historical_output(stdout) != b"isolated\n"
            or stderr != b""
        ):
            raise CheckFailure("child B observed child A writable state")
        for location in locations:
            if not child_b.joinpath(*location.split("/"), "sentinel").exists():
                continue
            raise CheckFailure(
                "child A writable state is visible to child B: " + location
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
    child_id = hashlib.sha256(spec.path.encode("utf-8")).hexdigest()[:16]
    child_root = temp_root / f"child-{child_id}"
    child_root.mkdir()
    cwd = child_root / "cwd"
    cwd.mkdir()
    child_temp_root = child_root / "runtime"
    child_temp_root.mkdir()
    launcher = (
        "import runpy,sys;"
        f"sys.path.insert(0,{os.fspath(materialized_tools)!r});"
        f"runpy.run_path({os.fspath(tool)!r},run_name='__main__')"
    )
    return_code, stdout, stderr = run_bounded_process(
        [sys.executable, "-I", "-B", "-c", launcher],
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
    expected_subprocesses = tuple(
        SubprocessSpec(
            path=str(item["path"]),
            success_oracle=_object(
                item["success_oracle"],
                "code-fixed subprocess success_oracle",
            ),
        )
        for item in ALLOWED_GATING_SUBPROCESSES
    )
    if context.subprocess_specs != expected_subprocesses:
        raise CheckFailure("gating subprocess authority is not code-fixed")
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
    """Prove alternate process and import bypasses fail closed."""
    graph_path = "tools/m8_test_minimal_1k_graph_v3.py"
    freeze_test_path = "tools/m8_test_freeze_s1_prerequisites_v3.py"
    rejected = (
        (graph_path, "import os\nos.system('x')\n", "alternate process invocation"),
        (graph_path, "import os\nos.popen('x')\n", "alternate process invocation"),
        (graph_path, "import os\nos.spawnv(0, 'x', ['x'])\n", "alternate process invocation"),
        (graph_path, "import os\nos.execv('x', ['x'])\n", "alternate process invocation"),
        (graph_path, "import os\nos.startfile('x')\n", "alternate process invocation"),
        (graph_path, "import asyncio\nasyncio.create_subprocess_exec('x')\n", "alternate process invocation"),
        (graph_path, "import asyncio\nasyncio.create_subprocess_shell('x')\n", "alternate process invocation"),
        (graph_path, "import multiprocessing\nmultiprocessing.Process()\n", "alternate process invocation"),
        (graph_path, "import multiprocessing\nmultiprocessing.Pool()\n", "alternate process invocation"),
        (graph_path, "import subprocess\nsubprocess.call(['x'])\n", "alternate process invocation"),
        (graph_path, "import subprocess\nsubprocess.check_call(['x'])\n", "alternate process invocation"),
        (graph_path, "import subprocess\nsubprocess.check_output(['x'])\n", "alternate process invocation"),
        (graph_path, "import subprocess as sp\nsp.run(['tool'])\n", "aliased subprocess imports"),
        (graph_path, "from subprocess import run\nrun(['tool'])\n", "from-subprocess imports"),
        (graph_path, "import subprocess\nsp = subprocess\nsp.run(['tool'])\n", "subprocess module aliases"),
        (graph_path, "import subprocess\nrunner = subprocess.run\nrunner(['tool'])\n", "process callable aliases"),
        (graph_path, "import subprocess\ngetattr(subprocess, 'run')(['tool'])\n", "indirect process or import invocation"),
        (graph_path, "import subprocess\nsubprocess.__dict__['run'](['tool'])\n", "process module dictionary access"),
        (graph_path, "import importlib\nimportlib.import_module('subprocess').run(['tool'])\n", "dynamic subprocess imports"),
        (graph_path, "import importlib as il\nil.import_module('requests')\n", "dynamic import of forbidden module requests"),
        (graph_path, "from importlib import import_module as load\nload('socket')\n", "dynamic import of forbidden module socket"),
        (graph_path, "import importlib\nimportlib.import_module('urllib.request')\n", "dynamic import of forbidden module urllib"),
        (graph_path, "import importlib\nname = 'urllib'\nimportlib.import_module(name)\n", "dynamic imports require one literal module name"),
        (graph_path, "import importlib\ngetattr(importlib, 'import_module')('httpx')\n", "indirect process or import invocation"),
        (graph_path, "import importlib\nimportlib.import_module('pip')\n", "dynamic import of forbidden module pip"),
        (graph_path, "import importlib\nimportlib.import_module('venv')\n", "dynamic import of forbidden module venv"),
        (graph_path, "import subprocess\nenabled = True\nsubprocess.run(['tool'], shell=enabled)\n", "shell must be omitted or literal False"),
        (graph_path, "import subprocess\noptions = {'shell': False}\nsubprocess.run(['tool'], **options)\n", "expanded subprocess keywords"),
        (graph_path, "import subprocess\nsubprocess.run(['tool'], shell=False)\n", "subprocess destination is not bound"),
        (graph_path, "import subprocess, sys\nsubprocess.run([sys.executable, 'other.py'])\n", "subprocess destination is not bound"),
        (graph_path, "import subprocess\nsubprocess.run(['cmd.exe', '/d', '/c', 'del', 'x'])\n", "subprocess destination is not bound"),
        (graph_path, "import subprocess\ncommand = ['tool']\nsubprocess.run(command)\n", "subprocess destination is not bound"),
        (
            graph_path,
            "import subprocess, sys\nfrom pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[1]\n"
            "GENERATOR = ROOT / 'tools' / 'm8_generate_minimal_1k_v3_fixtures.py'\n"
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
            "import subprocess\nfrom pathlib import Path\n"
            "def _terminate_process_tree(process):\n"
            "    taskkill = Path('other.exe')\n"
            "    subprocess.run([str(taskkill), '/PID', str(process.pid), '/F'])\n",
            "taskkill destination is not bound",
        ),
    )
    for logical_path, source, expected in rejected:
        try:
            _validate_execution_policy(logical_path, source)
        except CheckFailure as exc:
            if expected not in str(exc):
                raise CheckFailure(
                    "execution-policy regression failed incorrectly: " + str(exc)
                ) from exc
        else:
            raise CheckFailure(
                "execution-policy bypass was accepted: " + expected
            )

    _validate_execution_policy(
        graph_path,
        "import subprocess, sys\nfrom pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "GENERATOR = ROOT / 'tools/m8_generate_minimal_1k_v3_fixtures.py'\n"
        "subprocess.run([sys.executable, str(GENERATOR), "
        "'--output-root', 'fixture'])\n",
    )
    _validate_execution_policy(
        graph_path,
        "import subprocess\nfrom pathlib import Path\n"
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
    """Prove undeclared reads/processes and manifest expansion fail closed."""
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
    for undeclared in (
        "tools/m8_replay_historical_regressions_v3.py",
        "tools/definitely-not-declared.py",
    ):
        try:
            _context().require_subprocess(undeclared)
        except CheckFailure as exc:
            if "undeclared gating subprocess refused" not in str(exc):
                raise CheckFailure(
                    f"undeclared-process regression failed incorrectly: {exc}"
                ) from exc
        else:
            raise CheckFailure(
                f"undeclared gating subprocess was accepted: {undeclared}"
            )

    forged = json.loads(json.dumps(_context().manifest))
    gating = _object(forged["gating"], "forged gating")
    subprocesses = gating.get("allowed_subprocesses")
    if not isinstance(subprocesses, list):
        raise CheckFailure("forged subprocess list setup failed")
    subprocesses.append(
        {
            "path": "tools/canary-must-not-execute.py",
            "role": "bounded-test",
            "success_oracle": {
                "kind": "exact-line",
                "success_line": "FORGED PASS",
            },
        }
    )
    subprocesses.sort(key=lambda item: str(item["path"]).encode("utf-8"))
    try:
        parse_oracle_manifest(canonical(forged))
    except FreezeError as exc:
        if "code-fixed exact map" not in str(exc):
            raise CheckFailure(
                f"manifest authority regression failed incorrectly: {exc}"
            ) from exc
    else:
        raise CheckFailure("manifest expanded gating process authority")


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
    short_temp_parent = Path("C:/m8tmp")
    temporary_directory_kwargs: dict[str, object] = {
        "prefix": "m8-s1-gating-",
    }
    if short_temp_parent.is_dir():
        temporary_directory_kwargs["dir"] = os.fspath(short_temp_parent)
    with tempfile.TemporaryDirectory(**temporary_directory_kwargs) as directory:
        temp_root = inspect_path_components(
            Path(directory),
            "gating temporary directory",
        )
        for index, spec in enumerate(context.subprocess_specs):
            materialized_root = temp_root / f"closure-{index}"
            materialized_root.mkdir()
            context.materialize_closure(materialized_root)
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
            "per-child runtime isolation regressions",
            check_child_runtime_isolation_regressions,
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


def _historical_line_byte_offsets(source: bytes) -> list[int]:
    offsets = [0]
    for index, byte in enumerate(source):
        if byte == 0x0A:
            offsets.append(index + 1)
    return offsets


def _bind_historical_repository(
    source: bytes,
    repository_root: Path,
    logical_path: str,
) -> bytes:
    """Rewrite only the sole structural top-level REPO Path literal."""
    if source.startswith(b"\xef\xbb\xbf"):
        raise CheckFailure(
            f"historical validator has a UTF-8 BOM: {logical_path}"
        )
    try:
        text = source.decode("utf-8")
        module = ast.parse(text, filename=logical_path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise CheckFailure(
            f"historical validator cannot be parsed: {logical_path}"
        ) from exc
    candidates = [
        statement
        for statement in module.body
        if isinstance(statement, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "REPO"
            for target in statement.targets
        )
    ]
    if len(candidates) != 1:
        raise CheckFailure(
            "historical validator must contain exactly one top-level "
            f"REPO assignment: {logical_path}"
        )
    assignment = candidates[0]
    call = assignment.value
    if not (
        len(assignment.targets) == 1
        and isinstance(assignment.targets[0], ast.Name)
        and assignment.targets[0].id == "REPO"
        and isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "Path"
        and len(call.args) == 1
        and not call.keywords
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
    ):
        raise CheckFailure(
            f"historical validator REPO assignment has an unexpected shape: {logical_path}"
        )
    literal = call.args[0]
    if literal.end_lineno is None or literal.end_col_offset is None:
        raise CheckFailure(
            f"historical validator REPO literal has no source span: {logical_path}"
        )
    offsets = _historical_line_byte_offsets(source)
    start = offsets[literal.lineno - 1] + literal.col_offset
    end = offsets[literal.end_lineno - 1] + literal.end_col_offset
    rebound = (
        source[:start]
        + repr(str(repository_root)).encode("utf-8")
        + source[end:]
    )
    try:
        rebound_module = ast.parse(
            rebound.decode("utf-8"),
            filename=logical_path,
        )
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise CheckFailure(
            f"rebound historical validator cannot be parsed: {logical_path}"
        ) from exc
    rebound_assignments = [
        statement
        for statement in rebound_module.body
        if isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == "REPO"
    ]
    if len(rebound_assignments) != 1:
        raise CheckFailure(
            f"rebound historical validator lost its REPO assignment: {logical_path}"
        )
    rebound_call = rebound_assignments[0].value
    if not (
        isinstance(rebound_call, ast.Call)
        and len(rebound_call.args) == 1
        and isinstance(rebound_call.args[0], ast.Constant)
        and rebound_call.args[0].value == str(repository_root)
    ):
        raise CheckFailure(
            f"rebound historical validator has the wrong repository root: {logical_path}"
        )
    return rebound


def _normalize_historical_output(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _observe_historical_validator(
    logical_path: str,
    expected_checks: int,
    return_code: int,
    stdout: bytes,
    stderr: bytes,
) -> dict[str, object]:
    stdout = _normalize_historical_output(stdout)
    stderr = _normalize_historical_output(stderr)
    summaries = [
        line for line in stdout.splitlines() if line.startswith(b"checks: ")
    ]
    checks = passed = failed = -1
    if len(summaries) == 1:
        parts = summaries[0].decode("ascii", errors="replace").split()
        try:
            if (
                len(parts) == 6
                and parts[0] == "checks:"
                and parts[2] == "passed:"
                and parts[4] == "failed:"
            ):
                checks, passed, failed = (
                    int(parts[1]),
                    int(parts[3]),
                    int(parts[5]),
                )
        except ValueError:
            pass
    return {
        "all_checks_pass_marker_count": stdout.splitlines().count(
            b"ALL CHECKS PASS"
        ),
        "checks": checks,
        "expected_checks": expected_checks,
        "failed": failed,
        "passed": passed,
        "path": logical_path,
        "return_code": return_code,
        "stderr_byte_count": len(stderr),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stdout_byte_count": len(stdout),
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
    }


def _independently_replay_historical_validators(
    repo: Path,
    commit: str,
) -> list[dict[str, object]]:
    """Run exact validator blobs independently of the helper report."""
    context = _context()
    historical = _object(
        context.manifest["historical_replay"],
        "historical_replay",
    )
    raw_objects = historical.get("objects")
    raw_oracles = historical.get("runtime_oracles")
    if not isinstance(raw_objects, list) or not isinstance(raw_oracles, list):
        raise CheckFailure("historical replay declaration is invalid")
    blobs: dict[str, bytes] = {}
    for raw_path in raw_objects:
        if not isinstance(raw_path, str):
            raise CheckFailure("historical object path is invalid")
        mode, _oid, data = read_blob(commit, raw_path, repo)
        if mode != "100644":
            raise CheckFailure(
                f"historical object is not a regular non-executable blob: {raw_path}"
            )
        blobs[raw_path] = data
    validators: list[tuple[str, int]] = []
    for raw_oracle in raw_oracles:
        oracle = _object(raw_oracle, "historical runtime oracle")
        path = oracle.get("path")
        expected = oracle.get("expected_passed")
        if (
            not isinstance(path, str)
            or not isinstance(expected, int)
            or isinstance(expected, bool)
        ):
            raise CheckFailure("historical runtime oracle is invalid")
        validators.append((path, expected))
    observed: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(
        prefix="m8-s1-independent-historical-"
    ) as directory:
        temp_root = inspect_path_components(
            Path(directory),
            "independent historical replay directory",
        )
        repository_root = repo.resolve()
        if (
            temp_root.resolve() == repository_root
            or repository_root in temp_root.resolve().parents
            or temp_root.resolve() in repository_root.parents
        ):
            raise CheckFailure(
                "independent historical replay directory must be repository-external"
            )
        for index, (logical_path, expected_checks) in enumerate(validators):
            child_root = temp_root / f"child-{index}"
            materialized_root = child_root / "materialized"
            cwd = child_root / "cwd"
            runtime_root = child_root / "runtime"
            materialized_root.mkdir(parents=True)
            cwd.mkdir()
            runtime_root.mkdir()
            validator_paths = {path for path, _count in validators}
            for path, data in blobs.items():
                target = materialized_root.joinpath(*path.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                if path in validator_paths:
                    data = _bind_historical_repository(
                        data,
                        materialized_root,
                        path,
                    )
                target.write_bytes(data)
            validator = materialized_root.joinpath(*logical_path.split("/"))
            environment = _child_environment(runtime_root)
            return_code, stdout, stderr = run_bounded_process(
                [sys.executable, "-I", "-B", str(validator)],
                cwd,
                allowed_python_script=validator,
                environment=environment,
                timeout_seconds=120,
            )
            observed.append(
                _observe_historical_validator(
                    logical_path,
                    expected_checks,
                    return_code,
                    stdout,
                    stderr,
                )
            )
    return observed


def _validate_historical_report(
    report: dict[str, object],
    repo: Path,
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
    validate_commit(commit, repo)
    trusted_object_facts: dict[str, tuple[str, str, int, str]] = {}
    for raw_path in objects:
        if not isinstance(raw_path, str):
            raise CheckFailure("historical manifest object path is invalid")
        mode, oid, data = read_blob(commit, raw_path, repo)
        trusted_object_facts[raw_path] = (
            mode,
            oid,
            len(data),
            hashlib.sha256(data).hexdigest(),
        )
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
        trusted = trusted_object_facts.get(path)
        if trusted is None:
            raise CheckFailure("historical inventory path is not trusted")
        expected_mode, expected_oid, expected_bytes, expected_sha256 = trusted
        if (
            item["git_mode"] != expected_mode
            or item["git_blob_oid"] != expected_oid
            or item["byte_count"] != expected_bytes
            or item["sha256"] != expected_sha256
        ):
            raise CheckFailure(
                f"historical inventory facts mismatch exact Git object: {path}"
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
        context = _context()
        historical = _object(
            context.manifest["historical_replay"],
            "historical_replay",
        )
        entrypoint = historical.get("entrypoint")
        if entrypoint != "tools/m8_replay_historical_regressions_v3.py":
            raise CheckFailure("historical entrypoint is not code-fixed")
        helper_bytes = context.read_bytes(entrypoint)
        if hashlib.sha256(helper_bytes).hexdigest() != HISTORICAL_HELPER_SHA256:
            raise CheckFailure("historical helper provenance hash mismatch")
        freeze_bytes = context.read_bytes("tools/m8_freeze_s1_prerequisites_v3.py")
        validate_commit(commit, repo)
        trusted_inventory = tuple(
            str(path) for path in historical.get("objects", ())
        )
        if trusted_inventory != (
            "docs/plans/references/external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json",
            "docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json",
            "docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json",
            "docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json",
            "docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json",
            "docs/plans/references/m8-active-execution-protocol-draft-0.9.md",
            "tools/m8_validate_p0_r02.py",
            "tools/m8_validate_p1_materials.py",
        ):
            raise CheckFailure("historical inventory is not code-fixed")
        with tempfile.TemporaryDirectory(
            prefix="m8-s1-historical-dispatch-"
        ) as directory:
            temp_root = inspect_path_components(
                Path(directory),
                "historical dispatch temporary directory",
            )
            cwd = temp_root / "unrelated-cwd"
            cwd.mkdir()
            tools_root = temp_root / "tools"
            tools_root.mkdir()
            helper = tools_root / "m8_replay_historical_regressions_v3.py"
            helper.write_bytes(helper_bytes)
            (tools_root / "m8_freeze_s1_prerequisites_v3.py").write_bytes(
                freeze_bytes
            )
            helper_launcher = (
                "import runpy,sys;"
                f"sys.argv={[os.fspath(helper), '--repo', str(repo), '--commit', commit]!r};"
                f"runpy.run_path({os.fspath(helper)!r},run_name='__main__')"
            )
            return_code, stdout, stderr = run_bounded_process(
                [sys.executable, "-I", "-B", "-c", helper_launcher],
                cwd,
                allowed_isolated_code=helper_launcher,
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
        _validate_historical_report(report, repo, commit)
        independent_validators = _independently_replay_historical_validators(
            repo,
            commit,
        )
        helper_validators = report.get("validators")
        if helper_validators != independent_validators:
            raise CheckFailure(
                "historical helper report does not match independent replay"
            )
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

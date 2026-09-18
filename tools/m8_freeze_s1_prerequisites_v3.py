#!/usr/bin/env python3
"""Freeze approved M8 v3 S1 prerequisite records from Git objects only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import shutil
import sys
import tempfile
import threading
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
CANON = "sa-json-c14n-v1"
ORACLE_MANIFEST_PATH = (
    "docs/plans/references/m8-minimal-1k-v3-s1-prereq-oracle-manifest.json"
)
ORACLE_MANIFEST_FORMAT = "m8-s1-prerequisite-oracle-manifest-v1"
SUPPORTED_CLOSURE_VERSION = "m8-s1-prerequisite-closure-v2"
FREEZE_FORMAT = "m8-s1-prerequisites-v3-freeze-v2"
CODE_FIXED_BOOTSTRAP_PATHS = (
    ORACLE_MANIFEST_PATH,
    "tools/m8_freeze_s1_prerequisites_v3.py",
    "tools/m8_test_freeze_s1_prerequisites_v3.py",
    "tools/m8_test_s1_prerequisites_v3.py",
)
DECLARED_TEMPLATE_PATHS = (
    "docs/plans/references/templates/m8-minimal-1k-observer-config-v3.json",
    "docs/plans/references/templates/m8-minimal-1k-redaction-registry-v3.json",
    "docs/plans/references/templates/m8-minimal-1k-s1-config-v3.json",
    "docs/plans/references/templates/m8-minimal-1k-s1-gate-v3.json",
)
HISTORICAL_REPLAY_ENTRYPOINT = "tools/m8_replay_historical_regressions_v3.py"
HISTORICAL_REPLAY_OBJECTS = (
    "docs/plans/references/external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json",
    "docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json",
    "docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json",
    "docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json",
    "docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json",
    "docs/plans/references/m8-active-execution-protocol-draft-0.9.md",
    "tools/m8_validate_p0_r02.py",
    "tools/m8_validate_p1_materials.py",
)
HISTORICAL_RUNTIME_ORACLES = (
    ("tools/m8_validate_p1_materials.py", 88),
    ("tools/m8_validate_p0_r02.py", 77),
)
ALLOWED_GATING_SUBPROCESSES = (
    {
        "path": "tools/m8_test_freeze_minimal_1k_v3_review.py",
        "role": "bounded-test",
        "success_oracle": {
            "kind": "exact-line",
            "success_line": "ALL PASS: hermetic Git-object freeze and CLI checks",
        },
    },
    {
        "path": "tools/m8_test_freeze_s1_prerequisites_v3.py",
        "role": "bounded-test",
        "success_oracle": {
            "kind": "exact-line",
            "success_line": "ALL PASS: M8 v3 S1 prerequisite freeze self-test",
        },
    },
    {
        "path": "tools/m8_test_generate_minimal_1k_input_v3.py",
        "role": "bounded-test",
        "success_oracle": {
            "expected_test_count": 27,
            "kind": "unittest",
            "success_line": "OK",
        },
    },
    {
        "path": "tools/m8_test_minimal_1k_graph_v3.py",
        "role": "bounded-test",
        "success_oracle": {
            "kind": "exact-line",
            "success_line": (
                "ALL PASS: 5 persistent graphs + 45 fail-closed mutations "
                "+ 2 sensitivity proofs"
            ),
        },
    },
    {
        "path": "tools/m8_test_observe_minimal_1k_v3.py",
        "role": "bounded-test",
        "success_oracle": {
            "expected_test_count": 20,
            "kind": "unittest",
            "success_line": "OK",
        },
    },
    {
        "path": "tools/m8_test_s1_controls_v3.py",
        "role": "bounded-test",
        "success_oracle": {
            "kind": "exact-line",
            "success_line": "ALL PASS: canonical declared templates",
        },
    },
)
PROCESS_CONTROL_SUPPORT_MODULES = (
    "tools/m8_freeze_minimal_1k_v3_review.py",
    "tools/m8_freeze_s1_prerequisites_v3.py",
    "tools/m8_replay_historical_regressions_v3.py",
)
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
OID_RE = re.compile(r"[0-9a-f]{40}")
GIT_VERSION_RE = re.compile(r"git version (\d+)\.(\d+)\.(\d+)(?:\.[^\s]+)?")
GIT_TIMEOUT_SECONDS = 15
MAX_GIT_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
FIXTURE_ROOT = "docs/plans/references/fixtures/m8-minimal-1k-v3/"
FORBIDDEN_INVENTORY_PARTS = (
    "/external-gates/",
    "/external-artifacts/",
    "review-freeze",
    "reviewer",
    "worksheet",
)



class FreezeError(ValueError):
    def __init__(self, message: str, category: str = "validation"):
        super().__init__(message)
        self.category = category


class ControlledArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise FreezeError(message, "cli")


def canonical(obj: object) -> bytes:
    return (
        json.dumps(
            obj,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


_GIT_EXECUTABLE: Path | None = None
_GIT_EXECUTABLE_IDENTITY: tuple[int, int, int, str] | None = None
_GIT_CAPABILITY_CHECKED: Path | None = None


def has_reparse_point(file_stat: os.stat_result) -> bool:
    attributes = getattr(file_stat, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def absolute_lexical(path: Path) -> Path:
    try:
        return Path(os.path.abspath(os.fspath(path.expanduser())))
    except (OSError, RuntimeError, ValueError) as exc:
        raise FreezeError(f"path cannot be made absolute: {exc}") from exc


def inspect_path_components(
    path: Path,
    label: str,
    *,
    allow_missing_leaf: bool = False,
) -> Path:
    absolute = absolute_lexical(path)
    anchor = Path(absolute.anchor)
    current = anchor
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for index, part in enumerate(parts):
        current /= part
        try:
            file_stat = current.lstat()
        except FileNotFoundError:
            if allow_missing_leaf and index == len(parts) - 1:
                return absolute
            raise FreezeError(f"{label} does not exist: {current}") from None
        except OSError as exc:
            raise FreezeError(f"{label} cannot be inspected: {exc}") from exc
        if stat.S_ISLNK(file_stat.st_mode) or has_reparse_point(file_stat):
            raise FreezeError(f"{label} contains a symlink or reparse point: {current}")
    return absolute


def git_candidates() -> list[Path]:
    candidates: list[Path] = []
    if os.name == "nt":
        system_drive = Path(sys.executable).drive
        roots = [
            Path(system_drive + "/Program Files") if system_drive else None,
            Path(system_drive + "/Program Files (x86)") if system_drive else None,
        ]
        for root in roots:
            if root is None:
                continue
            for prefix in (root / "Git", root / "Programs/Git"):
                candidates.extend(
                    prefix / relative
                    for relative in (
                        "cmd/git.exe",
                        "bin/git.exe",
                        "mingw64/bin/git.exe",
                        "usr/bin/git.exe",
                    )
                )
        if system_drive:
            candidates.extend(
                Path(system_drive + "/Git") / relative
                for relative in (
                    "cmd/git.exe",
                    "bin/git.exe",
                    "mingw64/bin/git.exe",
                    "usr/bin/git.exe",
                )
            )
    else:
        candidates.extend((Path("/usr/bin/git"), Path("/usr/local/bin/git")))
    for command in ("git", "git.exe"):
        discovered = shutil.which(command)
        if discovered:
            candidates.append(Path(discovered))
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        absolute = absolute_lexical(candidate)
        key = os.path.normcase(os.fspath(absolute))
        if key not in seen:
            seen.add(key)
            unique.append(absolute)
    return unique


def trusted_git_executable(explicit: Path | None = None) -> Path:
    global _GIT_EXECUTABLE
    if explicit is None and _GIT_EXECUTABLE is not None:
        selected = _GIT_EXECUTABLE
    else:
        if explicit is not None and not explicit.is_absolute():
            raise FreezeError("Git executable must be an absolute regular file", "git")
        candidates = [explicit] if explicit is not None else git_candidates()
        selected = None
        for candidate in candidates:
            if candidate is None or not candidate.is_absolute():
                continue
            try:
                inspected = inspect_path_components(candidate, "Git executable")
                file_stat = inspected.lstat()
            except FreezeError:
                if explicit is not None:
                    raise
                continue
            if not stat.S_ISREG(file_stat.st_mode):
                if explicit is not None:
                    raise FreezeError("Git executable is not a regular file", "git")
                continue
            selected = inspected
            break
        if selected is None:
            if explicit is not None:
                raise FreezeError("Git executable must be an absolute regular file", "git")
            raise FreezeError("trusted Git executable cannot be located", "git")
    try:
        inspected = inspect_path_components(selected, "Git executable")
        file_stat = inspected.lstat()
    except OSError as exc:
        raise FreezeError("Git executable cannot be inspected", "git") from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise FreezeError("Git executable is not a regular file", "git")
    _GIT_EXECUTABLE = inspected
    return inspected


def git_executable_identity(executable: Path) -> tuple[int, int, int, str]:
    inspected = inspect_path_components(executable, "Git executable")
    try:
        file_stat = inspected.lstat()
        if not stat.S_ISREG(file_stat.st_mode):
            raise FreezeError("Git executable is not a regular file", "git")
        digest = hashlib.sha256()
        with inspected.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        after_stat = inspected.lstat()
    except FreezeError:
        raise
    except OSError as exc:
        raise FreezeError("Git executable cannot be inspected", "git") from exc
    if (
        not stat.S_ISREG(after_stat.st_mode)
        or (file_stat.st_dev, file_stat.st_ino, file_stat.st_size)
        != (after_stat.st_dev, after_stat.st_ino, after_stat.st_size)
    ):
        raise FreezeError("Git executable changed while inspected", "git")
    return (
        file_stat.st_dev,
        file_stat.st_ino,
        file_stat.st_size,
        digest.hexdigest(),
    )


def git_environment() -> dict[str, str]:
    blocked = {
        "BASH_ENV",
        "CDPATH",
        "ENV",
        "HOME",
        "IFS",
        "LD_AUDIT",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "LOCALAPPDATA",
        "PYTHONHOME",
        "PYTHONPATH",
        "SHELLOPTS",
        "XDG_CONFIG_HOME",
    }
    blocked_prefixes = (
        "DYLD_",
        "GIT_",
    )
    env = {
        name: value
        for name, value in os.environ.items()
        if name.upper() not in blocked
        and not name.upper().startswith(blocked_prefixes)
    }
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
    )
    return env


def run_git_process(
    command: list[str],
    args: tuple[str, ...],
    *,
    stdin: bytes | None = None,
) -> bytes:
    operation = args[0] if args else "command"
    executable = Path(command[0])
    before_identity = git_executable_identity(executable)
    if (
        _GIT_EXECUTABLE_IDENTITY is not None
        and before_identity != _GIT_EXECUTABLE_IDENTITY
    ):
        raise FreezeError("Git executable changed after validation", "git")

    process: subprocess.Popen[bytes] | None = None
    overflow: dict[str, str | None] = {"stream": None}
    stream_failure: list[BaseException] = []
    outputs: dict[str, bytearray] = {
        "stdout": bytearray(),
        "stderr": bytearray(),
    }
    output_lock = threading.Lock()
    termination_lock = threading.Lock()
    termination_attempted = False
    total_output_bytes = 0
    primary_error: BaseException | None = None

    def record_stream_failure(exc: BaseException) -> None:
        with output_lock:
            stream_failure.append(exc)

    def terminate_process_tree() -> None:
        nonlocal termination_attempted
        if process is None:
            return
        with termination_lock:
            if termination_attempted:
                return
            termination_attempted = True
            pid = getattr(process, "pid", None)
            if os.name == "nt" and isinstance(pid, int) and pid > 0:
                try:
                    system_root = os.environ.get("SystemRoot", r"C:\Windows")
                    taskkill = inspect_path_components(
                        Path(system_root) / "System32" / "taskkill.exe",
                        "taskkill executable",
                    )
                    killer: subprocess.Popen[bytes] | None = None
                    try:
                        killer = subprocess.Popen(
                            [str(taskkill), "/PID", str(pid), "/T", "/F"],
                            env=git_environment(),
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        killer.wait(timeout=GIT_TIMEOUT_SECONDS)
                    except (OSError, subprocess.SubprocessError) as exc:
                        record_stream_failure(exc)
                        if killer is not None:
                            try:
                                killer.kill()
                                killer.wait(timeout=GIT_TIMEOUT_SECONDS)
                            except (OSError, subprocess.SubprocessError) as reap_exc:
                                record_stream_failure(reap_exc)
                    if killer is not None and killer.returncode == 0:
                        return
                except (FreezeError, OSError) as exc:
                    record_stream_failure(exc)
            elif os.name != "nt" and isinstance(pid, int) and pid > 0:
                try:
                    os.killpg(pid, signal.SIGKILL)
                    return
                except OSError as exc:
                    record_stream_failure(exc)
            try:
                process.kill()
            except OSError as exc:
                record_stream_failure(exc)

    def collect(stream_name: str, stream) -> None:
        nonlocal total_output_bytes
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    return
                exceeded = False
                with output_lock:
                    if total_output_bytes + len(chunk) > MAX_GIT_OUTPUT_BYTES:
                        if overflow["stream"] is None:
                            overflow["stream"] = stream_name
                        exceeded = True
                    else:
                        outputs[stream_name].extend(chunk)
                        total_output_bytes += len(chunk)
                if exceeded:
                    terminate_process_tree()
                    return
        except (OSError, ValueError) as exc:
            record_stream_failure(exc)
            terminate_process_tree()
        finally:
            try:
                stream.close()
            except (OSError, ValueError):
                pass

    def close_streams() -> None:
        if process is None:
            return
        for stream in (
            getattr(process, "stdin", None),
            getattr(process, "stdout", None),
            getattr(process, "stderr", None),
        ):
            if stream is not None:
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass

    def join_readers(readers: list[threading.Thread]) -> bool:
        for reader in readers:
            reader.join(timeout=GIT_TIMEOUT_SECONDS)
        return not any(reader.is_alive() for reader in readers)

    def stop_and_reap() -> None:
        assert process is not None
        terminate_process_tree()
        try:
            process.wait(timeout=GIT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise FreezeError(
                f"Git operation could not be reaped: {operation}",
                "git",
            ) from exc

    creationflags = (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if os.name == "nt"
        else 0
    )
    start_new_session = os.name != "nt"
    readers: list[threading.Thread] = []
    try:
        process = subprocess.Popen(
            command,
            env=git_environment(),
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            start_new_session=start_new_session,
        )
        assert process.stdout is not None
        assert process.stderr is not None
        if stdin is not None:
            assert process.stdin is not None
            try:
                process.stdin.write(stdin)
                process.stdin.close()
            except OSError as exc:
                terminate_process_tree()
                raise FreezeError(
                    f"Git input stream failed: {operation}",
                    "git",
                ) from exc
        readers = [
            threading.Thread(
                target=collect,
                args=("stdout", process.stdout),
                daemon=False,
            ),
            threading.Thread(
                target=collect,
                args=("stderr", process.stderr),
                daemon=False,
            ),
        ]
        for reader in readers:
            reader.start()
        try:
            return_code = process.wait(timeout=GIT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            stop_and_reap()
            close_streams()
            join_readers(readers)
            raise FreezeError(
                f"Git operation timed out: {operation}",
                "git",
            ) from exc

        if not join_readers(readers):
            terminate_process_tree()
            close_streams()
            if not join_readers(readers):
                raise FreezeError(
                    f"Git output stream did not close: {operation}",
                    "git",
                )
        if stream_failure:
            raise FreezeError(
                f"Git output stream failed: {operation}",
                "git",
            ) from stream_failure[0]
        if overflow["stream"] is not None:
            raise FreezeError(
                f"Git output exceeds safety limit: {operation}",
                "git",
            )
        after_identity = git_executable_identity(executable)
        if before_identity != after_identity:
            raise FreezeError("Git executable changed while running", "git")
        if return_code != 0:
            raise FreezeError(f"Git operation failed: {operation}", "git")
        return bytes(outputs["stdout"])
    except FreezeError as exc:
        primary_error = exc
        raise
    except (FileNotFoundError, PermissionError, OSError) as exc:
        wrapped = FreezeError("Git executable cannot be run", "git")
        primary_error = wrapped
        raise wrapped from exc
    finally:
        cleanup_error: FreezeError | None = None
        if process is not None and process.returncode is None:
            try:
                stop_and_reap()
            except FreezeError as exc:
                cleanup_error = exc
        close_streams()
        if not join_readers(readers) and cleanup_error is None:
            cleanup_error = FreezeError(
                f"Git output stream did not close: {operation}",
                "git",
            )
        if cleanup_error is not None and primary_error is None:
            raise cleanup_error


def validate_git_capability(executable: Path | None = None) -> Path:
    global _GIT_CAPABILITY_CHECKED, _GIT_EXECUTABLE_IDENTITY
    selected = trusted_git_executable(executable)
    current_identity = git_executable_identity(selected)
    if (
        _GIT_CAPABILITY_CHECKED == selected
        and _GIT_EXECUTABLE_IDENTITY == current_identity
    ):
        return selected
    _GIT_CAPABILITY_CHECKED = None
    _GIT_EXECUTABLE_IDENTITY = None
    output = run_git_process(
        [str(selected), "--no-replace-objects", "--no-lazy-fetch", "--version"],
        ("--version",),
    )
    try:
        version_text = output.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise FreezeError("Git version is not ASCII", "git") from exc
    match = GIT_VERSION_RE.fullmatch(version_text)
    if match is None:
        raise FreezeError("Git version output is malformed", "git")
    version = tuple(int(part) for part in match.groups())
    if version < (2, 45, 0):
        raise FreezeError("Git 2.45.0 or newer is required for no-lazy-fetch", "git")
    validated_identity = git_executable_identity(selected)
    if current_identity != validated_identity:
        raise FreezeError("Git executable changed during validation", "git")
    _GIT_EXECUTABLE_IDENTITY = validated_identity
    _GIT_CAPABILITY_CHECKED = selected
    return selected


def select_git_executable(explicit: Path | None = None) -> Path:
    """Select and validate one Git executable for all subsequent operations."""
    global _GIT_EXECUTABLE, _GIT_EXECUTABLE_IDENTITY, _GIT_CAPABILITY_CHECKED
    if explicit is not None:
        selected = trusted_git_executable(explicit)
        if _GIT_EXECUTABLE != selected:
            _GIT_CAPABILITY_CHECKED = None
            _GIT_EXECUTABLE_IDENTITY = None
        _GIT_EXECUTABLE = selected
        return validate_git_capability(selected)

    prior_error: FreezeError | None = None
    for candidate in git_candidates():
        try:
            selected = trusted_git_executable(candidate)
            _GIT_EXECUTABLE = selected
            _GIT_CAPABILITY_CHECKED = None
            _GIT_EXECUTABLE_IDENTITY = None
            return validate_git_capability(selected)
        except FreezeError as exc:
            prior_error = exc
            if _GIT_EXECUTABLE == candidate:
                _GIT_EXECUTABLE = None
            _GIT_CAPABILITY_CHECKED = None
            _GIT_EXECUTABLE_IDENTITY = None
    if prior_error is not None:
        raise FreezeError(
            f"trusted Git executable cannot be located: {prior_error}",
            "git",
        ) from prior_error
    raise FreezeError("trusted Git executable cannot be located", "git")


def git(
    *args: str,
    repo_root: Path = ROOT,
    executable: Path | None = None,
    stdin: bytes | None = None,
) -> bytes:
    selected = validate_git_capability(executable)
    command = [
        str(selected),
        "--no-replace-objects",
        "--no-lazy-fetch",
        "-C",
        str(repo_root),
        "-c",
        "core.quotepath=false",
        "-c",
        "core.fsmonitor=false",
        "--literal-pathspecs",
        *args,
    ]
    return run_git_process(command, args, stdin=stdin)


def validate_repo(repo_root: Path) -> Path:
    if not repo_root.is_absolute():
        raise FreezeError("repository path must be absolute", "repository")
    repo_root = inspect_path_components(repo_root, "repository path")
    try:
        repo_stat = repo_root.lstat()
    except OSError as exc:
        raise FreezeError(f"repository path cannot be inspected: {exc}") from exc
    if not stat.S_ISDIR(repo_stat.st_mode):
        raise FreezeError("repository path is not a directory")
    try:
        top_level_text = git(
            "rev-parse",
            "--show-toplevel",
            repo_root=repo_root,
        ).decode("utf-8").strip()
    except FreezeError as exc:
        raise FreezeError(f"repository cannot be read: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise FreezeError("repository top level is not UTF-8") from exc
    top_level = inspect_path_components(Path(top_level_text), "repository top level")
    if top_level != repo_root:
        raise FreezeError("repository path must be the exact worktree top level")
    try:
        object_format = git(
            "rev-parse",
            "--show-object-format",
            repo_root=repo_root,
        ).decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise FreezeError("repository object format is not ASCII") from exc
    if object_format != "sha1":
        raise FreezeError(f"unsupported repository object format: {object_format or '<empty>'}")
    try:
        shallow = git(
            "rev-parse",
            "--is-shallow-repository",
            repo_root=repo_root,
        ).decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise FreezeError("repository shallow status is not ASCII") from exc
    if shallow not in {"true", "false"}:
        raise FreezeError("repository shallow status is invalid")
    if shallow == "true":
        raise FreezeError("shallow repositories are not allowed")
    try:
        alternates_text = git(
            "rev-parse",
            "--git-path",
            "objects/info/alternates",
            repo_root=repo_root,
        ).decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise FreezeError("repository alternates path is not UTF-8") from exc
    alternates_path = Path(alternates_text)
    if not alternates_path.is_absolute():
        alternates_path = repo_root / alternates_path
    alternates_path = absolute_lexical(alternates_path)
    try:
        alternates_stat = alternates_path.lstat()
    except FileNotFoundError:
        alternates_stat = None
    except OSError as exc:
        raise FreezeError(f"repository alternates cannot be inspected: {exc}") from exc
    if alternates_stat is not None:
        inspect_path_components(alternates_path, "repository alternates path")
        if not stat.S_ISREG(alternates_stat.st_mode):
            raise FreezeError("repository object alternates must be a regular file")
        try:
            if alternates_path.read_bytes().strip():
                raise FreezeError("repository object alternates are not allowed")
        except OSError as exc:
            raise FreezeError(f"repository alternates cannot be inspected: {exc}") from exc
    return repo_root


def validate_commit(
    commit: str,
    repo_root: Path = ROOT,
) -> None:
    if COMMIT_RE.fullmatch(commit) is None:
        raise FreezeError(
            "commit must be a full lowercase 40-hex object ID"
        )
    try:
        object_type = git(
            "cat-file",
            "-t",
            commit,
            repo_root=repo_root,
        ).decode("ascii").strip()
    except FreezeError as exc:
        raise FreezeError(
            f"commit object cannot be read: {exc}"
        ) from exc
    except UnicodeDecodeError as exc:
        raise FreezeError("commit type is not ASCII") from exc
    if object_type != "commit":
        raise FreezeError(
            f"object is {object_type}, not commit"
        )


def validate_logical_path(path: str) -> str:
    if (
        not path
        or "\\" in path
        or path.startswith("/")
        or re.match(r"^[A-Za-z]:", path)
        or path.startswith(":")
        or any(char in path for char in "*?[")
    ):
        raise FreezeError(f"invalid logical path: {path!r}")
    raw_parts = path.split("/")
    parts = PurePosixPath(path).parts
    if (
        any(part in {"", ".", ".."} for part in raw_parts)
        or tuple(raw_parts) != parts
    ):
        raise FreezeError(f"invalid logical path: {path!r}")
    if any(unicodedata.category(char) == "Cc" for char in path):
        raise FreezeError(f"invalid logical path: {path!r}")
    return path


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise FreezeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_oracle_manifest(data: bytes) -> dict[str, object]:
    """Strictly parse canonical oracle-manifest bytes."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise FreezeError("oracle manifest must not contain a UTF-8 BOM")
    if b"\r" in data:
        raise FreezeError("oracle manifest must not contain carriage returns")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FreezeError("oracle manifest is not valid UTF-8") from exc
    try:
        parsed = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
    except (json.JSONDecodeError, FreezeError) as exc:
        if isinstance(exc, FreezeError):
            raise
        raise FreezeError("oracle manifest is not valid JSON") from exc
    manifest = validate_oracle_manifest(parsed)
    if canonical(manifest) != data:
        raise FreezeError("oracle manifest is not canonical sa-json-c14n-v1")
    return manifest


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise FreezeError(f"{label} must be a JSON object")
    return value


def _require_exact_keys(
    value: Mapping[str, object],
    expected: set[str],
    label: str,
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if unexpected:
            detail.append("unexpected " + ", ".join(unexpected))
        raise FreezeError(f"{label} has invalid keys: {'; '.join(detail)}")


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise FreezeError(f"{label} must be a non-empty string")
    return value


def _validate_path_list(
    value: object,
    label: str,
    *,
    exact: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise FreezeError(f"{label} must be a list of logical path strings")
    paths = tuple(validate_logical_path(item) for item in value)
    if len(paths) != len(set(paths)):
        raise FreezeError(f"{label} contains duplicate paths")
    if exact is not None and paths != exact:
        raise FreezeError(f"{label} does not match the supported exact path list")
    if exact is None and paths != tuple(sorted(paths, key=lambda item: item.encode("utf-8"))):
        raise FreezeError(f"{label} must be sorted by UTF-8 bytes")
    return paths


def expand_fixture_paths(fixture_expansion: object) -> tuple[str, ...]:
    """Validate and mechanically expand a manifest fixture declaration."""
    fixture = _require_object(fixture_expansion, "fixture_expansion")
    _require_exact_keys(fixture, {"graphs", "members", "root"}, "fixture_expansion")
    root = _require_string(fixture["root"], "fixture_expansion.root")
    if not root.endswith("/"):
        raise FreezeError("fixture_expansion.root must end with '/' ")
    validate_logical_path(root[:-1])
    graphs = _validate_path_list(fixture["graphs"], "fixture_expansion.graphs")
    members = _validate_path_list(fixture["members"], "fixture_expansion.members")
    if not graphs or not members:
        raise FreezeError("fixture expansion must contain graphs and members")
    for graph in graphs:
        if "/" in graph:
            raise FreezeError("fixture graph names must be single path segments")
    paths = tuple(
        sorted(
            (validate_logical_path(f"{root}{graph}/{member}") for graph in graphs for member in members),
            key=lambda item: item.encode("utf-8"),
        )
    )
    if len(paths) != len(set(paths)):
        raise FreezeError("fixture expansion produced duplicate paths")
    return paths


def _path_matches_forbidden_class(
    path: str,
    declaration: Mapping[str, object],
) -> bool:
    match = declaration["match"]
    values = declaration["values"]
    assert isinstance(match, str) and isinstance(values, list)
    folded_path = path.casefold()
    if match == "exact_path":
        return folded_path in {value.casefold() for value in values if isinstance(value, str)}
    if match == "path_segment":
        segments = {part.casefold() for part in PurePosixPath(path).parts}
        return any(isinstance(value, str) and value.casefold() in segments for value in values)
    if match == "substring":
        return any(isinstance(value, str) and value.casefold() in folded_path for value in values)
    raise FreezeError(f"unsupported forbidden ambient match type: {match!r}")


def _validate_forbidden_classes(value: object) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list) or not value:
        raise FreezeError("forbidden_ambient_path_classes must be a non-empty list")
    declarations: list[dict[str, object]] = []
    identifiers: set[str] = set()
    for index, raw in enumerate(value):
        item = _require_object(raw, f"forbidden_ambient_path_classes[{index}]")
        _require_exact_keys(item, {"id", "match", "values"}, "forbidden ambient class")
        identifier = _require_string(item["id"], "forbidden ambient class id")
        if identifier in identifiers:
            raise FreezeError("duplicate forbidden ambient class id")
        identifiers.add(identifier)
        match = _require_string(item["match"], "forbidden ambient class match")
        if match not in {"exact_path", "path_segment", "substring"}:
            raise FreezeError("unsupported forbidden ambient match type")
        values = item["values"]
        if not isinstance(values, list) or not values or not all(
            isinstance(entry, str) and entry for entry in values
        ):
            raise FreezeError("forbidden ambient class values must be non-empty strings")
        if len(values) != len(set(values)) or values != sorted(values, key=lambda entry: entry.encode("utf-8")):
            raise FreezeError("forbidden ambient class values must be unique and UTF-8 sorted")
        if match == "exact_path":
            for entry in values:
                validate_logical_path(entry)
        elif match == "path_segment" and any("/" in entry or "\\" in entry for entry in values):
            raise FreezeError("forbidden path segments must be single segments")
        declarations.append(item)
    return tuple(declarations)


def validate_oracle_manifest(manifest: object) -> dict[str, object]:
    """Validate the supported closed manifest schema without reading the worktree."""
    result = _require_object(manifest, "oracle manifest")
    _require_exact_keys(
        result,
        {
            "canonicalization_id",
            "closure_version",
            "declared_templates",
            "fixture_expansion",
            "forbidden_ambient_path_classes",
            "format",
            "gating",
            "historical_replay",
            "purpose",
        },
        "oracle manifest",
    )
    if result["canonicalization_id"] != CANON:
        raise FreezeError("unsupported oracle manifest canonicalization_id")
    if result["format"] != ORACLE_MANIFEST_FORMAT:
        raise FreezeError("unsupported oracle manifest format")
    if result["closure_version"] != SUPPORTED_CLOSURE_VERSION:
        raise FreezeError("unsupported prerequisite closure version")
    if result["purpose"] != "S1_PREREQUISITE_ORACLE_ONLY_NOT_AUTHORIZATION":
        raise FreezeError("unsupported oracle manifest purpose")
    _validate_path_list(
        result["declared_templates"],
        "declared_templates",
        exact=DECLARED_TEMPLATE_PATHS,
    )
    expand_fixture_paths(result["fixture_expansion"])
    forbidden = _validate_forbidden_classes(result["forbidden_ambient_path_classes"])

    gating = _require_object(result["gating"], "gating")
    _require_exact_keys(
        gating,
        {
            "allowed_subprocesses",
            "default_mode",
            "entrypoint",
            "static_reads",
            "support_modules",
            "temporary_directory_allowances",
        },
        "gating",
    )
    if gating["default_mode"] != "gating-only":
        raise FreezeError("gating.default_mode must be 'gating-only'")
    if gating["entrypoint"] != "tools/m8_test_s1_prerequisites_v3.py":
        raise FreezeError("unsupported gating entrypoint")
    validate_logical_path(_require_string(gating["entrypoint"], "gating.entrypoint"))
    _validate_path_list(gating["static_reads"], "gating.static_reads")
    support_modules = _validate_path_list(gating["support_modules"], "gating.support_modules")
    if HISTORICAL_REPLAY_ENTRYPOINT not in support_modules:
        raise FreezeError("historical replay entrypoint must be bound as a support module")
    missing_process_support = sorted(
        set(PROCESS_CONTROL_SUPPORT_MODULES) - set(support_modules)
    )
    if missing_process_support:
        raise FreezeError(
            "manifest omits a process-control support module: "
            + missing_process_support[0]
        )

    subprocesses = gating["allowed_subprocesses"]
    if not isinstance(subprocesses, list) or not subprocesses:
        raise FreezeError("gating.allowed_subprocesses must be a non-empty list")
    subprocess_paths: list[str] = []
    for index, raw in enumerate(subprocesses):
        item = _require_object(raw, f"gating.allowed_subprocesses[{index}]")
        _require_exact_keys(
            item,
            {"path", "role", "success_oracle"},
            "allowed subprocess",
        )
        path = validate_logical_path(
            _require_string(item["path"], "allowed subprocess path")
        )
        if item["role"] != "bounded-test":
            raise FreezeError("unsupported allowed subprocess role")
        oracle = _require_object(
            item["success_oracle"],
            "allowed subprocess success_oracle",
        )
        kind = oracle.get("kind")
        if kind == "exact-line":
            _require_exact_keys(
                oracle,
                {"kind", "success_line"},
                "exact-line success oracle",
            )
        elif kind == "unittest":
            _require_exact_keys(
                oracle,
                {"expected_test_count", "kind", "success_line"},
                "unittest success oracle",
            )
            count = oracle["expected_test_count"]
            if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
                raise FreezeError(
                    "unittest expected_test_count must be a positive integer"
                )
        else:
            raise FreezeError("unsupported allowed subprocess success oracle")
        success_line = _require_string(
            oracle["success_line"],
            "allowed subprocess success line",
        )
        if not success_line or "\n" in success_line or "\r" in success_line:
            raise FreezeError(
                "allowed subprocess success line must be one non-empty line"
            )
        subprocess_paths.append(path)
    if len(subprocess_paths) != len(set(subprocess_paths)):
        raise FreezeError("gating.allowed_subprocesses contains duplicate paths")
    if subprocess_paths != sorted(subprocess_paths, key=lambda item: item.encode("utf-8")):
        raise FreezeError("gating.allowed_subprocesses must be sorted by UTF-8 path bytes")
    if subprocesses != list(ALLOWED_GATING_SUBPROCESSES):
        raise FreezeError(
            "gating.allowed_subprocesses does not match the code-fixed exact map"
        )
    if HISTORICAL_REPLAY_ENTRYPOINT in subprocess_paths:
        raise FreezeError("historical replay entrypoint must not be a gating subprocess")

    allowances = gating["temporary_directory_allowances"]
    if not isinstance(allowances, list) or not allowances:
        raise FreezeError("temporary_directory_allowances must be a non-empty list")
    allowance_ids: set[str] = set()
    for index, raw in enumerate(allowances):
        item = _require_object(raw, f"temporary_directory_allowances[{index}]")
        _require_exact_keys(
            item,
            {"id", "location_class", "repository_write", "scope"},
            "temporary directory allowance",
        )
        identifier = _require_string(item["id"], "temporary allowance id")
        if identifier in allowance_ids:
            raise FreezeError("duplicate temporary directory allowance id")
        allowance_ids.add(identifier)
        _require_string(item["location_class"], "temporary allowance location_class")
        _require_string(item["scope"], "temporary allowance scope")
        if item["repository_write"] is not False:
            raise FreezeError("temporary directory allowances must forbid repository writes")

    historical = _require_object(result["historical_replay"], "historical_replay")
    _require_exact_keys(
        historical,
        {"entrypoint", "gating", "mode", "objects", "runtime_oracles"},
        "historical_replay",
    )
    if historical["gating"] is not False:
        raise FreezeError("historical replay must be non-gating")
    if historical["mode"] != "explicit-commit-bound-only":
        raise FreezeError("unsupported historical replay mode")
    if historical["entrypoint"] != HISTORICAL_REPLAY_ENTRYPOINT:
        raise FreezeError("unsupported historical replay entrypoint")
    _validate_path_list(
        historical["objects"],
        "historical_replay.objects",
        exact=HISTORICAL_REPLAY_OBJECTS,
    )
    runtime_oracles = historical["runtime_oracles"]
    if not isinstance(runtime_oracles, list) or len(runtime_oracles) != len(HISTORICAL_RUNTIME_ORACLES):
        raise FreezeError("historical replay must declare exactly two runtime oracles")
    actual_oracles: list[tuple[str, int]] = []
    for index, raw in enumerate(runtime_oracles):
        item = _require_object(raw, f"historical runtime oracle {index}")
        _require_exact_keys(item, {"expected_passed", "path"}, "historical runtime oracle")
        path = validate_logical_path(_require_string(item["path"], "historical runtime oracle path"))
        count = item["expected_passed"]
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise FreezeError("historical runtime expected_passed must be a positive integer")
        actual_oracles.append((path, count))
    if tuple(actual_oracles) != HISTORICAL_RUNTIME_ORACLES:
        raise FreezeError("historical runtime oracles do not match the supported exact values")

    explicitly_declared = {
        _require_string(gating["entrypoint"], "gating.entrypoint"),
        *_validate_path_list(gating["static_reads"], "gating.static_reads"),
        *support_modules,
        *subprocess_paths,
    }
    missing_bootstrap = sorted(set[str](CODE_FIXED_BOOTSTRAP_PATHS) - explicitly_declared)
    if missing_bootstrap:
        raise FreezeError("manifest omits code-fixed bootstrap path: " + missing_bootstrap[0])
    closure = derive_gating_closure(result, _validated=True)
    missing_bootstrap = sorted(set[str](CODE_FIXED_BOOTSTRAP_PATHS) - set(closure))
    if missing_bootstrap:
        raise FreezeError("manifest omits code-fixed bootstrap path: " + missing_bootstrap[0])
    for path in closure:
        if any(_path_matches_forbidden_class(path, item) for item in forbidden):
            raise FreezeError("forbidden ambient path entered gating closure: " + path)
        guarded = f"/{path.casefold()}"
        if any(part in guarded for part in FORBIDDEN_INVENTORY_PARTS):
            raise FreezeError("code-fixed forbidden ambient path entered gating closure: " + path)
    return result


def derive_gating_closure(
    manifest: dict[str, object],
    *,
    _validated: bool = False,
) -> tuple[str, ...]:
    """Derive the unique UTF-8-sorted candidate gating closure."""
    if not _validated:
        manifest = validate_oracle_manifest(manifest)
    gating = _require_object(manifest["gating"], "gating")
    subprocesses = gating["allowed_subprocesses"]
    assert isinstance(subprocesses, list)
    declared = [
        *CODE_FIXED_BOOTSTRAP_PATHS,
        _require_string(gating["entrypoint"], "gating.entrypoint"),
        *_validate_path_list(gating["static_reads"], "gating.static_reads"),
        *_validate_path_list(gating["support_modules"], "gating.support_modules"),
        *_validate_path_list(
            manifest["declared_templates"],
            "declared_templates",
            exact=DECLARED_TEMPLATE_PATHS,
        ),
        *expand_fixture_paths(manifest["fixture_expansion"]),
    ]
    for item in subprocesses:
        assert isinstance(item, dict)
        declared.append(validate_logical_path(_require_string(item["path"], "allowed subprocess path")))
    return tuple(sorted(set(declared), key=lambda item: item.encode("utf-8")))


def derive_closure_digest(frozen_files: Sequence[Mapping[str, object]]) -> str:
    """Hash canonical ordered per-file closure facts."""
    facts: list[dict[str, object]] = []
    previous: bytes | None = None
    for raw in frozen_files:
        item = dict(raw)
        _require_exact_keys(
            item,
            {"byte_count", "git_blob_oid", "git_mode", "lf_count", "path", "sha256"},
            "frozen file fact",
        )
        path = validate_logical_path(_require_string(item["path"], "frozen file path"))
        encoded = path.encode("utf-8")
        if previous is not None and encoded <= previous:
            raise FreezeError("frozen file facts must have unique UTF-8-sorted paths")
        previous = encoded
        facts.append(item)
    return hashlib.sha256(canonical(facts)).hexdigest()


def load_oracle_manifest(
    commit: str,
    repo_root: Path = ROOT,
) -> tuple[dict[str, object], dict[str, object]]:
    """Load and summarize the canonical manifest blob at an exact commit."""
    mode, oid, data = read_blob(commit, ORACLE_MANIFEST_PATH, repo_root)
    manifest = parse_oracle_manifest(data)
    return manifest, summarize(ORACLE_MANIFEST_PATH, mode, oid, data)


def tree_entries(
    commit: str,
    prefix: str,
    repo_root: Path = ROOT,
) -> list[tuple[str, str, str, str]]:
    validate_logical_path(prefix)
    raw = git(
        "ls-tree",
        "-rz",
        "-r",
        commit,
        "--",
        prefix,
        repo_root=repo_root,
    )
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path_bytes = record.split(b"\t", 1)
            mode, object_type, oid = metadata.decode("ascii").split()
            path = path_bytes.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise FreezeError("malformed git ls-tree output") from exc
        if OID_RE.fullmatch(oid) is None:
            raise FreezeError("malformed git object ID")
        entries.append(
            (
                validate_logical_path(path),
                mode,
                object_type,
                oid,
            )
        )
    return entries


def read_blob(
    commit: str,
    path: str,
    repo_root: Path = ROOT,
) -> tuple[str, str, bytes]:
    path = validate_logical_path(path)
    raw = git(
        "ls-tree",
        "-z",
        commit,
        "--",
        path,
        repo_root=repo_root,
    )
    records = [record for record in raw.split(b"\0") if record]
    if len(records) != 1:
        raise FreezeError(f"missing path at commit: {path}")
    try:
        metadata, path_bytes = records[0].split(b"\t", 1)
        mode, object_type, oid = metadata.decode("ascii").split()
        actual_path = path_bytes.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise FreezeError("malformed git ls-tree output") from exc
    if actual_path != path:
        raise FreezeError(f"missing path at commit: {path}")
    if OID_RE.fullmatch(oid) is None:
        raise FreezeError("malformed git object ID")
    if object_type != "blob":
        raise FreezeError(f"path is {object_type}, not blob: {path}")
    if mode not in {"100644", "100755"}:
        raise FreezeError(f"path is not a regular file: {path}")
    data = git(
        "cat-file",
        "blob",
        oid,
        repo_root=repo_root,
    )
    if len(data) > MAX_FILE_BYTES:
        raise FreezeError(f"blob exceeds per-file safety limit: {path}")
    verify_blob_oid(path, oid, data)
    return mode, oid, data


def read_blob_batch(
    entries: list[tuple[str, str, str, str]],
    repo_root: Path = ROOT,
) -> dict[str, bytes]:
    """Read an exact blob inventory through one bounded Git object stream."""
    expected: dict[str, str] = {}
    request = bytearray()
    for path, mode, object_type, oid in entries:
        path = validate_logical_path(path)
        if path in expected:
            raise FreezeError(f"duplicate Git tree path: {path}")
        if OID_RE.fullmatch(oid) is None:
            raise FreezeError("malformed git object ID")
        if object_type != "blob":
            raise FreezeError(f"path is {object_type}, not blob: {path}")
        if mode not in {"100644", "100755"}:
            raise FreezeError(f"path is not a regular file: {path}")
        expected[path] = oid
        request.extend(oid.encode("ascii") + b"\n")

    raw = git(
        "cat-file",
        "--batch",
        stdin=bytes(request),
        repo_root=repo_root,
    )
    cursor = 0
    blobs: dict[str, bytes] = {}
    for path, _mode, _object_type, oid in entries:
        newline = raw.find(b"\n", cursor)
        if newline < 0:
            raise FreezeError("truncated git cat-file batch header")
        header = raw[cursor:newline]
        cursor = newline + 1
        try:
            actual_oid, object_type, size_text = header.decode("ascii").split()
            size = int(size_text)
        except (ValueError, UnicodeDecodeError) as exc:
            raise FreezeError("malformed git cat-file batch header") from exc
        if actual_oid != oid or object_type != "blob" or size < 0:
            raise FreezeError(f"unexpected git cat-file batch object: {path}")
        if size > MAX_FILE_BYTES:
            raise FreezeError(f"blob exceeds per-file safety limit: {path}")
        end = cursor + size
        if end >= len(raw) or raw[end:end + 1] != b"\n":
            raise FreezeError("truncated git cat-file batch body")
        data = raw[cursor:end]
        cursor = end + 1
        verify_blob_oid(path, oid, data)
        blobs[path] = data
    if cursor != len(raw):
        raise FreezeError("unexpected trailing git cat-file batch output")
    if set(blobs) != set(expected):
        raise FreezeError("Git blob batch inventory mismatch")
    return blobs


def verify_blob_oid(path: str, oid: str, data: bytes) -> None:
    header = f"blob {len(data)}\0".encode("ascii")
    actual_oid = hashlib.sha1(header + data).hexdigest()
    if actual_oid != oid:
        raise FreezeError(f"blob object ID mismatch: {path}")


def summarize(path: str, mode: str, oid: str, data: bytes) -> dict:
    return {
        "byte_count": len(data),
        "git_blob_oid": oid,
        "git_mode": mode,
        "lf_count": data.count(b"\n"),
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def build_freeze(
    commit: str,
    paths: list[str] | None = None,
    repo_root: Path = ROOT,
    *,
    git_executable: Path | None = None,
) -> dict:
    """Build a non-authorizing immutable record from target-commit declarations."""
    if git_executable is not None:
        select_git_executable(git_executable)
    repo_root = validate_repo(repo_root)
    validate_commit(commit, repo_root)
    if paths is not None:
        raise FreezeError("custom source inventory is not allowed")

    manifest, manifest_fact = load_oracle_manifest(commit, repo_root)
    closure = derive_gating_closure(manifest)
    candidate_entries = tree_entries(commit, ".gitattributes", repo_root)
    candidate_entries.extend(tree_entries(commit, "docs", repo_root))
    candidate_entries.extend(tree_entries(commit, "tools", repo_root))
    entry_by_path: dict[str, tuple[str, str, str, str]] = {}
    for entry in candidate_entries:
        path = entry[0]
        if path in entry_by_path:
            raise FreezeError("duplicate Git tree path: " + path)
        entry_by_path[path] = entry

    fixture_paths = expand_fixture_paths(manifest["fixture_expansion"])
    fixture = _require_object(manifest["fixture_expansion"], "fixture_expansion")
    fixture_root = _require_string(fixture["root"], "fixture_expansion.root")
    fixture_entries = [
        entry for entry in candidate_entries if entry[0].startswith(fixture_root)
    ]
    actual_fixture_paths = {path for path, _mode, _object_type, _oid in fixture_entries}
    expected_fixture_paths = set(fixture_paths)
    missing_fixture_paths = sorted(
        expected_fixture_paths - actual_fixture_paths,
        key=lambda path: path.encode("utf-8"),
    )
    unexpected_fixture_paths = sorted(
        actual_fixture_paths - expected_fixture_paths,
        key=lambda path: path.encode("utf-8"),
    )
    if missing_fixture_paths:
        raise FreezeError("fixture members are missing: " + ", ".join(missing_fixture_paths))
    if unexpected_fixture_paths:
        raise FreezeError("unexpected fixture members: " + ", ".join(unexpected_fixture_paths))

    missing_paths = [path for path in closure if path not in entry_by_path]
    if missing_paths:
        raise FreezeError("missing path at commit: " + missing_paths[0])
    selected_entries = [entry_by_path[path] for path in closure]
    blobs = read_blob_batch(selected_entries, repo_root)
    files: list[dict[str, object]] = []
    total_byte_count = 0
    for path, mode, _object_type, oid in selected_entries:
        data = blobs[path]
        total_byte_count += len(data)
        if total_byte_count > MAX_TOTAL_BYTES:
            raise FreezeError("candidate inventory exceeds total byte safety limit")
        files.append(summarize(path, mode, oid, data))
    files = sorted(files, key=lambda item: str(item["path"]).encode("utf-8"))

    gating = _require_object(manifest["gating"], "gating")
    historical = _require_object(manifest["historical_replay"], "historical_replay")
    templates = _validate_path_list(
        manifest["declared_templates"],
        "declared_templates",
        exact=DECLARED_TEMPLATE_PATHS,
    )
    return {
        "aggregate": {
            "closure_digest": derive_closure_digest(files),
            "file_count": len(files),
            "total_byte_count": total_byte_count,
        },
        "canonicalization_id": CANON,
        "closure_version": SUPPORTED_CLOSURE_VERSION,
        "declared_templates": list(templates),
        "fixture_expansion": {
            "file_count": len(fixture_paths),
            "graphs": list(_validate_path_list(fixture["graphs"], "fixture_expansion.graphs")),
            "members": list(_validate_path_list(fixture["members"], "fixture_expansion.members")),
            "root": fixture_root,
        },
        "format": FREEZE_FORMAT,
        "frozen_files": files,
        "gating": {
            "allowed_subprocesses": gating["allowed_subprocesses"],
            "default_mode": gating["default_mode"],
            "entrypoint": gating["entrypoint"],
            "static_reads": gating["static_reads"],
            "support_modules": gating["support_modules"],
            "temporary_directory_allowances": gating["temporary_directory_allowances"],
        },
        "historical_replay": {
            "entrypoint": historical["entrypoint"],
            "gating": False,
            "mode": historical["mode"],
            "object_count": len(HISTORICAL_REPLAY_OBJECTS),
            "runtime_oracles": historical["runtime_oracles"],
        },
        "manifest": manifest_fact,
        "purpose": "S1_PREREQUISITE_RECORD_ONLY_NOT_AUTHORIZATION",
        "source_commit": commit,
        "worktree_comparison": {
            "divergent_paths": [],
            "status": "NOT_REQUESTED",
        },
    }


def contained_inventory_path(
    root: Path,
    logical_path: str,
    *,
    allow_missing_leaf: bool = False,
) -> Path:
    root = inspect_path_components(root, "worktree root")
    candidate = inspect_path_components(
        root / validate_logical_path(logical_path),
        "worktree inventory path",
        allow_missing_leaf=allow_missing_leaf,
    )
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise FreezeError("worktree inventory path escapes repository") from exc
    return candidate


def read_bounded_worktree_file(path: Path, label: str) -> tuple[bytes, os.stat_result]:
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise FreezeError(f"worktree path is not a regular file: {label}")
        if before.st_size > MAX_FILE_BYTES:
            raise FreezeError(f"worktree file exceeds safety limit: {label}")
        data = bytearray()
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or (before.st_dev, before.st_ino)
                != (opened.st_dev, opened.st_ino)
            ):
                raise FreezeError(f"worktree path changed while opened: {label}")
            while True:
                chunk = handle.read(65536)
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > MAX_FILE_BYTES:
                    raise FreezeError(f"worktree file exceeds safety limit: {label}")
            after_read = os.fstat(handle.fileno())
        after = path.lstat()
    except FreezeError:
        raise
    except OSError as exc:
        raise FreezeError(
            f"worktree path cannot be inspected: {label}: {exc}"
        ) from exc
    identity = (before.st_dev, before.st_ino)
    stable_path_metadata = (
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) == (
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    stable_handle_metadata = (
        opened.st_size,
        opened.st_mtime_ns,
        opened.st_ctime_ns,
    ) == (
        after_read.st_size,
        after_read.st_mtime_ns,
        after_read.st_ctime_ns,
    )
    if (
        not stat.S_ISREG(after_read.st_mode)
        or not stat.S_ISREG(after.st_mode)
        or identity != (opened.st_dev, opened.st_ino)
        or identity != (after_read.st_dev, after_read.st_ino)
        or identity != (after.st_dev, after.st_ino)
        or before.st_size != len(data)
        or opened.st_size != len(data)
        or after_read.st_size != len(data)
        or after.st_size != len(data)
        or not stable_path_metadata
        or not stable_handle_metadata
    ):
        raise FreezeError(f"worktree path changed while inspected: {label}")
    return bytes(data), before


def compare_worktree(
    freeze: dict,
    root: Path = ROOT,
) -> list[str]:
    """Compare mutable worktree state without changing frozen Git-object facts."""
    divergent = []
    inventory = freeze["frozen_files"]
    total_byte_count = 0
    compare_modes = os.name != "nt"
    root = inspect_path_components(root, "worktree root")

    def repository_state() -> tuple[str, bytes]:
        try:
            head = git("rev-parse", "HEAD", repo_root=root).decode("ascii").strip()
            status_bytes = git(
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                repo_root=root,
            )
        except UnicodeDecodeError as exc:
            raise FreezeError("worktree HEAD is not ASCII") from exc
        return head, status_bytes

    before_head, before_status = repository_state()
    if before_head != freeze["source_commit"]:
        divergent.append("<repository-head>")
    if before_status:
        divergent.append("<repository-status>")
    for item in inventory:
        try:
            path = contained_inventory_path(root, item["path"], allow_missing_leaf=True)
            if not path.exists():
                divergent.append(item["path"])
                continue
            file_stat = path.lstat()
            if not stat.S_ISREG(file_stat.st_mode):
                divergent.append(item["path"])
                continue
            data, file_stat = read_bounded_worktree_file(path, item["path"])
            total_byte_count += len(data)
            if total_byte_count > MAX_TOTAL_BYTES:
                raise FreezeError("worktree inventory exceeds total byte safety limit")
            actual_executable = bool(file_stat.st_mode & stat.S_IXUSR)
        except FreezeError:
            raise
        except OSError as exc:
            raise FreezeError(
                f"worktree path cannot be inspected: {item['path']}: {exc}"
            ) from exc
        expected_executable = item["git_mode"] == "100755"
        if (
            hashlib.sha256(data).hexdigest() != item["sha256"]
            or (compare_modes and actual_executable != expected_executable)
        ):
            divergent.append(item["path"])
    after_head, after_status = repository_state()
    if after_head != before_head or after_status != before_status:
        raise FreezeError("repository state changed while comparing worktree")
    return sorted(set(divergent), key=lambda path: path.encode("utf-8"))


def prepare_output_path(output: Path, repo_root: Path, freeze: dict) -> Path:
    output = inspect_path_components(
        output,
        "output path",
        allow_missing_leaf=True,
    )
    parent = inspect_path_components(output.parent, "output parent")
    try:
        parent_stat = parent.lstat()
    except OSError as exc:
        raise FreezeError(f"output parent cannot be inspected: {exc}") from exc
    if not stat.S_ISDIR(parent_stat.st_mode):
        raise FreezeError("output parent directory must already exist")
    if output.exists():
        output_stat = output.lstat()
        if stat.S_ISLNK(output_stat.st_mode) or has_reparse_point(output_stat):
            raise FreezeError("output target must not be a symlink or reparse point")
        if not stat.S_ISREG(output_stat.st_mode):
            raise FreezeError("existing output target must be a regular file")
    inventory_paths = {
        contained_inventory_path(repo_root, item["path"])
        for item in freeze["frozen_files"]
    }
    if output in inventory_paths:
        raise FreezeError("output path overlaps frozen inventory")
    try:
        output.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise FreezeError("output path must be outside repository")
    return output


def publish_output(
    output: Path,
    data: bytes,
    *,
    replace_action=os.replace,
    temporary_factory=tempfile.NamedTemporaryFile,
) -> None:
    temporary = None
    try:
        output = inspect_path_components(
            output,
            "output path",
            allow_missing_leaf=True,
        )
        parent = inspect_path_components(output.parent, "output parent")
        parent_stat = parent.lstat()
        with temporary_factory(
            mode="wb",
            dir=parent,
            prefix=f".{output.name}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            written = handle.write(data)
            if written != len(data):
                raise OSError("short temporary output write")
            handle.flush()
            os.fsync(handle.fileno())
        inspect_path_components(temporary, "temporary output")
        current_parent = inspect_path_components(output.parent, "output parent")
        current_parent_stat = current_parent.lstat()
        if (
            current_parent != parent
            or (parent_stat.st_dev, parent_stat.st_ino)
            != (current_parent_stat.st_dev, current_parent_stat.st_ino)
        ):
            raise FreezeError("output parent changed while publishing")
        if temporary.parent != parent:
            raise FreezeError("temporary output escaped the inspected parent")
        if temporary.read_bytes() != data:
            raise OSError("temporary output verification failed")
        if output.exists():
            output_stat = output.lstat()
            if stat.S_ISLNK(output_stat.st_mode) or has_reparse_point(output_stat):
                raise FreezeError("output target changed to a symlink or reparse point")
            if not stat.S_ISREG(output_stat.st_mode):
                raise FreezeError("output target changed to a non-regular file")
        replace_action(temporary, output)
        temporary = None
        if output.read_bytes() != data:
            raise OSError("published output verification failed")
        if os.name != "nt":
            directory_fd = os.open(output.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def main() -> int:
    parser = ControlledArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="absolute repository whose Git objects and worktree are inspected",
    )
    parser.add_argument(
        "--git-executable",
        type=Path,
        help="absolute trusted Git executable; official layouts are auto-detected if omitted",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--compare-worktree",
        action="store_true",
    )
    try:
        args = parser.parse_args()
        if not args.repo.is_absolute():
            raise FreezeError("repository path must be absolute", "repository")
        if args.git_executable is not None and not args.git_executable.is_absolute():
            raise FreezeError("Git executable path must be absolute", "git")
        select_git_executable(args.git_executable)
        repo_root = validate_repo(args.repo)
        freeze = build_freeze(args.commit, repo_root=repo_root)
        divergent = compare_worktree(freeze, repo_root) if args.compare_worktree else []
        if args.compare_worktree:
            freeze["worktree_comparison"] = {
                "divergent_paths": divergent,
                "status": "MATCH" if not divergent else "DIVERGENT",
            }
        data = canonical(freeze)
        output = (
            prepare_output_path(args.output, repo_root, freeze)
            if args.output is not None
            else None
        )
        if divergent:
            if output is None:
                written = sys.stdout.buffer.write(data)
                if written != len(data):
                    raise OSError("short stdout write")
                sys.stdout.buffer.flush()
            return 3
        if output is not None:
            publish_output(output, data)
        else:
            written = sys.stdout.buffer.write(data)
            if written != len(data):
                raise OSError("short stdout write")
            sys.stdout.buffer.flush()
        return 0
    except FreezeError as exc:
        print(f"ERROR {exc.category}: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR io: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

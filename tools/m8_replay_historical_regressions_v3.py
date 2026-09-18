#!/usr/bin/env python3
"""Replay the two frozen draft-0.9 historical validators from Git objects."""
from __future__ import annotations

import argparse
import ast
import ctypes
import hashlib
import os
import signal
import stat
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import NoReturn

TOOLS = Path(__file__).resolve().parent
if os.fspath(TOOLS) not in sys.path:
    sys.path.insert(0, os.fspath(TOOLS))

from m8_freeze_s1_prerequisites_v3 import (
    FreezeError,
    canonical,
    inspect_path_components,
    read_blob_batch,
    select_git_executable,
    tree_entries,
    validate_commit,
    validate_repo,
)

FORMAT = "m8-v3-historical-regression-replay-v1"
PURPOSE = "HISTORICAL_REGRESSION_REPLAY_ONLY_NOT_AUTHORIZATION"
PROCESS_TIMEOUT_SECONDS = 20
MAX_PROCESS_OUTPUT_BYTES = 2 * 1024 * 1024
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
VALIDATORS = (
    ("tools/m8_validate_p1_materials.py", 88),
    ("tools/m8_validate_p0_r02.py", 77),
)
INVENTORY_PATHS = (
    "docs/plans/references/external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json",
    "docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json",
    "docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json",
    "docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json",
    "docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json",
    "docs/plans/references/m8-active-execution-protocol-draft-0.9.md",
    "tools/m8_validate_p0_r02.py",
    "tools/m8_validate_p1_materials.py",
)
EXPECTED_PATHS = tuple(sorted(INVENTORY_PATHS, key=lambda value: value.encode("utf-8")))


class ControlledArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise FreezeError(message, "cli")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitized_environment() -> dict[str, str]:
    """Return the minimal deterministic environment supplied to validators."""
    env: dict[str, str] = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    for name in ("COMSPEC", "PATHEXT", "SYSTEMROOT", "WINDIR"):
        value = os.environ.get(name)
        if value:
            env[name] = value
    if os.name != "nt":
        env["LANG"] = "C.UTF-8"
        env["LC_ALL"] = "C.UTF-8"
    return env



if os.name == "nt":
    from ctypes import wintypes

    class _JobObjectBasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]


    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]


    class _JobObjectExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JobObjectBasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]


def _create_kill_on_close_job() -> int | None:
    """Create a Windows job whose entire process tree dies when closed."""
    if os.name != "nt":
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise FreezeError("validator job object cannot be created", "process")
    information = _JobObjectExtendedLimitInformation()
    information.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        handle,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(information),
        ctypes.sizeof(information),
    ):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(handle)
        raise FreezeError(
            f"validator job object cannot be configured: winerror {error}",
            "process",
        )
    return int(handle)


def _assign_process_to_job(process: subprocess.Popen[bytes], job: int | None) -> None:
    """Assign one Windows process before it can create untracked descendants."""
    if job is None:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    process_handle = wintypes.HANDLE(int(getattr(process, "_handle")))
    if not kernel32.AssignProcessToJobObject(wintypes.HANDLE(job), process_handle):
        error = ctypes.get_last_error()
        raise FreezeError(
            f"validator process cannot be assigned to job: winerror {error}",
            "process",
        )


def _close_job(job: int | None) -> None:
    if job is None:
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle(wintypes.HANDLE(job))

def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Terminate the process group even when its original leader exited."""
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        taskkill = Path(system_root) / "System32" / "taskkill.exe"
        try:
            subprocess.run(
                [str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                env=sanitized_environment(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass


def run_bounded_process(
    command: list[str],
    cwd: Path,
    *,
    allowed_python_script: Path | None = None,
    allowed_isolated_code: str | None = None,
    environment: dict[str, str] | None = None,
    timeout_seconds: int = PROCESS_TIMEOUT_SECONDS,
) -> tuple[int, bytes, bytes]:
    """Run one process with an explicitly authorized Python destination."""
    if (allowed_python_script is None) == (allowed_isolated_code is None):
        raise FreezeError(
            "exactly one bounded process destination is required",
            "process",
        )
    if allowed_python_script is not None:
        expected = [sys.executable, "-I", str(allowed_python_script)]
    else:
        assert allowed_isolated_code is not None
        expected = [sys.executable, "-I", "-c", allowed_isolated_code]
    if command != expected:
        raise FreezeError("bounded process destination mismatch", "process")
    job = _create_kill_on_close_job()
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=sanitized_environment() if environment is None else environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                if os.name == "nt"
                else 0
            ),
            start_new_session=os.name != "nt",
        )
        _assign_process_to_job(process, job)
    except BaseException:
        if process is not None:
            _terminate_process_tree(process)
        _close_job(job)
        raise
    assert process.stdout is not None
    assert process.stderr is not None
    outputs = {"stdout": bytearray(), "stderr": bytearray()}
    lock = threading.Lock()
    failures: list[BaseException] = []
    overflow = [False]
    total = [0]

    def collect(name: str, stream) -> None:
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    return
                with lock:
                    if total[0] + len(chunk) > MAX_PROCESS_OUTPUT_BYTES:
                        overflow[0] = True
                    else:
                        outputs[name].extend(chunk)
                        total[0] += len(chunk)
                if overflow[0]:
                    _terminate_process_tree(process)
                    return
        except (OSError, ValueError) as exc:
            with lock:
                failures.append(exc)
            _terminate_process_tree(process)
        finally:
            try:
                stream.close()
            except (OSError, ValueError):
                pass

    readers = [
        threading.Thread(
            target=collect,
            args=("stdout", process.stdout),
            daemon=True,
        ),
        threading.Thread(
            target=collect,
            args=("stderr", process.stderr),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()
    try:
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            _terminate_process_tree(process)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired as reap_exc:
                raise FreezeError(
                    "validator process could not be reaped",
                    "process",
                ) from reap_exc
            raise FreezeError("validator process timed out", "process") from exc
        for reader in readers:
            reader.join(timeout=1)
        if any(reader.is_alive() for reader in readers):
            _close_job(job)
            job = None
            _terminate_process_tree(process)
            for stream in (process.stdout, process.stderr):
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
            for reader in readers:
                reader.join(timeout=1)
            if any(reader.is_alive() for reader in readers):
                raise FreezeError(
                    "validator output stream did not close",
                    "process",
                )
        if failures:
            raise FreezeError(
                "validator output stream failed",
                "process",
            ) from failures[0]
        if overflow[0]:
            raise FreezeError(
                "validator output exceeds safety limit",
                "process",
            )
        return return_code, bytes(outputs["stdout"]), bytes(outputs["stderr"])
    finally:
        _terminate_process_tree(process)
        _close_job(job)
        if process.poll() is None:
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except (OSError, ValueError):
                pass
        for reader in readers:
            reader.join(timeout=1)


def normalize_process_output(data: bytes) -> bytes:
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise FreezeError("validator output contains a bare carriage return", "process")
    try:
        normalized.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FreezeError("validator output is not UTF-8", "process") from exc
    return normalized


def load_inventory(commit: str, repo_root: Path) -> tuple[list[dict[str, object]], dict[str, bytes]]:
    """Load and verify the exact eight-path inventory from one commit tree."""
    validate_commit(commit, repo_root=repo_root)
    entries: list[tuple[str, str, str, str]] = []
    for path in EXPECTED_PATHS:
        matches = tree_entries(commit, path, repo_root=repo_root)
        exact = [entry for entry in matches if entry[0] == path]
        if len(matches) != 1 or len(exact) != 1:
            raise FreezeError(f"expected exactly one Git object for inventory path: {path}")
        entry = exact[0]
        if entry[1] != "100644" or entry[2] != "blob":
            raise FreezeError(f"inventory path is not a non-executable regular blob: {path}")
        entries.append(entry)
    if tuple(entry[0] for entry in entries) != EXPECTED_PATHS:
        raise FreezeError("Git object inventory does not match the exact eight paths")
    blobs = read_blob_batch(entries, repo_root=repo_root)
    inventory: list[dict[str, object]] = []
    for path, mode, _object_type, oid in entries:
        data = blobs[path]
        inventory.append(
            {
                "byte_count": len(data),
                "git_blob_oid": oid,
                "git_mode": mode,
                "path": path,
                "sha256": sha256_hex(data),
            }
        )
    return inventory, blobs


def _line_byte_offsets(source: bytes) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def bind_copied_repository(source: bytes, repository_root: Path, logical_path: str) -> bytes:
    """Replace only the Path string in the sole expected top-level REPO assignment."""
    if source.startswith(b"\xef\xbb\xbf"):
        raise FreezeError(f"validator source has a UTF-8 BOM: {logical_path}")
    try:
        text = source.decode("utf-8")
        module = ast.parse(text, filename=logical_path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise FreezeError(f"validator source cannot be parsed: {logical_path}") from exc
    candidates: list[ast.Assign] = []
    for statement in module.body:
        if not isinstance(statement, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "REPO" for target in statement.targets):
            candidates.append(statement)
    if len(candidates) != 1:
        raise FreezeError(
            f"validator must contain exactly one top-level REPO assignment: {logical_path}"
        )
    assignment = candidates[0]
    valid_target = (
        len(assignment.targets) == 1
        and isinstance(assignment.targets[0], ast.Name)
        and assignment.targets[0].id == "REPO"
    )
    call = assignment.value
    if not (
        valid_target
        and isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "Path"
        and len(call.args) == 1
        and not call.keywords
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
    ):
        raise FreezeError(f"validator REPO assignment has an unexpected shape: {logical_path}")
    literal = call.args[0]
    lineno = literal.lineno
    col_offset = literal.col_offset
    end_lineno = literal.end_lineno
    end_col_offset = literal.end_col_offset
    if end_lineno is None or end_col_offset is None:
        raise FreezeError(f"validator REPO literal has no source span: {logical_path}")
    offsets = _line_byte_offsets(source)
    start = offsets[lineno - 1] + col_offset
    end = offsets[end_lineno - 1] + end_col_offset
    replacement = repr(str(repository_root)).encode("utf-8")
    rebound = source[:start] + replacement + source[end:]
    try:
        rebound_module = ast.parse(rebound.decode("utf-8"), filename=logical_path)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise FreezeError(f"rebound validator source cannot be parsed: {logical_path}") from exc
    rebound_assignments = [
        statement
        for statement in rebound_module.body
        if isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == "REPO"
    ]
    if len(rebound_assignments) != 1:
        raise FreezeError(f"rebound validator lost its REPO assignment: {logical_path}")
    rebound_call = rebound_assignments[0].value
    if not (
        isinstance(rebound_call, ast.Call)
        and len(rebound_call.args) == 1
        and isinstance(rebound_call.args[0], ast.Constant)
        and rebound_call.args[0].value == str(repository_root)
    ):
        raise FreezeError(f"rebound validator has the wrong repository root: {logical_path}")
    return rebound


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def materialize_inventory(
    materialized_root: Path,
    inventory: list[dict[str, object]],
    blobs: dict[str, bytes],
) -> None:
    expected = {item["path"] for item in inventory}
    if expected != set(EXPECTED_PATHS) or len(inventory) != 8:
        raise FreezeError("refusing to materialize a non-exact inventory")
    materialized_root.mkdir()
    for item in inventory:
        logical_path = str(item["path"])
        destination = materialized_root.joinpath(*logical_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = blobs[logical_path]
        destination.write_bytes(data)
        copied = destination.read_bytes()
        if (
            len(copied) != item["byte_count"]
            or sha256_hex(copied) != item["sha256"]
        ):
            raise FreezeError(f"materialized Git object verification failed: {logical_path}")
        try:
            destination.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError as exc:
            raise FreezeError(f"materialized file permissions cannot be set: {logical_path}") from exc
    for logical_path, _expected_checks in VALIDATORS:
        copied_path = materialized_root.joinpath(*logical_path.split("/"))
        rebound = bind_copied_repository(
            copied_path.read_bytes(),
            materialized_root,
            logical_path,
        )
        copied_path.write_bytes(rebound)


def parse_validator_result(
    logical_path: str,
    expected_checks: int,
    return_code: int,
    stdout: bytes,
    stderr: bytes,
) -> tuple[dict[str, object], list[str]]:
    stdout = normalize_process_output(stdout)
    stderr = normalize_process_output(stderr)
    summary_prefix = b"checks: "
    summaries = [line for line in stdout.splitlines() if line.startswith(summary_prefix)]
    checks = passed = failed = -1
    if len(summaries) == 1:
        parts = summaries[0].decode("ascii", errors="replace").split()
        try:
            if len(parts) == 6 and parts[0] == "checks:" and parts[2] == "passed:" and parts[4] == "failed:":
                checks, passed, failed = int(parts[1]), int(parts[3]), int(parts[5])
        except ValueError:
            pass
    marker_count = stdout.splitlines().count(b"ALL CHECKS PASS")
    mismatches: list[str] = []
    if return_code != 0:
        mismatches.append(f"{logical_path}: validator exit code is not zero")
    if (checks, passed, failed) != (expected_checks, expected_checks, 0):
        mismatches.append(
            f"{logical_path}: expected {expected_checks}/{expected_checks} with zero failures"
        )
    if marker_count != 1:
        mismatches.append(f"{logical_path}: ALL CHECKS PASS marker is not exact")
    if stderr:
        mismatches.append(f"{logical_path}: validator stderr is not empty")
    result = {
        "all_checks_pass_marker_count": marker_count,
        "checks": checks,
        "expected_checks": expected_checks,
        "failed": failed,
        "passed": passed,
        "path": logical_path,
        "return_code": return_code,
        "stderr_byte_count": len(stderr),
        "stderr_sha256": sha256_hex(stderr),
        "stdout_byte_count": len(stdout),
        "stdout_sha256": sha256_hex(stdout),
    }
    return result, mismatches


def replay_historical_regressions(commit: str, repo_root: Path) -> dict[str, object]:
    """Replay each validator against a fresh verified materialization."""
    inventory, blobs = load_inventory(commit, repo_root)
    validators: list[dict[str, object]] = []
    mismatches: list[str] = []
    with tempfile.TemporaryDirectory(prefix="m8-v3-historical-replay-") as directory:
        temporary_root = inspect_path_components(
            Path(directory),
            "replay temporary directory",
        )
        if _is_within(temporary_root, repo_root) or _is_within(repo_root, temporary_root):
            raise FreezeError(
                "replay temporary directory must be external to the repository"
            )
        dummy_cwd = temporary_root / "unrelated-cwd"
        dummy_cwd.mkdir()
        for index, (logical_path, expected_checks) in enumerate(VALIDATORS):
            materialized_root = temporary_root / f"materialized-{index}"
            materialize_inventory(materialized_root, inventory, blobs)
            for item in inventory:
                inventory_path = str(item["path"])
                copied_path = materialized_root.joinpath(*inventory_path.split("/"))
                expected_bytes = blobs[inventory_path]
                if inventory_path in {path for path, _count in VALIDATORS}:
                    expected_bytes = bind_copied_repository(
                        expected_bytes,
                        materialized_root,
                        inventory_path,
                    )
                copied = copied_path.read_bytes()
                if copied != expected_bytes:
                    raise FreezeError(
                        f"fresh materialization differs from its verified source: {inventory_path}"
                    )
            validator = materialized_root.joinpath(*logical_path.split("/"))
            return_code, stdout, stderr = run_bounded_process(
                [sys.executable, "-I", str(validator)],
                dummy_cwd,
                allowed_python_script=validator,
            )
            result, validator_mismatches = parse_validator_result(
                logical_path,
                expected_checks,
                return_code,
                stdout,
                stderr,
            )
            validators.append(result)
            mismatches.extend(validator_mismatches)
    return {
        "canonicalization_id": "sa-json-c14n-v1",
        "format": FORMAT,
        "inventory": inventory,
        "inventory_file_count": len(inventory),
        "mismatches": mismatches,
        "purpose": PURPOSE,
        "source_commit": commit,
        "status": "PASS" if not mismatches else "FAIL",
        "validators": validators,
    }


def main() -> int:
    parser = ControlledArgumentParser()
    parser.add_argument(
        "--repo",
        required=True,
        type=Path,
        help="absolute repository whose Git objects are replayed",
    )
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--git-executable",
        type=Path,
        help="absolute trusted Git executable; official layouts are auto-detected if omitted",
    )
    try:
        args = parser.parse_args()
        if not args.repo.is_absolute():
            raise FreezeError("repository path must be absolute", "repository")
        if args.git_executable is not None and not args.git_executable.is_absolute():
            raise FreezeError("Git executable path must be absolute", "git")
        select_git_executable(args.git_executable)
        repo_root = validate_repo(args.repo)
        report = replay_historical_regressions(args.commit, repo_root)
        payload = canonical(report)
        written = sys.stdout.buffer.write(payload)
        if written != len(payload):
            raise OSError("short stdout write")
        sys.stdout.buffer.flush()
        return 0 if report["status"] == "PASS" else 1
    except FreezeError as exc:
        print(f"ERROR {exc.category}: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR io: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

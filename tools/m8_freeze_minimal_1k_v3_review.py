#!/usr/bin/env python3
"""Freeze M8 v3 review inputs from an explicit Git commit object."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import struct
import subprocess
import shutil
import sys
import tempfile
import threading
import unicodedata
from pathlib import Path, PurePosixPath
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
CANON = "sa-json-c14n-v1"
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
OID_RE = re.compile(r"[0-9a-f]{40}")
GIT_VERSION_RE = re.compile(r"git version (\d+)\.(\d+)\.(\d+)(?:\.[^\s]+)?")
GIT_TIMEOUT_SECONDS = 15
MAX_GIT_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_FIXTURE_TRAVERSAL_ENTRIES = 256
MAX_FIXTURE_TRAVERSAL_DEPTH = 8
EXPECTED_SOURCE_FILE_COUNT = 9
EXPECTED_FIXTURE_FILE_COUNT = 90
EXPECTED_CANDIDATE_FILE_COUNT = 99
FIXTURE_ROOT = "docs/plans/references/fixtures/m8-minimal-1k-v3"
DEFAULT_PATHS = [
    ".gitattributes",
    "docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md",
    "docs/plans/references/schemas/m8-minimal-1k-artifacts-v3.schema.json",
    "tools/m8_generate_minimal_1k_v3_fixtures.py",
    "tools/m8_validate_minimal_1k_graph_v3.py",
    "tools/m8_test_minimal_1k_graph_v3.py",
    "tools/m8_freeze_minimal_1k_v3_review.py",
    "tools/m8_test_freeze_minimal_1k_v3_review.py",
    "tools/README.md",
]
FIXTURE_GRAPHS = (
    "success",
    "failure-cleanup",
    "failure-observer",
    "failure-runtime",
    "failure-validation",
)
FIXTURE_MEMBERS = (
    "artifacts/cleanup-receipt.json",
    "artifacts/identity.json",
    "artifacts/input-manifest.json",
    "artifacts/run-report.json",
    "artifacts/s0.json",
    "artifacts/s1.json",
    "artifacts/s2.json",
    "artifacts/s3.json",
    "artifacts/validation-report.json",
    "events/network.jsonl",
    "events/process.jsonl",
    "events/redaction.jsonl",
    "events/write.jsonl",
    "expectation.json",
    "input/chunks.jsonl",
    "input/gold.jsonl",
    "input/queries.jsonl",
    "input/vectors.bin",
)
EXPECTED_FIXTURE_PATHS = frozenset(
    f"{FIXTURE_ROOT}/{graph}/{member}"
    for graph in FIXTURE_GRAPHS
    for member in FIXTURE_MEMBERS
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


def run_git_process(command: list[str], args: tuple[str, ...]) -> bytes:
    operation = args[0] if args else "command"
    executable = Path(command[0])
    before_identity = git_executable_identity(executable)
    if (
        _GIT_EXECUTABLE_IDENTITY is not None
        and before_identity != _GIT_EXECUTABLE_IDENTITY
    ):
        raise FreezeError("Git executable changed after validation", "git")
    process = None
    overflow: dict[str, str | None] = {"stream": None}
    outputs: dict[str, bytearray] = {
        "stdout": bytearray(),
        "stderr": bytearray(),
    }
    output_lock = threading.Lock()
    total_output_bytes = 0

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
                    if process is not None:
                        try:
                            process.terminate()
                        except OSError:
                            pass
                    return
        finally:
            stream.close()

    def stop_and_reap() -> None:
        assert process is not None
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=GIT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise FreezeError(
                f"Git operation could not be reaped: {operation}",
                "git",
            ) from exc

    try:
        process = subprocess.Popen(
            command,
            env=git_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdout is not None
        assert process.stderr is not None
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
            return_code = process.wait(timeout=GIT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as exc:
            stop_and_reap()
            for stream in (process.stdout, process.stderr):
                try:
                    stream.close()
                except OSError:
                    pass
            for reader in readers:
                reader.join(timeout=GIT_TIMEOUT_SECONDS)
            raise FreezeError(
                f"Git operation timed out: {operation}",
                "git",
            ) from exc
        for reader in readers:
            reader.join(timeout=GIT_TIMEOUT_SECONDS)
        if any(reader.is_alive() for reader in readers):
            for stream in (process.stdout, process.stderr):
                try:
                    stream.close()
                except OSError:
                    pass
            raise FreezeError(
                f"Git output stream did not close: {operation}",
                "git",
            )
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
    except FreezeError:
        raise
    except (FileNotFoundError, PermissionError, OSError) as exc:
        raise FreezeError("Git executable cannot be run", "git") from exc


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


def git(*args: str, repo_root: Path = ROOT, executable: Path | None = None) -> bytes:
    selected = validate_git_capability(executable)
    return run_git_process(
        [
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
        ],
        args,
    )


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


def fixture_blobs(
    commit: str,
    repo_root: Path = ROOT,
    *,
    byte_budget: int | None = None,
) -> list[tuple[str, str, str, bytes]]:
    entries = tree_entries(
        commit,
        FIXTURE_ROOT,
        repo_root,
    )
    if not entries:
        raise FreezeError("fixture tree is missing")
    actual_paths = {path for path, _mode, _kind, _oid in entries}
    missing = sorted(
        EXPECTED_FIXTURE_PATHS - actual_paths,
        key=lambda path: path.encode("utf-8"),
    )
    unexpected = sorted(
        actual_paths - EXPECTED_FIXTURE_PATHS,
        key=lambda path: path.encode("utf-8"),
    )
    if missing:
        raise FreezeError(
            "fixture members are missing: "
            + ", ".join(missing)
        )
    if unexpected:
        raise FreezeError(
            "unexpected fixture members: "
            + ", ".join(unexpected)
        )
    blobs = []
    total_byte_count = 0
    effective_budget = MAX_TOTAL_BYTES if byte_budget is None else byte_budget
    if effective_budget < 0 or effective_budget > MAX_TOTAL_BYTES:
        raise FreezeError("invalid fixture byte budget")
    for path, mode, object_type, oid in entries:
        if object_type != "blob":
            raise FreezeError(
                f"fixture member is {object_type}, not blob: {path}"
            )
        if mode not in {"100644", "100755"}:
            raise FreezeError(f"fixture member is not a regular file: {path}")
        data = git(
            "cat-file",
            "blob",
            oid,
            repo_root=repo_root,
        )
        if len(data) > MAX_FILE_BYTES:
            raise FreezeError(f"blob exceeds per-file safety limit: {path}")
        total_byte_count += len(data)
        if total_byte_count > effective_budget:
            raise FreezeError("candidate inventory exceeds total byte safety limit")
        verify_blob_oid(path, oid, data)
        blobs.append((path, mode, oid, data))
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


def fixture_tree_summary(blobs: list[tuple[str, str, str, bytes]]) -> dict:
    digest = hashlib.sha256()
    total = 0
    for path, _mode, _oid, data in sorted(
        blobs,
        key=lambda item: item[0].encode("utf-8"),
    ):
        relative = path.removeprefix(FIXTURE_ROOT + "/")
        if relative == path:
            raise FreezeError(f"fixture path outside namespace: {path}")
        path_bytes = relative.encode("utf-8")
        digest.update(struct.pack(">I", len(path_bytes)))
        digest.update(path_bytes)
        digest.update(struct.pack(">Q", len(data)))
        digest.update(data)
        total += len(data)
    return {
        "algorithm": "fixture-tree-v1",
        "file_count": len(blobs),
        "sha256": digest.hexdigest(),
        "total_byte_count": total,
    }


def build_freeze(
    commit: str,
    paths: list[str] | None = None,
    repo_root: Path = ROOT,
    *,
    git_executable: Path | None = None,
) -> dict:
    if git_executable is not None:
        select_git_executable(git_executable)
    repo_root = validate_repo(repo_root)
    validate_commit(commit, repo_root)
    if paths is not None:
        raise FreezeError("custom source inventory is not allowed")
    normalized = [validate_logical_path(path) for path in DEFAULT_PATHS]
    if len(normalized) != len(set(normalized)):
        raise FreezeError("duplicate logical path")
    if len(normalized) != EXPECTED_SOURCE_FILE_COUNT:
        raise FreezeError("default source inventory must contain exactly 9 files")
    fixture_prefix = FIXTURE_ROOT + "/"
    overlap = [
        path
        for path in normalized
        if path == FIXTURE_ROOT or path.startswith(fixture_prefix)
    ]
    if overlap:
        raise FreezeError(
            "frozen source inventory overlaps fixture inventory: "
            + ", ".join(overlap)
        )
    files = []
    source_total_byte_count = 0
    for path in normalized:
        mode, oid, data = read_blob(commit, path, repo_root)
        source_total_byte_count += len(data)
        if source_total_byte_count > MAX_TOTAL_BYTES:
            raise FreezeError("candidate inventory exceeds total byte safety limit")
        files.append(summarize(path, mode, oid, data))
    remaining_byte_budget = MAX_TOTAL_BYTES - source_total_byte_count
    blobs = fixture_blobs(
        commit,
        repo_root,
        byte_budget=remaining_byte_budget,
    )
    if len(blobs) != EXPECTED_FIXTURE_FILE_COUNT:
        raise FreezeError("fixture inventory must contain exactly 90 files")
    fixture_files = [
        summarize(path, mode, oid, data)
        for path, mode, oid, data in blobs
    ]
    files = sorted(files, key=lambda item: item["path"].encode("utf-8"))
    fixture_files = sorted(
        fixture_files,
        key=lambda item: item["path"].encode("utf-8"),
    )
    inventory = sorted(
        [*files, *fixture_files],
        key=lambda item: item["path"].encode("utf-8"),
    )
    if len(inventory) != EXPECTED_CANDIDATE_FILE_COUNT:
        raise FreezeError("candidate inventory must contain exactly 99 files")
    total_byte_count = sum(item["byte_count"] for item in inventory)
    if total_byte_count > MAX_TOTAL_BYTES:
        raise FreezeError("candidate inventory exceeds total byte safety limit")
    return {
        "aggregate": {
            "file_count": len(inventory),
            "total_byte_count": total_byte_count,
        },
        "candidate_files": inventory,
        "canonicalization_id": CANON,
        "fixture_files": fixture_files,
        "fixture_tree": fixture_tree_summary(blobs),
        "format": "m8-minimal-1k-v3-review-freeze-v1",
        "frozen_files": files,
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


def walk_fixture_files(root: Path) -> set[str]:
    fixture_root = contained_inventory_path(root, FIXTURE_ROOT)
    try:
        root_stat = fixture_root.lstat()
    except OSError as exc:
        raise FreezeError(f"fixture worktree cannot be inspected: {exc}") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise FreezeError("fixture worktree root is not a regular directory")
    paths = set()
    visited_entries = 0
    pending = [(fixture_root, 0)]
    while pending:
        directory, depth = pending.pop()
        if depth > MAX_FIXTURE_TRAVERSAL_DEPTH:
            raise FreezeError("fixture worktree traversal exceeds depth limit")
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    visited_entries += 1
                    if visited_entries > MAX_FIXTURE_TRAVERSAL_ENTRIES:
                        raise FreezeError(
                            "fixture worktree traversal exceeds entry limit"
                        )
                    path = Path(entry.path)
                    try:
                        file_stat = path.lstat()
                    except OSError as exc:
                        raise FreezeError(
                            f"fixture member cannot be inspected: {exc}"
                        ) from exc
                    if stat.S_ISLNK(file_stat.st_mode) or has_reparse_point(file_stat):
                        raise FreezeError(
                            "fixture worktree contains a symlink or reparse point: "
                            f"{path}"
                        )
                    if stat.S_ISDIR(file_stat.st_mode):
                        pending.append((path, depth + 1))
                    elif stat.S_ISREG(file_stat.st_mode):
                        paths.add(path.relative_to(root).as_posix())
                    else:
                        raise FreezeError(
                            "fixture worktree contains a non-regular member: "
                            f"{path}"
                        )
        except FreezeError:
            raise
        except OSError as exc:
            raise FreezeError(
                f"fixture worktree cannot be traversed: {exc}"
            ) from exc
    return paths


def compare_worktree(
    freeze: dict,
    root: Path = ROOT,
) -> list[str]:
    divergent = []
    inventory = [
        *freeze["frozen_files"],
        *freeze["fixture_files"],
    ]
    fixture_bytes = {}
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
            path = contained_inventory_path(
                root,
                item["path"],
                allow_missing_leaf=True,
            )
            if not path.exists():
                divergent.append(item["path"])
                continue
            file_stat = path.lstat()
            if not stat.S_ISREG(file_stat.st_mode):
                divergent.append(item["path"])
                continue
            data, file_stat = read_bounded_worktree_file(
                path,
                item["path"],
            )
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
        expected_executable = item.get("git_mode") == "100755"
        if (
            hashlib.sha256(data).hexdigest() != item["sha256"]
            or (compare_modes and actual_executable != expected_executable)
        ):
            divergent.append(item["path"])
        if item["path"].startswith(FIXTURE_ROOT + "/"):
            fixture_bytes[item["path"]] = data
    actual_fixture_paths = walk_fixture_files(root)
    expected_fixture_paths = {
        item["path"] for item in freeze["fixture_files"]
    }
    divergent.extend(
        sorted(
            actual_fixture_paths - expected_fixture_paths,
            key=lambda path: path.encode("utf-8"),
        )
    )
    if len(fixture_bytes) == len(expected_fixture_paths):
        actual_blobs = [
            (
                item["path"],
                item.get("git_mode", "100644"),
                "",
                fixture_bytes[item["path"]],
            )
            for item in freeze["fixture_files"]
        ]
        if fixture_tree_summary(actual_blobs) != freeze["fixture_tree"]:
            divergent.append(FIXTURE_ROOT)
    after_head, after_status = repository_state()
    if after_head != before_head or after_status != before_status:
        raise FreezeError("repository state changed while comparing worktree")
    return sorted(
        set(divergent),
        key=lambda path: path.encode("utf-8"),
    )


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
        for item in [*freeze["frozen_files"], *freeze["fixture_files"]]
    }
    if output in inventory_paths:
        raise FreezeError("output path overlaps frozen inventory")
    try:
        output.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise FreezeError("output path must be outside repository")
    fixture_root = contained_inventory_path(repo_root, FIXTURE_ROOT)
    try:
        output.relative_to(fixture_root)
    except ValueError:
        pass
    else:
        raise FreezeError("output path must not be inside fixture inventory")
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

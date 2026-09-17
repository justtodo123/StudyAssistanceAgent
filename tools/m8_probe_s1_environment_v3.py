#!/usr/bin/env python3
"""Read-only environment probe for the M8 v3 S1 preflight.

The probe never creates a root, generates workload data, imports optional
backends, installs packages, or writes a report.  Its only output is one
canonical JSON document on stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import ntpath
import os
import platform
import re
import stat
import sys
from pathlib import Path
from typing import NoReturn

CANONICALIZATION_ID = "sa-json-c14n-v1"
SCHEMA_ID = "sa.m8.minimal.s1-environment-facts.v3"
SCHEMA_VERSION = 3
ABSENT = "ABSENT"
DEPENDENCIES = ("lancedb", "numpy", "pyarrow", "psutil")
FROZEN_FILE_NAMES = {
    "generator-implementation",
    "generator-specification",
    "installation-inventory",
    "observer-config",
    "observer-implementation",
    "observer-specification",
    "production-preinventory",
    "protocol",
    "repository-preinventory",
    "python-executable",
    "redaction-registry",
    "wheel-inventory",
    "wheel-lancedb",
    "wheel-numpy",
    "wheel-psutil",
    "wheel-pyarrow",
}
EXTERNAL_SOURCES_ROOT = r"D:\111_Others_Subjects"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_FILE_BYTES = 16 * 1024 * 1024


class ProbeError(ValueError):
    """A controlled, fail-closed probe error."""


class ControlledParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ProbeError(message)


def reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json(data: bytes) -> object:
    return json.loads(
        data,
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_pairs,
    )


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _has_reparse_point(file_stat: os.stat_result) -> bool:
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(file_stat, "st_file_attributes", 0) & flag)


def _absolute(path: Path) -> Path:
    try:
        return Path(os.path.abspath(os.fspath(path.expanduser())))
    except (OSError, RuntimeError, ValueError) as exc:
        raise ProbeError(f"path cannot be made absolute: {exc}") from exc


def validate_canonical_windows_path(value: object, label: str) -> str:
    """Require a unique Win32 path spelling without namespace aliases."""
    if not isinstance(value, str) or not value:
        raise ProbeError(f"{label}: invalid canonical Windows path")
    if "\x00" in value or "/" in value or not ntpath.isabs(value):
        raise ProbeError(f"{label}: invalid canonical Windows path")
    drive, tail = ntpath.splitdrive(value)
    if (
        len(drive) != 2
        or drive[1] != ":"
        or not ("A" <= drive[0] <= "Z")
        or not tail.startswith("\\")
        or ":" in tail
        or value != ntpath.normpath(value)
    ):
        raise ProbeError(f"{label}: invalid canonical Windows path")
    reserved = {"CON", "PRN", "AUX", "NUL"}
    reserved.update(f"COM{index}" for index in range(1, 10))
    reserved.update(f"LPT{index}" for index in range(1, 10))
    components = tail.split("\\")[1:]
    if components == [""]:
        components = []
    for component in components:
        device_name = component.split(".", 1)[0].upper()
        if (
            not component
            or component.endswith((" ", "."))
            or device_name in reserved
        ):
            raise ProbeError(f"{label}: invalid canonical Windows path")
    return value


def inspect_existing_path(path: Path, label: str) -> Path:
    """Reject symlinks/reparse points in every existing path component."""
    absolute = _absolute(path)
    anchor = Path(absolute.anchor)
    current = anchor
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        try:
            file_stat = current.lstat()
        except OSError as exc:
            raise ProbeError(f"{label} cannot be inspected: {exc}") from exc
        if stat.S_ISLNK(file_stat.st_mode) or _has_reparse_point(file_stat):
            raise ProbeError(f"{label} contains a symlink or reparse point: {current}")
    return absolute


def canonical_windows_path(path: Path, *, require_absent: bool = False) -> str:
    """Return one unique absolute Windows path without touching the leaf."""
    absolute = _absolute(path)
    caller_text = os.fspath(absolute).replace("/", "\\")
    drive, tail = ntpath.splitdrive(caller_text)
    if drive:
        caller_text = drive.upper() + tail
    text = validate_canonical_windows_path(caller_text, "path")
    if require_absent:
        try:
            leaf_stat = absolute.lstat()
        except FileNotFoundError:
            leaf_stat = None
        except OSError as exc:
            raise ProbeError(f"root cannot be inspected: {exc}") from exc
        if leaf_stat is not None:
            raise ProbeError(f"root must be absent: {text}")
    return text


def parent_identity(root: Path) -> dict:
    absolute = _absolute(root)
    parent = inspect_existing_path(absolute.parent, "root parent")
    try:
        file_stat = parent.lstat()
    except OSError as exc:
        raise ProbeError(f"root parent cannot be inspected: {exc}") from exc
    if not stat.S_ISDIR(file_stat.st_mode):
        raise ProbeError("root parent must be a directory")
    return {
        "canonical_path": canonical_windows_path(parent),
        "st_dev": int(file_stat.st_dev),
        "st_ino": int(file_stat.st_ino),
    }


def root_fact(root: Path) -> dict:
    return {
        "canonical_path": canonical_windows_path(root, require_absent=True),
        "exists": False,
        "parent_identity": parent_identity(root),
    }


def dependency_versions() -> dict[str, str]:
    """Read package metadata only; never import optional dependency code."""
    versions: dict[str, str] = {}
    for distribution in DEPENDENCIES:
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = ABSENT
        except Exception as exc:  # metadata failure cannot be treated as absence
            raise ProbeError(f"dependency metadata unreadable: {distribution}: {exc}") from exc
        if not isinstance(version, str) or not version or any(ord(ch) < 32 for ch in version):
            raise ProbeError(f"dependency version is invalid: {distribution}")
        versions[distribution] = version
    return versions


def _git(repository: Path, *args: str) -> bytes:
    operation = args[0] if args else "command"
    try:
        from m8_freeze_s1_prerequisites_v3 import FreezeError, git as trusted_git
    except (ImportError, OSError) as exc:
        raise ProbeError(f"read-only Git query failed: {operation}") from exc
    try:
        return trusted_git(*args, repo_root=repository)
    except (FreezeError, OSError) as exc:
        raise ProbeError(f"read-only Git query failed: {operation}") from exc


def repository_fact(repository: Path) -> dict:
    repository = inspect_existing_path(repository, "repository")
    try:
        repo_stat = repository.lstat()
    except OSError as exc:
        raise ProbeError(f"repository cannot be inspected: {exc}") from exc
    if not stat.S_ISDIR(repo_stat.st_mode):
        raise ProbeError("repository must be a directory")
    try:
        top = _git(repository, "rev-parse", "--show-toplevel").decode("utf-8").strip()
        head = _git(repository, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
        tree = _git(repository, "rev-parse", "--verify", "HEAD^{tree}").decode("ascii").strip()
        status = _git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    except UnicodeDecodeError as exc:
        raise ProbeError("Git identity output has invalid encoding") from exc
    if inspect_existing_path(Path(top), "repository top level") != repository:
        raise ProbeError("repository must be the exact worktree top level")
    if HEX40.fullmatch(head) is None or HEX40.fullmatch(tree) is None:
        raise ProbeError("repository uses an unsupported Git object identity")
    return {
        "canonical_path": canonical_windows_path(repository),
        "clean": not status,
        "commit_object": head,
        "parent_identity": parent_identity(repository),
        "status_byte_count": len(status),
        "status_sha256": sha256_hex(status),
        "tree_object": tree,
        "worktree_head": head,
        "worktree_head_matches_commit_object": True,
    }


def file_fact(path: Path) -> dict:
    path = inspect_existing_path(path, "frozen file")
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise ProbeError("frozen file must be regular")
        if before.st_size > MAX_FILE_BYTES:
            raise ProbeError("frozen file exceeds safety limit")
        data = path.read_bytes()
        after = path.lstat()
    except ProbeError:
        raise
    except OSError as exc:
        raise ProbeError(f"frozen file cannot be read: {exc}") from exc
    if (before.st_dev, before.st_ino, before.st_size) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
    ):
        raise ProbeError("frozen file changed while read")
    return {
        "byte_count": len(data),
        "canonical_path": canonical_windows_path(path),
        "sha256": sha256_hex(data),
    }


def parse_named_path(value: str) -> tuple[str, Path]:
    try:
        name, raw_path = value.split("=", 1)
    except ValueError as exc:
        raise ProbeError("--frozen-file must be NAME=ABSOLUTE_PATH") from exc
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name) or not raw_path:
        raise ProbeError("--frozen-file name/path is invalid")
    return name, Path(raw_path)


def build_probe(
    repository: Path,
    temporary_root: Path,
    evidence_directory: Path,
    production_root: Path,
    frozen_files: dict[str, Path],
) -> dict:
    if set(frozen_files) != FROZEN_FILE_NAMES:
        raise ProbeError("frozen file set must be exact")
    temp_fact = root_fact(temporary_root)
    evidence_fact = root_fact(evidence_directory)
    production_root = inspect_existing_path(production_root, "production root")
    try:
        production_stat = production_root.lstat()
    except OSError as exc:
        raise ProbeError(f"production root cannot be inspected: {exc}") from exc
    if not stat.S_ISDIR(production_stat.st_mode):
        raise ProbeError("production root must be a directory")
    if os.path.normcase(temp_fact["canonical_path"]) == os.path.normcase(evidence_fact["canonical_path"]):
        raise ProbeError("temporary and evidence roots must be distinct")
    facts = {
        "dependencies": dependency_versions(),
        "files": {
            name: file_fact(frozen_files[name])
            for name in sorted(frozen_files, key=lambda item: item.encode("utf-8"))
        },
        "platform": {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "python_executable": canonical_windows_path(Path(sys.executable)),
            "system": platform.system(),
        },
        "protected_roots": {
            "production_root": {
                "canonical_path": canonical_windows_path(production_root),
                "parent_identity": parent_identity(production_root),
            }
        },
        "repository": repository_fact(repository),
        "roots": {
            "evidence_directory": evidence_fact,
            "temporary_root": temp_fact,
        },
    }
    return {
        "canonicalization_id": CANONICALIZATION_ID,
        "facts": facts,
        "schema_id": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
    }


def main(argv: list[str] | None = None) -> int:
    parser = ControlledParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--temporary-root", required=True, type=Path)
    parser.add_argument("--evidence-directory", required=True, type=Path)
    parser.add_argument("--production-root", required=True, type=Path)
    parser.add_argument("--frozen-file", action="append", default=[])
    try:
        args = parser.parse_args(argv)
        named_paths = [parse_named_path(item) for item in args.frozen_file]
        if len({name for name, _ in named_paths}) != len(named_paths):
            raise ProbeError("duplicate --frozen-file name")
        result = build_probe(
            args.repository,
            args.temporary_root,
            args.evidence_directory,
            args.production_root,
            dict(named_paths),
        )
        sys.stdout.buffer.write(canonical_bytes(result))
        return 0
    except (ProbeError, ValueError, OSError) as exc:
        error = {
            "errors": [str(exc)],
            "schema_id": "sa.m8.minimal.s1-environment-probe-error.v3",
            "status": "S1_ENVIRONMENT_PROBE_INVALID",
        }
        sys.stderr.buffer.write(canonical_bytes(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

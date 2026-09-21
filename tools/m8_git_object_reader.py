"""Bounded, offline-only reads of explicitly named local Git objects."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

try:
    from tools.m8_metadata_discovery_schema import (
        MAX_CHAIN_BYTES,
        MAX_DOCUMENT_BYTES,
        MetadataGovernanceError,
    )
except ImportError:  # pragma: no cover
    from m8_metadata_discovery_schema import (
        MAX_CHAIN_BYTES,
        MAX_DOCUMENT_BYTES,
        MetadataGovernanceError,
    )

HEX40 = re.compile(r"[0-9a-f]{40}")


class GitObjectReader:
    """Read explicit SHA-1 objects with per-object and traversal byte bounds."""

    def __init__(
        self,
        repo_root: Path,
        aggregate_limit: int = MAX_CHAIN_BYTES,
    ) -> None:
        if type(aggregate_limit) is not int or aggregate_limit < 1:
            raise MetadataGovernanceError("Git aggregate byte bound is invalid")
        self.repo_root = repo_root.resolve()
        self.aggregate_limit = aggregate_limit
        self.bytes_read = 0
        object_format = self._capture("rev-parse", "--show-object-format").decode(
            "ascii", errors="strict"
        ).strip()
        if object_format != "sha1":
            raise MetadataGovernanceError("Git repository object format must be sha1")

    def _command(self, *args: str) -> list[str]:
        return [
            "git",
            "--no-replace-objects",
            "--no-lazy-fetch",
            "-C",
            str(self.repo_root),
            *args,
        ]

    def _capture(self, *args: str, input_bytes: bytes | None = None) -> bytes:
        try:
            return subprocess.run(
                self._command(*args),
                check=True,
                capture_output=True,
                input=input_bytes,
                timeout=15,
            ).stdout
        except (
            OSError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as exc:
            raise MetadataGovernanceError("Git object lookup failed") from exc

    @staticmethod
    def require_oid(oid: object, label: str = "commit") -> str:
        if type(oid) is not str or HEX40.fullmatch(oid) is None:
            raise MetadataGovernanceError(
                f"{label} must be a full lowercase 40-character Git OID"
            )
        return oid

    @staticmethod
    def require_path(path: object) -> str:
        if type(path) is not str or not path or "\\" in path or "\0" in path:
            raise MetadataGovernanceError("Git blob path is unsafe")
        parts = path.split("/")
        if path.startswith("/") or any(part in {"", ".", ".."} for part in parts):
            raise MetadataGovernanceError("Git blob path is unsafe")
        return path

    def _object_header(self, oid: str) -> tuple[str, int]:
        try:
            object_type = self._capture("cat-file", "-t", oid).decode(
                "ascii", errors="strict"
            ).strip()
            raw_size = self._capture("cat-file", "-s", oid).decode(
                "ascii", errors="strict"
            ).strip()
        except UnicodeDecodeError as exc:
            raise MetadataGovernanceError("Git object header is malformed") from exc
        if not object_type or any(character.isspace() for character in object_type):
            raise MetadataGovernanceError("Git object header is malformed")
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise MetadataGovernanceError("Git object size is invalid") from exc
        if size < 1:
            raise MetadataGovernanceError("Git object size is invalid")
        return object_type, size

    def _charge(self, size: int) -> None:
        if size > MAX_DOCUMENT_BYTES:
            raise MetadataGovernanceError("Git object exceeds the document size bound")
        if self.bytes_read + size > self.aggregate_limit:
            raise MetadataGovernanceError("Git traversal exceeds the aggregate byte bound")
        self.bytes_read += size

    def _read_exact_object(self, oid: str, object_type: str, size: int) -> bytes:
        self._charge(size)
        try:
            process = subprocess.Popen(
                self._command("cat-file", object_type, oid),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise MetadataGovernanceError("Git object read failed") from exc
        assert process.stdout is not None
        chunks: list[bytes] = []
        remaining = size
        try:
            while remaining:
                chunk = process.stdout.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            extra = process.stdout.read(1)
            if remaining or extra:
                process.kill()
                process.communicate(timeout=5)
                raise MetadataGovernanceError("Git object framing does not match declared size")
            trailing_stdout, stderr = process.communicate(timeout=15)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.communicate()
            raise MetadataGovernanceError("Git object read timed out") from exc
        if process.returncode != 0:
            raise MetadataGovernanceError("Git object read failed")
        if trailing_stdout:
            raise MetadataGovernanceError("Git object framing has trailing bytes")
        data = b"".join(chunks)
        expected = hashlib.sha1(
            f"{object_type} {len(data)}\0".encode("ascii") + data
        ).hexdigest()
        if expected != oid:
            raise MetadataGovernanceError("Git object content does not match its OID")
        return data

    def read_object(self, oid: object, expected_type: str) -> bytes:
        exact_oid = self.require_oid(oid, "object")
        object_type, size = self._object_header(exact_oid)
        if object_type != expected_type:
            raise MetadataGovernanceError(
                f"Git object is not a {expected_type}"
            )
        return self._read_exact_object(exact_oid, object_type, size)

    def commit_binding(self, commit: object) -> dict[str, str]:
        exact_commit = self.require_oid(commit)
        data = self.read_object(exact_commit, "commit")
        try:
            header = data.split(b"\n\n", 1)[0].decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise MetadataGovernanceError("Git commit header is malformed") from exc
        tree_values = [line[5:] for line in header.splitlines() if line.startswith("tree ")]
        parent_values = [line[7:] for line in header.splitlines() if line.startswith("parent ")]
        if len(tree_values) != 1 or HEX40.fullmatch(tree_values[0]) is None:
            raise MetadataGovernanceError("Git commit tree binding is invalid")
        if len(parent_values) != 1 or HEX40.fullmatch(parent_values[0]) is None:
            raise MetadataGovernanceError(
                "Git commit must satisfy ordinary_single_parent_commit_only"
            )
        return {
            "commit": exact_commit,
            "parent": parent_values[0],
            "tree": tree_values[0],
        }

    def read_blob(self, commit: object, path: object) -> tuple[str, bytes]:
        exact_commit = self.require_oid(commit)
        exact_path = self.require_path(path)
        raw = self._capture(
            "ls-tree",
            "-z",
            exact_commit,
            "--",
            exact_path,
        )
        entries = [entry for entry in raw.split(b"\0") if entry]
        if len(entries) != 1:
            raise MetadataGovernanceError("Git path does not resolve to one object")
        try:
            metadata, returned_path = entries[0].split(b"\t", 1)
            mode, object_type, oid = metadata.decode(
                "ascii", errors="strict"
            ).split()
            decoded_path = returned_path.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise MetadataGovernanceError("Git tree entry is malformed") from exc
        if decoded_path != exact_path or object_type != "blob" or HEX40.fullmatch(oid) is None:
            raise MetadataGovernanceError("Git path does not resolve to a blob")
        if not mode.startswith("100"):
            raise MetadataGovernanceError("Git blob mode is invalid")
        data = self.read_object(oid, "blob")
        return oid, data

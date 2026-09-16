#!/usr/bin/env python3
"""Validate a persistent M8 v3 artifact directory.

Exit 0 means the directory is either a valid success graph or a valid,
fail-closed failure graph. Invalid or internally inconsistent graphs exit 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path, PurePosixPath
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT
    / "docs/plans/references/schemas/m8-minimal-1k-artifacts-v3.schema.json"
)
PROTOCOL_PATH = (
    ROOT
    / "docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md"
)
ROLE_SCHEMA = {
    "identity": "sa.m8.minimal.experiment-identity.v3",
    "input-manifest": "sa.m8.minimal.input-manifest.v3",
    "run-report": "sa.m8.minimal.run-report.v3",
    "validation-report": "sa.m8.minimal.validation-report.v3",
    "cleanup-receipt": "sa.m8.minimal.cleanup-receipt.v3",
    "s0": "sa.m8.minimal.decision-record.v3",
    "s1": "sa.m8.minimal.decision-record.v3",
    "s2": "sa.m8.minimal.decision-record.v3",
    "s3": "sa.m8.minimal.decision-record.v3",
}
GATE_MAP = {
    "S0": {
        "role": "s0",
        "actor": "independent-reviewer",
        "pairs": {
            ("PROTOCOL_ACCEPTED", "request-s1"),
            ("PROTOCOL_REJECTED", "stop"),
        },
    },
    "S1": {
        "role": "s1",
        "actor": "owner",
        "pairs": {
            ("DRY_RUN_AUTHORIZED", "run-s2"),
            ("NOT_AUTHORIZED", "stop"),
        },
    },
    "S2": {
        "role": "s2",
        "actor": "executor",
        "pairs": {
            ("EVIDENCE_READY", "request-s3"),
            ("DRY_RUN_FAILED", "stop"),
        },
    },
    "S3": {
        "role": "s3",
        "actor": "independent-reviewer",
        "pairs": {
            ("ACCEPT_1K_EVIDENCE", "stop"),
            ("REJECT_1K_EVIDENCE", "stop"),
        },
    },
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPERIMENT_ID = re.compile(r"^[a-z0-9-]+$")


def reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
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


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_jsonl_records(data: bytes) -> list[dict]:
    lines = (
        data[:-1].split(b"\n")
        if data.endswith(b"\n")
        else (data.split(b"\n") if data else [])
    )
    records = []
    for line in lines:
        if b"\r" in line:
            raise ValueError("JSONL must use LF-only line endings")
        obj = strict_json(line)
        if not isinstance(obj, dict):
            raise ValueError("JSONL records must be objects")
        if line + b"\n" != canonical(obj):
            raise ValueError("JSONL line is not canonical JSON")
        records.append(obj)
    return records


def jsonl_count(data: bytes) -> int:
    if not data:
        raise ValueError("JSONL must be non-empty")
    if not data.endswith(b"\n"):
        raise ValueError("JSONL must end with LF")
    return len(canonical_jsonl_records(data))


class Validator:
    def __init__(self, graph_dir: Path):
        self.requested_root = graph_dir.absolute()
        self.root = graph_dir.resolve()
        self.artifact_dir = self.root / "artifacts"
        self.errors: list[str] = []
        self.objects: dict[str, dict] = {}
        self.paths: dict[str, Path] = {}
        self.schema: dict | None = None
        self.fixture_graph = False

    def check(self, condition: bool, message: str) -> bool:
        if not condition:
            self.errors.append(message)
        return condition

    @staticmethod
    def strict_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _is_reparse_point(self, path: Path) -> bool:
        try:
            file_stat = path.lstat()
        except OSError:
            return False
        reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        return bool(
            getattr(file_stat, "st_file_attributes", 0)
            & reparse_attribute
        )

    def mapping(self, value: object, message: str) -> dict:
        if not isinstance(value, dict):
            self.errors.append(message)
            return {}
        return value

    def sequence(self, value: object, message: str) -> list:
        if not isinstance(value, list):
            self.errors.append(message)
            return []
        return value

    def safe_path(self, relative: object) -> Path:
        invalid = self.root / "__invalid_path__"
        if not isinstance(relative, str) or not relative:
            self.check(False, f"unsafe relative path: {relative}")
            return invalid
        raw_parts = relative.split("/")
        valid = (
            "\\" not in relative
            and not relative.startswith("/")
            and re.match(r"^[A-Za-z]:", relative) is None
            and not any(part in {"", ".", ".."} for part in raw_parts)
            and tuple(raw_parts) == PurePosixPath(relative).parts
            and not any(
                unicodedata.category(char) == "Cc"
                for char in relative
            )
        )
        if not self.check(valid, f"unsafe relative path: {relative}"):
            return invalid
        try:
            target = (self.root / relative).resolve()
        except OSError as exc:
            self.errors.append(f"path cannot be resolved: {relative}: {exc}")
            return invalid
        contained = target == self.root or self.root in target.parents
        if not self.check(contained, f"path escapes graph: {relative}"):
            return invalid
        return target

    def load_schema(self) -> None:
        try:
            data = SCHEMA_PATH.read_bytes()
            value = strict_json(data)
            schema = self.mapping(value, "schema root must be an object")
            self.check(
                schema.get("$id") == "sa.m8.minimal.artifacts.v3",
                "schema id mismatch",
            )
            self.check(
                schema.get("$schema")
                == "https://json-schema.org/draft/2020-12/schema",
                "schema draft mismatch",
            )
            self.schema = schema
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            self.errors.append(f"schema invalid: {exc}")

    def validate_envelope_schema(self, role: str, obj: dict) -> bool:
        if self.schema is None:
            return False
        properties = self.mapping(
            self.schema.get("properties"),
            "schema properties must be an object",
        )
        required = set(self.sequence(
            self.schema.get("required"),
            "schema required must be an array",
        ))
        valid = self.check(set(obj) == required, f"{role}: envelope keys")
        payload = obj.get("payload")
        valid &= self.check(
            isinstance(payload, dict),
            f"{role}: payload must be an object",
        )
        valid &= self.check(
            obj.get("canonicalization_id")
            == self.mapping(
                properties.get("canonicalization_id"),
                "schema canonicalization property invalid",
            ).get("const"),
            f"{role}: canonicalization",
        )
        schema_version = obj.get("schema_version")
        valid &= self.check(
            self.strict_int(schema_version)
            and schema_version
            == self.mapping(
                properties.get("schema_version"),
                "schema version property invalid",
            ).get("const"),
            f"{role}: schema version",
        )
        schema_ids = self.mapping(
            properties.get("schema_id"),
            "schema id property invalid",
        ).get("enum", [])
        valid &= self.check(
            obj.get("schema_id") in schema_ids,
            f"{role}: schema id is outside schema enum",
        )
        logical_name = obj.get("logical_name")
        logical_pattern = self.mapping(
            properties.get("logical_name"),
            "schema logical-name property invalid",
        ).get("pattern")
        valid &= self.check(
            isinstance(logical_name, str)
            and isinstance(logical_pattern, str)
            and re.fullmatch(logical_pattern, logical_name) is not None,
            f"{role}: logical name schema",
        )
        return bool(valid)

    def load_artifacts(self) -> None:
        expected = set(ROLE_SCHEMA)
        core_files = {
            *(f"artifacts/{role}.json" for role in expected),
            "input/chunks.jsonl",
            "input/gold.jsonl",
            "input/queries.jsonl",
            "input/vectors.bin",
            "events/network.jsonl",
            "events/process.jsonl",
            "events/redaction.jsonl",
            "events/write.jsonl",
        }
        fixture_path = self.root / "expectation.json"
        expected_files = set(core_files)
        if fixture_path.exists() or fixture_path.is_symlink():
            expected_files.add("expectation.json")
        actual_files: set[str] = set()
        inventory_valid = True
        try:
            if (
                not self.requested_root.is_dir()
                or self.requested_root.is_symlink()
                or self._is_reparse_point(self.requested_root)
                or self.requested_root.resolve() != self.root
            ):
                raise OSError("graph root must be a regular directory")
            for current, directories, files in os.walk(
                self.root, topdown=True, followlinks=False
            ):
                current_path = Path(current)
                safe_directories = []
                for name in directories:
                    path = current_path / name
                    relative = path.relative_to(self.root).as_posix()
                    resolved = path.resolve()
                    contained = resolved == self.root or self.root in resolved.parents
                    if (
                        path.is_symlink()
                        or self._is_reparse_point(path)
                        or not contained
                    ):
                        inventory_valid = False
                        self.errors.append(
                            f"graph inventory non-regular member: {relative}"
                        )
                    else:
                        safe_directories.append(name)
                directories[:] = safe_directories
                for name in files:
                    path = current_path / name
                    relative = path.relative_to(self.root).as_posix()
                    resolved = path.resolve()
                    contained = resolved == self.root or self.root in resolved.parents
                    if (
                        path.is_symlink()
                        or self._is_reparse_point(path)
                        or not contained
                        or not path.is_file()
                    ):
                        inventory_valid = False
                        self.errors.append(
                            f"graph inventory non-regular member: {relative}"
                        )
                    else:
                        actual_files.add(relative)
        except OSError as exc:
            self.errors.append(f"graph directory unreadable: {exc}")
            return
        inventory_valid &= self.check(
            actual_files == expected_files,
            f"graph inventory mismatch: {sorted(actual_files)}",
        )
        fixture_valid = True
        if "expectation.json" in expected_files:
            try:
                expectation_data = fixture_path.read_bytes()
                expectation = strict_json(expectation_data)
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.errors.append(f"expectation: invalid JSON: {exc}")
                fixture_valid = False
            else:
                fixture_valid &= self.check(
                    isinstance(expectation, dict),
                    "expectation: root must be an object",
                )
                if isinstance(expectation, dict):
                    fixture_valid &= self.check(
                        expectation_data == canonical(expectation),
                        "expectation: not canonical JSON",
                    )
                    fixture_valid &= self.check(
                        set(expectation)
                        == {
                            "fixture_kind",
                            "graph",
                            "intended_outcome",
                            "represented_failure",
                        },
                        "expectation: keys",
                    )
                    fixture_valid &= self.check(
                        expectation.get("fixture_kind")
                        == "validator-micro-fixture-not-real-1k",
                        "expectation: fixture marker",
                    )
                    fixture_valid &= self.check(
                        expectation.get("graph") == self.root.name,
                        "expectation: graph name",
                    )
                    fixture_valid &= self.check(
                        expectation.get("intended_outcome")
                        in {"PASS", "VALID_FAILURE_GRAPH"},
                        "expectation: intended outcome",
                    )
                    fixture_valid &= self.check(
                        expectation.get("represented_failure")
                        in {"none", "cleanup", "observer", "runtime", "validation"},
                        "expectation: represented failure",
                    )
        self.fixture_graph = "expectation.json" in expected_files and fixture_valid
        if not inventory_valid:
            return
        try:
            found = {
                path.stem for path in self.artifact_dir.glob("*.json")
            }
        except OSError as exc:
            self.errors.append(f"artifact directory unreadable: {exc}")
            return
        self.check(
            found == expected,
            f"artifact role set mismatch: {sorted(found)}",
        )
        for role in sorted(expected & found):
            path = self.artifact_dir / f"{role}.json"
            try:
                data = path.read_bytes()
                value = strict_json(data)
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.errors.append(f"{role}: invalid JSON: {exc}")
                continue
            if not isinstance(value, dict):
                self.errors.append(f"{role}: envelope must be an object")
                continue
            obj = value
            try:
                canonical_data = canonical(obj)
            except (TypeError, ValueError, UnicodeError) as exc:
                self.errors.append(f"{role}: non-canonical JSON value: {exc}")
                continue
            self.check(data == canonical_data, f"{role}: not canonical JSON")
            if not self.validate_envelope_schema(role, obj):
                continue
            self.check(
                obj.get("schema_id") == ROLE_SCHEMA[role],
                f"{role}: schema role mismatch",
            )
            payload = obj["payload"]
            experiment_id = payload.get("experiment_id")
            self.check(
                isinstance(experiment_id, str)
                and EXPERIMENT_ID.fullmatch(experiment_id) is not None,
                f"{role}: experiment id",
            )
            self.check(
                obj.get("logical_name")
                == f"minimal-1k/{experiment_id}/{role}.json",
                f"{role}: logical name",
            )
            self.objects[role] = obj
            self.paths[role] = path

    def validate_ref_schema(self, ref: object, label: str) -> dict:
        value = self.mapping(ref, f"{label}: ref must be an object")
        keys = {
            "logical_name",
            "role",
            "schema_id",
            "sha256",
            "byte_count",
        }
        self.check(set(value) == keys, f"{label}: ref keys")
        self.check(
            isinstance(value.get("logical_name"), str),
            f"{label}: ref logical-name type",
        )
        self.check(
            isinstance(value.get("role"), str),
            f"{label}: ref role type",
        )
        self.check(
            isinstance(value.get("schema_id"), str),
            f"{label}: ref schema type",
        )
        digest = value.get("sha256")
        self.check(
            isinstance(digest, str) and HEX64.fullmatch(digest) is not None,
            f"{label}: ref digest format",
        )
        byte_count = value.get("byte_count")
        self.check(
            isinstance(byte_count, int)
            and not isinstance(byte_count, bool)
            and byte_count >= 1,
            f"{label}: ref byte-count type",
        )
        return value

    def verify_ref(self, ref: object, expected_role: str) -> bool:
        before = len(self.errors)
        value = self.validate_ref_schema(ref, expected_role)
        self.check(
            value.get("role") == expected_role,
            f"{expected_role}: ref role",
        )
        target = self.objects.get(expected_role)
        path = self.paths.get(expected_role)
        if target is None or path is None:
            self.errors.append(f"{expected_role}: missing ref target")
            return False
        try:
            data = path.read_bytes()
        except OSError as exc:
            self.errors.append(f"{expected_role}: ref target unreadable: {exc}")
            return False
        self.check(
            value.get("logical_name") == target.get("logical_name"),
            f"{expected_role}: ref logical name",
        )
        self.check(
            value.get("schema_id") == target.get("schema_id"),
            f"{expected_role}: ref schema id",
        )
        self.check(
            value.get("sha256") == sha(data),
            f"{expected_role}: ref digest",
        )
        self.check(
            value.get("byte_count") == len(data),
            f"{expected_role}: ref byte count",
        )
        return len(self.errors) == before

    def validate_identity(self) -> None:
        raw_payload = self.objects["identity"].get("payload")
        if not isinstance(raw_payload, dict):
            return
        payload = raw_payload
        required = {
            "backends",
            "byte_order",
            "chunk_count",
            "dimension",
            "dtype",
            "experiment_id",
            "generator_algorithm",
            "normalization",
            "protocol_sha256",
            "seed",
            "synthetic_only",
            "top_k",
        }
        self.check(set(payload) == required, "identity: payload keys")
        self.check(
            payload.get("backends")
            == [
                "sqlite-linear-exact",
                "lancedb-embedded-exact-flat",
            ],
            "identity: backends",
        )
        workload_shape_valid = (
            self.strict_int(payload.get("chunk_count"))
            and payload.get("chunk_count") == 1000
            and self.strict_int(payload.get("dimension"))
            and payload.get("dimension") == 512
            and payload.get("dtype") == "float32"
            and payload.get("byte_order") == "little-endian"
            and payload.get("normalization") == "l2"
        )
        self.check(workload_shape_valid, "identity: workload shape")
        top_k = payload.get("top_k")
        deterministic_constants_valid = (
            self.strict_int(payload.get("seed"))
            and payload.get("seed") == 20260914
            and isinstance(top_k, list)
            and all(self.strict_int(value) for value in top_k)
            and top_k == [1, 3, 5]
        )
        self.check(
            deterministic_constants_valid,
            "identity: deterministic constants",
        )
        self.check(
            payload.get("generator_algorithm")
            == "sa-m8-synthetic-unit-v3"
            and payload.get("synthetic_only") is True,
            "identity: synthetic algorithm",
        )
        protocol_digest = payload.get("protocol_sha256")
        self.check(
            isinstance(protocol_digest, str)
            and HEX64.fullmatch(protocol_digest) is not None,
            "identity: protocol digest format",
        )
        try:
            protocol_data = PROTOCOL_PATH.read_bytes()
        except OSError as exc:
            self.errors.append(f"identity: protocol file unreadable: {exc}")
        else:
            self.check(
                protocol_digest == sha(protocol_data),
                "identity: protocol digest bytes",
            )

    def validate_member_schema(self, member: object, label: str) -> dict:
        value = self.mapping(member, f"{label}: member must be an object")
        self.check(
            set(value) == {
                "path",
                "sha256",
                "byte_count",
                "record_count",
            },
            f"{label}: member keys",
        )
        path = value.get("path")
        self.check(isinstance(path, str), f"{label}: member path type")
        digest = value.get("sha256")
        self.check(
            isinstance(digest, str) and HEX64.fullmatch(digest) is not None,
            f"{label}: member digest format",
        )
        for field in ("byte_count", "record_count"):
            number = value.get(field)
            self.check(
                isinstance(number, int)
                and not isinstance(number, bool)
                and number >= 1,
                f"{label}: member {field} type",
            )
        return value

    def validate_manifest(self) -> None:
        raw_payload = self.objects["input-manifest"].get("payload")
        if not isinstance(raw_payload, dict):
            return
        payload = raw_payload
        self.check(
            set(payload)
            == {
                "experiment_id",
                "identity_ref",
                "members",
                "synthetic_fixture_only",
            },
            "manifest: payload keys",
        )
        fixture_only = payload.get("synthetic_fixture_only")
        self.check(
            isinstance(fixture_only, bool),
            "manifest: fixture marker type",
        )
        self.check(
            fixture_only == self.fixture_graph,
            "manifest: fixture marker/inventory",
        )
        self.verify_ref(payload.get("identity_ref"), "identity")
        members = self.sequence(
            payload.get("members"),
            "manifest: members must be an array",
        )
        expected_paths = [
            "input/chunks.jsonl",
            "input/gold.jsonl",
            "input/queries.jsonl",
            "input/vectors.bin",
        ]
        values = [
            self.validate_member_schema(member, f"manifest member {index}")
            for index, member in enumerate(members)
        ]
        self.check(
            [item.get("path") for item in values] == expected_paths,
            "manifest: exact sorted members",
        )
        observed_counts: dict[str, int] = {}
        observed_bytes: dict[str, int] = {}
        for item in values:
            relative = item.get("path")
            path = self.safe_path(relative)
            if not self.check(
                path.is_file() and not path.is_symlink(),
                f"manifest: missing {relative}",
            ):
                continue
            try:
                data = path.read_bytes()
            except OSError as exc:
                self.errors.append(f"manifest: unreadable {relative}: {exc}")
                continue
            self.check(
                item.get("sha256") == sha(data),
                f"manifest: digest {relative}",
            )
            self.check(
                item.get("byte_count") == len(data),
                f"manifest: bytes {relative}",
            )
            if isinstance(relative, str):
                observed_bytes[relative] = len(data)
            if path.suffix == ".jsonl":
                try:
                    count: object = jsonl_count(data)
                except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                    self.errors.append(
                        f"manifest: invalid JSONL {relative}: {exc}"
                    )
                    count = item.get("record_count")
            elif fixture_only is True:
                count = item.get("record_count")
                self.check(
                    data == b"M8-V3-FIXTURE-VECTORS-NOT-REAL-1K\n",
                    "manifest: fixture vectors placeholder",
                )
            else:
                identity = self.mapping(
                    self.objects["identity"].get("payload"),
                    "identity: payload must be an object",
                )
                dimension = identity.get("dimension")
                count = (
                    len(data) // (dimension * 4)
                    if isinstance(dimension, int)
                    and not isinstance(dimension, bool)
                    and dimension > 0
                    and len(data) % (dimension * 4) == 0
                    else None
                )
            if (
                isinstance(relative, str)
                and isinstance(count, int)
                and not isinstance(count, bool)
            ):
                observed_counts[relative] = count
            self.check(
                item.get("record_count") == count,
                f"manifest: records {relative}",
            )
        chunks = observed_counts.get("input/chunks.jsonl")
        vectors = observed_counts.get("input/vectors.bin")
        queries = observed_counts.get("input/queries.jsonl")
        gold = observed_counts.get("input/gold.jsonl")
        self.check(chunks == vectors, "manifest: chunk/vector count")
        self.check(queries == gold, "manifest: query/gold count")
        if fixture_only is False:
            identity = self.mapping(
                self.objects["identity"].get("payload"),
                "identity: payload must be an object",
            )
            dimension = identity.get("dimension")
            real_shape_valid = (
                chunks == 1000
                and queries == 104
                and isinstance(dimension, int)
                and not isinstance(dimension, bool)
                and dimension == 512
                and observed_bytes.get("input/vectors.bin")
                == chunks * dimension * 4
            )
            self.check(real_shape_valid, "manifest: real workload shape")

    def validate_summary_schema(self, summary: object, name: str) -> dict:
        value = self.mapping(
            summary,
            f"observer {name}: summary must be an object",
        )
        self.check(
            set(value)
            == {"path", "sha256", "byte_count", "event_count", "status"},
            f"observer {name}: summary keys",
        )
        digest = value.get("sha256")
        self.check(
            isinstance(digest, str) and HEX64.fullmatch(digest) is not None,
            f"observer {name}: digest format",
        )
        for field, minimum in (("byte_count", 1), ("event_count", 2)):
            number = value.get(field)
            self.check(
                isinstance(number, int)
                and not isinstance(number, bool)
                and number >= minimum,
                f"observer {name}: {field} type",
            )
        self.check(
            value.get("status") in {"PASS", "FAIL"},
            f"observer {name}: status",
        )
        return value

    def validate_events_and_run(self) -> tuple[bool, bool, bool]:
        raw_payload = self.objects["run-report"].get("payload")
        if not isinstance(raw_payload, dict):
            return False, False, False
        payload = raw_payload
        required = {
            "backend_results",
            "experiment_id",
            "input_manifest_ref",
            "observers",
            "runtime_errors",
            "status",
        }
        self.check(set(payload) == required, "run: payload keys")
        self.verify_ref(
            payload.get("input_manifest_ref"),
            "input-manifest",
        )
        backend_results = self.sequence(
            payload.get("backend_results"),
            "run: backend results must be an array",
        )
        expected_backend_modes = [
            ("sqlite-linear-exact", "linear-exact"),
            (
                "lancedb-embedded-exact-flat",
                "embedded-exact-flat-no-ann",
            ),
        ]
        backend_statuses = []
        self.check(
            len(backend_results) == len(expected_backend_modes),
            "run: backend count",
        )
        for index, expected in enumerate(expected_backend_modes):
            value = self.mapping(
                backend_results[index] if index < len(backend_results) else None,
                f"run: backend {index} must be an object",
            )
            self.check(
                set(value)
                == {"backend", "mode", "status", "input_manifest_sha256"},
                f"run: backend {index} keys",
            )
            self.check(
                (value.get("backend"), value.get("mode")) == expected,
                f"run: backend {index} mode",
            )
            binding_digest = value.get("input_manifest_sha256")
            self.check(
                isinstance(binding_digest, str)
                and HEX64.fullmatch(binding_digest) is not None,
                f"run: backend {index} input manifest digest format",
            )
            backend_status = value.get("status")
            self.check(
                backend_status in {"PASS", "FAIL"},
                f"run: backend {index} status",
            )
            backend_statuses.append(backend_status)
        status = payload.get("status")
        self.check(status in {"PASS", "FAIL"}, "run: status")
        runtime_errors = self.sequence(
            payload.get("runtime_errors"),
            "run: runtime errors must be an array",
        )
        runtime_errors_valid = all(
            isinstance(item, str) and bool(item) for item in runtime_errors
        )
        self.check(
            runtime_errors_valid,
            "run: runtime error entries must be non-empty strings",
        )
        run_pass = (
            status == "PASS"
            and runtime_errors == []
            and backend_statuses == ["PASS", "PASS"]
        )
        self.check(
            (status == "PASS") == (runtime_errors == []),
            "run: errors/status",
        )
        self.check(
            (
                status == "PASS"
                and backend_statuses == ["PASS", "PASS"]
            )
            or (
                status == "FAIL"
                and "FAIL" in backend_statuses
            ),
            "run: backend aggregate status",
        )
        observers = self.mapping(
            payload.get("observers"),
            "run: observers must be an object",
        )
        expected_observers = {"network", "write", "process", "redaction"}
        self.check(set(observers) == expected_observers, "run: observer set")
        all_observers_pass = set(observers) == expected_observers
        closed_failure_kinds = {
            "network": {"outbound-connection"},
            "write": {"denied-write"},
            "process": {"unexpected-child"},
            "redaction": {"sensitive-match"},
        }
        allowed_kinds = {
            "network": {
                "observer-start",
                "observer-stop",
                "outbound-connection",
            },
            "write": {
                "observer-start",
                "observer-stop",
                "allowed-write",
                "denied-write",
            },
            "process": {
                "observer-start",
                "observer-stop",
                "child-count",
                "unexpected-child",
            },
            "redaction": {
                "observer-start",
                "observer-stop",
                "utf8-scan",
                "sensitive-match",
            },
        }
        for name in sorted(expected_observers & set(observers)):
            summary = self.mapping(
                observers[name],
                f"observer {name}: summary must be an object",
            )
            path = self.safe_path(summary.get("path"))
            self.check(
                path == self.root / f"events/{name}.jsonl",
                f"observer {name}: path",
            )
            if not path.is_file() or path.is_symlink():
                self.errors.append(f"observer {name}: missing ledger")
                all_observers_pass = False
                continue
            try:
                data = path.read_bytes()
            except OSError as exc:
                self.errors.append(f"observer {name}: unreadable ledger: {exc}")
                all_observers_pass = False
                continue
            nonempty_valid = bool(data)
            final_lf_valid = data.endswith(b"\n")
            if not nonempty_valid:
                self.errors.append(f"observer {name}: JSONL must be non-empty")
            if not final_lf_valid:
                self.errors.append(f"observer {name}: JSONL must end with LF")
            if not nonempty_valid or not final_lf_valid:
                all_observers_pass = False
            summary = self.validate_summary_schema(summary, name)
            digest_valid = self.check(
                summary.get("sha256") == sha(data),
                f"observer {name}: digest",
            )
            bytes_valid = self.check(
                summary.get("byte_count") == len(data),
                f"observer {name}: bytes",
            )
            try:
                events = canonical_jsonl_records(data)
            except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
                self.errors.append(f"observer {name}: invalid JSONL {exc}")
                all_observers_pass = False
                continue
            count_valid = self.check(
                summary.get("event_count") == len(events),
                f"observer {name}: count",
            )
            sequences = [item.get("sequence") for item in events]
            sequence_valid = (
                all(self.strict_int(value) for value in sequences)
                and sequences == list(range(len(events)))
            )
            self.check(sequence_valid, f"observer {name}: sequence")
            event_shapes_valid = True
            for item in events:
                event_shapes_valid &= self.check(
                    set(item) == {"detail", "kind", "sequence", "status"},
                    f"observer {name}: event keys",
                )
                event_shapes_valid &= self.check(
                    isinstance(item.get("detail"), str),
                    f"observer {name}: event detail type",
                )
                event_shapes_valid &= self.check(
                    item.get("kind") in allowed_kinds[name],
                    f"observer {name}: event kind",
                )
                event_shapes_valid &= self.check(
                    item.get("status") in {"PASS", "FAIL"},
                    f"observer {name}: event status",
                )
                event_shapes_valid &= self.check(
                    item.get("kind") not in closed_failure_kinds[name]
                    or item.get("status") == "FAIL",
                    f"observer {name}: closed event must fail",
                )
            lifecycle_valid = (
                bool(events)
                and events[0].get("kind") == "observer-start"
                and events[-1].get("kind") == "observer-stop"
            )
            self.check(lifecycle_valid, f"observer {name}: lifecycle")
            computed = (
                "FAIL"
                if any(item.get("status") == "FAIL" for item in events)
                else "PASS"
            )
            aggregate_valid = self.check(
                summary.get("status") == computed,
                f"observer {name}: aggregate status",
            )
            observer_pass = (
                digest_valid
                and bytes_valid
                and count_valid
                and sequence_valid
                and event_shapes_valid
                and lifecycle_valid
                and aggregate_valid
                and computed == "PASS"
            )
            all_observers_pass &= observer_pass
        same_input_pass = self._same_input_check(payload)
        return all_observers_pass, run_pass, same_input_pass

    def _same_input_check(self, run_payload: dict) -> bool:
        """Recompute that both backend executions bind the same manifest bytes."""
        ref = run_payload.get("input_manifest_ref")
        target = self.objects.get("input-manifest")
        path = self.paths.get("input-manifest")
        if not isinstance(ref, dict) or target is None or path is None:
            return False
        try:
            manifest_data = path.read_bytes()
        except OSError:
            return False
        manifest_digest = sha(manifest_data)
        ref_matches = (
            ref.get("role") == "input-manifest"
            and ref.get("logical_name") == target.get("logical_name")
            and ref.get("schema_id") == target.get("schema_id")
            and ref.get("sha256") == manifest_digest
            and self.strict_int(ref.get("byte_count"))
            and ref.get("byte_count") == len(manifest_data)
        )
        backend_results = run_payload.get("backend_results")
        backend_bindings_match = (
            isinstance(backend_results, list)
            and len(backend_results) == 2
            and all(
                isinstance(result, dict)
                and result.get("input_manifest_sha256") == manifest_digest
                for result in backend_results
            )
        )
        return ref_matches and backend_bindings_match

    def validate_cleanup_validation(
        self,
        observers_pass: bool,
        run_pass: bool,
        same_input_pass: bool,
    ) -> tuple[bool, bool]:
        raw_cleanup = self.objects["cleanup-receipt"].get("payload")
        if not isinstance(raw_cleanup, dict):
            return False, False
        cleanup = raw_cleanup
        self.check(
            set(cleanup)
            == {
                "after_count",
                "experiment_id",
                "failure_code",
                "status",
                "temporary_root_exists",
            },
            "cleanup: payload keys",
        )
        status = cleanup.get("status")
        self.check(status in {"CLEANED", "FAIL"}, "cleanup: status")
        after_count = cleanup.get("after_count")
        after_count_valid = (
            isinstance(after_count, int)
            and not isinstance(after_count, bool)
            and after_count >= 0
        )
        self.check(after_count_valid, "cleanup: after count type")
        temporary_root_exists = cleanup.get("temporary_root_exists")
        self.check(
            isinstance(temporary_root_exists, bool),
            "cleanup: temporary root flag type",
        )
        failure_code = cleanup.get("failure_code")
        self.check(
            isinstance(failure_code, str) and bool(failure_code),
            "cleanup: failure code type",
        )
        cleanup_facts = (
            after_count_valid
            and after_count == 0
            and temporary_root_exists is False
            and failure_code == "none"
        )
        failure_facts = (
            isinstance(after_count, int)
            and not isinstance(after_count, bool)
            and after_count > 0
            and temporary_root_exists is True
            and isinstance(failure_code, str)
            and failure_code not in {"", "none"}
        )
        self.check(
            (status == "CLEANED" and cleanup_facts)
            or (status == "FAIL" and failure_facts),
            "cleanup: status facts",
        )
        cleaned = status == "CLEANED" and cleanup_facts
        raw_validation = self.objects["validation-report"].get("payload")
        if not isinstance(raw_validation, dict):
            return cleaned, False
        validation = raw_validation
        self.check(
            set(validation)
            == {
                "checks",
                "cleanup_receipt_ref",
                "experiment_id",
                "run_report_ref",
                "verdict",
            },
            "validation: payload keys",
        )
        self.verify_ref(
            validation.get("cleanup_receipt_ref"),
            "cleanup-receipt",
        )
        self.verify_ref(validation.get("run_report_ref"), "run-report")
        checks = self.mapping(
            validation.get("checks"),
            "validation: checks must be an object",
        )
        expected_checks = {"cleanup", "observer", "runtime", "same_input"}
        self.check(set(checks) == expected_checks, "validation: check set")
        for name in expected_checks & set(checks):
            self.check(
                isinstance(checks[name], bool),
                f"validation: {name} check type",
            )
        self.check(
            checks.get("cleanup") == cleaned,
            "validation: cleanup check",
        )
        self.check(
            checks.get("observer") == observers_pass,
            "validation: observer check",
        )
        self.check(
            checks.get("runtime") == run_pass,
            "validation: runtime check",
        )
        self.check(
            checks.get("same_input") == same_input_pass,
            "validation: same-input check",
        )
        computed_pass = (
            cleaned
            and observers_pass
            and run_pass
            and same_input_pass
        )
        self.check(
            validation.get("verdict")
            == ("PASS" if computed_pass else "FAIL"),
            "validation: verdict",
        )
        return cleaned, computed_pass

    def validate_gate_payload(self, role: str) -> dict:
        raw_payload = self.objects[role].get("payload")
        if not isinstance(raw_payload, dict):
            return {}
        payload = raw_payload
        self.check(
            set(payload)
            == {
                "actor_role",
                "allowed_next_action",
                "decision",
                "experiment_id",
                "gate_id",
                "read_refs",
            },
            f"{role}: payload keys",
        )
        self.sequence(
            payload.get("read_refs"),
            f"{role}: read refs must be an array",
        )
        return payload

    def validate_gates(self, cleaned: bool, validation_pass: bool) -> None:
        gate_payloads = {
            spec["role"]: self.validate_gate_payload(spec["role"])
            for spec in GATE_MAP.values()
        }
        for gate_id, spec in GATE_MAP.items():
            role = spec["role"]
            payload = gate_payloads[role]
            self.check(
                payload.get("gate_id") == gate_id
                and payload.get("actor_role") == spec["actor"],
                f"{role}: gate actor mapping",
            )
            self.check(
                (
                    payload.get("decision"),
                    payload.get("allowed_next_action"),
                )
                in spec["pairs"],
                f"{role}: decision/action mapping",
            )
        s0 = gate_payloads["s0"]
        s0_refs = self.sequence(
            s0.get("read_refs"),
            "s0: read refs must be an array",
        )
        self.check(s0_refs == [], "s0: predecessor refs must be empty")
        s1 = gate_payloads["s1"]
        s1_refs = self.sequence(
            s1.get("read_refs"),
            "s1: read refs must be an array",
        )
        self.check(len(s1_refs) == 1, "s1: predecessor count")
        if len(s1_refs) == 1:
            self.verify_ref(s1_refs[0], "s0")
        s0_accepted = s0.get("decision") == "PROTOCOL_ACCEPTED"
        self.check(
            s1.get("decision") != "DRY_RUN_AUTHORIZED" or s0_accepted,
            "s1: predecessor authority",
        )
        s2 = gate_payloads["s2"]
        s2_refs = self.sequence(
            s2.get("read_refs"),
            "s2: read refs must be an array",
        )
        expected_roles = [
            "s1",
            "run-report",
            "cleanup-receipt",
            "validation-report",
        ]
        actual_roles = [
            ref.get("role") if isinstance(ref, dict) else None
            for ref in s2_refs
        ]
        self.check(actual_roles == expected_roles, "s2: authority refs")
        if len(s2_refs) == len(expected_roles):
            for ref, role in zip(s2_refs, expected_roles):
                self.verify_ref(ref, role)
        should_ready = (
            s1.get("decision") == "DRY_RUN_AUTHORIZED"
            and cleaned
            and validation_pass
        )
        self.check(
            (s2.get("decision") == "EVIDENCE_READY") == should_ready,
            "s2: evidence authority",
        )
        s3 = gate_payloads["s3"]
        s3_refs = self.sequence(
            s3.get("read_refs"),
            "s3: read refs must be an array",
        )
        self.check(len(s3_refs) == 1, "s3: predecessor count")
        if len(s3_refs) == 1:
            self.verify_ref(s3_refs[0], "s2")
        self.check(
            s3.get("decision") != "ACCEPT_1K_EVIDENCE" or should_ready,
            "s3: evidence authority",
        )

    def validate_experiment_consistency(self) -> None:
        experiment_ids = set()
        for role, obj in self.objects.items():
            payload = self.mapping(
                obj.get("payload"),
                f"{role}: payload must be an object",
            )
            experiment_ids.add(payload.get("experiment_id"))
        self.check(
            len(experiment_ids) == 1,
            "graph: experiment IDs differ",
        )

    def run(self) -> bool:
        self.load_schema()
        self.load_artifacts()
        if self.schema is None or set(self.objects) != set(ROLE_SCHEMA):
            return False
        self.validate_experiment_consistency()
        self.validate_identity()
        self.validate_manifest()
        observers_pass, run_pass, same_input_pass = (
            self.validate_events_and_run()
        )
        cleaned, validation_pass = self.validate_cleanup_validation(
            observers_pass,
            run_pass,
            same_input_pass,
        )
        self.validate_gates(cleaned, validation_pass)
        return not self.errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph_dir", type=Path)
    args = parser.parse_args()
    validator = Validator(args.graph_dir)
    try:
        ok = validator.run()
    except Exception as exc:  # Defensive fail-closed CLI boundary.
        validator.errors.append(
            f"internal validator error: {type(exc).__name__}: {exc}"
        )
        ok = False
    if ok:
        outcome = validator.objects["validation-report"]["payload"]["verdict"]
        print(f"VALID_GRAPH verdict={outcome} path={args.graph_dir}")
        return 0
    for error in validator.errors:
        print(f"FAIL {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

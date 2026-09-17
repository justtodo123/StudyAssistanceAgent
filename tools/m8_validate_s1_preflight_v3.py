#!/usr/bin/env python3
"""Fail-closed validator for an M8 v3 S1 preflight document."""
from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import os
import platform
import re
import stat
import sys
from pathlib import Path
from typing import NoReturn

from m8_probe_s1_environment_v3 import (
    ABSENT,
    CANONICALIZATION_ID,
    DEPENDENCIES,
    SCHEMA_ID as PROBE_SCHEMA_ID,
    canonical_bytes,
    canonical_windows_path,
    dependency_versions,
    file_fact,
    inspect_existing_path,
    parent_identity,
    reject_constant,
    reject_duplicate_pairs,
    validate_canonical_windows_path,
)

PREFLIGHT_SCHEMA_ID = "sa.m8.minimal.s1-preflight.v3"
PREFLIGHT_RESULT_SCHEMA_ID = "sa.m8.minimal.s1-preflight-result.v3"
SCHEMA_VERSION = 3
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPERIMENT_ID = re.compile(r"^sa-m8-minimal-1k-v3-[a-z0-9][a-z0-9-]*$")
WORKLOAD = {
    "backends": ["sqlite-linear-exact", "lancedb-embedded-exact-flat"],
    "byte_order": "little-endian",
    "chunk_count": 1000,
    "dimension": 512,
    "dtype": "float32",
    "generator_algorithm": "sa-m8-synthetic-unit-v3",
    "normalization": "l2",
    "normalization_tolerance": 0.000002,
    "perturbation_seed": 20260915,
    "query_count": 104,
    "agreement_denominator": 312,
    "required_agreement": 1.0,
    "seed": 20260914,
    "synthetic_only": True,
    "top_k": [1, 3, 5],
}
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
S0_SCHEMA_ID = "sa.m8.minimal.decision-record.v3"
S1_GATE_SCHEMA_ID = "sa.m8.minimal.s1-gate.v3"
ARTIFACT_SCHEMA_IDS = {
    "installation-inventory": "sa.m8.minimal.installation-inventory.v3",
    "observer-config": "sa.m8.minimal.observer-config.v3",
    "production-preinventory": "sa.m8.minimal.pre-inventory.v3",
    "python-executable": "sa.m8.minimal.python-executable.v3",
    "redaction-registry": "sa.m8.minimal.redaction-registry.v3",
    "repository-preinventory": "sa.m8.minimal.pre-inventory.v3",
    "wheel-inventory": "sa.m8.minimal.wheel-inventory.v3",
    "wheel-lancedb": "sa.m8.minimal.wheel.v3",
    "wheel-numpy": "sa.m8.minimal.wheel.v3",
    "wheel-psutil": "sa.m8.minimal.wheel.v3",
    "wheel-pyarrow": "sa.m8.minimal.wheel.v3",
}


OBSERVER_CONFIG_SCHEMA_ID = "sa.m8.minimal.observer-config.v3"
REDACTION_REGISTRY_SCHEMA_ID = "sa.m8.minimal.redaction-registry.v3"
OBSERVER_LOGICAL_NAME = "observer/config.json"
REDACTION_LOGICAL_NAME = "observer/redaction.json"
OBSERVER_COMPONENT_IDS = ("network", "write", "process", "redaction")
OBSERVER_PHASES = (
    "observer-bootstrap",
    "acquisition",
    "measured",
    "redaction-and-seal",
    "cleanup",
    "observer-finalize",
)
OBSERVER_COVERAGE_STRATEGIES = {
    "network": "continuous-event-plus-boundary-snapshot",
    "write": "pre-open-post-open-and-post-mutation-revalidation",
    "process": "continuous-process-tree-plus-phase-count",
    "redaction": "complete-evidence-set-scan-before-seal",
}
OBSERVER_ERROR_CODES = (
    "collector-coverage-failed",
    "collector-event-invalid",
    "collector-read-failed",
    "collector-seal-failed",
    "collector-start-failed",
    "collector-stop-failed",
    "network-listener-observed",
    "network-measured-outbound-observed",
    "network-observation-unavailable",
    "process-observation-unavailable",
    "process-pid-identity-ambiguous",
    "process-unexpected-child",
    "redaction-binary-unknown",
    "redaction-bytes-changed-before-seal",
    "redaction-observation-unavailable",
    "redaction-sensitive-match",
    "redaction-utf8-decode-failed",
    "write-containment-unverifiable",
    "write-observation-unavailable",
    "write-outside-allowed-root",
    "write-race-detected",
)
REDACTION_MATCHER_ALGORITHM = "sa-m8-redaction-digest-registry-v3"
REDACTION_PATTERN_CATEGORIES = (
    "external-sources-root",
    "host-identity",
    "private-key-marker",
    "real-content-marker",
    "s1-secret-literal",
    "token-marker",
    "uri-credential",
    "user-identity",
    "windows-absolute-path",
    "windows-device-path",
    "windows-unc-path",
)

class PreflightError(ValueError):
    """A controlled validation failure."""


class ControlledParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise PreflightError(message)


def strict_json_bytes(data: bytes) -> dict:
    value = json.loads(
        data,
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_pairs,
    )
    if not isinstance(value, dict):
        raise PreflightError("JSON root must be an object")
    return value


def require_keys(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise PreflightError(f"{label}: closed key set mismatch")
    return value


def require_list(value: object, label: str) -> list:
    if not isinstance(value, list):
        raise PreflightError(f"{label}: must be an array")
    return value


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_canonical(path: Path, label: str) -> tuple[dict, bytes]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PreflightError(f"{label}: cannot be read: {exc}") from exc
    value = strict_json_bytes(data)
    if canonical_bytes(value) != data:
        raise PreflightError(f"{label}: must be canonical JSON with one LF")
    return value, data


def validate_windows_path(value: object, label: str) -> str:
    try:
        return validate_canonical_windows_path(value, label)
    except ValueError as exc:
        raise PreflightError(str(exc)) from exc


def same_path(left: str, right: str) -> bool:
    def key(value: str) -> str:
        return ntpath.normcase(ntpath.normpath(value))

    return key(left) == key(right)


def is_descendant(child: str, parent: str) -> bool:
    child_value = ntpath.normcase(ntpath.normpath(child))
    parent_value = ntpath.normcase(ntpath.normpath(parent))
    try:
        return ntpath.commonpath([child_value, parent_value]) == parent_value
    except ValueError:
        return False


def _git(repository: Path, *args: str) -> bytes:
    operation = args[0] if args else "command"
    try:
        from m8_freeze_s1_prerequisites_v3 import FreezeError, git as trusted_git
    except (ImportError, OSError) as exc:
        raise PreflightError(f"Git verification failed: {operation}") from exc
    try:
        return trusted_git(*args, repo_root=repository)
    except (FreezeError, OSError) as exc:
        raise PreflightError(f"Git verification failed: {operation}") from exc


def validate_s0(s0_path: Path, expected_sha256: str, experiment_id: str) -> dict:
    if HEX64.fullmatch(expected_sha256) is None:
        raise PreflightError("s0 binding digest must be lowercase HEX64")
    s0, data = load_canonical(s0_path, "s0")
    if sha256_hex(data) != expected_sha256:
        raise PreflightError("s0: bound digest mismatch")
    require_keys(
        s0,
        {"canonicalization_id", "logical_name", "payload", "schema_id", "schema_version"},
        "s0 envelope",
    )
    payload = require_keys(
        s0.get("payload"),
        {"actor_role", "allowed_next_action", "decision", "experiment_id", "gate_id", "read_refs"},
        "s0 payload",
    )
    if (
        s0.get("canonicalization_id") != CANONICALIZATION_ID
        or s0.get("schema_id") != "sa.m8.minimal.decision-record.v3"
        or s0.get("schema_version") != 3
        or s0.get("logical_name") != f"minimal-1k/{experiment_id}/s0.json"
        or payload.get("actor_role") != "independent-reviewer"
        or payload.get("allowed_next_action") != "request-s1"
        or payload.get("decision") != "PROTOCOL_ACCEPTED"
        or payload.get("experiment_id") != experiment_id
        or payload.get("gate_id") != "S0"
        or payload.get("read_refs") != []
    ):
        raise PreflightError("s0: accepted authority binding is invalid")
    return {
        "byte_count": len(data),
        "logical_name": s0["logical_name"],
        "role": "s0",
        "schema_id": s0["schema_id"],
        "sha256": expected_sha256,
    }


def validate_probe(probe: dict) -> dict:
    require_keys(probe, {"canonicalization_id", "facts", "schema_id", "schema_version"}, "probe")
    if (
        probe.get("canonicalization_id") != CANONICALIZATION_ID
        or probe.get("schema_id") != PROBE_SCHEMA_ID
        or probe.get("schema_version") != SCHEMA_VERSION
    ):
        raise PreflightError("probe: envelope mismatch")
    facts = require_keys(
        probe.get("facts"),
        {
            "dependencies",
            "files",
            "platform",
            "protected_roots",
            "repository",
            "roots",
        },
        "probe facts",
    )
    dependencies = require_keys(facts.get("dependencies"), set(DEPENDENCIES), "dependencies")
    for name, version in dependencies.items():
        if not isinstance(version, str) or not version:
            raise PreflightError(f"dependency version invalid: {name}")
    files = require_keys(facts.get("files"), FROZEN_FILE_NAMES, "frozen files")
    for name, item in files.items():
        item = require_keys(item, {"byte_count", "canonical_path", "sha256"}, f"file {name}")
        validate_windows_path(item.get("canonical_path"), f"file {name}")
        if (
            not isinstance(item.get("byte_count"), int)
            or isinstance(item.get("byte_count"), bool)
            or item["byte_count"] < 1
            or HEX64.fullmatch(str(item.get("sha256"))) is None
        ):
            raise PreflightError(f"file facts invalid: {name}")
    platform_fact = require_keys(
        facts.get("platform"),
        {"implementation", "python_version", "python_executable", "system"},
        "platform",
    )
    if any(not isinstance(value, str) or not value for value in platform_fact.values()):
        raise PreflightError("platform facts invalid")
    validate_windows_path(platform_fact["python_executable"], "python executable")
    if platform_fact["implementation"] != "CPython" or platform_fact["system"] != "Windows":
        raise PreflightError("S1 requires CPython on Windows")

    def validate_existing_root_binding(value: object, label: str) -> dict:
        binding = require_keys(
            value,
            {"canonical_path", "parent_identity"},
            label,
        )
        validate_windows_path(binding.get("canonical_path"), label)
        parent = require_keys(
            binding.get("parent_identity"),
            {"canonical_path", "st_dev", "st_ino"},
            f"{label} parent",
        )
        validate_windows_path(parent.get("canonical_path"), f"{label} parent")
        if (
            not isinstance(parent.get("st_dev"), int)
            or isinstance(parent.get("st_dev"), bool)
            or not isinstance(parent.get("st_ino"), int)
            or isinstance(parent.get("st_ino"), bool)
            or ntpath.dirname(binding["canonical_path"]) != parent["canonical_path"]
        ):
            raise PreflightError(f"{label} parent identity invalid")
        return binding

    protected_roots = require_keys(
        facts.get("protected_roots"),
        {"production_root"},
        "protected roots",
    )
    validate_existing_root_binding(
        protected_roots.get("production_root"),
        "production root",
    )
    repository = require_keys(
        facts.get("repository"),
        {
            "canonical_path",
            "clean",
            "commit_object",
            "parent_identity",
            "status_byte_count",
            "status_sha256",
            "tree_object",
            "worktree_head",
            "worktree_head_matches_commit_object",
        },
        "repository facts",
    )
    validate_existing_root_binding(
        {
            "canonical_path": repository.get("canonical_path"),
            "parent_identity": repository.get("parent_identity"),
        },
        "repository",
    )
    if (
        repository.get("clean") is not True
        or repository.get("status_byte_count") != 0
        or repository.get("status_sha256") != sha256_hex(b"")
        or HEX40.fullmatch(str(repository.get("commit_object"))) is None
        or HEX40.fullmatch(str(repository.get("tree_object"))) is None
        or HEX40.fullmatch(str(repository.get("worktree_head"))) is None
        or repository.get("worktree_head_matches_commit_object") is not True
        or repository.get("worktree_head") != repository.get("commit_object")
    ):
        raise PreflightError("repository clean Git-object/worktree binding invalid")
    roots = require_keys(facts.get("roots"), {"evidence_directory", "temporary_root"}, "roots")
    for name, item in roots.items():
        item = require_keys(item, {"canonical_path", "exists", "parent_identity"}, f"root {name}")
        validate_windows_path(item.get("canonical_path"), f"root {name}")
        parent = require_keys(
            item.get("parent_identity"),
            {"canonical_path", "st_dev", "st_ino"},
            f"root parent {name}",
        )
        validate_windows_path(parent.get("canonical_path"), f"root parent {name}")
        if (
            item.get("exists") is not False
            or not isinstance(parent.get("st_dev"), int)
            or isinstance(parent.get("st_dev"), bool)
            or not isinstance(parent.get("st_ino"), int)
            or isinstance(parent.get("st_ino"), bool)
            or ntpath.dirname(item["canonical_path"]) != parent["canonical_path"]
        ):
            raise PreflightError(f"root absent/parent identity invalid: {name}")
    temp = roots["temporary_root"]["canonical_path"]
    evidence = roots["evidence_directory"]["canonical_path"]
    repository_path = repository["canonical_path"]
    production_path = protected_roots["production_root"]["canonical_path"]
    protected = (repository_path, production_path, EXTERNAL_SOURCES_ROOT)
    roots_overlap = same_path(temp, evidence) or is_descendant(
        temp, evidence
    ) or is_descendant(evidence, temp)
    protected_overlap = any(
        same_path(root, protected_root)
        or is_descendant(root, protected_root)
        or is_descendant(protected_root, root)
        for root in (temp, evidence)
        for protected_root in protected
    )
    if roots_overlap or protected_overlap:
        raise PreflightError(
            "roots must be distinct, outside repository/production, and outside forbidden roots"
        )
    return facts


def revalidate_live_facts(facts: dict) -> None:
    """Revalidate mutable host facts immediately before accepting preflight."""
    try:
        live_dependencies = dependency_versions()
        if live_dependencies != facts["dependencies"]:
            raise PreflightError("live dependency facts differ from the frozen probe")

        executable = inspect_existing_path(Path(sys.executable), "python executable")
        executable_before = executable.lstat()
        if not stat.S_ISREG(executable_before.st_mode):
            raise PreflightError("live Python executable is not a regular file")
        executable_path = canonical_windows_path(executable)
        executable_after = executable.lstat()
        if (
            executable_before.st_dev,
            executable_before.st_ino,
            executable_before.st_size,
        ) != (
            executable_after.st_dev,
            executable_after.st_ino,
            executable_after.st_size,
        ):
            raise PreflightError("live Python executable changed while inspected")
        live_platform = {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "python_executable": executable_path,
            "system": platform.system(),
        }
        if live_platform != facts["platform"]:
            raise PreflightError("live platform facts differ from the frozen probe")

        for name, expected_file in facts["files"].items():
            if file_fact(Path(expected_file["canonical_path"])) != expected_file:
                raise PreflightError(
                    f"live frozen-file facts differ from the frozen probe: {name}"
                )

        for label, expected_root in (
            ("repository", facts["repository"]),
            (
                "production root",
                facts["protected_roots"]["production_root"],
            ),
        ):
            inspected = inspect_existing_path(
                Path(expected_root["canonical_path"]), label
            )
            before = inspected.lstat()
            if not stat.S_ISDIR(before.st_mode):
                raise PreflightError(f"live {label} is not a directory")
            live_path = canonical_windows_path(inspected)
            live_parent = parent_identity(inspected)
            after = inspected.lstat()
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise PreflightError(f"live {label} changed while inspected")
            if live_path != expected_root["canonical_path"]:
                raise PreflightError(f"live {label} path differs from the frozen probe")
            if live_parent != expected_root["parent_identity"]:
                raise PreflightError(
                    f"live {label} parent identity differs from the frozen probe"
                )

        for name, expected_root in facts["roots"].items():
            root = Path(expected_root["canonical_path"])
            live_path = canonical_windows_path(root, require_absent=True)
            live_parent = parent_identity(root)
            if live_path != expected_root["canonical_path"]:
                raise PreflightError(
                    f"live future-root path differs from the frozen probe: {name}"
                )
            if live_parent != expected_root["parent_identity"]:
                raise PreflightError(
                    f"live future-root parent identity differs from the frozen probe: {name}"
                )
            if canonical_windows_path(root, require_absent=True) != live_path:
                raise PreflightError(f"live future root appeared while inspected: {name}")
    except PreflightError:
        raise
    except Exception as exc:
        raise PreflightError(f"live environment revalidation failed: {exc}") from exc


def validate_artifact_ref(
    value: object,
    facts: dict,
    frozen_name: str,
    *,
    logical_name: str,
    role: str,
) -> dict:
    reference = require_keys(
        value,
        {"byte_count", "logical_name", "role", "schema_id", "sha256"},
        f"s1 config reference {frozen_name}",
    )
    frozen = facts["files"][frozen_name]
    if (
        reference.get("byte_count") != frozen["byte_count"]
        or reference.get("logical_name") != logical_name
        or reference.get("role") != role
        or reference.get("schema_id") != ARTIFACT_SCHEMA_IDS[frozen_name]
        or reference.get("sha256") != frozen["sha256"]
    ):
        raise PreflightError(f"preflight: s1 config reference mismatch: {frozen_name}")
    return reference


def validate_repository_file_ref(
    value: object,
    facts: dict,
    frozen_name: str,
    *,
    path: str,
    role: str,
) -> dict:
    reference = require_keys(
        value,
        {"byte_count", "path", "role", "sha256"},
        f"s1 config repository reference {frozen_name}",
    )
    frozen = facts["files"][frozen_name]
    configured_path = reference.get("path")
    if not isinstance(configured_path, str):
        raise PreflightError(f"preflight: s1 config reference mismatch: {frozen_name}")
    expected_absolute = ntpath.join(facts["repository"]["canonical_path"], path.replace("/", "\\"))
    if (
        reference.get("byte_count") != frozen["byte_count"]
        or configured_path != path
        or reference.get("role") != role
        or reference.get("sha256") != frozen["sha256"]
        or not same_path(frozen["canonical_path"], expected_absolute)
    ):
        raise PreflightError(f"preflight: s1 config reference mismatch: {frozen_name}")
    return reference


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise PreflightError(f"{label}: sha256 invalid")
    return value


def _require_sorted_unique_strings(
    value: object,
    label: str,
    *,
    exact: tuple[str, ...] | None = None,
) -> list[str]:
    items = require_list(value, label)
    if any(not isinstance(item, str) or not item for item in items):
        raise PreflightError(f"{label}: entries must be nonempty strings")
    if items != sorted(items) or len(items) != len(set(items)):
        raise PreflightError(f"{label}: entries must be sorted and unique")
    if exact is not None and tuple(items) != exact:
        raise PreflightError(f"{label}: exact entries mismatch")
    return items


def _validate_repository_ref_value(
    value: object,
    expected: dict,
    label: str,
) -> dict:
    reference = require_keys(
        value,
        {"byte_count", "path", "role", "sha256"},
        label,
    )
    if reference != expected:
        raise PreflightError(f"{label}: repository reference mismatch")
    return reference


def validate_redaction_registry(
    registry: object,
    registry_data: bytes,
) -> dict:
    if not isinstance(registry, dict):
        raise PreflightError("redaction registry: must be an object")
    require_keys(
        registry,
        {"canonicalization_id", "payload", "schema_id", "schema_version"},
        "redaction registry envelope",
    )
    if (
        registry.get("canonicalization_id") != CANONICALIZATION_ID
        or registry.get("schema_id") != REDACTION_REGISTRY_SCHEMA_ID
        or registry.get("schema_version") != SCHEMA_VERSION
    ):
        raise PreflightError("redaction registry: envelope mismatch")
    if strict_json_bytes(registry_data) != registry or canonical_bytes(registry) != registry_data:
        raise PreflightError("redaction registry: supplied bytes are not canonical or do not match")
    payload = require_keys(
        registry.get("payload"),
        {"binary_allowlist", "matcher_algorithm", "patterns", "unknown_binary_policy"},
        "redaction registry payload",
    )
    if (
        payload.get("matcher_algorithm") != REDACTION_MATCHER_ALGORITHM
        or payload.get("unknown_binary_policy") != "fail-closed"
    ):
        raise PreflightError("redaction registry: matcher or binary policy mismatch")
    binary_allowlist = require_list(payload.get("binary_allowlist"), "redaction binary allowlist")
    binary_paths: list[str] = []
    for index, item in enumerate(binary_allowlist):
        entry = require_keys(
            item,
            {"path", "sha256"},
            f"redaction binary allowlist {index}",
        )
        path = entry.get("path")
        if (
            not isinstance(path, str)
            or not path
            or "\\" in path
            or path.startswith("/")
            or re.match(r"^[A-Za-z]:", path)
            or ".." in path.split("/")
        ):
            raise PreflightError("redaction registry: binary path invalid")
        _require_sha256(entry.get("sha256"), "redaction binary allowlist")
        binary_paths.append(path)
    if binary_paths != sorted(binary_paths) or len(binary_paths) != len(set(binary_paths)):
        raise PreflightError("redaction registry: binary allowlist must be sorted and unique")
    patterns = require_list(payload.get("patterns"), "redaction patterns")
    categories: list[str] = []
    pattern_ids: list[str] = []
    for index, item in enumerate(patterns):
        pattern = require_keys(
            item,
            {"category", "matcher_kind", "needle_sha256", "pattern_id"},
            f"redaction pattern {index}",
        )
        if pattern.get("matcher_kind") != "digest-literal":
            raise PreflightError("redaction registry: matcher kind mismatch")
        category = pattern.get("category")
        pattern_id = pattern.get("pattern_id")
        if not isinstance(category, str) or not isinstance(pattern_id, str):
            raise PreflightError("redaction registry: pattern identity invalid")
        _require_sha256(pattern.get("needle_sha256"), "redaction pattern")
        categories.append(category)
        pattern_ids.append(pattern_id)
    if tuple(categories) != REDACTION_PATTERN_CATEGORIES:
        raise PreflightError("redaction registry: exact pattern categories mismatch")
    if pattern_ids != sorted(pattern_ids) or len(pattern_ids) != len(set(pattern_ids)):
        raise PreflightError("redaction registry: pattern ids must be sorted and unique")
    return registry


def validate_observer_config(
    observer_config: object,
    observer_config_data: bytes,
    redaction_registry_data: bytes,
    implementation_ref: dict,
    redaction_registry_ref: dict,
) -> dict:
    if not isinstance(observer_config, dict):
        raise PreflightError("observer config: must be an object")
    require_keys(
        observer_config,
        {"canonicalization_id", "logical_name", "payload", "schema_id", "schema_version"},
        "observer config envelope",
    )
    if (
        observer_config.get("canonicalization_id") != CANONICALIZATION_ID
        or observer_config.get("logical_name") != OBSERVER_LOGICAL_NAME
        or observer_config.get("schema_id") != OBSERVER_CONFIG_SCHEMA_ID
        or observer_config.get("schema_version") != SCHEMA_VERSION
    ):
        raise PreflightError("observer config: envelope mismatch")
    if (
        strict_json_bytes(observer_config_data) != observer_config
        or canonical_bytes(observer_config) != observer_config_data
    ):
        raise PreflightError("observer config: supplied bytes are not canonical or do not match")
    payload = require_keys(
        observer_config.get("payload"),
        {"components", "error_code_registry", "persistent_file_allowlist", "redaction_registry_ref"},
        "observer config payload",
    )
    configured_registry_ref = require_keys(
        payload.get("redaction_registry_ref"),
        {"byte_count", "logical_name", "role", "schema_id", "sha256"},
        "observer config redaction registry ref",
    )
    expected_registry_ref = {
        **redaction_registry_ref,
        "byte_count": len(redaction_registry_data),
        "logical_name": REDACTION_LOGICAL_NAME,
        "role": "artifact",
        "schema_id": REDACTION_REGISTRY_SCHEMA_ID,
        "sha256": sha256_hex(redaction_registry_data),
    }
    if configured_registry_ref != expected_registry_ref:
        raise PreflightError("observer config: redaction registry reference mismatch")
    components = require_list(payload.get("components"), "observer components")
    if len(components) != len(OBSERVER_COMPONENT_IDS):
        raise PreflightError("observer config: exact component set required")
    for index, component_id in enumerate(OBSERVER_COMPONENT_IDS):
        component = require_keys(
            components[index],
            {
                "api_ids",
                "bounded_retry_count",
                "component_id",
                "coverage_strategy",
                "implementation_ref",
                "parameters",
                "poll_interval_ms",
                "timeout_ms",
            },
            f"observer component {index}",
        )
        if (
            component.get("component_id") != component_id
            or component.get("coverage_strategy") != OBSERVER_COVERAGE_STRATEGIES[component_id]
        ):
            raise PreflightError("observer config: component identity or coverage mismatch")
        _validate_repository_ref_value(
            component.get("implementation_ref"),
            implementation_ref,
            f"observer component {component_id} implementation",
        )
        _require_sorted_unique_strings(
            component.get("api_ids"),
            f"observer component {component_id} api ids",
        )
        parameters = require_keys(
            component.get("parameters"),
            {"arguments", "flags"},
            f"observer component {component_id} parameters",
        )
        _require_sorted_unique_strings(
            parameters.get("arguments"),
            f"observer component {component_id} arguments",
        )
        _require_sorted_unique_strings(
            parameters.get("flags"),
            f"observer component {component_id} flags",
        )
        for field in ("bounded_retry_count", "poll_interval_ms", "timeout_ms"):
            value = component.get(field)
            minimum = 0 if field == "bounded_retry_count" else 1
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                raise PreflightError(f"observer config: {field} invalid")
        if component["timeout_ms"] <= component["poll_interval_ms"]:
            raise PreflightError("observer config: timeout must exceed poll interval")
    _require_sorted_unique_strings(
        payload.get("error_code_registry"),
        "observer error code registry",
        exact=OBSERVER_ERROR_CODES,
    )
    persistent_files = require_list(
        payload.get("persistent_file_allowlist"),
        "observer persistent file allowlist",
    )
    persistent_paths: list[str] = []
    for index, item in enumerate(persistent_files):
        entry = require_keys(
            item,
            {"classification", "path", "schema_id"},
            f"observer persistent file {index}",
        )
        path = entry.get("path")
        if (
            not isinstance(path, str)
            or not path
            or "\\" in path
            or path.startswith("/")
            or re.match(r"^[A-Za-z]:", path)
            or ".." in path.split("/")
            or entry.get("classification")
            not in {"utf8-json", "utf8-jsonl", "utf8-markdown", "utf8-text", "binary"}
            or not isinstance(entry.get("schema_id"), str)
            or not entry["schema_id"]
        ):
            raise PreflightError("observer config: persistent file entry invalid")
        persistent_paths.append(path)
    if persistent_paths != sorted(persistent_paths) or len(persistent_paths) != len(set(persistent_paths)):
        raise PreflightError("observer config: persistent allowlist must be sorted and unique")
    return observer_config


def validate_preflight(
    preflight: dict,
    probe: dict,
    s0_path: Path,
    config: dict | None = None,
    config_data: bytes | None = None,
    observer_config: dict | None = None,
    observer_config_data: bytes | None = None,
    redaction_registry: dict | None = None,
    redaction_registry_data: bytes | None = None,
) -> dict:
    require_keys(
        preflight,
        {
            "allowed_write_roots",
            "canonicalization_id",
            "environment_facts_sha256",
            "experiment_id",
            "expected",
            "s0_binding",
            "schema_id",
            "schema_version",
        },
        "preflight",
    )
    if (
        preflight.get("canonicalization_id") != CANONICALIZATION_ID
        or preflight.get("schema_id") != PREFLIGHT_SCHEMA_ID
        or preflight.get("schema_version") != SCHEMA_VERSION
    ):
        raise PreflightError("preflight: envelope mismatch")
    experiment_id = preflight.get("experiment_id")
    if not isinstance(experiment_id, str) or EXPERIMENT_ID.fullmatch(experiment_id) is None:
        raise PreflightError("preflight: experiment id invalid")
    if preflight.get("environment_facts_sha256") != sha256_hex(canonical_bytes(probe)):
        raise PreflightError("preflight: environment facts digest mismatch")
    facts = validate_probe(probe)
    expected = require_keys(
        preflight.get("expected"),
        {
            "dependencies",
            "files",
            "platform",
            "protected_roots",
            "repository",
            "roots",
            "workload",
        },
        "expected facts",
    )
    if expected.get("dependencies") != facts["dependencies"]:
        raise PreflightError("preflight: dependency facts mismatch")
    for dependency, version in expected["dependencies"].items():
        if version == ABSENT:
            raise PreflightError(f"preflight: dependency is ABSENT: {dependency}")
    if expected.get("files") != facts["files"]:
        raise PreflightError("preflight: frozen file facts mismatch")
    if expected.get("platform") != facts["platform"]:
        raise PreflightError("preflight: platform facts mismatch")
    if expected.get("protected_roots") != facts["protected_roots"]:
        raise PreflightError("preflight: protected-root facts mismatch")
    if expected.get("repository") != facts["repository"]:
        raise PreflightError("preflight: repository facts mismatch")
    if expected.get("roots") != facts["roots"]:
        raise PreflightError("preflight: root facts mismatch")
    if expected.get("workload") != WORKLOAD:
        raise PreflightError("preflight: workload constants mismatch")

    allowed_write_roots = require_list(preflight.get("allowed_write_roots"), "allowed write roots")
    expected_roots = [
        facts["roots"]["evidence_directory"]["canonical_path"],
        facts["roots"]["temporary_root"]["canonical_path"],
    ]
    if allowed_write_roots != sorted(expected_roots, key=lambda item: item.casefold()):
        raise PreflightError("preflight: allowed write roots must be exact")

    config_binding = None
    if config is not None:
        require_keys(
            config,
            {"canonicalization_id", "logical_name", "payload", "schema_id", "schema_version"},
            "s1 config envelope",
        )
        config_payload = require_keys(
            config.get("payload"),
            {
                "allowed_write_roots",
                "dependencies",
                "environment",
                "experiment_id",
                "generator",
                "observer",
                "path_invariants",
                "protected_root_inventories",
                "protocol_ref",
                "repository",
                "workload",
            },
            "s1 config payload",
        )
        dependencies = require_keys(
            config_payload.get("dependencies"),
            {"installation_inventory_ref", "packages", "wheel_inventory_ref"},
            "s1 config dependencies",
        )
        environment = require_keys(
            config_payload.get("environment"),
            {
                "cpython_implementation",
                "cpython_version",
                "platform",
                "python_executable_ref",
            },
            "s1 config environment",
        )
        generator = require_keys(
            config_payload.get("generator"),
            {"algorithm_id", "implementation_ref", "specification_ref"},
            "s1 config generator",
        )
        observer = require_keys(
            config_payload.get("observer"),
            {
                "configuration_ref",
                "implementation_ref",
                "redaction_registry_ref",
                "specification_ref",
            },
            "s1 config observer",
        )
        repository = require_keys(
            config_payload.get("repository"),
            {
                "clean_status_byte_count",
                "clean_status_sha256",
                "commit",
                "root",
            },
            "s1 config repository",
        )
        config_workload = {
            key: value
            for key, value in WORKLOAD.items()
            if key != "generator_algorithm"
        }
        if (
            config.get("canonicalization_id") != CANONICALIZATION_ID
            or config.get("schema_id") != "sa.m8.minimal.s1-config.v3"
            or config.get("schema_version") != SCHEMA_VERSION
            or config.get("logical_name") != f"minimal-1k/{experiment_id}/s1-config.json"
            or config_payload.get("experiment_id") != experiment_id
            or config_payload.get("workload") != config_workload
            or generator.get("algorithm_id") != WORKLOAD["generator_algorithm"]
        ):
            raise PreflightError("preflight: s1 config identity or workload mismatch")

        configured_roots = require_list(
            config_payload.get("allowed_write_roots"),
            "s1 config allowed write roots",
        )
        if len(configured_roots) != 2:
            raise PreflightError("preflight: s1 config allowed roots mismatch")
        configured_paths = []
        expected_root_classes = ("temporary-root", "evidence-directory")
        for index, (configured_root, expected_root_class) in enumerate(
            zip(configured_roots, expected_root_classes)
        ):
            root = require_keys(
                configured_root,
                {"binding", "root_class"},
                f"s1 config allowed write root {index}",
            )
            binding = require_keys(
                root.get("binding"),
                {"canonical_path", "parent_identity"},
                f"s1 config allowed write binding {index}",
            )
            if root.get("root_class") != expected_root_class:
                raise PreflightError("preflight: s1 config allowed roots mismatch")
            configured_path = binding.get("canonical_path")
            if not isinstance(configured_path, str):
                raise PreflightError("preflight: s1 config allowed roots mismatch")
            configured_paths.append(configured_path.replace("/", "\\"))
        if sorted(configured_paths, key=lambda item: item.casefold()) != allowed_write_roots:
            raise PreflightError("preflight: s1 config allowed roots mismatch")

        configured_packages = require_list(
            dependencies.get("packages"),
            "s1 config dependency packages",
        )
        expected_dependency_names = ("numpy", "lancedb", "pyarrow", "psutil")
        if len(configured_packages) != len(expected_dependency_names):
            raise PreflightError("preflight: s1 config dependency facts mismatch")
        for index, (configured_package, expected_name) in enumerate(
            zip(configured_packages, expected_dependency_names)
        ):
            package = require_keys(
                configured_package,
                {"name", "version", "wheel_ref"},
                f"s1 config dependency package {index}",
            )
            if (
                package.get("name") != expected_name
                or package.get("version") != facts["dependencies"].get(expected_name)
            ):
                raise PreflightError("preflight: s1 config dependency facts mismatch")

        if (
            environment.get("cpython_implementation")
            != facts["platform"]["implementation"]
            or environment.get("cpython_version")
            != facts["platform"]["python_version"]
            or environment.get("platform") != "win32"
        ):
            raise PreflightError("preflight: s1 config platform facts mismatch")

        validate_artifact_ref(
            dependencies.get("installation_inventory_ref"),
            facts,
            "installation-inventory",
            logical_name="environment/installed.json",
            role="environment",
        )
        validate_artifact_ref(
            dependencies.get("wheel_inventory_ref"),
            facts,
            "wheel-inventory",
            logical_name="wheels/inventory.json",
            role="inventory",
        )
        for package in configured_packages:
            package_name = package["name"]
            validate_artifact_ref(
                package.get("wheel_ref"),
                facts,
                f"wheel-{package_name}",
                logical_name=f"wheels/{package_name}.whl",
                role="artifact",
            )
        validate_artifact_ref(
            environment.get("python_executable_ref"),
            facts,
            "python-executable",
            logical_name="environment/python.json",
            role="environment",
        )
        validate_repository_file_ref(
            generator.get("implementation_ref"),
            facts,
            "generator-implementation",
            path="tools/m8_generate_minimal_1k_input_v3.py",
            role="implementation",
        )
        validate_repository_file_ref(
            generator.get("specification_ref"),
            facts,
            "generator-specification",
            path="docs/plans/references/m8-minimal-1k-v3-generator-spec.md",
            role="generator-spec",
        )
        configuration_ref = validate_artifact_ref(
            observer.get("configuration_ref"),
            facts,
            "observer-config",
            logical_name=OBSERVER_LOGICAL_NAME,
            role="artifact",
        )
        implementation_ref = validate_repository_file_ref(
            observer.get("implementation_ref"),
            facts,
            "observer-implementation",
            path="tools/m8_observe_minimal_1k_v3.py",
            role="implementation",
        )
        redaction_registry_ref = validate_artifact_ref(
            observer.get("redaction_registry_ref"),
            facts,
            "redaction-registry",
            logical_name=REDACTION_LOGICAL_NAME,
            role="artifact",
        )
        validate_repository_file_ref(
            observer.get("specification_ref"),
            facts,
            "observer-specification",
            path="docs/plans/references/m8-minimal-1k-v3-observer-spec.md",
            role="observer-spec",
        )
        if (
            observer_config is None
            or observer_config_data is None
            or redaction_registry is None
            or redaction_registry_data is None
        ):
            raise PreflightError(
                "preflight: observer config and redaction registry objects and bytes are required"
            )
        if (
            configuration_ref.get("byte_count") != len(observer_config_data)
            or configuration_ref.get("sha256") != sha256_hex(observer_config_data)
        ):
            raise PreflightError("preflight: observer config byte binding mismatch")
        if (
            redaction_registry_ref.get("byte_count") != len(redaction_registry_data)
            or redaction_registry_ref.get("sha256") != sha256_hex(redaction_registry_data)
        ):
            raise PreflightError("preflight: redaction registry byte binding mismatch")
        validate_redaction_registry(redaction_registry, redaction_registry_data)
        validate_observer_config(
            observer_config,
            observer_config_data,
            redaction_registry_data,
            implementation_ref,
            redaction_registry_ref,
        )
        validate_repository_file_ref(
            config_payload.get("protocol_ref"),
            facts,
            "protocol",
            path="docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md",
            role="protocol",
        )

        repository_root = require_keys(
            repository.get("root"),
            {"canonical_path", "parent_identity"},
            "s1 config repository root",
        )
        configured_repository_path = repository_root.get("canonical_path")
        if not isinstance(configured_repository_path, str):
            raise PreflightError("preflight: s1 config repository facts mismatch")
        expected_repository_parent = {
            **facts["repository"]["parent_identity"],
            "canonical_path": facts["repository"]["parent_identity"]["canonical_path"].replace("\\", "/"),
        }
        if (
            repository.get("commit") != facts["repository"]["commit_object"]
            or repository.get("clean_status_byte_count")
            != facts["repository"]["status_byte_count"]
            or repository.get("clean_status_sha256")
            != facts["repository"]["status_sha256"]
            or configured_repository_path.replace("/", "\\")
            != facts["repository"]["canonical_path"]
            or repository_root.get("parent_identity") != expected_repository_parent
        ):
            raise PreflightError("preflight: s1 config repository facts mismatch")

        configured_parent_identities = []
        for index, configured_root in enumerate(configured_roots):
            binding = configured_root["binding"]
            configured_parent_identities.append(binding["parent_identity"])
            expected_root_key = (
                "temporary_root" if index == 0 else "evidence_directory"
            )
            expected_parent_identity = {
                **facts["roots"][expected_root_key]["parent_identity"],
                "canonical_path": facts["roots"][expected_root_key]["parent_identity"]["canonical_path"].replace("\\", "/"),
            }
            if binding["parent_identity"] != expected_parent_identity:
                raise PreflightError("preflight: s1 config root parent identity mismatch")
        if configured_parent_identities[0] != configured_parent_identities[1]:
            raise PreflightError("preflight: s1 config allowed roots must share one parent")

        protected_inventories = require_list(
            config_payload.get("protected_root_inventories"),
            "s1 config protected root inventories",
        )
        if len(protected_inventories) != 2:
            raise PreflightError("preflight: s1 config protected root inventories mismatch")
        expected_protected = (
            (
                "repository-root",
                facts["repository"]["canonical_path"],
                "repository-preinventory",
                "repository-preinventory.json",
            ),
            (
                "production-root",
                facts["protected_roots"]["production_root"]["canonical_path"],
                "production-preinventory",
                "production-preinventory.json",
            ),
        )
        for index, expected_inventory in enumerate(expected_protected):
            expected_class, expected_path, frozen_name, logical_file = expected_inventory
            inventory = require_keys(
                protected_inventories[index],
                {"pre_inventory_ref", "root", "root_class"},
                f"s1 config protected root inventory {index}",
            )
            protected_root = require_keys(
                inventory.get("root"),
                {"canonical_path", "parent_identity"},
                f"s1 config protected root {index}",
            )
            configured_path = protected_root.get("canonical_path")
            expected_parent_identity = (
                facts["repository"]["parent_identity"]
                if expected_class == "repository-root"
                else facts["protected_roots"]["production_root"]["parent_identity"]
            )
            expected_parent_identity = {
                **expected_parent_identity,
                "canonical_path": expected_parent_identity["canonical_path"].replace("\\", "/"),
            }
            if (
                inventory.get("root_class") != expected_class
                or not isinstance(configured_path, str)
                or not same_path(configured_path.replace("/", "\\"), expected_path)
                or protected_root.get("parent_identity") != expected_parent_identity
            ):
                raise PreflightError("preflight: s1 config protected root inventories mismatch")
            validate_artifact_ref(
                inventory.get("pre_inventory_ref"),
                facts,
                frozen_name,
                logical_name=f"inventory/{logical_file}",
                role="inventory",
            )

        path_invariants = require_keys(
            config_payload.get("path_invariants"),
            {
                "evidence_outside_repository_and_production",
                "roots_distinct",
                "roots_not_ancestors",
                "same_parent",
                "temporary_outside_repository_and_production",
            },
            "s1 config path invariants",
        )
        if any(value is not True for value in path_invariants.values()):
            raise PreflightError("preflight: s1 config path invariants mismatch")

        if config_data is None:
            config_data = canonical_bytes(config)
        elif strict_json_bytes(config_data) != config or canonical_bytes(config) != config_data:
            raise PreflightError("preflight: supplied s1 config bytes are not canonical or do not match")
        config_binding = {
            "byte_count": len(config_data),
            "logical_name": config["logical_name"],
            "role": "s1-config",
            "schema_id": config["schema_id"],
            "sha256": sha256_hex(config_data),
        }
    elif config_data is not None:
        raise PreflightError("preflight: s1 config bytes require a config object")
    elif any(
        value is not None
        for value in (
            observer_config,
            observer_config_data,
            redaction_registry,
            redaction_registry_data,
        )
    ):
        raise PreflightError("preflight: observer artifacts require an s1 config object")

    s0_binding = require_keys(
        preflight.get("s0_binding"),
        {"byte_count", "logical_name", "role", "schema_id", "sha256"},
        "s0 binding",
    )
    actual_s0 = validate_s0(s0_path, str(s0_binding.get("sha256")), experiment_id)
    if s0_binding != actual_s0:
        raise PreflightError("preflight: s0 binding mismatch")
    revalidate_live_facts(facts)
    repository_path = Path(facts["repository"]["canonical_path"])
    try:
        commit = _git(repository_path, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
        tree = _git(repository_path, "rev-parse", "--verify", "HEAD^{tree}").decode("ascii").strip()
        status = _git(repository_path, "status", "--porcelain=v1", "--untracked-files=all")
    except UnicodeDecodeError as exc:
        raise PreflightError("current Git identity has invalid encoding") from exc
    if (
        commit != facts["repository"]["commit_object"]
        or tree != facts["repository"]["tree_object"]
        or status
    ):
        raise PreflightError("current worktree differs from the frozen Git object")
    result = {
        "canonicalization_id": CANONICALIZATION_ID,
        "experiment_id": experiment_id,
        "preflight_sha256": sha256_hex(canonical_bytes(preflight)),
        "schema_id": PREFLIGHT_RESULT_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "status": "S1_PREFLIGHT_VALID",
    }
    if config_binding is not None:
        result["config_ref"] = config_binding
    return result


def main(argv: list[str] | None = None) -> int:
    parser = ControlledParser(description=__doc__)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--s0", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--observer-config", required=True, type=Path)
    parser.add_argument("--redaction-registry", required=True, type=Path)
    try:
        args = parser.parse_args(argv)
        preflight, _ = load_canonical(args.preflight, "preflight")
        environment, _ = load_canonical(args.environment, "environment")
        config, config_data = load_canonical(args.config, "s1 config")
        observer_config, observer_config_data = load_canonical(
            args.observer_config, "observer config"
        )
        redaction_registry, redaction_registry_data = load_canonical(
            args.redaction_registry, "redaction registry"
        )
        result = validate_preflight(
            preflight,
            environment,
            args.s0,
            config,
            config_data,
            observer_config,
            observer_config_data,
            redaction_registry,
            redaction_registry_data,
        )
        sys.stdout.buffer.write(canonical_bytes(result))
        return 0
    except (PreflightError, ValueError, OSError) as exc:
        result = {
            "errors": [str(exc)],
            "schema_id": PREFLIGHT_RESULT_SCHEMA_ID,
            "status": "S1_PREFLIGHT_INVALID",
        }
        sys.stderr.buffer.write(canonical_bytes(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

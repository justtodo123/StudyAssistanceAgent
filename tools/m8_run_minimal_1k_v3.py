#!/usr/bin/env python3
"""Authorization controller for the M8 v3 minimal-1K runner.

Only a closed, embedded ``mock-tiny`` behavior exists.  This controller can
validate an owner S1 record and the S1 preflight result, then emit a bounded
test-only receipt without loading supplied code.  It deliberately contains no
real SQLite/LanceDB S2 implementation and never creates S2/S3 gate records.
On Windows, mock-root use fails closed until validation can retain a no-follow
handle through the complete validate-and-list operation.
"""
from __future__ import annotations

import argparse
import json
import ntpath
import os
import re
import stat
import sys
from pathlib import Path
from typing import NoReturn

from m8_probe_s1_environment_v3 import (
    CANONICALIZATION_ID,
    canonical_bytes,
    reject_constant,
    reject_duplicate_pairs,
)
from m8_validate_s1_preflight_v3 import (
    PREFLIGHT_RESULT_SCHEMA_ID,
    PreflightError,
    load_canonical,
    require_keys,
    sha256_hex,
    validate_preflight,
)

RUNNER_RESULT_SCHEMA_ID = "sa.m8.minimal.mock-runner-result.v3"
S0_SCHEMA_ID = "sa.m8.minimal.decision-record.v3"
S1_CONFIG_SCHEMA_ID = "sa.m8.minimal.s1-config.v3"
S1_GATE_SCHEMA_ID = "sa.m8.minimal.s1-gate.v3"
SCHEMA_VERSION = 3
EXTERNAL_SOURCES_ROOT = r"D:\111_Others_Subjects"
FORMAL_EXPERIMENT_ID = re.compile(
    r"^sa-m8-minimal-1k-v3-[a-z0-9][a-z0-9-]*$"
)
WINDOWS_MOCK_ROOT_FAIL_CLOSED = os.name == "nt"
WINDOWS_MOCK_ROOT_UNPROVEN = (
    "Windows mock-root isolation cannot be proven without a retained no-follow handle"
)


class RunnerError(ValueError):
    """A controlled authorization or mock-runner failure."""


class ControlledParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise RunnerError(message)


def strict_json(data: bytes) -> dict:
    value = json.loads(
        data,
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicate_pairs,
    )
    if not isinstance(value, dict):
        raise RunnerError("JSON root must be an object")
    return value


def validate_preflight_result(path: Path) -> dict:
    result, _ = load_canonical(path, "preflight result")
    require_keys(
        result,
        {
            "canonicalization_id",
            "config_ref",
            "experiment_id",
            "preflight_sha256",
            "schema_id",
            "schema_version",
            "status",
        },
        "preflight result",
    )
    config_ref = require_keys(
        result.get("config_ref"),
        {"byte_count", "logical_name", "role", "schema_id", "sha256"},
        "preflight config ref",
    )
    experiment_id = result.get("experiment_id")
    if (
        result.get("canonicalization_id") != CANONICALIZATION_ID
        or result.get("schema_id") != PREFLIGHT_RESULT_SCHEMA_ID
        or result.get("schema_version") != SCHEMA_VERSION
        or result.get("status") != "S1_PREFLIGHT_VALID"
        or not isinstance(experiment_id, str)
        or FORMAL_EXPERIMENT_ID.fullmatch(experiment_id) is None
        or config_ref.get("role") != "s1-config"
        or config_ref.get("schema_id") != S1_CONFIG_SCHEMA_ID
        or config_ref.get("logical_name")
        != f"minimal-1k/{experiment_id}/s1-config.json"
    ):
        raise RunnerError("preflight result is not uniquely valid")
    return result


def validate_s1(
    path: Path,
    preflight_result: dict,
    s0_path: Path,
    config_path: Path,
) -> dict:
    s1, data = load_canonical(path, "s1")
    require_keys(
        s1,
        {"canonicalization_id", "logical_name", "payload", "schema_id", "schema_version"},
        "s1 envelope",
    )
    payload = require_keys(
        s1.get("payload"),
        {
            "actor",
            "allowed_next_action",
            "authorization_checks",
            "config_ref",
            "decision",
            "experiment_id",
            "gate_id",
            "preflight_ref",
            "reason",
            "s0_ref",
            "scope",
        },
        "s1 payload",
    )
    actor = require_keys(payload.get("actor"), {"name", "role"}, "s1 actor")
    checks = require_keys(
        payload.get("authorization_checks"),
        {
            "config_validated",
            "dependencies_frozen",
            "generator_frozen",
            "observer_frozen",
            "paths_isolated",
            "protected_inventories_frozen",
            "repository_clean",
            "s0_accepted",
        },
        "s1 authorization checks",
    )
    config_ref = require_keys(
        payload.get("config_ref"),
        {"byte_count", "logical_name", "role", "schema_id", "sha256"},
        "s1 config ref",
    )
    s0_ref = require_keys(
        payload.get("s0_ref"),
        {"byte_count", "logical_name", "role", "schema_id", "sha256"},
        "s1 s0 ref",
    )
    preflight_ref = require_keys(
        payload.get("preflight_ref"),
        {"byte_count", "logical_name", "role", "schema_id", "sha256"},
        "s1 preflight ref",
    )
    scope = require_keys(
        payload.get("scope"),
        {"acquisition_network_allowed", "measured_network_allowed", "production_write_allowed", "synthetic_only", "workloads"},
        "s1 scope",
    )
    s0, s0_data = load_canonical(s0_path, "s0")
    if (
        s0_ref.get("role") != "s0"
        or s0_ref.get("schema_id") != S0_SCHEMA_ID
        or s0_ref.get("logical_name") != s0.get("logical_name")
        or s0_ref.get("sha256") != sha256_hex(s0_data)
        or s0_ref.get("byte_count") != len(s0_data)
    ):
        raise RunnerError("s1 s0 ref does not bind the supplied s0 bytes")
    result_bytes = canonical_bytes(preflight_result)
    experiment_id = preflight_result.get("experiment_id")
    if (
        preflight_ref.get("role") != "s1-preflight"
        or preflight_ref.get("schema_id") != PREFLIGHT_RESULT_SCHEMA_ID
        or preflight_ref.get("logical_name") != f"minimal-1k/{experiment_id}/s1-preflight.json"
        or preflight_ref.get("sha256") != sha256_hex(result_bytes)
        or preflight_ref.get("byte_count") != len(result_bytes)
    ):
        raise RunnerError("s1 preflight ref does not bind the recomputed result")
    config, config_data = load_canonical(config_path, "s1 config")
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
    if (
        config.get("canonicalization_id") != CANONICALIZATION_ID
        or config.get("schema_id") != S1_CONFIG_SCHEMA_ID
        or config.get("schema_version") != SCHEMA_VERSION
        or config.get("logical_name") != f"minimal-1k/{experiment_id}/s1-config.json"
        or config_payload.get("experiment_id") != experiment_id
        or config_ref.get("role") != "s1-config"
        or config_ref.get("schema_id") != S1_CONFIG_SCHEMA_ID
        or config_ref.get("logical_name") != config.get("logical_name")
        or config_ref.get("sha256") != sha256_hex(config_data)
        or config_ref.get("byte_count") != len(config_data)
    ):
        raise RunnerError("s1 config ref does not bind the supplied config bytes")
    expected_scope = {
        "acquisition_network_allowed": True,
        "measured_network_allowed": False,
        "production_write_allowed": False,
        "synthetic_only": True,
        "workloads": ["sqlite-linear-exact", "lancedb-embedded-exact-flat"],
    }
    if (
        s1.get("canonicalization_id") != CANONICALIZATION_ID
        or s1.get("schema_id") != S1_GATE_SCHEMA_ID
        or s1.get("schema_version") != SCHEMA_VERSION
        or s1.get("logical_name") != f"minimal-1k/{experiment_id}/s1-gate.json"
        or actor.get("role") != "owner"
        or not isinstance(actor.get("name"), str)
        or not actor.get("name")
        or any(value is not True for value in checks.values())
        or payload.get("allowed_next_action") != "run-s2"
        or payload.get("decision") != "DRY_RUN_AUTHORIZED"
        or payload.get("experiment_id") != experiment_id
        or payload.get("gate_id") != "S1"
        or not isinstance(payload.get("reason"), str)
        or not payload.get("reason")
        or scope != expected_scope
    ):
        raise RunnerError("exact owner DRY_RUN_AUTHORIZED/run-s2 gate is required")
    return {"object": s1, "bytes": data, "payload": payload}


def validate_preflight_binding(preflight_path: Path, preflight_result: dict) -> dict:
    preflight, data = load_canonical(preflight_path, "preflight")
    if sha256_hex(data) != preflight_result.get("preflight_sha256"):
        raise RunnerError("preflight result does not bind the supplied preflight bytes")
    if preflight.get("experiment_id") != preflight_result.get("experiment_id"):
        raise RunnerError("preflight experiment differs from the verified result")
    return preflight


def validate_mock_root(
    preflight: dict, environment: dict, mock_root: Path
) -> Path:
    roots = preflight.get("allowed_write_roots")
    if not isinstance(roots, list) or len(roots) != 2:
        raise RunnerError("preflight allowed root set is invalid")
    facts = environment.get("facts")
    if not isinstance(facts, dict):
        raise RunnerError("environment facts are invalid")
    repository = facts.get("repository")
    protected_roots = facts.get("protected_roots")
    if not isinstance(repository, dict) or not isinstance(protected_roots, dict):
        raise RunnerError("environment protected root set is invalid")
    production_root = protected_roots.get("production_root")
    if not isinstance(production_root, dict):
        raise RunnerError("environment production root is invalid")
    repository_path = repository.get("canonical_path")
    production_path = production_root.get("canonical_path")
    if not isinstance(repository_path, str) or not isinstance(production_path, str):
        raise RunnerError("environment protected path is invalid")
    try:
        root = Path(os.path.abspath(os.fspath(mock_root)))
        file_stat = root.lstat()
    except OSError as exc:
        raise RunnerError(f"mock root must already exist: {exc}") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISDIR(file_stat.st_mode)
        or stat.S_ISLNK(file_stat.st_mode)
        or bool(getattr(file_stat, "st_file_attributes", 0) & reparse_flag)
    ):
        raise RunnerError("mock root must be a regular existing directory")
    if WINDOWS_MOCK_ROOT_FAIL_CLOSED:
        raise RunnerError(WINDOWS_MOCK_ROOT_UNPROVEN)

    def normalized_path(value: str) -> str:
        return os.path.normcase(os.path.normpath(os.fspath(Path(value))))

    def windows_normalized_path(value: str) -> str:
        return ntpath.normcase(ntpath.normpath(value))

    def overlaps(left: str, right: str, *, windows: bool = False) -> bool:
        normalize = windows_normalized_path if windows else normalized_path
        left_value = normalize(left)
        right_value = normalize(right)
        path_module = ntpath if windows else os.path
        try:
            common = path_module.commonpath((left_value, right_value))
        except ValueError:
            return False
        return common == left_value or common == right_value

    normalized = normalized_path(os.fspath(root))
    for future_root in roots:
        if not isinstance(future_root, str):
            raise RunnerError("preflight allowed root set is invalid")
        if overlaps(normalized, future_root, windows=os.name != "nt"):
            raise RunnerError("mock root must not overlap a frozen future write root")
    for protected in (repository_path, production_path, EXTERNAL_SOURCES_ROOT):
        if overlaps(normalized, protected, windows=os.name != "nt"):
            raise RunnerError("mock root must not overlap a protected root")

    # Revalidate every existing parent component; no parent junction/symlink may
    # redirect the supposedly isolated synthetic root after lexical validation.
    current = root
    chain: list[Path] = []
    while True:
        chain.append(current)
        if current.parent == current:
            break
        current = current.parent
    for component in chain:
        try:
            component_stat = component.lstat()
        except OSError as exc:
            raise RunnerError("mock root parent chain cannot be verified") from exc
        if (
            stat.S_ISLNK(component_stat.st_mode)
            or bool(getattr(component_stat, "st_file_attributes", 0) & reparse_flag)
        ):
            raise RunnerError("mock root parent chain contains a reparse point")
    return root


def build_embedded_mock_result(context: dict[str, object], root: Path) -> dict[str, object]:
    """Return the only closed mock receipt supported by this controller."""

    if set(context) != {
        "config_sha256",
        "experiment_id",
        "mode",
        "preflight_sha256",
        "s1_sha256",
    }:
        raise RunnerError("embedded mock context has an open shape")
    if context.get("mode") != "mock-tiny":
        raise RunnerError("embedded mock context mode is invalid")
    experiment_id = context.get("experiment_id")
    if (
        not isinstance(experiment_id, str)
        or FORMAL_EXPERIMENT_ID.fullmatch(experiment_id) is None
    ):
        raise RunnerError("embedded mock experiment id is invalid")
    for name in ("config_sha256", "preflight_sha256", "s1_sha256"):
        value = context.get(name)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise RunnerError(f"embedded mock {name} is invalid")
    if WINDOWS_MOCK_ROOT_FAIL_CLOSED:
        raise RunnerError(WINDOWS_MOCK_ROOT_UNPROVEN)
    try:
        before = root.stat()
    except OSError as exc:
        raise RunnerError("embedded mock root cannot be revalidated") from exc
    if not stat.S_ISDIR(before.st_mode):
        raise RunnerError("embedded mock root is no longer a directory")
    entries = list(root.iterdir())
    try:
        after = root.stat()
    except OSError as exc:
        raise RunnerError("embedded mock root changed during validation") from exc
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        raise RunnerError("embedded mock root identity changed during validation")
    if entries:
        raise RunnerError("embedded mock root must be empty")
    return {
        "backend_id": "embedded-closed-mock-v1",
        "context": dict(context),
        "root_empty": True,
        "status": "PASS",
    }


def execute_mock(
    *,
    s0_path: Path,
    s1_path: Path,
    environment_path: Path,
    preflight_path: Path,
    preflight_result_path: Path,
    config_path: Path,
    observer_config_path: Path,
    redaction_registry_path: Path,
    mock_root: Path,
) -> dict:
    preflight, _ = load_canonical(preflight_path, "preflight")
    environment, _ = load_canonical(environment_path, "environment")
    config, config_data = load_canonical(config_path, "s1 config")
    observer_config, observer_config_data = load_canonical(
        observer_config_path, "observer config"
    )
    redaction_registry, redaction_registry_data = load_canonical(
        redaction_registry_path, "redaction registry"
    )
    supplied_result = validate_preflight_result(preflight_result_path)
    validate_preflight_binding(preflight_path, supplied_result)
    s1 = validate_s1(s1_path, supplied_result, s0_path, config_path)
    recomputed_result = validate_preflight(
        preflight,
        environment,
        s0_path,
        config,
        config_data,
        observer_config,
        observer_config_data,
        redaction_registry,
        redaction_registry_data,
    )
    if supplied_result != recomputed_result:
        raise RunnerError("supplied preflight result differs from recomputed validation")
    validate_preflight_binding(preflight_path, recomputed_result)
    root = validate_mock_root(preflight, environment, mock_root)
    context: dict[str, object] = {
        "config_sha256": recomputed_result["config_ref"]["sha256"],
        "experiment_id": recomputed_result["experiment_id"],
        "mode": "mock-tiny",
        "preflight_sha256": recomputed_result["preflight_sha256"],
        "s1_sha256": sha256_hex(s1["bytes"]),
    }
    result = build_embedded_mock_result(context, root)
    if set(result) != {"backend_id", "context", "root_empty", "status"}:
        raise RunnerError("embedded mock result has an open shape")
    if (
        result.get("backend_id") != "embedded-closed-mock-v1"
        or result.get("context") != context
        or result.get("root_empty") is not True
        or result.get("status") != "PASS"
    ):
        raise RunnerError("embedded mock result is invalid")
    return {
        "canonicalization_id": CANONICALIZATION_ID,
        "experiment_id": context["experiment_id"],
        "mock_result": result,
        "mode": "mock-tiny",
        "next_gate_created": False,
        "schema_id": RUNNER_RESULT_SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "status": "MOCK_TINY_COMPLETED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = ControlledParser(description=__doc__)
    parser.add_argument("--mode", choices=("mock-tiny",), required=True)
    parser.add_argument("--s0", required=True, type=Path)
    parser.add_argument("--s1", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--preflight-result", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--observer-config", required=True, type=Path)
    parser.add_argument("--redaction-registry", required=True, type=Path)
    parser.add_argument("--mock-root", required=True, type=Path)
    try:
        args = parser.parse_args(argv)
        result = execute_mock(
            s0_path=args.s0,
            s1_path=args.s1,
            environment_path=args.environment,
            preflight_path=args.preflight,
            preflight_result_path=args.preflight_result,
            config_path=args.config,
            observer_config_path=args.observer_config,
            redaction_registry_path=args.redaction_registry,
            mock_root=args.mock_root,
        )
        sys.stdout.buffer.write(canonical_bytes(result))
        return 0
    except (RunnerError, PreflightError, ValueError, OSError) as exc:
        result = {
            "errors": [str(exc)],
            "schema_id": RUNNER_RESULT_SCHEMA_ID,
            "status": "MOCK_TINY_BLOCKED",
        }
        sys.stderr.buffer.write(canonical_bytes(result))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

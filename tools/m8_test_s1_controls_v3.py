#!/usr/bin/env python3
"""Focused hermetic tests for M8 v3 S1 controls.

These tests use synthetic Windows facts and the closed embedded tiny mock.  They
do not install dependencies, import real vector backends, generate 1K input, or
create a production identity/evidence root.
"""
from __future__ import annotations

import copy
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Callable, TypeAlias
from unittest import mock

TOOLS = Path(__file__).resolve().parent
if os.fspath(TOOLS) not in sys.path:
    sys.path.insert(0, os.fspath(TOOLS))

import m8_probe_s1_environment_v3 as probe
import m8_run_minimal_1k_v3 as runner
import m8_validate_minimal_1k_graph_v3 as graph_validator
import m8_validate_s1_preflight_v3 as preflight


FAKE_COMMIT = "a" * 40
FAKE_TREE = "b" * 40
FAKE_DIGEST = "c" * 64
EXPERIMENT = "sa-m8-minimal-1k-v3-synthetic-s1-positive"
ORACLE_MANIFEST = "m8-minimal-1k-v3-s1-prereq-oracle-manifest.json"
EXPECTED_DECLARED_TEMPLATES = {
    "docs/plans/references/templates/m8-minimal-1k-observer-config-v3.json",
    "docs/plans/references/templates/m8-minimal-1k-redaction-registry-v3.json",
    "docs/plans/references/templates/m8-minimal-1k-s1-config-v3.json",
    "docs/plans/references/templates/m8-minimal-1k-s1-gate-v3.json",
}
ObserverMutation: TypeAlias = Callable[[dict], None]


ROOTS = {
    "evidence_directory": r"C:\synthetic\evidence",
    "temporary_root": r"C:\synthetic\temporary",
}


def fake_file(path: str, digest: str = FAKE_DIGEST) -> dict:
    return {"byte_count": 17, "canonical_path": path, "sha256": digest}


def fake_parent(path: str) -> dict:
    return {"canonical_path": path, "st_dev": 1, "st_ino": 2}


def synthetic_facts() -> dict:
    repository_paths = {
        "generator-implementation": r"C:\repo\tools\m8_generate_minimal_1k_input_v3.py",
        "generator-specification": (
            r"C:\repo\docs\plans\references\m8-minimal-1k-v3-generator-spec.md"
        ),
        "observer-implementation": r"C:\repo\tools\m8_observe_minimal_1k_v3.py",
        "observer-specification": (
            r"C:\repo\docs\plans\references\m8-minimal-1k-v3-observer-spec.md"
        ),
        "production-preinventory": r"C:\repo\synthetic-artifacts\production-preinventory.json",
        "protocol": (
            r"C:\repo\docs\plans\references\m8-minimal-1k-dry-run-protocol-v3.md"
        ),
        "repository-preinventory": r"C:\repo\synthetic-artifacts\repository-preinventory.json",
    }
    files = {
        name: fake_file(
            repository_paths.get(name, rf"C:\repo\synthetic-artifacts\{name}.json")
        )
        for name in sorted(preflight.FROZEN_FILE_NAMES)
    }
    observer_path = Path(__file__).with_name("m8_observe_minimal_1k_v3.py")
    observer_data = observer_path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in observer_data:
        raise RuntimeError("observer implementation contains a non-CRLF carriage return")
    files["observer-implementation"]["byte_count"] = len(observer_data)
    files["observer-implementation"]["sha256"] = probe.sha256_hex(observer_data)
    return {
        "dependencies": {name: "1.0.0" for name in probe.DEPENDENCIES},
        "files": files,
        "platform": {
            "implementation": "CPython",
            "python_version": "3.12.0",
            "python_executable": r"C:\Python312\python.exe",
            "system": "Windows",
        },
        "protected_roots": {
            "production_root": {
                "canonical_path": r"C:\production",
                "parent_identity": fake_parent("C:\\"),
            }
        },
        "repository": {
            "canonical_path": r"C:\repo",
            "clean": True,
            "commit_object": FAKE_COMMIT,
            "parent_identity": fake_parent("C:\\"),
            "status_byte_count": 0,
            "status_sha256": probe.sha256_hex(b""),
            "tree_object": FAKE_TREE,
            "worktree_head": FAKE_COMMIT,
            "worktree_head_matches_commit_object": True,
        },
        "roots": {
            name: {
                "canonical_path": path,
                "exists": False,
                "parent_identity": fake_parent(ntpath_dirname(path)),
            }
            for name, path in ROOTS.items()
        },
    }


def ntpath_dirname(path: str) -> str:
    # Keep this helper local so the synthetic fixture is independent of the
    # host filesystem and of pathlib's host-specific parsing.
    import ntpath

    return ntpath.dirname(path)


def synthetic_probe() -> dict:
    facts = synthetic_facts()
    return {
        "canonicalization_id": probe.CANONICALIZATION_ID,
        "facts": facts,
        "schema_id": probe.SCHEMA_ID,
        "schema_version": probe.SCHEMA_VERSION,
    }


def write_canonical(path: Path, value: object) -> bytes:
    data = probe.canonical_bytes(value)
    path.write_bytes(data)
    return data


def s0_object() -> dict:
    return {
        "canonicalization_id": probe.CANONICALIZATION_ID,
        "logical_name": f"minimal-1k/{EXPERIMENT}/s0.json",
        "payload": {
            "actor_role": "independent-reviewer",
            "allowed_next_action": "request-s1",
            "decision": "PROTOCOL_ACCEPTED",
            "experiment_id": EXPERIMENT,
            "gate_id": "S0",
            "read_refs": [],
        },
        "schema_id": "sa.m8.minimal.decision-record.v3",
        "schema_version": 3,
    }


def preflight_object(environment: dict, s0_data: bytes) -> dict:
    facts = environment["facts"]
    return {
        "allowed_write_roots": sorted(ROOTS.values(), key=lambda item: item.casefold()),
        "canonicalization_id": probe.CANONICALIZATION_ID,
        "environment_facts_sha256": probe.sha256_hex(probe.canonical_bytes(environment)),
        "experiment_id": EXPERIMENT,
        "expected": {
            "dependencies": facts["dependencies"],
            "files": facts["files"],
            "platform": facts["platform"],
            "protected_roots": facts["protected_roots"],
            "repository": facts["repository"],
            "roots": facts["roots"],
            "workload": preflight.WORKLOAD,
        },
        "s0_binding": {
            "byte_count": len(s0_data),
            "logical_name": f"minimal-1k/{EXPERIMENT}/s0.json",
            "role": "s0",
            "schema_id": "sa.m8.minimal.decision-record.v3",
            "sha256": probe.sha256_hex(s0_data),
        },
        "schema_id": preflight.PREFLIGHT_SCHEMA_ID,
        "schema_version": 3,
    }


def config_object(environment: dict) -> dict:
    facts = environment["facts"]

    def artifact_ref(
        role: str,
        logical_name: str,
        schema_id: str,
        frozen_name: str | None = None,
        digest: str | None = None,
    ) -> dict:
        frozen = facts["files"].get(frozen_name or "")
        return {
            "byte_count": frozen["byte_count"] if frozen else 17,
            "logical_name": logical_name,
            "role": role,
            "schema_id": schema_id,
            "sha256": digest or (frozen["sha256"] if frozen else FAKE_DIGEST),
        }

    def repository_ref(role: str, path: str, frozen_name: str) -> dict:
        frozen = facts["files"][frozen_name]
        return {
            "byte_count": frozen["byte_count"],
            "path": path,
            "role": role,
            "sha256": frozen["sha256"],
        }

    shared_parent = {
        **facts["roots"]["temporary_root"]["parent_identity"],
        "canonical_path": facts["roots"]["temporary_root"]["parent_identity"]["canonical_path"].replace("\\", "/"),
    }
    repository_parent = {
        **facts["repository"]["parent_identity"],
        "canonical_path": facts["repository"]["parent_identity"]["canonical_path"].replace("\\", "/"),
    }
    production_root = facts["protected_roots"]["production_root"]
    production_parent = {
        **production_root["parent_identity"],
        "canonical_path": production_root["parent_identity"]["canonical_path"].replace("\\", "/"),
    }
    return {
        "canonicalization_id": probe.CANONICALIZATION_ID,
        "logical_name": f"minimal-1k/{EXPERIMENT}/s1-config.json",
        "payload": {
            "allowed_write_roots": [
                {
                    "binding": {
                        "canonical_path": ROOTS["temporary_root"].replace("\\", "/"),
                        "parent_identity": shared_parent,
                    },
                    "root_class": "temporary-root",
                },
                {
                    "binding": {
                        "canonical_path": ROOTS["evidence_directory"].replace("\\", "/"),
                        "parent_identity": shared_parent,
                    },
                    "root_class": "evidence-directory",
                },
            ],
            "dependencies": {
                "installation_inventory_ref": artifact_ref(
                    "environment",
                    "environment/installed.json",
                    "sa.m8.minimal.installation-inventory.v3",
                    "installation-inventory",
                ),
                "packages": [
                    {
                        "name": name,
                        "version": facts["dependencies"][name],
                        "wheel_ref": artifact_ref(
                            "artifact",
                            f"wheels/{name}.whl",
                            "sa.m8.minimal.wheel.v3",
                            f"wheel-{name}",
                        ),
                    }
                    for name in ("numpy", "lancedb", "pyarrow", "psutil")
                ],
                "wheel_inventory_ref": artifact_ref(
                    "inventory",
                    "wheels/inventory.json",
                    "sa.m8.minimal.wheel-inventory.v3",
                    "wheel-inventory",
                ),
            },
            "environment": {
                "cpython_implementation": "CPython",
                "cpython_version": facts["platform"]["python_version"],
                "platform": "win32",
                "python_executable_ref": artifact_ref(
                    "environment",
                    "environment/python.json",
                    "sa.m8.minimal.python-executable.v3",
                    "python-executable",
                ),
            },
            "experiment_id": EXPERIMENT,
            "generator": {
                "algorithm_id": "sa-m8-synthetic-unit-v3",
                "implementation_ref": repository_ref(
                    "implementation",
                    "tools/m8_generate_minimal_1k_input_v3.py",
                    "generator-implementation",
                ),
                "specification_ref": repository_ref(
                    "generator-spec",
                    "docs/plans/references/m8-minimal-1k-v3-generator-spec.md",
                    "generator-specification",
                ),
            },
            "observer": {
                "configuration_ref": artifact_ref(
                    "artifact",
                    "observer/config.json",
                    "sa.m8.minimal.observer-config.v3",
                    "observer-config",
                ),
                "implementation_ref": repository_ref(
                    "implementation",
                    "tools/m8_observe_minimal_1k_v3.py",
                    "observer-implementation",
                ),
                "redaction_registry_ref": artifact_ref(
                    "artifact",
                    "observer/redaction.json",
                    "sa.m8.minimal.redaction-registry.v3",
                    "redaction-registry",
                ),
                "specification_ref": repository_ref(
                    "observer-spec",
                    "docs/plans/references/m8-minimal-1k-v3-observer-spec.md",
                    "observer-specification",
                ),
            },
            "path_invariants": {
                "evidence_outside_repository_and_production": True,
                "roots_distinct": True,
                "roots_not_ancestors": True,
                "same_parent": True,
                "temporary_outside_repository_and_production": True,
            },
            "protected_root_inventories": [
                {
                    "pre_inventory_ref": artifact_ref(
                        "inventory",
                        f"inventory/{logical_file}",
                        "sa.m8.minimal.pre-inventory.v3",
                        frozen_name=frozen_name,
                    ),
                    "root": {
                        "canonical_path": path,
                        "parent_identity": parent_identity,
                    },
                    "root_class": root_class,
                }
                for root_class, path, parent_identity, frozen_name, logical_file in (
                    (
                        "repository-root",
                        facts["repository"]["canonical_path"].replace("\\", "/"),
                        repository_parent,
                        "repository-preinventory",
                        "repository-preinventory.json",
                    ),
                    (
                        "production-root",
                        production_root["canonical_path"].replace("\\", "/"),
                        production_parent,
                        "production-preinventory",
                        "production-preinventory.json",
                    ),
                )
            ],
            "protocol_ref": repository_ref(
                "protocol",
                "docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md",
                "protocol",
            ),
            "repository": {
                "clean_status_byte_count": 0,
                "clean_status_sha256": probe.sha256_hex(b""),
                "commit": facts["repository"]["commit_object"],
                "root": {
                    "canonical_path": facts["repository"]["canonical_path"].replace("\\", "/"),
                    "parent_identity": repository_parent,
                },
            },
            "workload": {
                key: value
                for key, value in preflight.WORKLOAD.items()
                if key != "generator_algorithm"
            },
        },
        "schema_id": runner.S1_CONFIG_SCHEMA_ID,
        "schema_version": 3,
    }


def redaction_registry_object() -> dict:
    patterns = [
        {
            "category": category,
            "matcher_kind": "digest-literal",
            "needle_sha256": probe.sha256_hex(category.encode("utf-8")),
            "pattern_id": f"p{index:02d}-{category}",
        }
        for index, category in enumerate(preflight.REDACTION_PATTERN_CATEGORIES, start=1)
    ]
    return {
        "canonicalization_id": probe.CANONICALIZATION_ID,
        "payload": {
            "binary_allowlist": [
                {"path": "vectors/chunks.f32le", "sha256": "1" * 64},
                {"path": "vectors/queries.f32le", "sha256": "2" * 64},
            ],
            "matcher_algorithm": preflight.REDACTION_MATCHER_ALGORITHM,
            "patterns": patterns,
            "unknown_binary_policy": "fail-closed",
        },
        "schema_id": preflight.REDACTION_REGISTRY_SCHEMA_ID,
        "schema_version": preflight.SCHEMA_VERSION,
    }


def observer_config_object(environment: dict, registry_data: bytes) -> dict:
    frozen = environment["facts"]["files"]["observer-implementation"]
    implementation_ref = {
        "byte_count": frozen["byte_count"],
        "path": "tools/m8_observe_minimal_1k_v3.py",
        "role": "implementation",
        "sha256": frozen["sha256"],
    }
    api_ids = {
        "network": ["fake-network-event-stream"],
        "write": ["fake-write-event-stream"],
        "process": ["fake-process-event-stream"],
        "redaction": ["fake-redaction-scan-stream"],
    }
    return {
        "canonicalization_id": probe.CANONICALIZATION_ID,
        "logical_name": preflight.OBSERVER_LOGICAL_NAME,
        "payload": {
            "components": [
                {
                    "api_ids": api_ids[component_id],
                    "bounded_retry_count": 2,
                    "component_id": component_id,
                    "coverage_strategy": preflight.OBSERVER_COVERAGE_STRATEGIES[component_id],
                    "implementation_ref": copy.deepcopy(implementation_ref),
                    "parameters": {
                        "arguments": [f"--{component_id}-synthetic"],
                        "flags": ["fail-closed"],
                    },
                    "poll_interval_ms": 10,
                    "timeout_ms": 1000,
                }
                for component_id in preflight.OBSERVER_COMPONENT_IDS
            ],
            "error_code_registry": list(preflight.OBSERVER_ERROR_CODES),
            "persistent_file_allowlist": [
                {
                    "classification": "utf8-jsonl",
                    "path": f"events/{observer}.jsonl",
                    "schema_id": "sa.m8.minimal.observer-ledger.v3",
                }
                for observer in sorted(preflight.OBSERVER_COMPONENT_IDS)
            ],
            "redaction_registry_ref": {
                "byte_count": len(registry_data),
                "logical_name": preflight.REDACTION_LOGICAL_NAME,
                "role": "artifact",
                "schema_id": preflight.REDACTION_REGISTRY_SCHEMA_ID,
                "sha256": probe.sha256_hex(registry_data),
            },
        },
        "schema_id": preflight.OBSERVER_CONFIG_SCHEMA_ID,
        "schema_version": preflight.SCHEMA_VERSION,
    }


def observer_artifacts(environment: dict) -> tuple[dict, bytes, dict, bytes]:
    registry = redaction_registry_object()
    registry_data = probe.canonical_bytes(registry)
    observer_config = observer_config_object(environment, registry_data)
    observer_config_data = probe.canonical_bytes(observer_config)
    for name, data in (
        ("observer-config", observer_config_data),
        ("redaction-registry", registry_data),
    ):
        environment["facts"]["files"][name]["byte_count"] = len(data)
        environment["facts"]["files"][name]["sha256"] = probe.sha256_hex(data)
    return observer_config, observer_config_data, registry, registry_data


def schema_errors(instance: object, schema: dict) -> list[str]:
    """Validate the closed JSON Schema subset used by the S1 config contract."""
    errors: list[str] = []
    definitions = schema.get("$defs", {})

    def add(path: str, message: str) -> None:
        errors.append(f"{path}: {message}")

    def visit(value: object, rule: object, path: str) -> None:
        if not isinstance(rule, dict):
            add(path, "schema rule must be an object")
            return
        reference = rule.get("$ref")
        if reference is not None:
            prefix = "#/$defs/"
            if not isinstance(reference, str) or not reference.startswith(prefix):
                add(path, "unsupported schema reference")
                return
            target = definitions.get(reference[len(prefix):])
            if not isinstance(target, dict):
                add(path, "missing schema definition")
                return
            visit(value, target, path)
        branches = rule.get("allOf", [])
        if not isinstance(branches, list):
            add(path, "allOf must be an array")
            return
        for branch in branches:
            visit(value, branch, path)
        if "const" in rule and value != rule["const"]:
            add(path, "const mismatch")
        if "enum" in rule and value not in rule["enum"]:
            add(path, "enum mismatch")

        expected_type = rule.get("type")
        valid_type = True
        if expected_type == "array":
            valid_type = isinstance(value, list)
        elif expected_type == "boolean":
            valid_type = isinstance(value, bool)
        elif expected_type == "integer":
            valid_type = isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "object":
            valid_type = isinstance(value, dict)
        elif expected_type == "string":
            valid_type = isinstance(value, str)
        elif expected_type is not None:
            add(path, "unsupported schema type")
            return
        if not valid_type:
            add(path, f"expected {expected_type}")
            return

        if isinstance(value, dict):
            properties = rule.get("properties", {})
            required = rule.get("required", [])
            for name in required:
                if name not in value:
                    add(path, f"missing required property {name}")
            if rule.get("additionalProperties") is False:
                for name in value:
                    if name not in properties:
                        add(path, f"additional property {name}")
            for name, child_rule in properties.items():
                if name in value:
                    visit(value[name], child_rule, f"{path}.{name}")
        elif isinstance(value, list):
            minimum = rule.get("minItems")
            maximum = rule.get("maxItems")
            if isinstance(minimum, int) and len(value) < minimum:
                add(path, "too few items")
            if isinstance(maximum, int) and len(value) > maximum:
                add(path, "too many items")
            prefixes = rule.get("prefixItems", [])
            for index, child_rule in enumerate(prefixes[:len(value)]):
                visit(value[index], child_rule, f"{path}[{index}]")
            item_rule = rule.get("items")
            if item_rule is False and len(value) > len(prefixes):
                add(path, "additional array items")
            elif isinstance(item_rule, dict):
                start = len(prefixes) if prefixes else 0
                for index in range(start, len(value)):
                    visit(value[index], item_rule, f"{path}[{index}]")
            if rule.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
                add(path, "duplicate array item")
        elif isinstance(value, str):
            minimum = rule.get("minLength")
            maximum = rule.get("maxLength")
            if isinstance(minimum, int) and len(value) < minimum:
                add(path, "string too short")
            if isinstance(maximum, int) and len(value) > maximum:
                add(path, "string too long")
            pattern = rule.get("pattern")
            if isinstance(pattern, str):
                try:
                    matched = re.search(pattern, value)
                except re.error as exc:
                    add(path, f"invalid schema pattern: {exc}")
                else:
                    if matched is None:
                        add(path, "pattern mismatch")
        elif isinstance(value, int) and not isinstance(value, bool):
            minimum = rule.get("minimum")
            if isinstance(minimum, int) and value < minimum:
                add(path, "integer below minimum")

    visit(instance, schema, "$")
    return errors


def replace_template_placeholders(
    value: object,
    replacements: dict[str, object],
    structured_replacements: dict[tuple[str | int, ...], object] | None = None,
) -> object:
    """Replace parsed placeholder values and declared structured slots."""
    structured = structured_replacements or {}
    if () in structured:
        raise AssertionError("structured replacement cannot replace the template root")
    consumed: set[tuple[str | int, ...]] = set()

    def visit(current: object, path: tuple[str | int, ...]) -> object:
        if path in structured:
            consumed.add(path)
            return copy.deepcopy(structured[path])
        if isinstance(current, dict):
            return {
                key: visit(child, (*path, key))
                for key, child in current.items()
            }
        if isinstance(current, list):
            return [
                visit(child, (*path, index))
                for index, child in enumerate(current)
            ]
        if isinstance(current, str):
            matches = re.findall(r"__[A-Z0-9_]+_PLACEHOLDER__", current)
            if not matches:
                return current
            if current in replacements:
                return copy.deepcopy(replacements[current])
            replaced = current
            for placeholder in matches:
                replacement = replacements.get(placeholder)
                if replacement is None or not isinstance(replacement, str):
                    raise AssertionError(
                        f"missing string replacement for {placeholder}"
                    )
                replaced = replaced.replace(placeholder, replacement)
            return replaced
        return copy.deepcopy(current)

    result = visit(value, ())
    missing = set(structured).difference(consumed)
    if missing:
        path = sorted(missing, key=repr)[0]
        raise AssertionError(
            f"structured replacement path is absent: {path!r}"
        )
    return result



def assert_structured_replacement_rejections() -> None:
    """Reject malformed or unconsumed parsed-tree replacement paths."""
    template = {"payload": {"items": [{"value": "unchanged"}]}}
    rejected: tuple[dict[tuple[str | int, ...], object], ...] = (
        {("missing", "leaf"): "value"},
        {("payload", "missing", "leaf"): "value"},
        {("payload", "deleted_slot"): "value"},
        {("payload", "items", 2, "value"): "value"},
        {("payload", "items", 0, 0): "value"},
        {(): "value"},
    )
    for structured in rejected:
        try:
            replace_template_placeholders(template, {}, structured)
        except AssertionError:
            continue
        raise AssertionError(
            f"malformed structured replacement was accepted: {structured!r}"
        )


def assert_raw_text_substitution_is_not_an_instantiation_path() -> None:
    """Raw byte replacement cannot produce the typed structured instance."""
    raw = b'{"payload":{"enabled":"__BOOLEAN_PLACEHOLDER__"}}\n'
    parsed = probe.strict_json(raw)
    populated = replace_template_placeholders(
        parsed,
        {"__BOOLEAN_PLACEHOLDER__": True},
    )
    canonical = probe.canonical_bytes(populated)
    if canonical != b'{"payload":{"enabled":true}}\n':
        raise AssertionError("parsed-tree replacement did not preserve the typed value")
    textually_substituted = raw.replace(
        b"__BOOLEAN_PLACEHOLDER__",
        b"true",
    )
    textual_value = probe.strict_json(textually_substituted)
    if textual_value == populated:
        raise AssertionError("raw textual substitution reproduced the typed instance")
    if not isinstance(textual_value, dict):
        raise AssertionError("raw textual substitution changed the root type")
    textual_payload = textual_value.get("payload")
    if not isinstance(textual_payload, dict):
        raise AssertionError("raw textual substitution changed the payload type")
    if not isinstance(textual_payload.get("enabled"), str):
        raise AssertionError("raw textual substitution unexpectedly preserved the type")

class S1ControlsTests(unittest.TestCase):
    def test_s1_contract_documents_are_strict_and_schema_compatible(self) -> None:
        references = Path(__file__).resolve().parents[1] / "docs" / "plans" / "references"
        schema_paths = (
            references / "schemas" / "m8-minimal-1k-s1-config-v3.schema.json",
            references / "schemas" / "m8-minimal-1k-s1-gate-v3.schema.json",
            references / "schemas" / "m8-minimal-1k-observer-config-v3.schema.json",
            references / "schemas" / "m8-minimal-1k-redaction-registry-v3.schema.json",
        )
        template_paths = (
            references / "templates" / "m8-minimal-1k-s1-config-v3.json",
            references / "templates" / "m8-minimal-1k-s1-gate-v3.json",
            references / "templates" / "m8-minimal-1k-observer-config-v3.json",
            references / "templates" / "m8-minimal-1k-redaction-registry-v3.json",
        )
        parsed = {}
        for path in (*schema_paths, *template_paths):
            with self.subTest(path=path.name):
                value = preflight.strict_json_bytes(path.read_bytes())
                parsed[path.name] = value

        config_schema = parsed[schema_paths[0].name]
        gate_schema = parsed[schema_paths[1].name]
        observer_schema = parsed[schema_paths[2].name]
        redaction_schema = parsed[schema_paths[3].name]
        for schema in (
            config_schema,
            gate_schema,
            observer_schema,
            redaction_schema,
        ):
            self.assertEqual(
                schema["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )
        workload_schema = config_schema["$defs"]["workload"]
        expected_workload = {
            key: value
            for key, value in preflight.WORKLOAD.items()
            if key != "generator_algorithm"
        }
        self.assertEqual(set(workload_schema["properties"]), set(expected_workload))
        self.assertEqual(set(workload_schema["required"]), set(expected_workload))
        self.assertFalse(workload_schema["additionalProperties"])
        self.assertFalse(workload_schema["properties"]["backends"]["items"])
        self.assertFalse(workload_schema["properties"]["top_k"]["items"])
        artifact_refs = config_schema["$defs"]
        self.assertEqual(
            artifact_refs["installation_inventory_ref"]["allOf"][1]["properties"]["schema_id"]["const"],
            preflight.ARTIFACT_SCHEMA_IDS["installation-inventory"],
        )
        self.assertEqual(
            artifact_refs["pre_inventory_ref"]["allOf"][1]["properties"]["schema_id"]["const"],
            preflight.ARTIFACT_SCHEMA_IDS["repository-preinventory"],
        )

        config = config_object(synthetic_probe())
        self.assertEqual(schema_errors(config, config_schema), [])
        payload = config["payload"]
        self.assertEqual(payload["workload"], expected_workload)
        for root in payload["allowed_write_roots"]:
            self.assertRegex(root["binding"]["canonical_path"], r"^[A-Z]:/[^\\]+$")
        for root in payload["protected_root_inventories"]:
            self.assertRegex(root["root"]["canonical_path"], r"^[A-Z]:/[^\\]+$")
        self.assertRegex(payload["repository"]["root"]["canonical_path"], r"^[A-Z]:/[^\\]+$")

        malformed_parents = {
            "missing-st-ino": {"canonical_path": "C:/", "st_dev": 1},
            "legacy-fields": {
                "file_id": "synthetic",
                "volume_serial_number": "synthetic",
            },
            "string-st-dev": {
                "canonical_path": "C:/",
                "st_dev": "1",
                "st_ino": 2,
            },
            "string-st-ino": {
                "canonical_path": "C:/",
                "st_dev": 1,
                "st_ino": "2",
            },
            "negative-st-dev": {
                "canonical_path": "C:/",
                "st_dev": -1,
                "st_ino": 2,
            },
            "negative-st-ino": {
                "canonical_path": "C:/",
                "st_dev": 1,
                "st_ino": -2,
            },
            "lowercase-drive": {
                "canonical_path": "c:/",
                "st_dev": 1,
                "st_ino": 2,
            },
            "backslash": {
                "canonical_path": "C:\\",
                "st_dev": 1,
                "st_ino": 2,
            },
            "parent-traversal": {
                "canonical_path": "C:/safe/../escape",
                "st_dev": 1,
                "st_ino": 2,
            },
            "malformed-drive-root": {
                "canonical_path": "C://",
                "st_dev": 1,
                "st_ino": 2,
            },
            "doubled-separator": {
                "canonical_path": "C:/safe//child",
                "st_dev": 1,
                "st_ino": 2,
            },
        }
        for name, parent_identity in malformed_parents.items():
            changed = copy.deepcopy(config)
            changed["payload"]["repository"]["root"]["parent_identity"] = parent_identity
            with self.subTest(parent_identity=name):
                self.assertTrue(schema_errors(changed, config_schema))

        drive_root = copy.deepcopy(config)
        drive_root["payload"]["repository"]["root"]["parent_identity"] = {
            "canonical_path": "C:/",
            "st_dev": 1,
            "st_ino": 2,
        }
        self.assertEqual(schema_errors(drive_root, config_schema), [])

        config_template = parsed[template_paths[0].name]
        self.assertTrue(
            schema_errors(config_template, config_schema),
            "blank placeholder template must remain a non-authorizing non-instance",
        )
        self.assertEqual(set(config_template["payload"]), set(config_schema["properties"]["payload"]["properties"]))
        self.assertEqual(
            set(config_template["payload"]["workload"]),
            set(workload_schema["properties"]),
        )

        observer_template = parsed[template_paths[2].name]
        redaction_template = parsed[template_paths[3].name]
        self.assertTrue(
            schema_errors(observer_template, observer_schema),
            "blank observer template must remain a non-instance",
        )
        self.assertTrue(
            schema_errors(redaction_template, redaction_schema),
            "blank redaction template must remain a non-instance",
        )
        environment = synthetic_probe()
        observer_config, _, registry, _ = observer_artifacts(environment)
        self.assertEqual(schema_errors(observer_config, observer_schema), [])
        self.assertEqual(schema_errors(registry, redaction_schema), [])
        self.assertEqual(
            observer_schema["properties"]["logical_name"]["const"],
            preflight.OBSERVER_LOGICAL_NAME,
        )
        self.assertEqual(
            redaction_schema["properties"]["payload"]["properties"]
            ["matcher_algorithm"]["const"],
            preflight.REDACTION_MATCHER_ALGORITHM,
        )
        self.assertEqual(
            redaction_schema["properties"]["payload"]["properties"]
            ["unknown_binary_policy"]["const"],
            "fail-closed",
        )

    def test_declared_templates_are_canonical_blank_non_instances(self) -> None:
        assert_structured_replacement_rejections()
        assert_raw_text_substitution_is_not_an_instantiation_path()
        repository = Path(__file__).resolve().parents[1]
        references = repository / "docs" / "plans" / "references"
        manifest_path = references / ORACLE_MANIFEST
        manifest_raw = manifest_path.read_bytes()
        manifest_value = probe.strict_json(manifest_raw)
        if not isinstance(manifest_value, dict):
            self.fail("oracle manifest must be an object")
        manifest = manifest_value
        declared_value = manifest.get("declared_templates")
        if not isinstance(declared_value, list):
            self.fail("oracle manifest declared_templates must be a list")
        declared = declared_value
        self.assertEqual(len(declared), 4)
        self.assertTrue(all(isinstance(path, str) for path in declared))
        self.assertEqual(set(declared), EXPECTED_DECLARED_TEMPLATES)
        self.assertEqual(len(set(declared)), len(declared))

        schema_names = {
            "m8-minimal-1k-observer-config-v3.json": "m8-minimal-1k-observer-config-v3.schema.json",
            "m8-minimal-1k-redaction-registry-v3.json": "m8-minimal-1k-redaction-registry-v3.schema.json",
            "m8-minimal-1k-s1-config-v3.json": "m8-minimal-1k-s1-config-v3.schema.json",
            "m8-minimal-1k-s1-gate-v3.json": "m8-minimal-1k-s1-gate-v3.schema.json",
        }
        replacements: dict[str, object] = {
            "__ALLOWED_NEXT_ACTION_PLACEHOLDER__": "stop",
            "__BOOLEAN_PLACEHOLDER__": True,
            "__BOUNDED_RETRY_COUNT_PLACEHOLDER__": 1,
            "__BYTE_COUNT_PLACEHOLDER__": 1,
            "__CANONICAL_WINDOWS_PARENT_PATH_PLACEHOLDER__": "C:/synthetic",
            "__CANONICAL_WINDOWS_PATH_PLACEHOLDER__": "C:/synthetic/path",
            "__CLEAN_STATUS_BYTE_COUNT_PLACEHOLDER__": 0,
            "__CLEAN_STATUS_SHA256_PLACEHOLDER__": probe.sha256_hex(b""),
            "__CPYTHON_VERSION_PLACEHOLDER__": "3.12.0",
            "__DECISION_PLACEHOLDER__": "NOT_AUTHORIZED",
            "__EXPERIMENT_ID_PLACEHOLDER__": EXPERIMENT,
            "__LANCEDB_VERSION_PLACEHOLDER__": "1.0.0",
            "__LOGICAL_NAME_PLACEHOLDER__": "synthetic/artifact.json",
            "__NUMPY_VERSION_PLACEHOLDER__": "1.0.0",
            "__OWNER_NAME_PLACEHOLDER__": "synthetic-owner",
            "__POLL_INTERVAL_MS_PLACEHOLDER__": 1,
            "__PSUTIL_VERSION_PLACEHOLDER__": "1.0.0",
            "__PYARROW_VERSION_PLACEHOLDER__": "1.0.0",
            "__REASON_PLACEHOLDER__": "synthetic non-authorizing template test",
            "__REPOSITORY_COMMIT_PLACEHOLDER__": FAKE_COMMIT,
            "__REPOSITORY_RELATIVE_PATH_PLACEHOLDER__": "tools/synthetic.py",
            "__S0_EXPERIMENT_ID_PLACEHOLDER__": EXPERIMENT,
            "__SHA256_PLACEHOLDER__": FAKE_DIGEST,
            "__ST_DEV_PLACEHOLDER__": 1,
            "__ST_INO_PLACEHOLDER__": 2,
            "__TIMEOUT_MS_PLACEHOLDER__": 1,
        }
        environment = synthetic_probe()
        template_registry = redaction_registry_object()
        template_registry_bytes = probe.canonical_bytes(template_registry)
        frozen_observer = environment["facts"]["files"]["observer-implementation"]
        observer_components = observer_config_object(
            environment,
            template_registry_bytes,
        )["payload"]
        structured_by_name: dict[
            str,
            dict[tuple[str | int, ...], object],
        ] = {
            "m8-minimal-1k-observer-config-v3.json": {
                ("logical_name",): preflight.OBSERVER_LOGICAL_NAME,
                ("payload", "components", 0, "api_ids"): [
                    "fake-network-event-stream"
                ],
                ("payload", "components", 1, "api_ids"): [
                    "fake-write-event-stream"
                ],
                ("payload", "components", 2, "api_ids"): [
                    "fake-process-event-stream"
                ],
                ("payload", "components", 3, "api_ids"): [
                    "fake-redaction-scan-stream"
                ],
                ("payload", "error_code_registry"): copy.deepcopy(
                    observer_components["error_code_registry"]
                ),
                ("payload", "persistent_file_allowlist"): copy.deepcopy(
                    observer_components["persistent_file_allowlist"]
                ),
                ("payload", "redaction_registry_ref"): copy.deepcopy(
                    observer_components["redaction_registry_ref"]
                ),
            },
            "m8-minimal-1k-redaction-registry-v3.json": {
                ("payload", "binary_allowlist"): copy.deepcopy(
                    template_registry["payload"]["binary_allowlist"]
                ),
                ("payload", "patterns"): copy.deepcopy(
                    template_registry["payload"]["patterns"]
                ),
            },
        }
        template_replacements = dict(replacements)
        template_replacements["__BYTE_COUNT_PLACEHOLDER__"] = frozen_observer[
            "byte_count"
        ]
        template_replacements["__SHA256_PLACEHOLDER__"] = frozen_observer[
            "sha256"
        ]
        schema_by_template: dict[str, dict] = {}
        template_by_name: dict[str, dict] = {}
        populated_by_name: dict[str, dict] = {}
        for logical_path in declared:
            with self.subTest(template=logical_path):
                self.assertRegex(
                    logical_path,
                    r"^docs/plans/references/templates/[^/]+\.json$",
                )
                template_path = repository / Path(logical_path)
                raw = template_path.read_bytes()
                self.assertNotIn(b"\xef\xbb\xbf", raw[:3])
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))
                self.assertFalse(raw.endswith(b"\n\n"))
                parsed_value = probe.strict_json(raw)
                self.assertEqual(raw, probe.canonical_bytes(parsed_value))
                if not isinstance(parsed_value, dict):
                    self.fail(f"template must be an object: {logical_path}")
                value = parsed_value
                self.assertEqual(
                    value.get("canonicalization_id"),
                    probe.CANONICALIZATION_ID,
                )
                schema_name = schema_names[template_path.name]
                parsed_schema = preflight.strict_json_bytes(
                    (references / "schemas" / schema_name).read_bytes()
                )
                if not isinstance(parsed_schema, dict):
                    self.fail(f"schema must be an object: {schema_name}")
                schema = parsed_schema
                schema_by_template[template_path.name] = schema
                template_by_name[template_path.name] = value
                self.assertTrue(
                    schema_errors(value, schema),
                    f"blank template unexpectedly became an instance: {logical_path}",
                )

                populated_value = replace_template_placeholders(
                    value,
                    template_replacements,
                    structured_by_name.get(template_path.name),
                )
                if not isinstance(populated_value, dict):
                    self.fail(f"populated template must be an object: {logical_path}")
                populated = populated_value
                populated_by_name[template_path.name] = populated
                populated_bytes = probe.canonical_bytes(populated)
                self.assertEqual(probe.strict_json(populated_bytes), populated)
                self.assertEqual(populated_bytes, probe.canonical_bytes(probe.strict_json(populated_bytes)))
                self.assertNotIn(b"_PLACEHOLDER__", populated_bytes)
                self.assertEqual(
                    schema_errors(populated, schema),
                    [],
                    f"populated template is schema-invalid: {logical_path}",
                )

        gate = template_by_name["m8-minimal-1k-s1-gate-v3.json"]
        gate_schema = schema_by_template["m8-minimal-1k-s1-gate-v3.json"]
        self.assertTrue(schema_errors(gate, gate_schema))
        self.assertNotEqual(gate["payload"].get("decision"), "DRY_RUN_AUTHORIZED")
        self.assertNotEqual(gate["payload"].get("allowed_next_action"), "run-s2")
        populated_gate = populated_by_name["m8-minimal-1k-s1-gate-v3.json"]
        self.assertEqual(schema_errors(populated_gate, gate_schema), [])
        self.assertEqual(populated_gate["payload"]["decision"], "NOT_AUTHORIZED")
        self.assertEqual(populated_gate["payload"]["allowed_next_action"], "stop")

    def test_probe_is_read_only_and_marks_missing_metadata_absent(self) -> None:
        with mock.patch.object(probe.importlib.metadata, "version", side_effect=probe.importlib.metadata.PackageNotFoundError):
            versions = probe.dependency_versions()
        self.assertEqual(set(versions), set(probe.DEPENDENCIES))
        self.assertTrue(all(value == probe.ABSENT for value in versions.values()))
        self.assertIn("repository-preinventory", probe.FROZEN_FILE_NAMES)
        self.assertIn("production-preinventory", probe.FROZEN_FILE_NAMES)

    def test_positive_synthetic_preflight_without_real_identity_or_roots(self) -> None:
        environment = synthetic_probe()
        observer_config, observer_config_data, registry, registry_data = observer_artifacts(environment)
        config = config_object(environment)
        config_data = probe.canonical_bytes(config)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            s0_path = root / "s0.json"
            s0_data = write_canonical(s0_path, s0_object())
            candidate = preflight_object(environment, s0_data)
            with mock.patch.object(
                preflight,
                "revalidate_live_facts",
            ) as live_facts, mock.patch.object(
                preflight,
                "_git",
                side_effect=[
                    (FAKE_COMMIT + "\n").encode(),
                    (FAKE_TREE + "\n").encode(),
                    b"",
                ],
            ):
                result = preflight.validate_preflight(
                    candidate,
                    environment,
                    s0_path,
                    config,
                    config_data,
                    observer_config,
                    observer_config_data,
                    registry,
                    registry_data,
                )
        live_facts.assert_called_once_with(environment["facts"])
        self.assertEqual(result["status"], "S1_PREFLIGHT_VALID")
        self.assertEqual(result["experiment_id"], EXPERIMENT)
        self.assertEqual(result["config_ref"]["byte_count"], len(config_data))
        self.assertEqual(result["config_ref"]["sha256"], probe.sha256_hex(config_data))
        self.assertEqual(environment["facts"]["roots"]["temporary_root"]["exists"], False)


    def test_live_fact_revalidation_is_closed_and_fail_closed(self) -> None:
        facts = synthetic_facts()
        expected_files = list(facts["files"].values())
        existing_roots = {
            facts["repository"]["canonical_path"]: facts["repository"],
            facts["protected_roots"]["production_root"]["canonical_path"]: (
                facts["protected_roots"]["production_root"]
            ),
        }
        absent_roots = {
            item["canonical_path"]: item
            for item in facts["roots"].values()
        }

        class PathStat:
            def __init__(self, mode: int, size: int = 0) -> None:
                self.st_mode = mode
                self.st_dev = 7
                self.st_ino = 11
                self.st_size = size

        class ExistingPath:
            def __init__(self, value: str, *, regular: bool = False) -> None:
                self.value = value
                self.regular = regular

            def lstat(self) -> PathStat:
                return PathStat(0o100000 if self.regular else 0o040000, 123)

        def live_file_fact(path: Path) -> dict:
            for item in expected_files:
                if str(path) == item["canonical_path"]:
                    return item
            raise AssertionError(f"unexpected live file path: {path}")

        def live_inspect(path: Path, label: str) -> ExistingPath:
            del label
            value = str(path)
            if value == str(Path(sys.executable)):
                return ExistingPath(value, regular=True)
            if value not in existing_roots:
                raise AssertionError(f"unexpected live existing path: {value}")
            return ExistingPath(value)

        def live_canonical(path: Path | ExistingPath, *, require_absent: bool = False) -> str:
            value = path.value if isinstance(path, ExistingPath) else str(path)
            if require_absent:
                if value not in absent_roots:
                    raise AssertionError(f"unexpected live absent path: {value}")
                return value
            if value == str(Path(sys.executable)):
                return facts["platform"]["python_executable"]
            if value in existing_roots:
                return value
            raise AssertionError(f"unexpected canonical path: {value}")

        def live_parent(path: Path | ExistingPath) -> dict:
            value = path.value if isinstance(path, ExistingPath) else str(path)
            if value in existing_roots:
                return existing_roots[value]["parent_identity"]
            if value in absent_roots:
                return absent_roots[value]["parent_identity"]
            raise AssertionError(f"unexpected parent path: {value}")

        live_dependencies = copy.deepcopy(facts["dependencies"])
        live_platform = copy.deepcopy(facts["platform"])

        def run_live(candidate: dict) -> None:
            with mock.patch.object(
                preflight,
                "dependency_versions",
                return_value=live_dependencies,
            ), mock.patch.object(
                preflight.platform,
                "python_implementation",
                return_value=live_platform["implementation"],
            ), mock.patch.object(
                preflight.platform,
                "python_version",
                return_value=live_platform["python_version"],
            ), mock.patch.object(
                preflight.platform,
                "system",
                return_value=live_platform["system"],
            ), mock.patch.object(
                preflight,
                "file_fact",
                side_effect=live_file_fact,
            ), mock.patch.object(
                preflight,
                "inspect_existing_path",
                side_effect=live_inspect,
            ), mock.patch.object(
                preflight,
                "canonical_windows_path",
                side_effect=live_canonical,
            ), mock.patch.object(
                preflight,
                "parent_identity",
                side_effect=live_parent,
            ):
                preflight.revalidate_live_facts(candidate)

        run_live(facts)

        drift_cases: list[tuple[str, dict]] = []
        changed = copy.deepcopy(facts)
        changed["dependencies"]["numpy"] = "drifted"
        drift_cases.append(("dependency", changed))
        changed = copy.deepcopy(facts)
        changed["platform"]["python_version"] = "0.0.0"
        drift_cases.append(("platform", changed))
        changed = copy.deepcopy(facts)
        changed["files"]["protocol"]["sha256"] = "0" * 64
        drift_cases.append(("frozen-file", changed))
        changed = copy.deepcopy(facts)
        changed["repository"]["parent_identity"]["st_ino"] += 1
        drift_cases.append(("repository-parent", changed))
        changed = copy.deepcopy(facts)
        changed["protected_roots"]["production_root"]["parent_identity"]["st_ino"] += 1
        drift_cases.append(("production-parent", changed))
        changed = copy.deepcopy(facts)
        changed["roots"]["temporary_root"]["parent_identity"]["st_ino"] += 1
        drift_cases.append(("future-root-parent", changed))

        for name, changed in drift_cases:
            with self.subTest(name=name), self.assertRaises(preflight.PreflightError):
                run_live(changed)

        with mock.patch.object(
            preflight,
            "dependency_versions",
            side_effect=probe.ProbeError("unreadable"),
        ), self.assertRaises(preflight.PreflightError):
            preflight.revalidate_live_facts(facts)

        with mock.patch.object(
            preflight,
            "dependency_versions",
            return_value=facts["dependencies"],
        ), mock.patch.object(
            preflight,
            "inspect_existing_path",
            side_effect=probe.ProbeError("symlink or reparse point"),
        ), self.assertRaises(preflight.PreflightError):
            preflight.revalidate_live_facts(facts)

        appearance_calls: dict[str, int] = {}

        def appearing_root(path: Path | ExistingPath, *, require_absent: bool = False) -> str:
            value = path.value if isinstance(path, ExistingPath) else str(path)
            if require_absent:
                appearance_calls[value] = appearance_calls.get(value, 0) + 1
                if appearance_calls[value] > 1:
                    raise probe.ProbeError("root must be absent")
            return live_canonical(path, require_absent=require_absent)

        with mock.patch.object(
            preflight,
            "dependency_versions",
            return_value=facts["dependencies"],
        ), mock.patch.object(
            preflight.platform,
            "python_implementation",
            return_value=facts["platform"]["implementation"],
        ), mock.patch.object(
            preflight.platform,
            "python_version",
            return_value=facts["platform"]["python_version"],
        ), mock.patch.object(
            preflight.platform,
            "system",
            return_value=facts["platform"]["system"],
        ), mock.patch.object(
            preflight,
            "file_fact",
            side_effect=live_file_fact,
        ), mock.patch.object(
            preflight,
            "inspect_existing_path",
            side_effect=live_inspect,
        ), mock.patch.object(
            preflight,
            "canonical_windows_path",
            side_effect=appearing_root,
        ), mock.patch.object(
            preflight,
            "parent_identity",
            side_effect=live_parent,
        ), self.assertRaises(preflight.PreflightError):
            preflight.revalidate_live_facts(facts)

    def test_preflight_rejects_authorization_bypass_mutations(self) -> None:
        environment = synthetic_probe()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            s0_path = root / "s0.json"
            s0_data = write_canonical(s0_path, s0_object())
            base = preflight_object(environment, s0_data)
            cases: list[tuple[str, dict, dict]] = []

            changed = copy.deepcopy(base)
            changed["expected"]["workload"]["chunk_count"] = 1
            cases.append(("workload", changed, environment))

            changed = copy.deepcopy(base)
            changed["allowed_write_roots"] = [ROOTS["temporary_root"]]
            cases.append(("allowed-root-set", changed, environment))

            changed = copy.deepcopy(base)
            changed["s0_binding"]["sha256"] = "d" * 64
            cases.append(("s0-binding", changed, environment))

            changed = copy.deepcopy(base)
            changed["expected"]["repository"]["worktree_head"] = "e" * 40
            cases.append(("repository-binding", changed, environment))

            overlap_values = {
                "case-aliased-repository-descendant": r"c:\REPO\future",
                "repository-ancestor": "C:\\",
                "production-ancestor": "C:\\",
                "external-source-ancestor": "D:\\",
                "future-root-ancestor": r"D:\m8-v3-s1",
                "future-root-descendant": r"D:\m8-v3-s1\temp\child",
            }
            for name, value in overlap_values.items():
                overlap_environment = copy.deepcopy(environment)
                overlap_environment["facts"]["roots"]["temporary_root"][
                    "canonical_path"
                ] = value
                overlap_environment["facts"]["roots"]["temporary_root"][
                    "parent_identity"
                ]["canonical_path"] = ntpath_dirname(value)
                overlap = preflight_object(overlap_environment, s0_data)
                cases.append((name, overlap, overlap_environment))

            for name, mutated, mutated_environment in cases:
                with self.subTest(mutation=name):
                    with mock.patch.object(
                        preflight,
                        "_git",
                        side_effect=[
                            (FAKE_COMMIT + "\n").encode(),
                            (FAKE_TREE + "\n").encode(),
                            b"",
                        ],
                    ), self.assertRaises(preflight.PreflightError):
                        preflight.validate_preflight(
                            mutated, mutated_environment, s0_path
                        )

    def test_preflight_rejects_win32_path_aliases(self) -> None:
        environment = synthetic_probe()
        aliases = (
            r"C:\repo\..\Windows",
            r"C:\repo.",
            "C:\\repo ",
            r"C:\repo:ads",
            r"C:\synthetic\NUL",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            s0_path = root / "s0.json"
            s0_data = write_canonical(s0_path, s0_object())
            for value in aliases:
                with self.subTest(path=value):
                    mutated_environment = copy.deepcopy(environment)
                    root_fact = mutated_environment["facts"]["roots"][
                        "temporary_root"
                    ]
                    root_fact["canonical_path"] = value
                    root_fact["parent_identity"]["canonical_path"] = ntpath_dirname(
                        value
                    )
                    mutated = preflight_object(mutated_environment, s0_data)
                    with self.assertRaises(preflight.PreflightError):
                        preflight.validate_preflight(
                            mutated,
                            mutated_environment,
                            s0_path,
                        )

    def test_preflight_rejects_config_identity_shape_and_byte_mutations(self) -> None:
        environment = synthetic_probe()
        observer_config, observer_config_data, registry, registry_data = observer_artifacts(environment)
        config = config_object(environment)
        config_data = probe.canonical_bytes(config)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            s0_path = root / "s0.json"
            s0_data = write_canonical(s0_path, s0_object())
            candidate = preflight_object(environment, s0_data)
            mutations = []

            def add_mutation(name: str, changed: dict) -> None:
                mutations.append((name, changed, probe.canonical_bytes(changed)))

            changed = copy.deepcopy(config)
            changed["logical_name"] = f"minimal-1k/{EXPERIMENT}/wrong.json"
            add_mutation("logical-name", changed)

            changed = copy.deepcopy(config)
            changed["schema_id"] = "sa.m8.minimal.s1-config.wrong"
            add_mutation("schema-id", changed)

            changed = copy.deepcopy(config)
            changed["schema_version"] = 4
            add_mutation("schema-version", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["experiment_id"] = "sa-m8-minimal-1k-v3-wrong"
            add_mutation("experiment-id", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["unexpected"] = True
            add_mutation("extra-payload-key", changed)

            changed = copy.deepcopy(config)
            del changed["payload"]["observer"]
            add_mutation("missing-payload-key", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["workload"]["chunk_count"] = 1
            add_mutation("workload", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["generator"]["algorithm_id"] = "wrong-algorithm"
            add_mutation("generator-algorithm", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["generator"] = "not-an-object"
            add_mutation("generator-shape", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["allowed_write_roots"][0]["binding"]["canonical_path"] = "C:/wrong"
            add_mutation("allowed-root", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["dependencies"]["packages"][0]["name"] = "wrong"
            add_mutation("dependency-name", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["dependencies"]["packages"][0]["version"] = "wrong"
            add_mutation("dependency-version", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["dependencies"]["packages"].reverse()
            add_mutation("dependency-order", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["dependencies"]["packages"][0]["unexpected"] = True
            add_mutation("dependency-package-shape", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["dependencies"]["installation_inventory_ref"]["schema_id"] = (
                "sa.m8.minimal.wrong.v3"
            )
            add_mutation("artifact-schema-id", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["protected_root_inventories"][0]["pre_inventory_ref"]["byte_count"] += 1
            add_mutation("pre-inventory-byte-count", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["protected_root_inventories"][0]["pre_inventory_ref"]["schema_id"] = (
                "sa.m8.minimal.wrong.v3"
            )
            add_mutation("pre-inventory-schema-id", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["protected_root_inventories"][0]["pre_inventory_ref"]["sha256"] = "0" * 64
            add_mutation("pre-inventory-digest", changed)

            for field, value in (
                ("cpython_implementation", "PyPy"),
                ("cpython_version", "0.0.0"),
                ("platform", "linux"),
            ):
                changed = copy.deepcopy(config)
                changed["payload"]["environment"][field] = value
                add_mutation(f"environment-{field}", changed)

            for field, value in (
                ("commit", "0" * 40),
                ("clean_status_byte_count", 1),
                ("clean_status_sha256", "0" * 64),
            ):
                changed = copy.deepcopy(config)
                changed["payload"]["repository"][field] = value
                add_mutation(f"repository-{field}", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["repository"]["root"]["canonical_path"] = "C:/wrong"
            add_mutation("repository-path", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["allowed_write_roots"][0]["binding"]["parent_identity"]["st_ino"] += 1
            add_mutation("root-parent-identity", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["repository"]["root"]["parent_identity"]["st_ino"] += 1
            add_mutation("repository-parent-identity", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["allowed_write_roots"][1]["binding"]["parent_identity"] = {
                "canonical_path": "C:\\different",
                "st_dev": 2,
                "st_ino": 3,
            }
            add_mutation("roots-different-parents", changed)

            for field in config["payload"]["path_invariants"]:
                changed = copy.deepcopy(config)
                changed["payload"]["path_invariants"][field] = False
                add_mutation(f"path-invariant-{field}", changed)

            changed = copy.deepcopy(config)
            changed["payload"]["path_invariants"]["same_parent"] = 1
            add_mutation("path-invariant-nonboolean", changed)

            mutations.append(("stale-bytes", config, config_data.replace(b"\n", b" \n")))

            for name, mutated_config, mutated_data in mutations:
                with self.subTest(name=name), self.assertRaises(preflight.PreflightError):
                    preflight.validate_preflight(
                        candidate,
                        environment,
                        s0_path,
                        mutated_config,
                        mutated_data,
                        observer_config,
                        observer_config_data,
                        registry,
                        registry_data,
                    )

            with self.assertRaises(preflight.PreflightError):
                preflight.validate_preflight(
                    candidate,
                    environment,
                    s0_path,
                    None,
                    config_data,
                    observer_config,
                    observer_config_data,
                    registry,
                    registry_data,
                )

    def test_preflight_rejects_observer_and_redaction_mutations(self) -> None:
        def run_case(
            name: str,
            *,
            mutate_observer: ObserverMutation | None = None,
            mutate_registry: ObserverMutation | None = None,
            noncanonical_observer: bool = False,
            noncanonical_registry: bool = False,
        ) -> None:
            environment = synthetic_probe()
            registry = redaction_registry_object()
            if mutate_registry is not None:
                mutate_registry(registry)
            registry_data = probe.canonical_bytes(registry)
            if noncanonical_registry:
                registry_data = registry_data.replace(b"\n", b" \n")
            observer_config = observer_config_object(environment, registry_data)
            if mutate_observer is not None:
                mutate_observer(observer_config)
            observer_config_data = probe.canonical_bytes(observer_config)
            if noncanonical_observer:
                observer_config_data = observer_config_data.replace(b"\n", b" \n")
            for artifact_name, data in (
                ("observer-config", observer_config_data),
                ("redaction-registry", registry_data),
            ):
                environment["facts"]["files"][artifact_name]["byte_count"] = len(data)
                environment["facts"]["files"][artifact_name]["sha256"] = probe.sha256_hex(data)
            config = config_object(environment)
            config_data = probe.canonical_bytes(config)
            with tempfile.TemporaryDirectory() as directory:
                s0_path = Path(directory) / "s0.json"
                s0_data = write_canonical(s0_path, s0_object())
                candidate = preflight_object(environment, s0_data)
                with self.subTest(name=name), mock.patch.object(
                    preflight,
                    "_git",
                    side_effect=[
                        (FAKE_COMMIT + "\n").encode(),
                        (FAKE_TREE + "\n").encode(),
                        b"",
                    ],
                ), self.assertRaises(preflight.PreflightError):
                    preflight.validate_preflight(
                        candidate,
                        environment,
                        s0_path,
                        config,
                        config_data,
                        observer_config,
                        observer_config_data,
                        registry,
                        registry_data,
                    )

        observer_mutations: list[tuple[str, ObserverMutation]] = [
            (
                "observer-extra-envelope-field",
                lambda value: value.__setitem__("unexpected", True),
            ),
            (
                "observer-wrong-logical-name",
                lambda value: value.__setitem__("logical_name", "observer/wrong.json"),
            ),
            (
                "observer-missing-component",
                lambda value: value["payload"]["components"].pop(),
            ),
            (
                "observer-reordered-components",
                lambda value: value["payload"]["components"].reverse(),
            ),
            (
                "observer-duplicate-component",
                lambda value: value["payload"]["components"].__setitem__(
                    1,
                    copy.deepcopy(value["payload"]["components"][0]),
                ),
            ),
            (
                "observer-wrong-coverage",
                lambda value: value["payload"]["components"][0].__setitem__(
                    "coverage_strategy",
                    "complete-evidence-set-scan-before-seal",
                ),
            ),
            (
                "observer-stale-implementation",
                lambda value: value["payload"]["components"][0]
                ["implementation_ref"].__setitem__("sha256", "0" * 64),
            ),
            (
                "observer-unsorted-api-ids",
                lambda value: value["payload"]["components"][0].__setitem__(
                    "api_ids",
                    ["z-api", "a-api"],
                ),
            ),
            (
                "observer-duplicate-api-id",
                lambda value: value["payload"]["components"][0].__setitem__(
                    "api_ids",
                    ["same-api", "same-api"],
                ),
            ),
            (
                "observer-negative-retry",
                lambda value: value["payload"]["components"][0].__setitem__(
                    "bounded_retry_count",
                    -1,
                ),
            ),
            (
                "observer-zero-poll",
                lambda value: value["payload"]["components"][0].__setitem__(
                    "poll_interval_ms",
                    0,
                ),
            ),
            (
                "observer-timeout-not-greater-than-poll",
                lambda value: value["payload"]["components"][0].__setitem__(
                    "timeout_ms",
                    value["payload"]["components"][0]["poll_interval_ms"],
                ),
            ),
            (
                "observer-incomplete-error-registry",
                lambda value: value["payload"]["error_code_registry"].pop(),
            ),
            (
                "observer-reordered-error-registry",
                lambda value: value["payload"]["error_code_registry"].reverse(),
            ),
            (
                "observer-unsorted-persistent-allowlist",
                lambda value: value["payload"]["persistent_file_allowlist"].reverse(),
            ),
            (
                "observer-duplicate-persistent-path",
                lambda value: value["payload"]["persistent_file_allowlist"].__setitem__(
                    1,
                    copy.deepcopy(value["payload"]["persistent_file_allowlist"][0]),
                ),
            ),
            (
                "observer-invalid-persistent-path",
                lambda value: value["payload"]["persistent_file_allowlist"][0].__setitem__(
                    "path",
                    "../escape.jsonl",
                ),
            ),
            (
                "observer-stale-registry-ref",
                lambda value: value["payload"]["redaction_registry_ref"].__setitem__(
                    "sha256",
                    "0" * 64,
                ),
            ),
        ]
        for name, mutation in observer_mutations:
            run_case(name, mutate_observer=mutation)
        run_case("observer-noncanonical-bytes", noncanonical_observer=True)

        registry_mutations: list[tuple[str, ObserverMutation]] = [
            (
                "registry-extra-envelope-field",
                lambda value: value.__setitem__("logical_name", preflight.REDACTION_LOGICAL_NAME),
            ),
            (
                "registry-wrong-matcher-algorithm",
                lambda value: value["payload"].__setitem__("matcher_algorithm", "wrong"),
            ),
            (
                "registry-weakened-binary-policy",
                lambda value: value["payload"].__setitem__("unknown_binary_policy", "ignore"),
            ),
            (
                "registry-missing-category",
                lambda value: value["payload"]["patterns"].pop(),
            ),
            (
                "registry-reordered-categories",
                lambda value: value["payload"]["patterns"].reverse(),
            ),
            (
                "registry-duplicate-category",
                lambda value: value["payload"]["patterns"].__setitem__(
                    1,
                    copy.deepcopy(value["payload"]["patterns"][0]),
                ),
            ),
            (
                "registry-plaintext-pattern",
                lambda value: value["payload"]["patterns"][0].__setitem__(
                    "pattern",
                    "secret",
                ),
            ),
            (
                "registry-wrong-matcher-kind",
                lambda value: value["payload"]["patterns"][0].__setitem__(
                    "matcher_kind",
                    "regex",
                ),
            ),
            (
                "registry-malformed-needle-digest",
                lambda value: value["payload"]["patterns"][0].__setitem__(
                    "needle_sha256",
                    "not-a-digest",
                ),
            ),
            (
                "registry-unsorted-pattern-ids",
                lambda value: value["payload"]["patterns"][0].__setitem__(
                    "pattern_id",
                    "z-pattern",
                ),
            ),
            (
                "registry-duplicate-pattern-id",
                lambda value: value["payload"]["patterns"][1].__setitem__(
                    "pattern_id",
                    value["payload"]["patterns"][0]["pattern_id"],
                ),
            ),
            (
                "registry-unsorted-binary-paths",
                lambda value: value["payload"]["binary_allowlist"].reverse(),
            ),
            (
                "registry-duplicate-binary-path",
                lambda value: value["payload"]["binary_allowlist"].__setitem__(
                    1,
                    copy.deepcopy(value["payload"]["binary_allowlist"][0]),
                ),
            ),
            (
                "registry-invalid-binary-path",
                lambda value: value["payload"]["binary_allowlist"][0].__setitem__(
                    "path",
                    "C:/escape.bin",
                ),
            ),
            (
                "registry-malformed-binary-digest",
                lambda value: value["payload"]["binary_allowlist"][0].__setitem__(
                    "sha256",
                    "BAD",
                ),
            ),
        ]
        for name, mutation in registry_mutations:
            run_case(name, mutate_registry=mutation)
        run_case("registry-noncanonical-bytes", noncanonical_registry=True)

    def test_runner_requires_exact_owner_gate_and_verified_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = synthetic_probe()
            production_root = root / "production"
            production_root.mkdir()
            repository_root = root / "repo"
            repository_root.mkdir()
            environment["facts"]["protected_roots"]["production_root"][
                "canonical_path"
            ] = str(production_root)
            environment["facts"]["repository"]["canonical_path"] = str(repository_root)
            observer_config, observer_config_data, registry, registry_data = observer_artifacts(
                environment
            )
            environment_path = root / "environment.json"
            write_canonical(environment_path, environment)
            observer_config_path = root / "observer-config.json"
            write_canonical(observer_config_path, observer_config)
            redaction_registry_path = root / "redaction-registry.json"
            write_canonical(redaction_registry_path, registry)
            s0_path = root / "s0.json"
            s0_data = write_canonical(s0_path, s0_object())
            candidate = preflight_object(environment, s0_data)
            preflight_path = root / "preflight.json"
            preflight_data = write_canonical(preflight_path, candidate)
            config_path = root / "s1-config.json"
            config = config_object(environment)
            config_data = write_canonical(config_path, config)
            result = {
                "canonicalization_id": probe.CANONICALIZATION_ID,
                "config_ref": {
                    "byte_count": len(config_data),
                    "logical_name": config["logical_name"],
                    "role": "s1-config",
                    "schema_id": runner.S1_CONFIG_SCHEMA_ID,
                    "sha256": probe.sha256_hex(config_data),
                },
                "experiment_id": EXPERIMENT,
                "preflight_sha256": probe.sha256_hex(preflight_data),
                "schema_id": runner.PREFLIGHT_RESULT_SCHEMA_ID,
                "schema_version": 3,
                "status": "S1_PREFLIGHT_VALID",
            }
            result_path = root / "preflight-result.json"
            write_canonical(result_path, result)
            result_bytes = probe.canonical_bytes(result)
            s1 = {
                "canonicalization_id": probe.CANONICALIZATION_ID,
                "logical_name": f"minimal-1k/{EXPERIMENT}/s1-gate.json",
                "payload": {
                    "actor": {"name": "synthetic-owner", "role": "owner"},
                    "allowed_next_action": "run-s2",
                    "authorization_checks": {
                        key: True
                        for key in (
                            "config_validated",
                            "dependencies_frozen",
                            "generator_frozen",
                            "observer_frozen",
                            "paths_isolated",
                            "protected_inventories_frozen",
                            "repository_clean",
                            "s0_accepted",
                        )
                    },
                    "config_ref": {
                        "byte_count": len(config_data),
                        "logical_name": f"minimal-1k/{EXPERIMENT}/s1-config.json",
                        "role": "s1-config",
                        "schema_id": runner.S1_CONFIG_SCHEMA_ID,
                        "sha256": probe.sha256_hex(config_data),
                    },
                    "decision": "DRY_RUN_AUTHORIZED",
                    "experiment_id": EXPERIMENT,
                    "gate_id": "S1",
                    "preflight_ref": {
                        "byte_count": len(result_bytes),
                        "logical_name": f"minimal-1k/{EXPERIMENT}/s1-preflight.json",
                        "role": "s1-preflight",
                        "schema_id": runner.PREFLIGHT_RESULT_SCHEMA_ID,
                        "sha256": probe.sha256_hex(result_bytes),
                    },
                    "reason": "synthetic mock-only authorization boundary test",
                    "s0_ref": {
                        "byte_count": len(s0_data),
                        "logical_name": f"minimal-1k/{EXPERIMENT}/s0.json",
                        "role": "s0",
                        "schema_id": runner.S0_SCHEMA_ID,
                        "sha256": probe.sha256_hex(s0_data),
                    },
                    "scope": {
                        "acquisition_network_allowed": True,
                        "measured_network_allowed": False,
                        "production_write_allowed": False,
                        "synthetic_only": True,
                        "workloads": [
                            "sqlite-linear-exact",
                            "lancedb-embedded-exact-flat",
                        ],
                    },
                },
                "schema_id": runner.S1_GATE_SCHEMA_ID,
                "schema_version": 3,
            }
            s1_path = root / "s1.json"
            write_canonical(s1_path, s1)
            mutated = copy.deepcopy(s1)
            mutated["payload"]["decision"] = "NOT_AUTHORIZED"
            mutated["payload"]["allowed_next_action"] = "stop"
            mutated_path = root / "mutated-s1.json"
            write_canonical(mutated_path, mutated)
            mock_root = root / "mock-root"
            mock_root.mkdir()
            common_paths = {
                "s0_path": s0_path,
                "environment_path": environment_path,
                "preflight_path": preflight_path,
                "preflight_result_path": result_path,
                "config_path": config_path,
                "observer_config_path": observer_config_path,
                "redaction_registry_path": redaction_registry_path,
                "mock_root": mock_root,
            }
            expected_preflight_call = (
                candidate,
                environment,
                s0_path,
                config,
                config_data,
                observer_config,
                observer_config_data,
                registry,
                registry_data,
            )
            with mock.patch.object(
                runner,
                "validate_preflight",
            ) as recomputed, mock.patch.object(
                preflight,
                "_git",
            ) as live_git, mock.patch.object(
                runner,
                "build_embedded_mock_result",
            ) as embedded_mock:
                with self.assertRaises(runner.RunnerError):
                    runner.execute_mock(s1_path=mutated_path, **common_paths)
                recomputed.assert_not_called()
                live_git.assert_not_called()
                embedded_mock.assert_not_called()

            with mock.patch.object(
                runner,
                "validate_preflight",
                return_value=result,
            ), mock.patch.object(
                runner,
                "WINDOWS_MOCK_ROOT_FAIL_CLOSED",
                True,
            ), mock.patch.object(
                runner,
                "build_embedded_mock_result",
            ) as windows_blocked_mock:
                with self.assertRaisesRegex(
                    runner.RunnerError,
                    "Windows mock-root isolation cannot be proven",
                ):
                    runner.execute_mock(s1_path=s1_path, **common_paths)
                windows_blocked_mock.assert_not_called()

            with mock.patch.object(
                runner,
                "validate_preflight",
                return_value=result,
            ), mock.patch.object(
                runner,
                "WINDOWS_MOCK_ROOT_FAIL_CLOSED",
                False,
            ):
                completed = runner.execute_mock(s1_path=s1_path, **common_paths)
            self.assertEqual(completed["status"], "MOCK_TINY_COMPLETED")
            self.assertFalse(completed["next_gate_created"])
            self.assertEqual(
                completed["mock_result"]["backend_id"], "embedded-closed-mock-v1"
            )
            self.assertEqual(completed["mock_result"]["status"], "PASS")
            self.assertTrue(completed["mock_result"]["root_empty"])

            supplied_python = root / "supplied.py"
            supplied_python.write_text(
                "raise RuntimeError('must never execute supplied Python')\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                runner,
                "validate_preflight",
                return_value=result,
            ), mock.patch.object(
                runner,
                "WINDOWS_MOCK_ROOT_FAIL_CLOSED",
                False,
            ):
                second = runner.execute_mock(s1_path=s1_path, **common_paths)
            self.assertEqual(second, completed)

            (mock_root / "unexpected.txt").write_text("not empty", encoding="utf-8")
            with mock.patch.object(
                runner,
                "validate_preflight",
                return_value=result,
            ), mock.patch.object(
                runner,
                "WINDOWS_MOCK_ROOT_FAIL_CLOSED",
                False,
            ):
                with self.assertRaisesRegex(runner.RunnerError, "must be empty"):
                    runner.execute_mock(s1_path=s1_path, **common_paths)
            (mock_root / "unexpected.txt").unlink()

            protected_roots = (
                production_root,
                production_root / "child",
                repository_root,
                repository_root / "child",
            )
            for protected_mock_root in protected_roots:
                protected_mock_root.mkdir(exist_ok=True)
                protected_paths = {**common_paths, "mock_root": protected_mock_root}
                with mock.patch.object(
                    runner,
                    "validate_preflight",
                    return_value=result,
                ), mock.patch.object(
                    runner,
                    "WINDOWS_MOCK_ROOT_FAIL_CLOSED",
                    False,
                ), mock.patch.object(
                    runner,
                    "build_embedded_mock_result",
                ) as protected_mock:
                    with self.assertRaises(runner.RunnerError):
                        runner.execute_mock(s1_path=s1_path, **protected_paths)
                    protected_mock.assert_not_called()

            for ancestor in (production_root.parent, repository_root.parent):
                ancestor_paths = {**common_paths, "mock_root": ancestor}
                with mock.patch.object(
                    runner,
                    "validate_preflight",
                    return_value=result,
                ), mock.patch.object(
                    runner,
                    "WINDOWS_MOCK_ROOT_FAIL_CLOSED",
                    False,
                ), mock.patch.object(
                    runner,
                    "build_embedded_mock_result",
                ) as ancestor_mock:
                    with self.assertRaises(runner.RunnerError):
                        runner.execute_mock(s1_path=s1_path, **ancestor_paths)
                    ancestor_mock.assert_not_called()

            stale = copy.deepcopy(s1)
            stale["payload"]["preflight_ref"]["sha256"] = "f" * 64
            stale_path = root / "stale-s1.json"
            write_canonical(stale_path, stale)
            with mock.patch.object(
                runner,
                "validate_preflight",
                return_value=result,
            ), mock.patch.object(
                runner, "build_embedded_mock_result"
            ) as stale_mock:
                with self.assertRaises(runner.RunnerError):
                    runner.execute_mock(s1_path=stale_path, **common_paths)
                stale_mock.assert_not_called()

            stale_config = copy.deepcopy(s1)
            stale_config["payload"]["config_ref"]["sha256"] = "e" * 64
            stale_config_path = root / "stale-config-s1.json"
            write_canonical(stale_config_path, stale_config)
            with mock.patch.object(
                runner,
                "validate_preflight",
                return_value=result,
            ), mock.patch.object(
                runner, "build_embedded_mock_result"
            ) as stale_config_mock:
                with self.assertRaises(runner.RunnerError):
                    runner.execute_mock(s1_path=stale_config_path, **common_paths)
                stale_config_mock.assert_not_called()

    def test_runner_only_allows_mock_tiny_mode(self) -> None:
        with mock.patch.object(runner.sys, "stderr", new=io.TextIOWrapper(io.BytesIO())):
            self.assertEqual(runner.main(["--mode", "real-s2"]), 1)
        with mock.patch.object(runner.sys, "stderr", new=io.TextIOWrapper(io.BytesIO())):
            self.assertEqual(
                runner.main(["--mode", "mock-tiny", "--mock-backend", "supplied.py"]),
                1,
            )


    def test_embedded_mock_requires_formal_context(self) -> None:
        context: dict[str, object] = {
            "config_sha256": FAKE_DIGEST,
            "experiment_id": EXPERIMENT,
            "mode": "mock-tiny",
            "preflight_sha256": FAKE_DIGEST,
            "s1_sha256": FAKE_DIGEST,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(
                runner,
                "WINDOWS_MOCK_ROOT_FAIL_CLOSED",
                False,
            ):
                self.assertEqual(
                    runner.build_embedded_mock_result(context, root)["status"],
                    "PASS",
                )
            for value in (
                "sa-m8-v3-fixture-success",
                "sa-m8-unrestricted-example",
            ):
                rejected = dict(context)
                rejected["experiment_id"] = value
                with self.assertRaisesRegex(
                    runner.RunnerError, "embedded mock experiment id is invalid"
                ):
                    runner.build_embedded_mock_result(rejected, root)


    def test_windows_embedded_mock_fails_closed_without_retained_handle(self) -> None:
        context: dict[str, object] = {
            "config_sha256": FAKE_DIGEST,
            "experiment_id": EXPERIMENT,
            "mode": "mock-tiny",
            "preflight_sha256": FAKE_DIGEST,
            "s1_sha256": FAKE_DIGEST,
        }
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            runner,
            "WINDOWS_MOCK_ROOT_FAIL_CLOSED",
            True,
        ):
            with self.assertRaisesRegex(
                runner.RunnerError,
                "Windows mock-root isolation cannot be proven",
            ):
                runner.build_embedded_mock_result(context, Path(directory))


    def test_experiment_id_namespaces_are_closed(self) -> None:
        formal = EXPERIMENT
        fixture = "sa-m8-v3-fixture-success"
        generic = "sa-m8-unrestricted-example"
        self.assertIsNotNone(preflight.EXPERIMENT_ID.fullmatch(formal))
        self.assertIsNone(preflight.EXPERIMENT_ID.fullmatch(fixture))
        self.assertIsNone(preflight.EXPERIMENT_ID.fullmatch(generic))
        self.assertIsNotNone(graph_validator.EXPERIMENT_ID.fullmatch(formal))
        self.assertIsNotNone(graph_validator.EXPERIMENT_ID.fullmatch(fixture))
        self.assertIsNone(graph_validator.EXPERIMENT_ID.fullmatch(generic))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            formal_result = {
                "canonicalization_id": probe.CANONICALIZATION_ID,
                "config_ref": {
                    "byte_count": 1,
                    "logical_name": f"minimal-1k/{formal}/s1-config.json",
                    "role": "s1-config",
                    "schema_id": runner.S1_CONFIG_SCHEMA_ID,
                    "sha256": FAKE_DIGEST,
                },
                "experiment_id": formal,
                "preflight_sha256": FAKE_DIGEST,
                "schema_id": runner.PREFLIGHT_RESULT_SCHEMA_ID,
                "schema_version": 3,
                "status": "S1_PREFLIGHT_VALID",
            }
            formal_path = root / "formal-result.json"
            write_canonical(formal_path, formal_result)
            self.assertEqual(
                runner.validate_preflight_result(formal_path)["experiment_id"],
                formal,
            )
            wrong_logical_name = copy.deepcopy(formal_result)
            wrong_logical_name["config_ref"]["logical_name"] = (
                f"minimal-1k/{fixture}/s1-config.json"
            )
            wrong_logical_name_path = root / "wrong-logical-name.json"
            write_canonical(wrong_logical_name_path, wrong_logical_name)
            with self.assertRaisesRegex(
                runner.RunnerError, "preflight result is not uniquely valid"
            ):
                runner.validate_preflight_result(wrong_logical_name_path)
            for value in (fixture, generic):
                rejected = copy.deepcopy(formal_result)
                rejected["experiment_id"] = value
                rejected["config_ref"]["logical_name"] = (
                    f"minimal-1k/{value}/s1-config.json"
                )
                rejected_path = root / f"{value}.json"
                write_canonical(rejected_path, rejected)
                with self.assertRaisesRegex(
                    runner.RunnerError, "preflight result is not uniquely valid"
                ):
                    runner.validate_preflight_result(rejected_path)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    if result.wasSuccessful():
        print("ALL PASS: canonical declared templates")
    raise SystemExit(0 if result.wasSuccessful() else 1)

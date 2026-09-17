#!/usr/bin/env python3
"""Generate the M8 v3 deterministic synthetic 1K input.

The formal workload is deliberately guarded.  This program never downloads data,
reads external material, installs dependencies, or runs a backend.  ``test-only``
is an explicit tiny fixture mode and is not a formal identity/evidence producer.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    from m8_validate_s1_preflight_v3 import (
        PreflightError,
        validate_preflight as validate_s1_preflight,
    )
except ModuleNotFoundError:  # Supports import as tools.m8_generate_minimal_1k_input_v3.
    from tools.m8_validate_s1_preflight_v3 import (
        PreflightError,
        validate_preflight as validate_s1_preflight,
    )

try:
    import numpy as np
except Exception as exc:  # pragma: no cover - exercised by preflight tests
    np = None
    _NUMPY_IMPORT_ERROR = str(exc)
else:
    _NUMPY_IMPORT_ERROR = None

FORMAL_NUMPY_VERSION = "2.4.6"
FORMAL_SEED = 20260914
FORMAL_PERTURBATION_SEED = 20260915
FORMAL_CHUNK_COUNT = 1000
FORMAL_DIMENSION = 512
FORMAL_QUERY_COUNT = 104
FORMAL_TOP_K = [1, 3, 5]
NORMALIZATION_TOLERANCE = 2e-6
PERTURBATION_NORM = 0.001
ALGORITHM = "sa-m8-synthetic-unit-v3"
CANONICALIZATION = "sa-json-c14n-v1"
S0_SCHEMA_ID = "sa.m8.minimal.decision-record.v3"
S1_CONFIG_SCHEMA_ID = "sa.m8.minimal.s1-config.v3"
S1_GATE_SCHEMA_ID = "sa.m8.minimal.s1-gate.v3"
PREFLIGHT_RESULT_SCHEMA_ID = "sa.m8.minimal.s1-preflight-result.v3"
FORMAL_EXPERIMENT_ID = re.compile(
    r"^sa-m8-minimal-1k-v3-[a-z0-9][a-z0-9-]*$"
)
FORMAL_AUTHORIZATION_FILES = (
    "s0_path",
    "s1_path",
    "environment_path",
    "config_path",
    "observer_config_path",
    "redaction_registry_path",
    "preflight_path",
    "preflight_result_path",
)


@dataclass(frozen=True)
class FormalAuthorization:
    """Exact canonical artifacts required before formal generation is reachable."""

    s0_path: Path
    s1_path: Path
    environment_path: Path
    config_path: Path
    observer_config_path: Path
    redaction_registry_path: Path
    preflight_path: Path
    preflight_result_path: Path


class GeneratorError(Exception):
    """A controlled, machine-readable generator failure."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def canonical_json(value: Any) -> bytes:
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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _error(code: str, message: str, **details: Any) -> GeneratorError:
    return GeneratorError(code, message, **details)


def _version() -> str:
    return "unavailable" if np is None else str(np.__version__)


def _strict_object(data: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    def closed_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    try:
        value = json.loads(
            data,
            parse_constant=reject_constant,
            object_pairs_hook=closed_pairs,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error("FORMAL_AUTHORIZATION_INVALID", f"{label} is invalid JSON") from exc
    if not isinstance(value, dict) or canonical_json(value) != data:
        raise _error("FORMAL_AUTHORIZATION_INVALID", f"{label} is not canonical JSON")
    return value


def _load_authorization(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise _error(
            "FORMAL_AUTHORIZATION_INVALID",
            f"cannot read {label}",
        ) from exc
    return _strict_object(data, label), data


def _closed_mapping(
    value: object,
    keys: set[str],
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise _error("FORMAL_AUTHORIZATION_INVALID", f"{label} has an open or incomplete shape")
    return value


def _bound_ref(
    reference: object,
    data: bytes,
    *,
    role: str,
    schema_id: str,
    logical_name: str,
    label: str,
) -> None:
    value = _closed_mapping(
        reference,
        {"byte_count", "logical_name", "role", "schema_id", "sha256"},
        label,
    )
    if (
        value.get("role") != role
        or value.get("schema_id") != schema_id
        or value.get("logical_name") != logical_name
        or value.get("sha256") != sha256(data)
        or value.get("byte_count") != len(data)
    ):
        raise _error("FORMAL_AUTHORIZATION_INVALID", f"{label} does not bind supplied bytes")


def _canonical_path_text(path: Path) -> str:
    return str(Path(os.path.abspath(os.fspath(path)))).replace("\\", "/")


def _file_identity(file_stat: os.stat_result) -> dict[str, int]:
    return {"st_dev": int(file_stat.st_dev), "st_ino": int(file_stat.st_ino)}


def _has_reparse_point(file_stat: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(file_stat, "st_file_attributes", 0) & reparse_flag)


def _inspect_components(path: Path, label: str) -> Path:
    absolute = Path(os.path.abspath(os.fspath(path)))
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        try:
            file_stat = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise _error("OUTPUT_PATH_UNVERIFIABLE", f"{label} cannot be inspected") from exc
        if stat.S_ISLNK(file_stat.st_mode) or _has_reparse_point(file_stat):
            raise _error(
                "OUTPUT_PATH_REPARSE_POINT",
                f"{label} contains a symlink or reparse point",
            )
    return absolute


def _inspect_output_path(output_root: Path) -> tuple[Path, dict[str, object]]:
    if not output_root.is_absolute():
        raise _error("OUTPUT_ROOT_NOT_ABSOLUTE", "output root must be an absolute path")
    absolute = _inspect_components(output_root, "output root")
    if absolute.exists():
        raise _error(
            "OUTPUT_ROOT_EXISTS",
            "output root must not exist",
            output_root=str(absolute),
        )
    parent = absolute.parent
    if not parent.exists() or not parent.is_dir():
        raise _error("OUTPUT_PARENT_MISSING", "output root parent does not exist")
    parent = _inspect_components(parent, "output root parent")
    try:
        parent_stat = parent.lstat()
    except OSError as exc:
        raise _error("OUTPUT_PATH_UNVERIFIABLE", "output root parent cannot be inspected") from exc
    if not stat.S_ISDIR(parent_stat.st_mode):
        raise _error("OUTPUT_PARENT_MISSING", "output root parent is not a directory")
    if not os.access(str(parent), os.W_OK):
        raise _error("OUTPUT_ROOT_NOT_WRITABLE", "output root parent is not writable")
    return absolute, {
        "canonical_path": _canonical_path_text(parent),
        **_file_identity(parent_stat),
    }


def _validate_formal_authorization(
    output_root: Path,
    authorization: FormalAuthorization,
) -> dict[str, Any]:
    if not isinstance(authorization, FormalAuthorization):
        raise _error("FORMAL_AUTHORIZATION_REQUIRED", "formal authorization context is invalid")
    paths = [getattr(authorization, name) for name in FORMAL_AUTHORIZATION_FILES]
    if any(not isinstance(path, Path) for path in paths):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "authorization paths must be pathlib Paths")

    s0, s0_data = _load_authorization(authorization.s0_path, "accepted S0")
    result, result_data = _load_authorization(
        authorization.preflight_result_path,
        "preflight result",
    )
    preflight_object, preflight_data = _load_authorization(
        authorization.preflight_path,
        "preflight",
    )
    environment, _ = _load_authorization(
        authorization.environment_path,
        "environment",
    )
    config, config_data = _load_authorization(authorization.config_path, "S1 config")
    observer_config, observer_config_data = _load_authorization(
        authorization.observer_config_path,
        "observer config",
    )
    redaction_registry, redaction_registry_data = _load_authorization(
        authorization.redaction_registry_path,
        "redaction registry",
    )
    s1, _ = _load_authorization(authorization.s1_path, "owner S1 gate")

    s0_payload = _closed_mapping(
        s0.get("payload"),
        {
            "actor_role",
            "allowed_next_action",
            "decision",
            "experiment_id",
            "gate_id",
            "read_refs",
        },
        "accepted S0 payload",
    )
    experiment_id = result.get("experiment_id")
    if (
        s0.get("canonicalization_id") != CANONICALIZATION
        or s0.get("schema_id") != S0_SCHEMA_ID
        or s0.get("schema_version") != 3
        or s0_payload.get("actor_role") != "independent-reviewer"
        or s0_payload.get("decision") != "PROTOCOL_ACCEPTED"
        or s0_payload.get("allowed_next_action") != "request-s1"
        or s0_payload.get("gate_id") != "S0"
        or s0_payload.get("experiment_id") != experiment_id
    ):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "accepted S0 is not exact")

    result_keys = {
        "canonicalization_id",
        "config_ref",
        "experiment_id",
        "preflight_sha256",
        "schema_id",
        "schema_version",
        "status",
    }
    _closed_mapping(result, result_keys, "preflight result")
    if (
        result.get("canonicalization_id") != CANONICALIZATION
        or result.get("schema_id") != PREFLIGHT_RESULT_SCHEMA_ID
        or result.get("schema_version") != 3
        or result.get("status") != "S1_PREFLIGHT_VALID"
        or not isinstance(experiment_id, str)
        or FORMAL_EXPERIMENT_ID.fullmatch(experiment_id) is None
        or result.get("preflight_sha256") != sha256(preflight_data)
        or preflight_object.get("experiment_id") != experiment_id
    ):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "preflight result is not exact")
    try:
        recomputed_result = validate_s1_preflight(
            preflight_object,
            environment,
            authorization.s0_path,
            config,
            config_data,
            observer_config,
            observer_config_data,
            redaction_registry,
            redaction_registry_data,
        )
    except (PreflightError, ValueError, OSError) as exc:
        raise _error(
            "FORMAL_PREFLIGHT_REVALIDATION_FAILED",
            "authoritative S1 preflight revalidation failed",
        ) from exc
    if recomputed_result != result:
        raise _error(
            "FORMAL_PREFLIGHT_RESULT_MISMATCH",
            "supplied preflight result differs from authoritative recomputation",
        )

    config_payload = _closed_mapping(
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
        "S1 config payload",
    )
    config_logical_name = f"minimal-1k/{experiment_id}/s1-config.json"
    _bound_ref(
        result.get("config_ref"),
        config_data,
        role="s1-config",
        schema_id=S1_CONFIG_SCHEMA_ID,
        logical_name=config_logical_name,
        label="preflight config ref",
    )
    if (
        config.get("canonicalization_id") != CANONICALIZATION
        or config.get("schema_id") != S1_CONFIG_SCHEMA_ID
        or config.get("schema_version") != 3
        or config.get("logical_name") != config_logical_name
        or config_payload.get("experiment_id") != experiment_id
    ):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "S1 config identity is not exact")

    payload = _closed_mapping(
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
        "owner S1 payload",
    )
    actor = _closed_mapping(payload.get("actor"), {"name", "role"}, "owner S1 actor")
    checks = _closed_mapping(
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
        "owner S1 checks",
    )
    scope = _closed_mapping(
        payload.get("scope"),
        {
            "acquisition_network_allowed",
            "measured_network_allowed",
            "production_write_allowed",
            "synthetic_only",
            "workloads",
        },
        "owner S1 scope",
    )
    _bound_ref(
        payload.get("s0_ref"),
        s0_data,
        role="s0",
        schema_id=S0_SCHEMA_ID,
        logical_name=str(s0.get("logical_name")),
        label="owner S1 S0 ref",
    )
    _bound_ref(
        payload.get("config_ref"),
        config_data,
        role="s1-config",
        schema_id=S1_CONFIG_SCHEMA_ID,
        logical_name=config_logical_name,
        label="owner S1 config ref",
    )
    _bound_ref(
        payload.get("preflight_ref"),
        result_data,
        role="s1-preflight",
        schema_id=PREFLIGHT_RESULT_SCHEMA_ID,
        logical_name=f"minimal-1k/{experiment_id}/s1-preflight.json",
        label="owner S1 preflight ref",
    )
    expected_scope = {
        "acquisition_network_allowed": True,
        "measured_network_allowed": False,
        "production_write_allowed": False,
        "synthetic_only": True,
        "workloads": ["sqlite-linear-exact", "lancedb-embedded-exact-flat"],
    }
    if (
        s1.get("canonicalization_id") != CANONICALIZATION
        or s1.get("schema_id") != S1_GATE_SCHEMA_ID
        or s1.get("schema_version") != 3
        or s1.get("logical_name") != f"minimal-1k/{experiment_id}/s1-gate.json"
        or actor.get("role") != "owner"
        or not isinstance(actor.get("name"), str)
        or not actor.get("name")
        or any(value is not True for value in checks.values())
        or payload.get("allowed_next_action") != "run-s2"
        or payload.get("decision") != "DRY_RUN_AUTHORIZED"
        or payload.get("experiment_id") != experiment_id
        or payload.get("gate_id") != "S1"
        or scope != expected_scope
    ):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "exact owner S1 authorization is required")

    workload = config_payload.get("workload")
    packages = config_payload.get("dependencies")
    if not isinstance(workload, dict) or not isinstance(packages, dict):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "S1 workload or dependencies are invalid")
    package_entries = packages.get("packages")
    if not isinstance(package_entries, list):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "S1 package list is invalid")
    numpy_entries = [
        item
        for item in package_entries
        if isinstance(item, dict) and item.get("name") == "numpy"
    ]
    if len(numpy_entries) != 1 or not isinstance(numpy_entries[0].get("version"), str):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "S1 NumPy version is not unique")
    expected_workload = {
        "agreement_denominator": 312,
        "backends": ["sqlite-linear-exact", "lancedb-embedded-exact-flat"],
        "byte_order": "little-endian",
        "chunk_count": FORMAL_CHUNK_COUNT,
        "dimension": FORMAL_DIMENSION,
        "dtype": "float32",
        "normalization": "l2",
        "normalization_tolerance": NORMALIZATION_TOLERANCE,
        "perturbation_seed": FORMAL_PERTURBATION_SEED,
        "query_count": FORMAL_QUERY_COUNT,
        "required_agreement": 1.0,
        "seed": FORMAL_SEED,
        "synthetic_only": True,
        "top_k": FORMAL_TOP_K,
    }
    if workload != expected_workload:
        raise _error("FORMAL_AUTHORIZATION_INVALID", "S1 workload does not freeze the formal contract")
    if numpy_entries[0]["version"] != FORMAL_NUMPY_VERSION:
        raise _error("FORMAL_AUTHORIZATION_INVALID", "S1 NumPy version is not the frozen formal version")

    allowed_roots = config_payload.get("allowed_write_roots")
    if not isinstance(allowed_roots, list):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "S1 allowed write roots are invalid")
    temporary = [
        item
        for item in allowed_roots
        if isinstance(item, dict) and item.get("root_class") == "temporary-root"
    ]
    if len(temporary) != 1 or not isinstance(temporary[0].get("binding"), dict):
        raise _error("FORMAL_AUTHORIZATION_INVALID", "S1 temporary root binding is not unique")
    binding = temporary[0]["binding"]
    expected_root = binding.get("canonical_path")
    supplied_root = _canonical_path_text(output_root)
    if expected_root != supplied_root:
        raise _error(
            "FORMAL_OUTPUT_ROOT_MISMATCH",
            "formal output root differs from the exact S1 temporary root",
            expected=expected_root,
            actual=supplied_root,
        )
    parent_binding = binding.get("parent_identity")
    if not isinstance(parent_binding, dict):
        raise _error(
            "FORMAL_AUTHORIZATION_INVALID",
            "S1 temporary root parent identity is invalid",
        )
    normalized_parent_binding = {
        **parent_binding,
        "canonical_path": str(parent_binding.get("canonical_path", "")).replace(
            "\\", "/"
        ),
    }
    return {
        "normalization_tolerance": workload["normalization_tolerance"],
        "numpy_version": numpy_entries[0]["version"],
        "parent_identity": normalized_parent_binding,
    }


def _revalidate_publication(
    output_root: Path,
    expected_parent_identity: Mapping[str, object],
) -> None:
    absolute, actual_parent_identity = _inspect_output_path(output_root)
    if absolute != output_root:
        raise _error("OUTPUT_ROOT_CHANGED", "output root lexical identity changed")
    if dict(expected_parent_identity) != actual_parent_identity:
        raise _error(
            "OUTPUT_PARENT_CHANGED",
            "output root parent identity changed before publication",
        )


def preflight(
    output_root: Path,
    mode: str,
    *,
    numpy_version: str | None = None,
    authorization: FormalAuthorization | None = None,
) -> dict[str, Any]:
    """Validate authorization and path invariants before staging exists."""
    if mode not in {"formal", "test-only"}:
        raise _error("INVALID_MODE", "mode must be formal or test-only", mode=mode)
    if mode == "formal":
        if authorization is None:
            raise _error(
                "FORMAL_AUTHORIZATION_REQUIRED",
                "formal mode requires exact accepted S0, owner S1, config, and preflight artifacts",
            )
        authority = _validate_formal_authorization(output_root, authorization)
        expected_numpy_version = authority["numpy_version"]
        normalization_tolerance = authority["normalization_tolerance"]
    else:
        if authorization is not None:
            raise _error(
                "TEST_AUTHORIZATION_FORBIDDEN",
                "test-only mode cannot consume or represent S1 authorization",
            )
        expected_numpy_version = None
        normalization_tolerance = NORMALIZATION_TOLERANCE

    absolute, parent_identity = _inspect_output_path(output_root)
    if mode == "formal" and authority["parent_identity"] != parent_identity:
        raise _error(
            "FORMAL_OUTPUT_PARENT_MISMATCH",
            "live output parent identity differs from the exact S1 binding",
            expected=authority["parent_identity"],
            actual=parent_identity,
        )
    actual_version = numpy_version if numpy_version is not None else _version()
    if np is None:
        raise _error(
            "NUMPY_UNAVAILABLE",
            "NumPy is required",
            import_error=_NUMPY_IMPORT_ERROR,
        )
    if mode == "formal" and actual_version != expected_numpy_version:
        raise _error(
            "NUMPY_VERSION_MISMATCH",
            "formal mode requires the S1-frozen NumPy version",
            expected=expected_numpy_version,
            actual=actual_version,
        )
    return {
        "mode": mode,
        "normalization_tolerance": normalization_tolerance,
        "numpy_version": actual_version,
        "output_root": str(absolute),
        "parent_identity": parent_identity,
    }


def _normalize(rows: Any, tolerance: float = NORMALIZATION_TOLERANCE) -> Any:
    if not isinstance(tolerance, (int, float)) or not np.isfinite(tolerance) or tolerance <= 0:
        raise _error("INVALID_NORMALIZATION_TOLERANCE", "normalization tolerance must be positive and finite")
    source = np.asarray(rows)
    if source.dtype != np.dtype(np.float64) or not source.flags.c_contiguous:
        raise _error("INVALID_VECTOR_LAYOUT", "working vectors must be C-contiguous float64")
    if not bool(np.all(np.isfinite(source))):
        raise _error("INVALID_VECTOR", "vectors must be finite")
    norms = np.sqrt(np.sum(source * source, axis=1, dtype=np.float64))
    if not bool(np.all(np.isfinite(norms))) or bool(np.any(norms == 0)):
        raise _error("INVALID_VECTOR", "vector norms must be finite and non-zero")
    normalized = source / norms[:, None]
    result = np.asarray(normalized, dtype="<f4", order="C")
    if not result.flags.c_contiguous or result.dtype != np.dtype("<f4"):
        raise _error("INVALID_VECTOR_LAYOUT", "stored vectors must be C-contiguous little-endian float32")
    if not bool(np.all(np.isfinite(result))):
        raise _error("INVALID_VECTOR", "converted vectors must be finite")
    restored = result.astype(np.float64)
    final_norms = np.sqrt(np.sum(restored * restored, axis=1, dtype=np.float64))
    if bool(np.any(np.abs(final_norms - 1.0) > tolerance)):
        raise _error("VECTOR_NORMALIZATION_ERROR", "float32 vectors exceed norm tolerance")
    return result


def _make_vectors(
    chunk_count: int,
    dimension: int,
    seed: int,
    perturb_seed: int,
    tolerance: float = NORMALIZATION_TOLERANCE,
) -> tuple[Any, Any]:
    rng = np.random.Generator(np.random.PCG64(seed))
    raw = rng.standard_normal(size=(chunk_count, dimension), dtype=np.float64)
    if not raw.flags.c_contiguous:
        raise _error("INVALID_VECTOR_LAYOUT", "generated matrix must be C-contiguous")
    vectors = _normalize(raw, tolerance)

    perturb_count = min(25, chunk_count)
    target_ordinals = [(25 + index) % chunk_count for index in range(perturb_count)]
    prng = np.random.Generator(np.random.PCG64(perturb_seed))
    noise = prng.standard_normal(size=(perturb_count, dimension), dtype=np.float64)
    if not noise.flags.c_contiguous or not bool(np.all(np.isfinite(noise))):
        raise _error("INVALID_VECTOR", "perturbation matrix must be finite C-contiguous float64")
    noise_norms = np.sqrt(np.sum(noise * noise, axis=1, dtype=np.float64))
    if not bool(np.all(np.isfinite(noise_norms))) or bool(np.any(noise_norms == 0)):
        raise _error("INVALID_VECTOR", "perturbation norms must be finite and non-zero")
    scaled_noise = noise / noise_norms[:, None] * PERTURBATION_NORM
    targets = vectors[target_ordinals].astype(np.float64)
    perturbed_working = np.asarray(targets + scaled_noise, dtype=np.float64, order="C")
    perturbed = _normalize(perturbed_working, tolerance)
    return vectors, perturbed


def _chunk_records(count: int, dimension: int = FORMAL_DIMENSION) -> list[dict[str, Any]]:
    vector_byte_length = dimension * 4
    records: list[dict[str, Any]] = []
    for ordinal in range(count):
        record: dict[str, Any] = {
            "chunk_id": f"m8-s00-{ordinal:05d}",
            "filter_label": f"label-{ordinal:05d}",
            "generation": "generation-01",
            "ordinal": ordinal,
            "owner_id": "owner-00",
            "published": True,
            "snapshot": "snapshot-01",
            "source_id": "source-00",
            "tombstone": False,
            "vector_byte_length": vector_byte_length,
            "vector_byte_offset": ordinal * vector_byte_length,
        }
        if ordinal == 100:
            record["tombstone"] = True
        elif ordinal == 101:
            record["published"] = False
        elif ordinal == 102:
            record["generation"] = "generation-mismatch"
        elif ordinal == 103:
            record["snapshot"] = "snapshot-mismatch"
        records.append(record)
    return records


def _query_records(vectors: Any, perturbed: Any, count: int, dimension: int) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    vector_bytes = vectors.astype("<f4", order="C", copy=False)

    def encoded(row: Any) -> str:
        return base64.b64encode(np.asarray(row, dtype="<f4", order="C").tobytes(order="C")).decode("ascii")

    def normal_filter(ordinal: int) -> dict[str, Any]:
        return {
            "filter_label": f"label-{ordinal:05d}",
            "generation": "generation-01",
            "owner_id": "owner-00",
            "published": True,
            "snapshot": "snapshot-01",
            "source_id": "source-00",
            "tombstone": False,
        }

    usable = min(25, count)
    for index in range(usable):
        queries.append({
            "filter": {key: "*" for key in normal_filter(index)},
            "query_id": f"m8-q-exact-{index:03d}",
            "query_type": "exact",
            "target_chunk_id": f"m8-s00-{index:05d}",
            "vector_f32_le_base64": encoded(vector_bytes[index]),
        })
    for index in range(usable):
        ordinal = (25 + index) % count
        queries.append({
            "filter": {key: "*" for key in normal_filter(ordinal)},
            "query_id": f"m8-q-perturbed-{index:03d}",
            "query_type": "perturbed",
            "target_chunk_id": f"m8-s00-{ordinal:05d}",
            "vector_f32_le_base64": encoded(perturbed[index]),
        })
    for index in range(usable):
        ordinal = (50 + index) % count
        queries.append({
            "filter": normal_filter(ordinal),
            "query_id": f"m8-q-metadata-filter-{index:03d}",
            "query_type": "metadata-filter",
            "target_chunk_id": f"m8-s00-{ordinal:05d}",
            "vector_f32_le_base64": encoded(vector_bytes[ordinal]),
        })
    for index in range(usable):
        ordinal = (75 + index) % count
        query_filter = normal_filter(ordinal)
        query_filter["owner_id"] = "owner-missing"
        queries.append({
            "filter": query_filter,
            "query_id": f"m8-q-wrong-owner-no-hit-{index:03d}",
            "query_type": "wrong-owner-no-hit",
            "target_chunk_id": f"m8-s00-{ordinal:05d}",
            "vector_f32_le_base64": encoded(vector_bytes[ordinal]),
        })
    if count >= FORMAL_CHUNK_COUNT:
        for ordinal in range(100, 104):
            queries.append({
                "filter": normal_filter(ordinal),
                "query_id": f"m8-q-negative-{ordinal}",
                "query_type": "negative-fixture",
                "target_chunk_id": f"m8-s00-{ordinal:05d}",
                "vector_f32_le_base64": encoded(vector_bytes[ordinal]),
            })
    return queries


def _gold_from_persisted(
    chunks_path: Path,
    queries_path: Path,
    vectors_path: Path,
    dimension: int,
    *,
    normalization_tolerance: float = NORMALIZATION_TOLERANCE,
    formal_contract: bool = False,
) -> list[dict[str, Any]]:
    chunk_keys = {
        "chunk_id",
        "filter_label",
        "generation",
        "ordinal",
        "owner_id",
        "published",
        "snapshot",
        "source_id",
        "tombstone",
        "vector_byte_length",
        "vector_byte_offset",
    }
    query_keys = {
        "filter",
        "query_id",
        "query_type",
        "target_chunk_id",
        "vector_f32_le_base64",
    }
    filter_keys = {
        "filter_label",
        "generation",
        "owner_id",
        "published",
        "snapshot",
        "source_id",
        "tombstone",
    }

    def load_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise _error("PERSISTED_READ_FAILED", f"cannot read persisted {label}") from exc
        if not data or not data.endswith(b"\n") or b"\r" in data:
            raise _error("NONCANONICAL_JSONL", f"persisted {label} framing is invalid")

        def reject_constant(value: str) -> None:
            raise ValueError(f"non-finite JSON constant: {value}")

        def closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            output: dict[str, Any] = {}
            for key, value in pairs:
                if key in output:
                    raise ValueError(f"duplicate JSON key: {key}")
                output[key] = value
            return output

        records: list[dict[str, Any]] = []
        for line in data.splitlines(keepends=True):
            try:
                record = json.loads(
                    line,
                    object_pairs_hook=closed_object,
                    parse_constant=reject_constant,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise _error("INVALID_JSONL", f"persisted {label} contains invalid JSON") from exc
            try:
                canonical = canonical_json(record)
            except (TypeError, ValueError) as exc:
                raise _error("INVALID_JSONL", f"persisted {label} cannot be canonicalized") from exc
            if not isinstance(record, dict) or canonical != line:
                raise _error("NONCANONICAL_JSONL", f"persisted {label} is not canonical")
            records.append(record)
        return records

    chunks = load_jsonl(chunks_path, "chunks")
    queries = load_jsonl(queries_path, "queries")
    if formal_contract and (
        len(chunks) != FORMAL_CHUNK_COUNT or len(queries) != FORMAL_QUERY_COUNT
    ):
        raise _error(
            "FORMAL_RECORD_COUNT_MISMATCH",
            "persisted formal record counts are invalid",
        )
    if not chunks:
        raise _error("EMPTY_CHUNKS", "persisted chunks must not be empty")
    expected_chunks = (
        _chunk_records(FORMAL_CHUNK_COUNT, dimension) if formal_contract else None
    )
    chunk_ids: set[str] = set()
    for index, chunk in enumerate(chunks):
        if set(chunk) != chunk_keys:
            raise _error("INVALID_CHUNK_RECORD", "persisted chunk keys are invalid")
        chunk_id = chunk.get("chunk_id")
        if not isinstance(chunk_id, str) or chunk_id in chunk_ids:
            raise _error("DUPLICATE_CHUNK_ID", "persisted chunk ids must be unique strings")
        chunk_ids.add(chunk_id)
        if (
            chunk.get("ordinal") != index
            or chunk.get("vector_byte_length") != dimension * 4
            or chunk.get("vector_byte_offset") != index * dimension * 4
        ):
            raise _error("INVALID_CHUNK_LAYOUT", "persisted chunk vector layout is invalid")
        if expected_chunks is not None and chunk != expected_chunks[index]:
            raise _error(
                "INVALID_FORMAL_CHUNK",
                "persisted formal chunk semantics are invalid",
            )

    try:
        vector_bytes = vectors_path.read_bytes()
    except OSError as exc:
        raise _error("PERSISTED_READ_FAILED", "cannot read persisted vectors") from exc
    expected_bytes = len(chunks) * dimension * 4
    if len(vector_bytes) != expected_bytes:
        raise _error(
            "VECTOR_BYTE_COUNT_MISMATCH",
            "persisted vector byte count is invalid",
        )
    stored_vectors = np.frombuffer(vector_bytes, dtype="<f4").reshape(
        (len(chunks), dimension)
    )
    vectors = stored_vectors.astype(np.float64)
    if not bool(np.all(np.isfinite(vectors))):
        raise _error("INVALID_VECTOR", "persisted vectors must be finite")
    vector_norms = np.sqrt(np.sum(vectors * vectors, axis=1, dtype=np.float64))
    if bool(np.any(np.abs(vector_norms - 1.0) > normalization_tolerance)):
        raise _error(
            "VECTOR_NORMALIZATION_ERROR",
            "persisted vectors exceed norm tolerance",
        )

    expected_queries = None
    if formal_contract:
        expected_vectors, expected_perturbed = _make_vectors(
            FORMAL_CHUNK_COUNT,
            dimension,
            FORMAL_SEED,
            FORMAL_PERTURBATION_SEED,
            normalization_tolerance,
        )
        if vector_bytes != expected_vectors.tobytes(order="C"):
            raise _error(
                "INVALID_FORMAL_VECTOR",
                "persisted formal vectors differ from deterministic derivation",
            )
        expected_queries = _query_records(
            expected_vectors,
            expected_perturbed,
            FORMAL_CHUNK_COUNT,
            dimension,
        )

    query_ids: set[str] = set()
    decoded_queries: list[tuple[dict[str, Any], Any]] = []
    for query_index, query in enumerate(queries):
        if set(query) != query_keys or set(query.get("filter", {})) != filter_keys:
            raise _error("INVALID_QUERY_RECORD", "persisted query keys are invalid")
        if expected_queries is not None and query != expected_queries[query_index]:
            raise _error(
                "INVALID_FORMAL_QUERY",
                "persisted formal query semantics are invalid",
            )
        query_id = query.get("query_id")
        if not isinstance(query_id, str) or query_id in query_ids:
            raise _error("DUPLICATE_QUERY_ID", "persisted query ids must be unique strings")
        query_ids.add(query_id)
        if query.get("target_chunk_id") not in chunk_ids:
            raise _error("UNKNOWN_TARGET_CHUNK", "persisted query target must name a chunk")
        encoded = query.get("vector_f32_le_base64")
        if not isinstance(encoded, str):
            raise _error("INVALID_QUERY_VECTOR", "query vector must be base64 text")
        try:
            raw_query = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise _error("INVALID_QUERY_VECTOR", "query vector base64 is invalid") from exc
        if (
            base64.b64encode(raw_query).decode("ascii") != encoded
            or len(raw_query) != dimension * 4
        ):
            raise _error(
                "INVALID_QUERY_VECTOR",
                "query vector bytes are noncanonical or wrong-sized",
            )
        query_vector = np.frombuffer(raw_query, dtype="<f4").astype(np.float64)
        if query_vector.shape != (dimension,) or not bool(
            np.all(np.isfinite(query_vector))
        ):
            raise _error(
                "INVALID_QUERY_VECTOR",
                "query vector must contain finite float32 values",
            )
        query_norm = float(
            np.sqrt(np.sum(query_vector * query_vector, dtype=np.float64))
        )
        if abs(query_norm - 1.0) > normalization_tolerance:
            raise _error(
                "QUERY_NORMALIZATION_ERROR",
                "persisted query vector exceeds norm tolerance",
            )
        decoded_queries.append((query, query_vector))

    output: list[dict[str, Any]] = []
    for query, query_vector in decoded_queries:
        query_filter = query["filter"]
        candidates: list[tuple[float, bytes, str]] = []
        for index, chunk in enumerate(chunks):
            if any(
                expected != "*" and chunk[key] != expected
                for key, expected in query_filter.items()
            ):
                continue
            score = float(np.dot(query_vector, vectors[index]))
            if not np.isfinite(score):
                raise _error("INVALID_SCORE", "ranking score must be finite")
            chunk_id = chunk["chunk_id"]
            candidates.append((score, chunk_id.encode("utf-8"), chunk_id))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        ordered = [item[2] for item in candidates]
        output.append(
            {
                "gold_by_k": {str(k): ordered[:k] for k in FORMAL_TOP_K},
                "query_id": query["query_id"],
            }
        )
    return output


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> bytes:
    data = b"".join(canonical_json(record) for record in records)
    path.write_bytes(data)
    return data


def _load_persisted_gold(
    gold_path: Path,
    expected_gold: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reopen canonical gold JSONL and prove exact semantic equality."""

    try:
        data = gold_path.read_bytes()
    except OSError as exc:
        raise _error("PERSISTED_READ_FAILED", "cannot read persisted gold") from exc
    if not data or not data.endswith(b"\n") or b"\r" in data:
        raise _error("NONCANONICAL_JSONL", "persisted gold framing is invalid")

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    def closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    records: list[dict[str, Any]] = []
    for index, line in enumerate(data.splitlines(keepends=True)):
        try:
            record = json.loads(
                line,
                object_pairs_hook=closed_object,
                parse_constant=reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise _error(
                "INVALID_GOLD_JSONL",
                "persisted gold contains invalid JSON",
            ) from exc
        try:
            canonical = canonical_json(record)
        except (TypeError, ValueError) as exc:
            raise _error(
                "INVALID_GOLD_JSONL",
                "persisted gold cannot be canonicalized",
            ) from exc
        if not isinstance(record, dict) or canonical != line:
            raise _error("NONCANONICAL_JSONL", "persisted gold is not canonical")
        if set(record) != {"gold_by_k", "query_id"}:
            raise _error("INVALID_GOLD_RECORD", "persisted gold keys are invalid")
        gold_by_k = record.get("gold_by_k")
        if not isinstance(gold_by_k, dict) or set(gold_by_k) != {
            str(value) for value in FORMAL_TOP_K
        }:
            raise _error("INVALID_GOLD_RECORD", "persisted gold_by_k keys are invalid")
        query_id = record.get("query_id")
        if not isinstance(query_id, str):
            raise _error("INVALID_GOLD_RECORD", "persisted gold query id is invalid")
        for value in gold_by_k.values():
            if (
                not isinstance(value, list)
                or any(not isinstance(chunk_id, str) for chunk_id in value)
                or len(value) != len(set(value))
            ):
                raise _error("INVALID_GOLD_RECORD", "persisted gold chunk ids are invalid")
        if index >= len(expected_gold) or record != expected_gold[index]:
            raise _error(
                "GOLD_RECOMPUTATION_MISMATCH",
                "persisted gold differs from independent recomputation",
            )
        records.append(record)
    if len(records) != len(expected_gold):
        raise _error(
            "GOLD_RECOMPUTATION_MISMATCH",
            "persisted gold record count differs from independent recomputation",
        )
    return records


def _build_tree(
    staging: Path,
    mode: str,
    chunk_count: int,
    dimension: int,
    seed: int,
    perturb_seed: int,
    *,
    normalization_tolerance: float = NORMALIZATION_TOLERANCE,
) -> None:
    if np is None:
        raise _error("NUMPY_UNAVAILABLE", "NumPy is required")
    vectors, perturbed = _make_vectors(
        chunk_count,
        dimension,
        seed,
        perturb_seed,
        normalization_tolerance,
    )
    chunks = _chunk_records(chunk_count, dimension)
    queries = _query_records(vectors, perturbed, chunk_count, dimension)
    input_dir = staging / "input"
    input_dir.mkdir(parents=True)
    chunks_path = input_dir / "chunks.jsonl"
    queries_path = input_dir / "queries.jsonl"
    vectors_path = input_dir / "vectors.bin"
    gold_path = input_dir / "gold.jsonl"
    _write_jsonl(chunks_path, chunks)
    _write_jsonl(queries_path, queries)
    vectors_path.write_bytes(vectors.tobytes(order="C"))
    gold = _gold_from_persisted(
        chunks_path,
        queries_path,
        vectors_path,
        dimension,
        normalization_tolerance=normalization_tolerance,
        formal_contract=mode == "formal",
    )
    _write_jsonl(gold_path, gold)
    persisted_gold = _load_persisted_gold(gold_path, gold)

    jsonl_counts: dict[str, int] = {
        "gold.jsonl": len(persisted_gold),
    }
    for name in ("chunks.jsonl", "queries.jsonl"):
        body = (input_dir / name).read_bytes()
        if not body or not body.endswith(b"\n") or b"\r" in body:
            raise _error(
                "NONCANONICAL_JSONL",
                f"persisted {name} framing is invalid",
            )
        jsonl_counts[name] = len(body.splitlines())
    vector_body = vectors_path.read_bytes()
    vector_record_size = dimension * 4
    if len(vector_body) % vector_record_size:
        raise _error(
            "VECTOR_BYTE_COUNT_MISMATCH",
            "persisted vector byte geometry is invalid",
        )
    record_counts = {
        **jsonl_counts,
        "vectors.bin": len(vector_body) // vector_record_size,
    }
    if record_counts != {
        "chunks.jsonl": len(chunks),
        "gold.jsonl": len(gold),
        "queries.jsonl": len(queries),
        "vectors.bin": chunk_count,
    }:
        raise _error(
            "PERSISTED_RECORD_COUNT_MISMATCH",
            "persisted member record counts are invalid",
        )

    members: list[dict[str, Any]] = []
    for name in sorted(
        record_counts,
        key=lambda item: f"input/{item}".encode("utf-8"),
    ):
        body = (input_dir / name).read_bytes()
        members.append(
            {
                "byte_count": len(body),
                "path": f"input/{name}",
                "record_count": record_counts[name],
                "sha256": sha256(body),
            }
        )
    manifest = {
        "agreement_denominator": record_counts["queries.jsonl"]
        * len(FORMAL_TOP_K),
        "algorithm": ALGORITHM,
        "canonicalization_id": CANONICALIZATION,
        "chunk_count": record_counts["chunks.jsonl"],
        "dimension": dimension,
        "dtype": "<f4",
        "formal_identity": mode == "formal",
        "members": members,
        "mode": mode,
        "negative_objects": [
            "tombstone",
            "unpublished",
            "generation-mismatch",
            "snapshot-mismatch",
        ]
        if mode == "formal"
        else [],
        "normalization_tolerance": normalization_tolerance,
        "numpy_version": str(np.__version__),
        "partitions": {
            "exact": [0, 24],
            "metadata-filter": [50, 74],
            "negative-fixture": [100, 103],
            "perturbed": [25, 49],
            "wrong-owner-no-hit": [75, 99],
        }
        if mode == "formal"
        else {"test-only": [0, record_counts["queries.jsonl"] - 1]},
        "perturbation_seed": perturb_seed,
        "query_count": record_counts["queries.jsonl"],
        "required_set_agreement": 1.0,
        "seed": seed,
        "top_k": FORMAL_TOP_K,
        "vectors_order": "C",
    }
    (staging / "manifest.json").write_bytes(canonical_json(manifest))


def generate(
    output_root: Path,
    mode: str = "test-only",
    *,
    seed: int = FORMAL_SEED,
    perturb_seed: int = FORMAL_PERTURBATION_SEED,
    chunk_count: int | None = None,
    dimension: int | None = None,
    authorization: FormalAuthorization | None = None,
) -> dict[str, Any]:
    """Generate only after preflight, then atomically publish a complete tree."""
    preflight_result = preflight(
        output_root,
        mode,
        authorization=authorization,
    )
    output_root = Path(preflight_result["output_root"])
    if mode == "formal":
        chunk_count = FORMAL_CHUNK_COUNT
        dimension = FORMAL_DIMENSION
        seed = FORMAL_SEED
        perturb_seed = FORMAL_PERTURBATION_SEED
    elif chunk_count is None or dimension is None or chunk_count < 1 or dimension < 1:
        raise _error(
            "TEST_SIZE_REQUIRED",
            "test-only mode requires positive chunk-count and dimension",
        )
    parent = output_root.parent
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.staging-",
            dir=str(parent),
        )
    )
    try:
        _build_tree(
            staging,
            mode,
            chunk_count,
            dimension,
            seed,
            perturb_seed,
            normalization_tolerance=preflight_result["normalization_tolerance"],
        )
        _revalidate_publication(output_root, preflight_result["parent_identity"])
        os.replace(str(staging), str(output_root))
        return {
            "status": "PUBLISHED",
            "mode": mode,
            "output_root": str(output_root),
            "formal_identity": mode == "formal",
        }
    except GeneratorError:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    except (OSError, ValueError, TypeError) as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise _error("GENERATION_FAILED", str(exc)) from None
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        required=True,
        help="absolute absent directory to publish",
    )
    parser.add_argument(
        "--mode",
        choices=("formal", "test-only"),
        default="test-only",
    )
    parser.add_argument("--chunk-count", type=int, help="test-only size")
    parser.add_argument("--dimension", type=int, help="test-only size")
    parser.add_argument("--seed", type=int, default=FORMAL_SEED)
    parser.add_argument(
        "--perturbation-seed",
        type=int,
        default=FORMAL_PERTURBATION_SEED,
    )
    parser.add_argument("--s0", type=Path, help="formal accepted S0 canonical JSON")
    parser.add_argument("--s1", type=Path, help="formal owner S1 canonical JSON")
    parser.add_argument("--environment", type=Path, help="formal environment canonical JSON")
    parser.add_argument("--s1-config", type=Path, help="formal S1 config canonical JSON")
    parser.add_argument(
        "--observer-config",
        type=Path,
        help="formal observer config canonical JSON",
    )
    parser.add_argument(
        "--redaction-registry",
        type=Path,
        help="formal redaction registry canonical JSON",
    )
    parser.add_argument("--preflight", type=Path, help="formal preflight canonical JSON")
    parser.add_argument(
        "--preflight-result",
        type=Path,
        help="formal validated preflight-result canonical JSON",
    )
    return parser.parse_args(argv)


def _authorization_from_args(args: argparse.Namespace) -> FormalAuthorization | None:
    values = {
        "s0_path": args.s0,
        "s1_path": args.s1,
        "environment_path": args.environment,
        "config_path": args.s1_config,
        "observer_config_path": args.observer_config,
        "redaction_registry_path": args.redaction_registry,
        "preflight_path": args.preflight,
        "preflight_result_path": args.preflight_result,
    }
    supplied = [value is not None for value in values.values()]
    if not any(supplied):
        return None
    if not all(supplied):
        raise _error(
            "FORMAL_AUTHORIZATION_INCOMPLETE",
            "all formal authorization artifacts must be supplied together",
        )
    return FormalAuthorization(**values)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
        result = generate(
            Path(args.output_root),
            args.mode,
            seed=args.seed,
            perturb_seed=args.perturbation_seed,
            chunk_count=args.chunk_count,
            dimension=args.dimension,
            authorization=_authorization_from_args(args),
        )
    except GeneratorError as exc:
        print(
            json.dumps(
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        **exc.details,
                    }
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": str(exc),
                    }
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

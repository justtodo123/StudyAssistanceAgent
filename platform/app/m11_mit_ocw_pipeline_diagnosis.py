"""Strict metadata-only diagnosis for the two MIT OCW pipeline rejections."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any, NoReturn

from .m11_acquisition import AcquisitionError, validate_receipt
from .m11_mit_ocw_candidate_materialization import (
    MitOcwCandidateMaterializationError,
    validate_mit_ocw_candidate_materialization,
)

SCHEMA = "sa.m11.p0.mit-ocw-pipeline-diagnosis.v1"
SOURCE_ID = "mit-ocw-6-004-2017"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
MATERIALIZATION_DIGEST = "bb4bae3e49d17fc91b1abcee7ba2f173bc5e6d251fe8be89011ac54c0ea87f0e"
DIGEST_EVIDENCE_DIGEST = "a6503d2629414759ea6bce97190a991a5a4797e2ab9fcb2325849be7c1d23425"
RECEIPT_BATCH_DIGEST = "0a7d9184d30546b9bc5713bc564f43b2b9712515abfc8547de2911a3fa6c7431"
EXPECTED = {
    "digital_answers": {
        "pipeline_reason": "SOURCE_PARSE_FAILED",
        "source_digest": "4952128b9969642958a217aea10c095cd0646e54acbd14e1957e9ccb7969ee58",
        "bytes": 483980,
        "rejected_artifact": "mit-ocw-6-004-2017-digital_answers.json",
        "rejected_artifact_sha256": "72a41203261ce72bd37f055b63aca1166f6fd02a1b0935dc79ecf4cabaa5c3d7",
    },
    "information_worksheet": {
        "pipeline_reason": "INVALID_CANDIDATE_INPUT",
        "source_digest": "3b6f2746c3c4a9573884f9daf542d2d33779b94d9d6259c40f6ae3bb4cc86764",
        "bytes": 301876,
        "rejected_artifact": "mit-ocw-6-004-2017-information_worksheet.json",
        "rejected_artifact_sha256": "aea400a725d59489803040745d0c26cbcc99c88c2439acc2e641064d8299202c",
    },
}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_FALSE_FLAGS = (
    "authority_issued", "human_review_reject_mapped", "evidence_failed_mapped",
    "successor_created", "formal_gate0_executed", "production_artifact_repaired",
    "parser_contract_changed", "network_used", "lifecycle_mutation",
    "host_paths_included", "bodies_included",
)


class MitOcwPipelineDiagnosisError(ValueError):
    """The bounded diagnosis is malformed, unsealed, or escalates scope."""


def _fail(code: str) -> NoReturn:
    raise MitOcwPipelineDiagnosisError(code)


def _payload_digest(payload: Mapping[str, Any]) -> str:
    try:
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MitOcwPipelineDiagnosisError("MIT_DIAGNOSIS_DEPENDENCY_INVALID") from exc
    return hashlib.sha256(encoded).hexdigest()


def _validated_dependencies(materialization: Mapping[str, Any], digest_evidence: Mapping[str, Any], receipt_batch: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if _payload_digest(materialization) != MATERIALIZATION_DIGEST:
        _fail("MIT_DIAGNOSIS_MATERIALIZATION_SEAL_INVALID")
    try:
        validated = validate_mit_ocw_candidate_materialization(materialization)
    except (MitOcwCandidateMaterializationError, TypeError, ValueError) as exc:
        raise MitOcwPipelineDiagnosisError("MIT_DIAGNOSIS_MATERIALIZATION_INVALID") from exc
    if _payload_digest(digest_evidence) != DIGEST_EVIDENCE_DIGEST:
        _fail("MIT_DIAGNOSIS_DIGEST_EVIDENCE_SEAL_INVALID")
    if _payload_digest(receipt_batch) != RECEIPT_BATCH_DIGEST:
        _fail("MIT_DIAGNOSIS_RECEIPT_BATCH_SEAL_INVALID")
    if digest_evidence.get("schema") != "sa.m11.p0-digest-evidence.v1" or not isinstance(digest_evidence.get("assets"), list):
        _fail("MIT_DIAGNOSIS_DIGEST_EVIDENCE_INVALID")
    if receipt_batch.get("schema") != "sa.m11.p0.acquisition-receipt-batch.v1" or receipt_batch.get("scope_digest") != SCOPE_DIGEST or not isinstance(receipt_batch.get("receipts"), list):
        _fail("MIT_DIAGNOSIS_RECEIPT_BATCH_INVALID")

    rejected = {item["asset_id"]: item for item in validated["rejections"]}
    digests = {item.get("asset_id"): item for item in digest_evidence["assets"] if item.get("source_id") == SOURCE_ID}
    receipts: dict[str, Mapping[str, Any]] = {}
    for item in receipt_batch["receipts"]:
        try:
            receipt = validate_receipt(item)
        except (AcquisitionError, TypeError, ValueError) as exc:
            raise MitOcwPipelineDiagnosisError("MIT_DIAGNOSIS_RECEIPT_INVALID") from exc
        if receipt.source_id == SOURCE_ID and receipt.asset_id in EXPECTED:
            receipts[receipt.asset_id] = item
    if set(rejected) != set(EXPECTED) or not set(EXPECTED) <= set(digests) or set(receipts) != set(EXPECTED):
        _fail("MIT_DIAGNOSIS_DEPENDENCY_SCOPE_INVALID")

    linked: dict[str, dict[str, Any]] = {}
    for asset_id, expected in EXPECTED.items():
        rejection = rejected[asset_id]
        digest = digests[asset_id]
        receipt = receipts[asset_id]
        if (
            rejection.get("reason") != expected["pipeline_reason"]
            or rejection.get("rejected_artifact") != expected["rejected_artifact"]
            or rejection.get("rejected_artifact_sha256") != expected["rejected_artifact_sha256"]
            or digest.get("sha256") != expected["source_digest"]
            or digest.get("bytes") != expected["bytes"]
            or receipt.get("sha256") != expected["source_digest"]
            or receipt.get("revision") != expected["source_digest"]
            or receipt.get("bytes") != expected["bytes"]
        ):
            _fail("MIT_DIAGNOSIS_DEPENDENCY_LINK_INVALID")
        linked[asset_id] = {
            **expected,
            "revision": receipt["revision"],
            "receipt_digest": _payload_digest(receipt),
        }
    return linked


def validate_mit_ocw_pipeline_diagnosis(
    payload: Mapping[str, Any], *, materialization: Mapping[str, Any],
    digest_evidence: Mapping[str, Any], receipt_batch: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the sealed diagnosis without reading raw bodies or rerunning parsers."""
    required = {
        "schema", "diagnosis_id", "generated_at", "operation", "metadata_only",
        "source_id", "scope_digest", "runtime", "dependencies", "asset_count",
        "diagnoses", "limitations", *_FALSE_FLAGS,
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("MIT_DIAGNOSIS_FIELDS_INVALID")
    if (
        payload["schema"] != SCHEMA
        or payload["diagnosis_id"] != "m11-p0-mit-ocw-pipeline-diagnosis-20260929"
        or payload["generated_at"] != "2026-09-29"
        or payload["operation"] != "bounded_offline_diagnosis"
        or payload["metadata_only"] is not True
        or payload["source_id"] != SOURCE_ID
        or payload["scope_digest"] != SCOPE_DIGEST
    ):
        _fail("MIT_DIAGNOSIS_IDENTITY_INVALID")
    if payload["runtime"] != {
        "implementation": "CPython", "python_version": "3.11.9",
        "parser_contract": "sa.source.parser-matrix.v1", "contract_changed": False,
    }:
        _fail("MIT_DIAGNOSIS_RUNTIME_INVALID")
    if payload["dependencies"] != {
        "candidate_materialization": "data/manifests/m11-p0-mit-ocw-candidate-materialization-v1.json",
        "candidate_materialization_digest": MATERIALIZATION_DIGEST,
        "digest_evidence": "data/manifests/m11-p0-digest-evidence-v1.json",
        "digest_evidence_digest": DIGEST_EVIDENCE_DIGEST,
        "receipt_batch": "data/manifests/m11-p0-acquisition-26-receipts-v1.json",
        "receipt_batch_digest": RECEIPT_BATCH_DIGEST,
    }:
        _fail("MIT_DIAGNOSIS_DEPENDENCY_REFERENCE_INVALID")
    linked = _validated_dependencies(materialization, digest_evidence, receipt_batch)
    diagnoses = payload["diagnoses"]
    if payload["asset_count"] != 2 or not isinstance(diagnoses, list) or len(diagnoses) != 2:
        _fail("MIT_DIAGNOSIS_COUNT_INVALID")
    seen: set[str] = set()
    expected_observations = [
        {
            "probe": "parse_file_extensionless_without_declared_format",
            "result_code": "FORMAT_UNSUPPORTED",
            "classification": "BOUNDED_OBSERVATION_NOT_ROOT_CAUSE",
        },
        {
            "probe": "parse_file_extensionless_with_declared_pdf",
            "result_code": "FORMAT_MISMATCH",
            "classification": "BOUNDED_OBSERVATION_NOT_ROOT_CAUSE",
        },
    ]
    fields = {
        "asset_id", "pipeline_reason", "diagnosis_status", "exact_root_cause_proved",
        "source_digest", "revision", "bytes", "receipt_digest", "rejected_artifact",
        "rejected_artifact_sha256", "pdf_magic_observed", "raw_identity_matches_tracked",
        "probe_observations", "factual_conclusion",
    }
    for diagnosis in diagnoses:
        if not isinstance(diagnosis, Mapping) or set(diagnosis) != fields:
            _fail("MIT_DIAGNOSIS_RECORD_FIELDS_INVALID")
        asset_id = diagnosis.get("asset_id")
        if asset_id in seen or asset_id not in linked:
            _fail("MIT_DIAGNOSIS_RECORD_SCOPE_INVALID")
        seen.add(asset_id)
        expected = linked[asset_id]
        for field in ("source_digest", "revision", "receipt_digest", "rejected_artifact_sha256"):
            if not isinstance(diagnosis[field], str) or not _HEX.fullmatch(diagnosis[field]):
                _fail("MIT_DIAGNOSIS_DIGEST_INVALID")
        if any(diagnosis.get(key) != expected[key] for key in expected):
            _fail("MIT_DIAGNOSIS_DEPENDENCY_LINK_INVALID")
        if (
            diagnosis["diagnosis_status"] != "UNRESOLVED"
            or diagnosis["exact_root_cause_proved"] is not False
            or diagnosis["pdf_magic_observed"] is not True
            or diagnosis["raw_identity_matches_tracked"] is not True
            or diagnosis["probe_observations"] != expected_observations
            or diagnosis["factual_conclusion"] != "EXACT_ROOT_CAUSE_NOT_PROVED_FROM_AVAILABLE_ARTIFACTS"
        ):
            _fail("MIT_DIAGNOSIS_CONCLUSION_INVALID")
    if seen != set(EXPECTED):
        _fail("MIT_DIAGNOSIS_RECORD_SCOPE_INVALID")
    if payload["limitations"] != [
        "PROBES_DO_NOT_REPRODUCE_OR_EXPLAIN_THE_ORIGINAL_PIPELINE_FAILURE",
        "NO_ORIGINAL_EXCEPTION_DETAIL_IS_PRESENT_IN_REJECTED_METADATA",
        "DIAGNOSIS_DOES_NOT_CHANGE_PIPELINE_OR_HUMAN_REVIEW_STATUS",
    ]:
        _fail("MIT_DIAGNOSIS_LIMITATIONS_INVALID")
    if any(payload[field] is not False for field in _FALSE_FLAGS):
        _fail("MIT_DIAGNOSIS_ESCALATION_FORBIDDEN")
    return copy.deepcopy(dict(payload))

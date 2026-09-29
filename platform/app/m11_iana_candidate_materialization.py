"""Strict metadata contract for the IANA exact-three replay checkpoint."""
from __future__ import annotations

import copy
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

SCHEMA = "sa.m11.p0.iana-candidate-materialization.v1"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
SOURCE_ID = "iana-registries"
ASSET_IDS = [
    "service-names-port-numbers-csv",
    "service-names-port-numbers-xml",
    "service-names-port-numbers-txt",
]
PARSER_CONTRACT = "cpython-textio==3.11.9"
PREDECESSOR_SLICE_ID = "rfc-iana-evidence-review-defer-6-20260927"
FORMAL_GATE0_RESULT_ID = "m11-p0-formal-gate0-26-result-20260928"
EXPECTED_DOCUMENT_CHUNKS = {
    "service-names-port-numbers-csv": ("0d257654ec0788a56d220f71cd12907d", "8b6eaae1ffaf1e7a64f96fba8bc7c104"),
    "service-names-port-numbers-xml": ("50e564768edc1cc7d7d0d7c989fee49d", "a59ae838bd18817062abecbd3d37fcb1"),
    "service-names-port-numbers-txt": ("b7e9d4df1e7e752bd190243d46efd760", "fa39d45703d9598805947b084f5c0546"),
}
EXPECTED_RAW_DIGESTS = {
    "service-names-port-numbers-csv": "34328ed0940d889207de6da29bf0e6e1438d604483c8e1ffb03dceab8f7ec26f",
    "service-names-port-numbers-xml": "30a69353af6e017ffd9e141d079f90a7b7117f113f122d2d89ee20ffb587da19",
    "service-names-port-numbers-txt": "6aa4def90086ae3dd71ee8f72e2bddb57857828718d3155b42c107138a3c1d29",
}
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")

class IanaCandidateMaterializationError(ValueError):
    """The exact-three checkpoint is malformed or escalates authority."""

def _fail(code: str) -> NoReturn:
    raise IanaCandidateMaterializationError(code)

def _digest(value: Any) -> None:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        _fail("IANA_MATERIALIZATION_DIGEST_INVALID")

def _artifact(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith(".json") or "/" in value or "\\" in value:
        _fail("IANA_MATERIALIZATION_ARTIFACT_INVALID")

def frozen_runtime_identity() -> dict[str, str]:
    """Require the replay to run only on the frozen CPython 3.11.9 contract."""
    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.implementation.name != "cpython" or version != "3.11.9":
        _fail("IANA_MATERIALIZATION_RUNTIME_UNAVAILABLE")
    return {"implementation": "cpython", "python": version, "parser_contract": PARSER_CONTRACT}

def validate_iana_candidate_materialization(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact-three identities and all non-promotion boundaries."""
    if not isinstance(payload, Mapping):
        _fail("IANA_MATERIALIZATION_PAYLOAD_INVALID")
    required = {
        "schema", "materialization_id", "generated_at", "source_id", "scope_digest", "asset_ids",
        "input_asset_count", "candidate_asset_count", "validated_candidate_artifact_count", "candidate_chunk_count",
        "rejections", "assets", "parser_environment", "parser_observations", "evidence_bindings",
        "predecessor", "historical_gate0", "current_heads", "approved_document_count", "approved_chunk_count",
        "counts_toward_3k", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized",
        "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included",
    }
    if set(payload) != required:
        _fail("IANA_MATERIALIZATION_FIELDS_INVALID")
    if payload["schema"] != SCHEMA or payload["source_id"] != SOURCE_ID or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("IANA_MATERIALIZATION_IDENTITY_INVALID")
    if payload["asset_ids"] != ASSET_IDS or payload["generated_at"] != "2026-09-29":
        _fail("IANA_MATERIALIZATION_SCOPE_INVALID")
    if not isinstance(payload["materialization_id"], str) or not _ID.fullmatch(payload["materialization_id"]):
        _fail("IANA_MATERIALIZATION_ID_INVALID")
    if payload["parser_environment"] != {"implementation": "cpython", "python": "3.11.9", "parser_contract": PARSER_CONTRACT}:
        _fail("IANA_MATERIALIZATION_PARSER_INVALID")
    observations = payload["parser_observations"]
    if observations != {"csv": "REPLAYED", "xml": "REPLAYED", "txt": "FAIL_CLOSED_AMBIENT_ONLY"}:
        _fail("IANA_MATERIALIZATION_PARSER_OBSERVATION_INVALID")
    if payload["rejections"] != [] or payload["current_heads"] != {"rfc": "3 ACCEPT", "iana": "3 DEFER", "mit_ocw": "20 DEFER"}:
        _fail("IANA_MATERIALIZATION_HISTORY_INVALID")
    if payload["predecessor"] != {"slice_id": PREDECESSOR_SLICE_ID, "manifest": "data/manifests/m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json", "sha256": "57b7f286cadb62613f7f0ec8ee32b32e67e4c96e264b2725f6ec13ff2b3774b1", "status": "DEFER", "asset_count": 3}:
        _fail("IANA_MATERIALIZATION_PREDECESSOR_INVALID")
    if payload["historical_gate0"] != {"result_id": FORMAL_GATE0_RESULT_ID, "manifest": "data/manifests/m11-p0-formal-gate0-26-result-v1.json", "sha256": "fb08c974171f9935823c8819141de873f9c29565058b7a7583839b3130c4ac41", "result": "BLOCKED", "immutable": True}:
        _fail("IANA_MATERIALIZATION_GATE0_INVALID")
    for field in ("counts_toward_3k", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"):
        if payload[field] is not False:
            _fail("IANA_MATERIALIZATION_ESCALATION_FORBIDDEN")
    if payload["approved_document_count"] != 0 or payload["approved_chunk_count"] != 0:
        _fail("IANA_MATERIALIZATION_APPROVAL_FORBIDDEN")
    assets = payload["assets"]
    if not isinstance(assets, Sequence) or isinstance(assets, (str, bytes)) or len(assets) != 3:
        _fail("IANA_MATERIALIZATION_PARTITION_INVALID")
    seen = set()
    for item in assets:
        if not isinstance(item, Mapping) or set(item) != {"asset_id", "candidate_artifact", "candidate_artifact_sha256", "normalized_artifact", "normalized_artifact_sha256", "raw_sha256", "receipt_sha256", "revision", "document_id", "chunk_id", "chunk_count", "content_fingerprint", "status"}:
            _fail("IANA_MATERIALIZATION_ASSET_FIELDS_INVALID")
        asset = item["asset_id"]
        if asset not in ASSET_IDS or asset in seen or item["status"] != "CANDIDATE_VALIDATED" or item["chunk_count"] != 1:
            _fail("IANA_MATERIALIZATION_ASSET_INVALID")
        seen.add(asset)
        for field in ("candidate_artifact_sha256", "normalized_artifact_sha256", "raw_sha256", "receipt_sha256", "revision", "content_fingerprint"):
            _digest(item[field])
        _artifact(item["candidate_artifact"]); _artifact(item["normalized_artifact"])
        if not isinstance(item["document_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", item["document_id"]):
            _fail("IANA_MATERIALIZATION_DOCUMENT_ID_INVALID")
        if not isinstance(item["chunk_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", item["chunk_id"]):
            _fail("IANA_MATERIALIZATION_CHUNK_ID_INVALID")
        if (item["document_id"], item["chunk_id"]) != EXPECTED_DOCUMENT_CHUNKS[asset] or item["raw_sha256"] != EXPECTED_RAW_DIGESTS[asset]:
            _fail("IANA_MATERIALIZATION_IDENTITY_DIGEST_INVALID")
    if seen != set(ASSET_IDS) or payload["input_asset_count"] != 3 or payload["candidate_asset_count"] != 3 or payload["validated_candidate_artifact_count"] != 3 or payload["candidate_chunk_count"] != 3:
        _fail("IANA_MATERIALIZATION_COUNTS_INVALID")
    bindings = payload["evidence_bindings"]
    if bindings != {"digest_manifest": "data/manifests/m11-p0-digest-evidence-v1.json", "digest_manifest_sha256": "d5314cdb02152032d188662ee5fd8b25a39f377893b6dc9c88a6ea1581c604f5", "receipt_manifest": "data/manifests/m11-p0-acquisition-26-receipts-v1.json", "receipt_manifest_sha256": "0a7d9184d30546b9bc5713bc564f43b2b9712515abfc8547de2911a3fa6c7431", "review_result": "data/manifests/m11-p0-iana-evidence-review-result-v1.json", "review_result_sha256": "8f6da4267619dd16415d6c484902855df161192f99ef1b87abacce4f70145f4f", "packet": "data/manifests/m11-p0-iana-evidence-closure-packet-v1.json", "packet_sha256": "12d2a52564ccc22fc6345b0b53c811e7aac6f810ff39ebe0077d35c64d696d20", "census": "data/manifests/m11-p0-iana-evidence-census-v1.json", "census_sha256": "51580e8a5dad89f777c747ab169d71866ea47cf8a4420eca494444800c278c68", "disposition": "data/manifests/m11-p0-iana-owner-disposition-v1.json", "disposition_sha256": "df3b09eee78d977dc8b699b317236909aff1ffe97e7ae36e7e04b188fe0509a1"}:
        _fail("IANA_MATERIALIZATION_EVIDENCE_BINDING_INVALID")
    return copy.deepcopy(dict(payload))

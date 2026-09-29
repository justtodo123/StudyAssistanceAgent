"""Strict non-executing MIT OCW exact-20 owner decision-input packet."""
from __future__ import annotations
import copy, hashlib, json, re
from collections.abc import Mapping
from typing import Any, NoReturn
from .m11_acquisition import AcquisitionError, validate_receipt
from .m11_gate0 import EVIDENCE_CATEGORIES
from .m11_mit_ocw_candidate_materialization import EXPECTED_CANDIDATES, EXPECTED_REJECTIONS, MitOcwCandidateMaterializationError, validate_mit_ocw_candidate_materialization
from .m11_mit_ocw_evidence_review import EXACT_ASSETS

SCHEMA = "sa.m11.p0.mit-ocw-owner-decision-input-packet.v1"
SOURCE_ID = "mit-ocw-6-004-2017"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
MATERIALIZATION_DIGEST = "bb4bae3e49d17fc91b1abcee7ba2f173bc5e6d251fe8be89011ac54c0ea87f0e"
DIGEST_EVIDENCE_DIGEST = "a6503d2629414759ea6bce97190a991a5a4797e2ab9fcb2325849be7c1d23425"
RECEIPT_BATCH_DIGEST = "0a7d9184d30546b9bc5713bc564f43b2b9712515abfc8547de2911a3fa6c7431"
GATE0_RESULT_DIGEST = "fb08c974171f9935823c8819141de873f9c29565058b7a7583839b3130c4ac41"
ASSETS = EXACT_ASSETS[SOURCE_ID]
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_DOC_ID = re.compile(r"[0-9a-f]{32}\Z")
_RECORD_FIELDS = {"source_id","asset_id","source_digest","receipt_digest","revision","candidate_pipeline_status","candidate_digest","document_id","chunk_count","normalization_status","pipeline_reason"}
_FALSE_FLAGS = ("formal_gate0_executed","candidate_approval_granted","publication_authorized","network_used","source_expansion","lifecycle_mutation","host_paths_included","bodies_included")

class MitOcwOwnerDecisionPacketError(ValueError):
    """The MIT owner decision-input packet is malformed or escalates scope."""

def _fail(code: str) -> NoReturn:
    raise MitOcwOwnerDecisionPacketError(code)

def _payload_digest(payload: Mapping[str, Any]) -> str:
    try: encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc: raise MitOcwOwnerDecisionPacketError("MIT_PACKET_DEPENDENCY_INVALID") from exc
    return hashlib.sha256(encoded).hexdigest()

def _receipt_digest(receipt: Mapping[str, Any]) -> str: return _payload_digest(receipt)

def _validated_dependencies(materialization, digest_evidence, receipt_batch, gate0_result):
    if _payload_digest(materialization) != MATERIALIZATION_DIGEST: _fail("MIT_PACKET_MATERIALIZATION_DEPENDENCY_INVALID")
    try: mat = validate_mit_ocw_candidate_materialization(materialization)
    except (MitOcwCandidateMaterializationError, TypeError, ValueError) as exc: raise MitOcwOwnerDecisionPacketError("MIT_PACKET_MATERIALIZATION_DEPENDENCY_INVALID") from exc
    if (_payload_digest(digest_evidence) != DIGEST_EVIDENCE_DIGEST or digest_evidence.get("schema") != "sa.m11.p0-digest-evidence.v1" or digest_evidence.get("status") != "DIGESTS_CAPTURED_CANDIDATE_PIPELINE_AUTHORIZED" or digest_evidence.get("asset_count") != 26 or not isinstance(digest_evidence.get("assets"), list)): _fail("MIT_PACKET_DIGEST_DEPENDENCY_INVALID")
    db = {x.get("asset_id"): x for x in digest_evidence["assets"] if isinstance(x, Mapping) and x.get("source_id") == SOURCE_ID}
    if set(db) != set(ASSETS): _fail("MIT_PACKET_DIGEST_DEPENDENCY_INVALID")
    if (_payload_digest(receipt_batch) != RECEIPT_BATCH_DIGEST or receipt_batch.get("schema") != "sa.m11.p0.acquisition-receipt-batch.v1" or receipt_batch.get("scope_digest") != SCOPE_DIGEST or receipt_batch.get("asset_count") != 26 or receipt_batch.get("decision") != "ACQUIRED" or not isinstance(receipt_batch.get("receipts"), list)): _fail("MIT_PACKET_RECEIPT_DEPENDENCY_INVALID")
    rb = {}
    for item in receipt_batch["receipts"]:
        try: vr = validate_receipt(item)
        except (AcquisitionError, TypeError, ValueError) as exc: raise MitOcwOwnerDecisionPacketError("MIT_PACKET_RECEIPT_DEPENDENCY_INVALID") from exc
        if vr.source_id == SOURCE_ID:
            if vr.asset_id in rb or vr.status != "ACQUIRED": _fail("MIT_PACKET_RECEIPT_DEPENDENCY_INVALID")
            rb[vr.asset_id] = item
    if set(rb) != set(ASSETS): _fail("MIT_PACKET_RECEIPT_DEPENDENCY_INVALID")
    if (_payload_digest(gate0_result) != GATE0_RESULT_DIGEST or gate0_result.get("schema") != "sa.m11.formal-gate0-result.v1" or gate0_result.get("result_id") != "m11-p0-formal-gate0-26-result-20260928" or gate0_result.get("status") != "BLOCKED"): _fail("MIT_PACKET_GATE0_DEPENDENCY_INVALID")
    ca = {x["asset_id"]: x for x in mat["assets"]}; rj = {x["asset_id"]: x for x in mat["rejections"]}; out = {}
    for asset in ASSETS:
        d, r = db[asset], rb[asset]; sd = d.get("sha256")
        if not isinstance(sd, str) or not _HEX.fullmatch(sd) or r.get("sha256") != sd or r.get("revision") != sd or r.get("canonical_url") != d.get("url") or r.get("bytes") != d.get("bytes"): _fail("MIT_PACKET_DEPENDENCY_LINK_INVALID")
        base = {"source_id": SOURCE_ID, "asset_id": asset, "source_digest": sd, "receipt_digest": _receipt_digest(r), "revision": r["revision"]}
        if asset in ca:
            x = ca[asset]; base.update(candidate_pipeline_status="CANDIDATE_VALIDATED", candidate_digest=x["candidate_digest"], document_id=x["document_id"], chunk_count=x["chunk_count"], normalization_status="CANDIDATE", pipeline_reason="NONE")
        else:
            x = rj[asset]; base.update(candidate_pipeline_status="REJECTED", candidate_digest=x["rejected_artifact_sha256"], document_id=None, chunk_count=0, normalization_status="REJECTED", pipeline_reason=x["reason"])
        out[asset] = base
    return out

def validate_mit_ocw_owner_decision_packet(payload: Mapping[str, Any], *, materialization, digest_evidence, receipt_batch, gate0_result) -> dict[str, Any]:
    required = {"schema","packet_id","scope_digest","operation","metadata_only","authority_issued","source_id","candidate_materialization_manifest","source_manifest","receipt_manifest","candidate_materialization_digest","digest_evidence_digest","receipt_batch_digest","asset_count","validated_candidate_count","pipeline_rejected_count","validated_assets","pipeline_rejected_assets","pipeline_rejections","batch_records","proposed_statuses","current_heads","current_status","historical_gate0_reference",*_FALSE_FLAGS}
    if not isinstance(payload, Mapping) or set(payload) != required: _fail("MIT_PACKET_FIELDS_INVALID")
    if (payload["schema"],payload["scope_digest"],payload["operation"],payload["source_id"]) != (SCHEMA,SCOPE_DIGEST,"owner_decision_inputs",SOURCE_ID): _fail("MIT_PACKET_IDENTITY_INVALID")
    if payload["metadata_only"] is not True or payload["authority_issued"] is not False: _fail("MIT_PACKET_AUTHORITY_ESCALATION")
    if (payload["candidate_materialization_manifest"],payload["source_manifest"],payload["receipt_manifest"],payload["candidate_materialization_digest"],payload["digest_evidence_digest"],payload["receipt_batch_digest"]) != ("data/manifests/m11-p0-mit-ocw-candidate-materialization-v1.json","data/manifests/m11-p0-digest-evidence-v1.json","data/manifests/m11-p0-acquisition-26-receipts-v1.json",MATERIALIZATION_DIGEST,DIGEST_EVIDENCE_DIGEST,RECEIPT_BATCH_DIGEST): _fail("MIT_PACKET_DEPENDENCY_REFERENCE_INVALID")
    expected = _validated_dependencies(materialization,digest_evidence,receipt_batch,gate0_result)
    if (payload["asset_count"],payload["validated_candidate_count"],payload["pipeline_rejected_count"]) != (20,18,2) or payload["validated_assets"] != [x["asset_id"] for x in materialization["assets"]] or payload["pipeline_rejected_assets"] != [x["asset_id"] for x in materialization["rejections"]] or set(payload["validated_assets"]) != EXPECTED_CANDIDATES or set(payload["pipeline_rejected_assets"]) != set(EXPECTED_REJECTIONS): _fail("MIT_PACKET_PARTITION_INVALID")
    if payload["pipeline_rejections"] != {a:{"status":"REJECTED","reason":r} for a,r in EXPECTED_REJECTIONS.items()}: _fail("MIT_PACKET_PIPELINE_FACTS_INVALID")
    records = payload["batch_records"]
    if not isinstance(records,list) or len(records) != 20: _fail("MIT_PACKET_RECORDS_INVALID")
    seen=set()
    for record in records:
        if not isinstance(record,Mapping) or set(record) != _RECORD_FIELDS: _fail("MIT_PACKET_RECORD_FIELDS_INVALID")
        asset=record.get("asset_id")
        if asset in seen or record.get("source_id") != SOURCE_ID or asset not in expected: _fail("MIT_PACKET_RECORD_SCOPE_INVALID")
        seen.add(asset)
        if any(not isinstance(record[f],str) or not _HEX.fullmatch(record[f]) for f in ("source_digest","receipt_digest","revision","candidate_digest")): _fail("MIT_PACKET_RECORD_DIGEST_INVALID")
        if record["document_id"] is not None and (not isinstance(record["document_id"],str) or not _DOC_ID.fullmatch(record["document_id"])): _fail("MIT_PACKET_DOCUMENT_ID_INVALID")
        if record != expected[asset]: _fail("MIT_PACKET_DEPENDENCY_LINK_INVALID")
    if seen != set(ASSETS): _fail("MIT_PACKET_RECORD_SCOPE_INVALID")
    statuses=payload["proposed_statuses"]
    if not isinstance(statuses,Mapping) or set(statuses) != set(ASSETS): _fail("MIT_PACKET_STATUS_SCOPE_INVALID")
    for asset in ASSETS:
        if not isinstance(statuses[asset],Mapping) or set(statuses[asset]) != set(EVIDENCE_CATEGORIES) or any(statuses[asset][c] != "PENDING" for c in EVIDENCE_CATEGORIES): _fail("MIT_PACKET_STATUS_MUST_REMAIN_PENDING")
    if payload["current_heads"] != {"rfc":"3 ACCEPT","iana":"3 DEFER","mit_ocw":"20 DEFER"} or payload["current_status"] != "REVIEW_REQUIRED": _fail("MIT_PACKET_CURRENT_STATE_INVALID")
    if payload["historical_gate0_reference"] != {"result_manifest":"data/manifests/m11-p0-formal-gate0-26-result-v1.json","result_id":"m11-p0-formal-gate0-26-result-20260928","status":"BLOCKED"}: _fail("MIT_PACKET_GATE0_REFERENCE_INVALID")
    if any(payload[f] is not False for f in _FALSE_FLAGS): _fail("MIT_PACKET_ESCALATION_FORBIDDEN")
    return copy.deepcopy(dict(payload))

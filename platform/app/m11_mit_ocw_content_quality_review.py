from __future__ import annotations

from typing import Any
from collections.abc import Mapping

from app._m11_mit_ocw_review_common import timestamp, validate_authority, validate_packet, validate_result_common
from app.m11_mit_ocw_schema_review import RESULT_ID as SCHEMA_RESULT_ID, validate_mit_ocw_schema_result
from app.m11_mit_ocw_technical_evidence_review import RESULT_ID as TECHNICAL_RESULT_ID, validate_mit_ocw_technical_result

AUTHORITY_ID = "m11-mit-ocw-content-quality-review-18-20260929"
RESULT_ID = "m11-p0-mit-ocw-content-quality-review-result-20260929"
SCHEMA = "sa.m11.p0.mit-ocw-content-quality-review-result.v1"

class MitOcwContentQualityReviewError(ValueError):
    pass

def validate_mit_ocw_content_quality_authority(payload: Mapping[str, Any]) -> dict[str, Any]:
    return validate_authority(payload, authority_id=AUTHORITY_ID, error=MitOcwContentQualityReviewError, prefix="MIT_QUALITY")

def validate_mit_ocw_content_quality_result(payload: Mapping[str, Any], *, authority: Mapping[str, Any], schema_result: Mapping[str, Any], schema_authority: Mapping[str, Any], technical_result: Mapping[str, Any], technical_authority: Mapping[str, Any], packet: Mapping[str, Any], materialization: Mapping[str, Any], digest_evidence: Mapping[str, Any], receipt_batch: Mapping[str, Any], gate0_result: Mapping[str, Any]) -> dict[str, Any]:
    validate_packet(packet=packet, materialization=materialization, digest_evidence=digest_evidence, receipt_batch=receipt_batch, gate0_result=gate0_result, error=MitOcwContentQualityReviewError, prefix="MIT_QUALITY")
    try:
        validate_mit_ocw_schema_result(schema_result, authority=schema_authority, packet=packet, materialization=materialization, digest_evidence=digest_evidence, receipt_batch=receipt_batch, gate0_result=gate0_result)
        validate_mit_ocw_technical_result(technical_result, authority=technical_authority, schema_result=schema_result, schema_authority=schema_authority, packet=packet, materialization=materialization, digest_evidence=digest_evidence, receipt_batch=receipt_batch, gate0_result=gate0_result)
    except (TypeError, ValueError) as exc:
        raise MitOcwContentQualityReviewError("MIT_QUALITY_PREDECESSOR_RESULT_INVALID") from exc
    if timestamp(payload.get("signed_at"), MitOcwContentQualityReviewError, "MIT_QUALITY_TIMESTAMP_INVALID") <= timestamp(technical_result.get("signed_at"), MitOcwContentQualityReviewError, "MIT_QUALITY_TIMESTAMP_INVALID"):
        raise MitOcwContentQualityReviewError("MIT_QUALITY_PREDECESSOR_TIMESTAMP_INVALID")
    return validate_result_common(payload, authority=authority, authority_id=AUTHORITY_ID, result_id=RESULT_ID, schema=SCHEMA, predecessor_ids={"owner_decision_packet": packet["packet_id"], "schema_result": SCHEMA_RESULT_ID, "technical_result": TECHNICAL_RESULT_ID}, predecessor_payloads={"owner_decision_packet": packet, "schema_result": schema_result, "technical_result": technical_result}, records=("content_quality",), error=MitOcwContentQualityReviewError, prefix="MIT_QUALITY")

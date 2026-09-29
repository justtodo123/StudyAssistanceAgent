from __future__ import annotations

from typing import Any
from collections.abc import Mapping

from app._m11_mit_ocw_review_common import validate_authority, validate_packet, validate_result_common

AUTHORITY_ID = "m11-mit-ocw-schema-review-18-20260929"
RESULT_ID = "m11-p0-mit-ocw-schema-review-result-20260929"
SCHEMA = "sa.m11.p0.mit-ocw-schema-review-result.v1"

class MitOcwSchemaReviewError(ValueError):
    pass

def validate_mit_ocw_schema_authority(payload: Mapping[str, Any]) -> dict[str, Any]:
    return validate_authority(payload, authority_id=AUTHORITY_ID, error=MitOcwSchemaReviewError, prefix="MIT_SCHEMA")

def validate_mit_ocw_schema_result(payload: Mapping[str, Any], *, authority: Mapping[str, Any], packet: Mapping[str, Any], materialization: Mapping[str, Any], digest_evidence: Mapping[str, Any], receipt_batch: Mapping[str, Any], gate0_result: Mapping[str, Any]) -> dict[str, Any]:
    validate_packet(packet=packet, materialization=materialization, digest_evidence=digest_evidence, receipt_batch=receipt_batch, gate0_result=gate0_result, error=MitOcwSchemaReviewError, prefix="MIT_SCHEMA")
    return validate_result_common(payload, authority=authority, authority_id=AUTHORITY_ID, result_id=RESULT_ID, schema=SCHEMA, predecessor_ids={"owner_decision_packet": packet["packet_id"]}, predecessor_payloads={"owner_decision_packet": packet}, records=("schema",), error=MitOcwSchemaReviewError, prefix="MIT_SCHEMA")

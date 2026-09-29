"""Run and verify the read-only M11 Formal Gate 0 record for the frozen 26-asset scope."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_acquisition import resolve_authorized_assets  # noqa: E402
from app.m11_evidence_closure import validate_closure_bundle  # noqa: E402
from app.m11_execution_authority import load_execution_authority  # noqa: E402
from app.m11_gate0 import EVIDENCE_CATEGORIES, Gate0Error, run_gate0  # noqa: E402
from app.m11_gate0_result import (  # noqa: E402
    FormalGate0ResultError,
    validate_formal_gate0_result,
)
from app.m11_mit_ocw_candidate_materialization import (  # noqa: E402
    MitOcwCandidateMaterializationError,
    validate_mit_ocw_candidate_materialization,
)
from app.m11_review import ReviewError, project_current_review_heads  # noqa: E402
from app.m11_rfc_candidate_materialization import (  # noqa: E402
    RfcCandidateMaterializationError,
    validate_rfc_candidate_materialization,
)
from app.m11_rfc_content_quality_review import validate_rfc_content_quality_result  # noqa: E402
from app.m11_rfc_content_quality_sampling import (  # noqa: E402
    validate_rfc_content_quality_sampling_result,
)
from app.m11_rfc_legal_policy_census import validate_rfc_legal_policy_census  # noqa: E402
from app.m11_rfc_legal_policy_review import validate_rfc_legal_policy_result  # noqa: E402
from app.m11_rfc_schema_review import validate_rfc_schema_review_result  # noqa: E402
from app.m11_rfc_technical_evidence_review import validate_rfc_technical_result  # noqa: E402

MANIFESTS = ROOT / "data/manifests"
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
SIGNED_AT = "2026-09-28T18:00:00Z"
OWNER_ID = "justtodo123"
RESULT_NAME = "m11-p0-formal-gate0-26-result-v1.json"


def _load(name: str) -> dict[str, Any]:
    """Load one tracked JSON manifest without accepting external locations."""
    value = json.loads((MANIFESTS / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("FORMAL_GATE0_MANIFEST_INVALID")
    return value


def _records(name: str) -> list[dict[str, Any]]:
    payload = _load(name)
    records = payload.get("records")
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError("FORMAL_GATE0_RECORDS_INVALID")
    return records


def _validate_rfc_provenance(
    *,
    schema: Mapping[str, Any],
    technical: Mapping[str, Any],
    quality: Mapping[str, Any],
    legal: Mapping[str, Any],
    sampling: Mapping[str, Any],
    census: Mapping[str, Any],
) -> None:
    """Bind accepted RFC decisions to tracked signer, refs, and frozen digests."""
    expected_refs = {
        "schema": {"m11-p0-rfc-candidate-materialization-v1", "m11-p0-rfc-evidence-closure-packet-20260928"},
        "technical": {"m11-p0-rfc-candidate-materialization-v1", "m11-p0-acquisition-26-receipts-v1"},
        "quality": {"m11-p0-rfc-content-quality-sampling-result-20260928"},
        "legal": {"m11-p0-rfc-legal-policy-census-20260928", "rfc-use-policy", "rfc-robots-digest-match"},
    }
    for result in (schema, technical, quality, legal):
        if result.get("signed_by") != OWNER_ID:
            raise ValueError("FORMAL_GATE0_RFC_SIGNER_INVALID")
    for record in schema["records"]:
        if set(record["schema"]["refs"]) != expected_refs["schema"]:
            raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
    for record in technical["records"]:
        for category in ("revision", "provenance", "parser"):
            refs = set(record[category]["refs"])
            if not refs or not refs <= expected_refs["technical"]:
                raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
            if category != "provenance" and refs != {"m11-p0-rfc-candidate-materialization-v1"}:
                raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
            if category == "provenance" and refs != expected_refs["technical"]:
                raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
    for record in quality["records"]:
        if set(record["content_quality"]["refs"]) != expected_refs["quality"]:
            raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
    for record in legal["records"]:
        for category in ("license", "robots_terms", "notice_ipr"):
            refs = set(record[category]["refs"])
            if not refs or not refs <= expected_refs["legal"]:
                raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
            if category == "license" and refs != {"m11-p0-rfc-legal-policy-census-20260928", "rfc-use-policy"}:
                raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
            if category == "robots_terms" and refs != {"m11-p0-rfc-legal-policy-census-20260928", "rfc-robots-digest-match"}:
                raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
            if category == "notice_ipr" and refs != {"m11-p0-rfc-legal-policy-census-20260928"}:
                raise ValueError("FORMAL_GATE0_RFC_REFERENCE_INVALID")
    candidate_assets = {
        item["asset_id"]: item for item in _load("m11-p0-rfc-candidate-materialization-v1.json")["assets"]
    }
    for item in sampling["assets"]:
        candidate = candidate_assets.get(item["asset_id"])
        if candidate is None or item["candidate_artifact_sha256"] != candidate["candidate_artifact_sha256"] or item["normalized_artifact_sha256"] != candidate["normalized_artifact_sha256"] or item["candidate_digest"] != candidate["candidate_digest"] or item["revision"] != candidate["revision"]:
            raise ValueError("FORMAL_GATE0_RFC_DIGEST_LINK_INVALID")
    digest_assets = {
        item["asset_id"]: item for item in _load("m11-p0-digest-evidence-v1.json")["assets"]
    }
    for record in census["records"]:
        digest = digest_assets.get(record["asset_id"])
        if digest is None or record["raw_sha256"] != digest["sha256"]:
            raise ValueError("FORMAL_GATE0_RFC_DIGEST_LINK_INVALID")

def _validated_rfc_results() -> tuple[dict[str, Any], ...]:
    """Validate the exact RFC evidence decision chain before projecting statuses."""
    schema = validate_rfc_schema_review_result(
        _load("m11-p0-rfc-schema-review-result-v1.json"),
        authority=_load("m11-p0-rfc-schema-review-authority-v1.json"),
    )
    technical = validate_rfc_technical_result(
        _load("m11-p0-rfc-technical-evidence-review-result-v1.json"),
        authority=_load("m11-p0-rfc-technical-evidence-review-authority-v1.json"),
        schema_result=schema,
    )
    sampling = validate_rfc_content_quality_sampling_result(
        _load("m11-p0-rfc-content-quality-sampling-result-v1.json")
    )
    quality = validate_rfc_content_quality_result(
        _load("m11-p0-rfc-content-quality-review-result-v1.json"),
        authority=_load("m11-p0-rfc-content-quality-review-authority-v1.json"),
        sampling_result=sampling,
        technical_result=technical,
        schema_result=schema,
    )
    census = validate_rfc_legal_policy_census(
        _load("m11-p0-rfc-legal-policy-census-v1.json")
    )
    legal = validate_rfc_legal_policy_result(
        _load("m11-p0-rfc-legal-policy-review-result-v1.json"),
        authority=_load("m11-p0-rfc-legal-policy-review-authority-v1.json"),
        census=census,
        content_quality_result=quality,
    )
    _validate_rfc_provenance(
        schema=schema,
        technical=technical,
        quality=quality,
        legal=legal,
        sampling=sampling,
        census=census,
    )
    return schema, technical, quality, legal


def _apply_rfc_statuses(
    evidence: dict[tuple[str, str], dict[str, str]], payload: Mapping[str, Any]
) -> None:
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("FORMAL_GATE0_RFC_EVIDENCE_INVALID")
    for record in records:
        if not isinstance(record, Mapping) or not isinstance(record.get("asset_id"), str):
            raise ValueError("FORMAL_GATE0_RFC_EVIDENCE_INVALID")
        key = ("rfc-editor-index", record["asset_id"])
        if key not in evidence:
            raise ValueError("FORMAL_GATE0_RFC_EVIDENCE_INVALID")
        for category in EVIDENCE_CATEGORIES:
            cell = record.get(category)
            if cell is not None:
                if not isinstance(cell, Mapping) or cell.get("status") not in {
                    "VERIFIED", "NOT_APPLICABLE", "PENDING", "FAILED"
                }:
                    raise ValueError("FORMAL_GATE0_RFC_EVIDENCE_INVALID")
                evidence[key][category] = cell["status"]


def _evidence(matrix: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    records = matrix.get("records")
    if not isinstance(records, list):
        raise ValueError("FORMAL_GATE0_CLOSURE_INVALID")
    projected: dict[tuple[str, str], dict[str, str]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("FORMAL_GATE0_CLOSURE_INVALID")
        key = (record.get("source_id"), record.get("asset_id"))
        cells = record.get("evidence")
        if not all(isinstance(part, str) for part in key) or not isinstance(cells, Mapping):
            raise ValueError("FORMAL_GATE0_CLOSURE_INVALID")
        statuses: dict[str, str] = {}
        for category in EVIDENCE_CATEGORIES:
            cell = cells.get(category)
            if not isinstance(cell, Mapping) or cell.get("status") not in {
                "VERIFIED", "NOT_APPLICABLE", "PENDING", "FAILED"
            }:
                raise ValueError("FORMAL_GATE0_CLOSURE_INVALID")
            statuses[category] = cell["status"]
        if key in projected:
            raise ValueError("FORMAL_GATE0_CLOSURE_INVALID")
        projected[key] = statuses
    for payload in _validated_rfc_results():
        _apply_rfc_statuses(projected, payload)
    return projected


def _reviews() -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for name in (
        "m11-p0-human-review-rfc-iana-6-v1.json",
        "m11-p0-human-review-mit-ocw-20-v1.json",
        "m11-p0-human-review-acq-defer-26-v1.json",
        "m11-p0-human-review-closure-defer-26-v1.json",
        "m11-p0-human-review-official-observation-defer-26-v1.json",
        "m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json",
        "m11-p0-human-review-mit-ocw-evidence-defer-20-v1.json",
        "m11-p0-human-review-rfc-exact-three-accept-3-v1.json",
    ):
        history.extend(_records(name))
    return [record.as_dict() for record in project_current_review_heads(history)]


def _candidate_validated(
    required_assets: Sequence[tuple[str, str]],
) -> dict[tuple[str, str], bool]:
    rfc = validate_rfc_candidate_materialization(
        _load("m11-p0-rfc-candidate-materialization-v1.json")
    )
    mit = validate_mit_ocw_candidate_materialization(
        _load("m11-p0-mit-ocw-candidate-materialization-v1.json")
    )
    validated = {key: False for key in required_assets}
    for item in rfc["assets"]:
        validated[(rfc["source_id"], item["asset_id"])] = True
    for item in mit["assets"]:
        validated[(mit["source_id"], item["asset_id"])] = True
    return validated


def _authority_payload(authority: Any) -> dict[str, Any]:
    """Recover the exact safe authority fields from a validated authority object."""
    return {
        "schema": "sa.m11.execution-authority.v1",
        "operation": authority.operation,
        "authority_id": authority.authority_id,
        "issued_by": authority.issued_by,
        "issued_at": authority.issued_at,
        "expires_at": authority.expires_at,
        "scope_digest": authority.scope_digest,
        "source_ids": list(authority.source_ids),
        "asset_ids": {source: list(assets) for source, assets in authority.asset_ids},
        "metadata_only": False,
        "publication_authorized": authority.publication_authorized,
        "status": "AUTHORIZED",
    }


def evaluate() -> dict[str, Any]:
    """Evaluate exact repository metadata and return the only permitted Formal Gate 0 result."""
    gate0_authority = load_execution_authority(
        MANIFESTS / "m11-p0-formal-gate0-26-authority-v1.json",
        operation="gate0", expected_scope_digest=SCOPE_DIGEST,
    )
    acquisition_authority = load_execution_authority(
        MANIFESTS / "m11-p0-acquisition-26-authority-v1.json",
        operation="acquisition", expected_scope_digest=SCOPE_DIGEST,
    )
    digest = _load("m11-p0-digest-evidence-v1.json")
    receipts = _load("m11-p0-acquisition-26-receipts-v1.json")["receipts"]
    matrix = _load("m11-p0-evidence-closure-26-v1.json")
    required_assets = sorted(resolve_authorized_assets(ROOT, acquisition_authority))
    validate_closure_bundle(
        matrix,
        digest_assets=digest["assets"],
        receipts=receipts,
        reviews=_records("m11-p0-human-review-closure-defer-26-v1.json"),
        prior_reviews=_records("m11-p0-human-review-acq-defer-26-v1.json"),
        expected_assets=required_assets,
    )
    result = run_gate0(
        required_assets=required_assets,
        evidence=_evidence(matrix),
        reviews=_reviews(),
        acquisition_receipts=receipts,
        candidate_validated=_candidate_validated(required_assets),
        frozen_assets=resolve_authorized_assets(ROOT, acquisition_authority),
        authority=_authority_payload(gate0_authority),
        acquisition_authority=_authority_payload(acquisition_authority),
        scope_digest=SCOPE_DIGEST,
        lifecycle_counts={
            "approved_chunks": 0,
            "approved_documents": 0,
            "candidate_chunks": 96,
            "candidate_documents": 21,
        },
        owner_id=OWNER_ID,
        signed_at=SIGNED_AT,
    )
    if result["status"] != "BLOCKED":
        raise Gate0Error("FORMAL_GATE0_UNEXPECTED_STATUS")
    if result["candidate_promotion_authorized"] or result["publication_authorized"]:
        raise Gate0Error("FORMAL_GATE0_ESCALATION_FORBIDDEN")
    return result


def _committed_result(runner_result: Mapping[str, Any]) -> dict[str, Any]:
    result = _load(RESULT_NAME)
    return validate_formal_gate0_result(result, expected_runner_result=runner_result)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-json", action="store_true", help="print the validated committed metadata-only result"
    )
    args = parser.parse_args(argv)
    try:
        result = _committed_result(evaluate())
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        Gate0Error,
        ReviewError,
        RfcCandidateMaterializationError,
        MitOcwCandidateMaterializationError,
        FormalGate0ResultError,
    ) as exc:
        print(f"invalid: {exc}")
        return 1
    if args.print_json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(
            "valid: Formal Gate 0 BLOCKED; 26 receipts; "
            "3 current ACCEPT_FOR_PROMOTION_REVIEW heads; no promotion, publication, or formal 3K"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the offline M11 P0 evidence-gap checklist projection."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CHECKLIST_SCHEMA = "sa.m11.p0.evidence-gap-checklist.v1"
EXPECTED_SCOPE = "frozen M11 P0 candidate assets only"
ALLOWED_STATUSES = {"pending", "verified", "blocked"}
EXPECTED_COUNTS = {
    "asset_count": 887,
    "candidate_count": 884,
    "rejected_count": 3,
    "approved_asset_count": 0,
    "approved_document_count": 0,
    "approved_chunk_count": 0,
    "published_count": 0,
}
EXPECTED_GAPS = {
    "license": 887,
    "revision": 887,
    "robots": 887,
    "notice_or_ipr": 864,
    "schema": 3,
    "provenance": 887,
    "content_quality": 887,
}
EXPECTED_SOURCES = {
    "iana-registries": {
        "asset_count": 3,
        "gaps": {"license": 3, "revision": 3, "robots": 3, "schema": 3, "provenance": 3, "content_quality": 3},
    },
    "mit-ocw-6-004-2017": {
        "asset_count": 20,
        "gaps": {"license": 20, "revision": 20, "robots": 20, "provenance": 20, "content_quality": 20},
    },
    "opendsa-main": {
        "asset_count": 861,
        "gaps": {"license": 861, "revision": 861, "robots": 861, "notice_or_ipr": 861, "provenance": 861, "content_quality": 861},
    },
    "rfc-editor-index": {
        "asset_count": 3,
        "gaps": {"license": 3, "revision": 3, "robots": 3, "notice_or_ipr": 3, "provenance": 3, "content_quality": 3},
    },
}
EXPECTED_BLOCKED = {
    "formal-gate0",
    "formal-3k-run",
    "candidate-promotion",
    "publication",
    "source-expansion",
    "network-acquisition",
}
SOURCE_REFERENCES = {
    "candidate_manifest": "data/manifests/sources/m11-p0-candidate-assets-v1.json",
    "review_manifest": "data/manifests/m11-p0-asset-review-v1.json",
    "normalization_report": "data/reports/m11-p0-candidate-normalization-report.json",
}
CONTRACT_FIELDS = {
    "schema", "checklist_kind", "result", "scope", "source_references",
    "formal_gate0_executed", "formal_3k_executed", "candidate_approval_granted",
    "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation",
    "host_paths_included", "bodies_included", "owner_decisions_filled", "counts",
    "gap_categories", "source_gaps", "blocked_actions",
}
FORBIDDEN_KEYS = {
    "body", "content", "text", "raw_content", "normalized_content", "credential",
    "credentials", "password", "token", "learning_state", "private_learning_state",
    "raw_path", "normalized_path", "candidate_path", "rejected_path", "signature",
    "reviewer", "gold_document_id", "sample_content",
}


class EvidenceGapValidationError(ValueError):
    """Raised when the evidence-gap projection is unsafe or inconsistent."""


def _fail(message: str) -> None:
    raise EvidenceGapValidationError(message)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read JSON {path}: {exc}")
    if not isinstance(value, dict):
        _fail(f"JSON root must be an object: {path}")
    return value


def _contract_from_markdown(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _fail(f"cannot read checklist {path}: {exc}")
    matches = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL)
    if len(matches) != 1:
        _fail("checklist must contain exactly one JSON contract")
    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        _fail(f"invalid checklist JSON contract: {exc}")
    if not isinstance(value, dict):
        _fail("checklist contract root must be an object")
    return value


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in _walk_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in _walk_keys(child)}
    return set()


def _validate_contract(contract: dict[str, Any]) -> None:
    if set(contract) != CONTRACT_FIELDS:
        _fail("contract fields differ")
    if contract["schema"] != CHECKLIST_SCHEMA:
        _fail("unsupported evidence-gap schema")
    if contract["checklist_kind"] != "METADATA_ONLY_EVIDENCE_GAPS":
        _fail("checklist must be metadata-only evidence gaps")
    if contract["result"] != "REVIEW_REQUIRED" or contract["scope"] != EXPECTED_SCOPE:
        _fail("checklist result or scope is not frozen")
    if contract["source_references"] != SOURCE_REFERENCES:
        _fail("source references differ from frozen inputs")
    for field in (
        "formal_gate0_executed", "formal_3k_executed", "candidate_approval_granted",
        "publication_authorized", "network_used", "source_expansion", "lifecycle_mutation",
        "host_paths_included", "bodies_included", "owner_decisions_filled",
    ):
        if contract[field] is not False:
            _fail(f"unsafe true value for {field}")
    counts = contract["counts"]
    if not isinstance(counts, dict) or counts != EXPECTED_COUNTS:
        _fail("frozen count drift")
    forbidden = _walk_keys(contract) & FORBIDDEN_KEYS
    if forbidden:
        _fail(f"privacy-bearing fields in checklist: {sorted(forbidden)}")

    categories = contract["gap_categories"]
    if not isinstance(categories, list) or len(categories) != len(EXPECTED_GAPS):
        _fail("evidence-gap categories are incomplete")
    seen: set[str] = set()
    for row in categories:
        if not isinstance(row, dict) or set(row) != {"id", "status", "count"}:
            _fail("each evidence-gap category must contain only id, status, count")
        if row["id"] in seen or row["id"] not in EXPECTED_GAPS:
            _fail(f"unknown or duplicate evidence-gap category: {row.get('id')}")
        if row["status"] not in ALLOWED_STATUSES or row["status"] != "pending":
            _fail(f"unsupported evidence-gap status: {row.get('status')}")
        if row["count"] != EXPECTED_GAPS[row["id"]]:
            _fail(f"evidence-gap count drift: {row['id']}")
        seen.add(row["id"])
    if seen != set(EXPECTED_GAPS):
        _fail("evidence-gap category IDs are incomplete")

    sources = contract["source_gaps"]
    if not isinstance(sources, list) or len(sources) != len(EXPECTED_SOURCES):
        _fail("source gap rows are incomplete")
    seen_sources: set[str] = set()
    for row in sources:
        if not isinstance(row, dict) or set(row) != {"source_id", "asset_count", "gaps", "status"}:
            _fail("each source gap row has unexpected fields")
        source_id = row["source_id"]
        if source_id in seen_sources or source_id not in EXPECTED_SOURCES:
            _fail(f"unknown or duplicate source gap row: {source_id}")
        expected = EXPECTED_SOURCES[source_id]
        if row["asset_count"] != expected["asset_count"] or row["gaps"] != expected["gaps"]:
            _fail(f"source-category gap drift: {source_id}")
        if row["status"] != "pending":
            _fail(f"unsupported source gap status: {source_id}")
        seen_sources.add(source_id)
    if seen_sources != set(EXPECTED_SOURCES):
        _fail("source gap IDs are incomplete")

    actions = contract["blocked_actions"]
    if not isinstance(actions, list) or len(actions) != len(EXPECTED_BLOCKED):
        _fail("blocked action rows are incomplete")
    seen_actions: set[str] = set()
    for row in actions:
        if not isinstance(row, dict) or set(row) != {"id", "status"}:
            _fail("each blocked action row has unexpected fields")
        if row["id"] in seen_actions or row["id"] not in EXPECTED_BLOCKED:
            _fail(f"unknown or duplicate blocked action: {row.get('id')}")
        if row["status"] != "blocked":
            _fail(f"blocked action is not blocked: {row['id']}")
        seen_actions.add(row["id"])
    if seen_actions != EXPECTED_BLOCKED:
        _fail("blocked action IDs are incomplete")


def _record_gap_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for record in records:
        if record.get("license_review_status") == "pending" or record.get("source_id") == "iana-registries":
            counts["license"] += 1
        if record.get("revision_status") in {"pending", "metadata-only", "pinned", "digest-captured"}:
            counts["revision"] += 1
        if record.get("robots_review_status") in {"pending", "not-applicable-git-api-metadata"}:
            counts["robots"] += 1
        if (
            record.get("notice_review_status") == "pending"
            or record.get("ipr_review_status") == "pending"
            or record.get("source_id") == "opendsa-main"
        ):
            counts["notice_or_ipr"] += 1
        if record.get("schema_review_status") == "pending":
            counts["schema"] += 1
        if record.get("provenance_review_status") == "pending":
            counts["provenance"] += 1
        if record.get("content_quality_review_status") == "pending":
            counts["content_quality"] += 1
    return dict(counts)


def _record_source_gaps(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record.get("source_id")].append(record)
    result = {}
    for source_id, source_records in grouped.items():
        counts = _record_gap_counts(source_records)
        result[source_id] = {"asset_count": len(source_records), "gaps": counts}
    return result


def _validate_inputs(
    candidate: dict[str, Any], review: dict[str, Any], report: dict[str, Any]
) -> None:
    if review.get("asset_count") != EXPECTED_COUNTS["asset_count"]:
        _fail("review asset_count is not frozen")
    if review.get("candidate_count") + review.get("rejected_count") != review.get("asset_count"):
        _fail("review candidate/rejected counts do not reconcile")
    for field in ("asset_count", "candidate_count", "rejected_count"):
        if report.get(field) != review.get(field):
            _fail(f"report/review mismatch: {field}")
    for field in ("host_paths_included", "bodies_included"):
        if review.get(field) is not False or report.get(field) is not False:
            _fail(f"privacy boundary is not false: {field}")
    for field in ("approved_count", "published_count", "approved_asset_count", "approved_document_count", "approved_chunk_count"):
        if report.get(field) != 0:
            _fail(f"unsafe report value for {field}")
    if report.get("status") != "CANDIDATE_ONLY" or report.get("publication_authorized") is not False:
        _fail("report is not candidate-only")
    if review.get("review_policy", {}).get("formal_run_authorized") is not False:
        _fail("review formal-run authorization is not false")
    if review.get("review_policy", {}).get("publication_authorized") is not False:
        _fail("review publication authorization is not false")
    records = review.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_COUNTS["asset_count"]:
        _fail("review records are not the frozen inventory")
    statuses = Counter(item.get("normalization_status") for item in records)
    if statuses != Counter({"CANDIDATE": 884, "REJECTED": 3}):
        _fail("record statuses do not reconcile with frozen counts")
    if any(item.get("approved") is not False for item in records):
        _fail("review contains an approved asset")
    if candidate.get("review_policy", {}).get("approved_assets") != []:
        _fail("candidate manifest contains approved assets")
    if candidate.get("review_policy", {}).get("publication_authorized") is not False:
        _fail("candidate publication authorization is not false")
    if _record_gap_counts(records) != EXPECTED_GAPS:
        _fail("record-derived aggregate gaps disagree with frozen gaps")
    if _record_source_gaps(records) != EXPECTED_SOURCES:
        _fail("record-derived source gaps disagree with frozen gaps")
    forbidden = (_walk_keys(candidate) | _walk_keys(review) | _walk_keys(report)) & FORBIDDEN_KEYS
    if forbidden:
        _fail(f"privacy-bearing fields in metadata inputs: {sorted(forbidden)}")


def validate_evidence_gaps(
    checklist_path: Path, candidate_path: Path, review_path: Path, report_path: Path
) -> None:
    """Validate the checklist against frozen local metadata only."""
    contract = _contract_from_markdown(checklist_path)
    _validate_contract(contract)
    _validate_inputs(_load_json(candidate_path), _load_json(review_path), _load_json(report_path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--checklist", type=Path, default=root / "docs/plans/references/m11-p0-evidence-gap-checklist-v1.md")
    parser.add_argument("--candidate", type=Path, default=root / "data/manifests/sources/m11-p0-candidate-assets-v1.json")
    parser.add_argument("--review", type=Path, default=root / "data/manifests/m11-p0-asset-review-v1.json")
    parser.add_argument("--report", type=Path, default=root / "data/reports/m11-p0-candidate-normalization-report.json")
    args = parser.parse_args(argv)
    try:
        validate_evidence_gaps(args.checklist, args.candidate, args.review, args.report)
    except EvidenceGapValidationError as exc:
        parser.error(str(exc))
    print("M11 P0 evidence-gap checklist: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

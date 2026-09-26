"""Validate the offline M11 P0 metadata-only Gate 0 checklist."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CHECKLIST_SCHEMA = "sa.m11.p0.metadata-only-gate0-checklist.v1"
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
EXPECTED_STATUS_IDS = {
    "stage-authority",
    "candidate-scope",
    "inventory-counts",
    "report-reconciliation",
    "rejected-mapping",
    "digest-evidence",
    "privacy-boundary",
    "candidate-only",
    "deterministic-review",
    "asset-license-review",
    "robots-review",
    "rfc-notice-ipr-review",
    "iana-schema-review",
    "human-gate-review",
    "formal-3k-run",
    "candidate-promotion",
    "publication",
    "source-expansion",
    "network-acquisition",
}
EXPECTED_STATUS_VALUES = {
    "stage-authority": "verified",
    "candidate-scope": "verified",
    "inventory-counts": "verified",
    "report-reconciliation": "verified",
    "rejected-mapping": "verified",
    "digest-evidence": "verified",
    "privacy-boundary": "verified",
    "candidate-only": "verified",
    "deterministic-review": "verified",
    "asset-license-review": "pending",
    "robots-review": "pending",
    "rfc-notice-ipr-review": "pending",
    "iana-schema-review": "pending",
    "human-gate-review": "pending",
    "formal-3k-run": "blocked",
    "candidate-promotion": "blocked",
    "publication": "blocked",
    "source-expansion": "blocked",
    "network-acquisition": "blocked",
}
CONTRACT_FIELDS = {
    "schema",
    "checklist_kind",
    "result",
    "scope",
    "formal_gate0_executed",
    "formal_3k_executed",
    "candidate_approval_granted",
    "publication_authorized",
    "network_used",
    "source_expansion",
    "lifecycle_mutation",
    "host_paths_included",
    "bodies_included",
    "counts",
    "statuses",
}
FORBIDDEN_KEYS = {
    "body",
    "content",
    "text",
    "raw_content",
    "normalized_content",
    "credential",
    "credentials",
    "password",
    "token",
    "learning_state",
    "private_learning_state",
    "raw_path",
    "normalized_path",
    "candidate_path",
    "rejected_path",
}


class ChecklistValidationError(ValueError):
    """Raised when the checklist or its frozen metadata inputs are unsafe."""


def _fail(message: str) -> None:
    raise ChecklistValidationError(message)


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
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def _validate_contract(contract: dict[str, Any]) -> None:
    if set(contract) != CONTRACT_FIELDS:
        missing = sorted(CONTRACT_FIELDS - set(contract))
        unknown = sorted(set(contract) - CONTRACT_FIELDS)
        _fail(f"contract fields differ; missing={missing}, unknown={unknown}")
    if contract["schema"] != CHECKLIST_SCHEMA:
        _fail("unsupported checklist schema")
    if contract["checklist_kind"] != "METADATA_ONLY":
        _fail("checklist must be metadata-only")
    if contract["result"] != "REVIEW_REQUIRED" or contract["scope"] != EXPECTED_SCOPE:
        _fail("checklist result or scope is not frozen")
    for field in (
        "formal_gate0_executed",
        "formal_3k_executed",
        "candidate_approval_granted",
        "publication_authorized",
        "network_used",
        "source_expansion",
        "lifecycle_mutation",
        "host_paths_included",
        "bodies_included",
    ):
        if contract[field] is not False:
            _fail(f"unsafe true value for {field}")
    counts = contract["counts"]
    if not isinstance(counts, dict) or set(counts) != set(EXPECTED_COUNTS):
        _fail("count fields differ from the frozen contract")
    if counts != EXPECTED_COUNTS:
        _fail(f"frozen count drift: {counts}")
    statuses = contract["statuses"]
    if not isinstance(statuses, list) or len(statuses) != len(EXPECTED_STATUS_IDS):
        _fail("checklist status rows are incomplete")
    seen: set[str] = set()
    for row in statuses:
        if not isinstance(row, dict) or set(row) != {"id", "status"}:
            _fail("each checklist status row must contain only id and status")
        row_id = row["id"]
        status = row["status"]
        if row_id in seen or row_id not in EXPECTED_STATUS_IDS:
            _fail(f"unknown or duplicate checklist row: {row_id}")
        if status not in ALLOWED_STATUSES:
            _fail(f"unsupported checklist status: {status}")
        if EXPECTED_STATUS_VALUES[row_id] != status:
            _fail(f"unexpected status for checklist row: {row_id}")
        seen.add(row_id)
    if seen != EXPECTED_STATUS_IDS:
        _fail("checklist status IDs are incomplete")
    forbidden = _walk_keys(contract) & FORBIDDEN_KEYS
    if forbidden:
        _fail(f"privacy-bearing fields in checklist: {sorted(forbidden)}")


def _validate_inputs(review: dict[str, Any], report: dict[str, Any]) -> None:
    for field, expected in EXPECTED_COUNTS.items():
        if field in review and field not in {"published_count"} and review[field] != expected:
            _fail(f"review count drift: {field}")
    if review.get("asset_count") != EXPECTED_COUNTS["asset_count"]:
        _fail("review asset_count is not frozen")
    if review.get("candidate_count") + review.get("rejected_count") != review.get("asset_count"):
        _fail("review candidate/rejected counts do not reconcile")
    for field in ("asset_count", "candidate_count", "rejected_count"):
        if report.get(field) != review.get(field):
            _fail(f"report/review mismatch: {field}")
    if report.get("rejection_reasons") != review.get("rejection_reasons"):
        _fail("report/review mismatch: rejection_reasons")
    for field in ("host_paths_included", "bodies_included"):
        if review.get(field) is not False or report.get(field) is not False:
            _fail(f"privacy boundary is not false: {field}")
    required_zeroes = {
        "approved_count": 0,
        "published_count": 0,
        "approved_asset_count": 0,
        "approved_document_count": 0,
        "approved_chunk_count": 0,
    }
    for field, expected in required_zeroes.items():
        if report.get(field) != expected:
            _fail(f"unsafe report value for {field}")
    if report.get("status") != "CANDIDATE_ONLY":
        _fail("report is not candidate-only")
    if report.get("publication_authorized") is not False:
        _fail("report publication authorization is not false")
    if review.get("review_policy", {}).get("formal_run_authorized") is not False:
        _fail("review formal-run authorization is not false")
    if review.get("review_policy", {}).get("publication_authorized") is not False:
        _fail("review publication authorization is not false")
    forbidden = (_walk_keys(review) | _walk_keys(report)) & FORBIDDEN_KEYS
    if forbidden:
        _fail(f"privacy-bearing fields in metadata inputs: {sorted(forbidden)}")
    records = review.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_COUNTS["asset_count"]:
        _fail("review records are not the frozen inventory")
    candidate_count = sum(item.get("normalization_status") == "CANDIDATE" for item in records)
    rejected_count = sum(item.get("normalization_status") == "REJECTED" for item in records)
    if (candidate_count, rejected_count) != (884, 3):
        _fail("record statuses do not reconcile with frozen counts")
    if any(item.get("approved") is not False for item in records):
        _fail("review contains an approved asset")


def validate_checklist(checklist_path: Path, review_path: Path, report_path: Path) -> None:
    """Validate the checklist and its local frozen metadata inputs."""
    contract = _contract_from_markdown(checklist_path)
    _validate_contract(contract)
    _validate_inputs(_load_json(review_path), _load_json(report_path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--checklist", type=Path, default=root / "docs/plans/references/m11-p0-metadata-only-gate0-checklist-v1.md")
    parser.add_argument("--review", type=Path, default=root / "data/manifests/m11-p0-asset-review-v1.json")
    parser.add_argument("--report", type=Path, default=root / "data/reports/m11-p0-candidate-normalization-report.json")
    args = parser.parse_args(argv)
    try:
        validate_checklist(args.checklist, args.review, args.report)
    except ChecklistValidationError as exc:
        parser.error(str(exc))
    print("M11 P0 metadata-only checklist: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

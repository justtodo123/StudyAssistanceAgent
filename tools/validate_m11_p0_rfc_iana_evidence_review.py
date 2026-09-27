"""Offline validator for the M11 RFC/IANA exact-six evidence-review batch."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_iana_evidence_review import (  # noqa: E402
    RfcIanaEvidenceReviewError,
    validate_rfc_iana_evidence_review_bundle,
)

MANIFESTS = ROOT / "data/manifests"
DIGEST = MANIFESTS / "m11-p0-digest-evidence-v1.json"
RECEIPTS = MANIFESTS / "m11-p0-acquisition-26-receipts-v1.json"
CLOSURE = MANIFESTS / "m11-p0-evidence-closure-26-v1.json"
ACQUISITION_REVIEWS = MANIFESTS / "m11-p0-human-review-acq-defer-26-v1.json"
CLOSURE_WRAPPER = MANIFESTS / "m11-p0-human-review-closure-defer-26-v1.json"
OFFICIAL = MANIFESTS / "m11-p0-official-source-observations-26-v1.json"
OFFICIAL_AUTHORITY = MANIFESTS / "m11-p0-human-review-26-authority-v1.json"
OFFICIAL_REVIEWS = MANIFESTS / "m11-p0-human-review-official-observation-defer-26-v1.json"
APPLICATION = MANIFESTS / "m11-p0-rfc-iana-evidence-review-application-v1.json"
AUTHORITY = MANIFESTS / "m11-p0-rfc-iana-evidence-review-authority-v1.json"
RESULT = MANIFESTS / "m11-p0-rfc-iana-evidence-review-result-v1.json"
SUCCESSOR = MANIFESTS / "m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    try:
        digest = _load(DIGEST)
        receipts = _load(RECEIPTS)
        closure = _load(CLOSURE)
        acquisition_wrapper = _load(ACQUISITION_REVIEWS)
        closure_wrapper = _load(CLOSURE_WRAPPER)
        official = _load(OFFICIAL)
        official_authority = _load(OFFICIAL_AUTHORITY)
        official_reviews = _load(OFFICIAL_REVIEWS)
        application = _load(APPLICATION)
        authority = _load(AUTHORITY)
        result = _load(RESULT)
        successor = _load(SUCCESSOR)
        validated = validate_rfc_iana_evidence_review_bundle(
            application,
            authority=authority,
            result=result,
            digest_assets=digest["assets"],
            digest_robots=digest["robots"],
            receipts=receipts["receipts"],
            closure_matrix=closure,
            acquisition_review_wrapper=acquisition_wrapper,
            closure_review_wrapper=closure_wrapper,
            official_observation=official,
            official_authority=official_authority,
            official_review_wrapper=official_reviews,
            successor_wrapper=successor,
        )
        print(
            f"valid: {validated['asset_count']} exact-six assets; "
            "48 evidence statuses remain PENDING; Gate 0 remains BLOCKED"
        )
        return 0
    except (OSError, KeyError, TypeError, json.JSONDecodeError, RfcIanaEvidenceReviewError) as exc:
        print(f"invalid: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

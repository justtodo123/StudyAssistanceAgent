"""Offline validator for the M11 P0 26-asset evidence-closure projection."""

from __future__ import annotations

import json
from pathlib import Path

from app.m11_evidence_closure import EvidenceClosureError, validate_closure_bundle

ROOT = Path(__file__).resolve().parents[1]
DIGEST = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
MATRIX = ROOT / "data/manifests/m11-p0-evidence-closure-26-v1.json"
RECEIPTS = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"
PRIOR = ROOT / "data/manifests/m11-p0-human-review-acq-defer-26-v1.json"
CLOSURE = ROOT / "data/manifests/m11-p0-human-review-closure-defer-26-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    try:
        digest = _load(DIGEST)
        matrix = _load(MATRIX)
        receipts = _load(RECEIPTS)
        prior = _load(PRIOR)
        closure = _load(CLOSURE)
        expected = [(item["source_id"], item["asset_id"]) for item in digest["assets"]]
        result = validate_closure_bundle(
            matrix,
            digest_assets=digest["assets"],
            receipts=receipts["receipts"],
            reviews=closure["records"],
            prior_reviews=prior["records"],
            expected_assets=expected,
        )
        print(
            f"valid: {result['asset_count']} assets, "
            "eight-category closure projection remains REVIEW_REQUIRED; no Gate 0 executed"
        )
        return 0
    except (OSError, KeyError, TypeError, json.JSONDecodeError, EvidenceClosureError) as exc:
        print(f"invalid: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

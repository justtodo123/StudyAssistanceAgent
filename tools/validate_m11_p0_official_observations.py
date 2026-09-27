"""Offline validator for the M11 P0 official-source observation layer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_official_observation import (  # noqa: E402
    OfficialObservationError,
    validate_official_observation_bundle,
)
DIGEST = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
RECEIPTS = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"
CLOSURE = ROOT / "data/manifests/m11-p0-evidence-closure-26-v1.json"
PRIOR = ROOT / "data/manifests/m11-p0-human-review-closure-defer-26-v1.json"
OBSERVATION = ROOT / "data/manifests/m11-p0-official-source-observations-26-v1.json"
SUCCESSOR = ROOT / "data/manifests/m11-p0-human-review-official-observation-defer-26-v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    try:
        digest = _load(DIGEST)
        receipts = _load(RECEIPTS)
        closure = _load(CLOSURE)
        prior = _load(PRIOR)
        observation = _load(OBSERVATION)
        successor = _load(SUCCESSOR)
        authority = _load(ROOT / observation["authority_record"])
        prior_wrapper = _load(ROOT / observation["prior_review_record"])
        expected = [(item["source_id"], item["asset_id"]) for item in digest["assets"]]
        result = validate_official_observation_bundle(
            observation,
            digest_assets=digest["assets"],
            receipts=receipts["receipts"],
            closure_matrix=closure,
            closure_reviews=prior["records"],
            successor_reviews=successor["records"],
            expected_assets=expected,
            authority=authority,
            successor_wrapper=successor,
            prior_review_wrapper=prior_wrapper,
            robots=digest["robots"],
        )
        print(
            f"valid: {result['asset_count']} assets, official observations recorded; "
            "closure remains REVIEW_REQUIRED; no Gate 0 executed"
        )
        return 0
    except (OSError, KeyError, TypeError, json.JSONDecodeError, OfficialObservationError) as exc:
        print(f"invalid: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

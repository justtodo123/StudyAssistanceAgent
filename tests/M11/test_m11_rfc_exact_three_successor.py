from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.m11

from app.m11_rfc_exact_three_successor import (
    RfcExactThreeSuccessorError,
    validate_rfc_exact_three_successor,
)

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "data/manifests"


def load(name: str) -> dict:
    return json.loads((M / name).read_text(encoding="utf-8"))


def args() -> dict:
    return {
        "authority": load("m11-p0-rfc-exact-three-accept-authority-v1.json"),
        "result": load("m11-p0-rfc-exact-three-accept-result-v1.json"),
        "legal_result": load("m11-p0-rfc-legal-policy-review-result-v1.json"),
        "successor_wrapper": load("m11-p0-human-review-rfc-exact-three-accept-3-v1.json"),
        "official_reviews": load("m11-p0-human-review-official-observation-defer-26-v1.json")["records"],
        "exact_six_reviews": load("m11-p0-human-review-rfc-iana-evidence-defer-6-v1.json")["records"],
        "mit_reviews": load("m11-p0-human-review-mit-ocw-evidence-defer-20-v1.json")["records"],
    }


def test_exact_three_successor_is_valid_and_non_escalating():
    validated = validate_rfc_exact_three_successor(**args())
    assert validated["decision"] == "ACCEPT_FOR_PROMOTION_REVIEW"
    assert validated["successor_slice_written"] is True
    assert validated["formal_gate0_executed"] is False
    assert validated["candidate_approval_granted"] is False
    assert validated["publication_authorized"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        lambda a: a["successor_wrapper"].__setitem__("publication_authorized", True),
        lambda a: a["successor_wrapper"]["records"][0].__setitem__("decision", "DEFER"),
        lambda a: a["successor_wrapper"]["records"][0].__setitem__("supersedes", "m11-hr-20260926-official-observation-rfc1034"),
        lambda a: a["successor_wrapper"]["records"][0].__setitem__("document_id", "f" * 32),
        lambda a: a["successor_wrapper"]["records"][0]["chunk_ids"].__setitem__(0, "f" * 32),
        lambda a: a["successor_wrapper"]["records"][0].__setitem__("attestation_digest", "f" * 64),
        lambda a: a["authority"].__setitem__("operation", "gate0"),
        lambda a: a["legal_result"].__setitem__("pending_cell_count", 1),
    ),
)
def test_successor_mutations_fail_closed(mutation):
    payload = copy.deepcopy(args())
    mutation(payload)
    with pytest.raises(RfcExactThreeSuccessorError):
        validate_rfc_exact_three_successor(**payload)


def test_validation_returns_detached_copy():
    payload = args()
    validated = validate_rfc_exact_three_successor(**payload)
    validated["decision"] = "changed"
    assert payload["result"]["decision"] == "ACCEPT_FOR_PROMOTION_REVIEW"

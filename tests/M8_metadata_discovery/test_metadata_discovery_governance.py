"""Stage-isolated tests for offline M8 metadata-discovery governance."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tools import m8_build_metadata_discovery_cycle as builder
from tools import m8_metadata_discovery_schema as schema
from tools import m8_validate_metadata_discovery_review as reviewer


pytestmark = pytest.mark.m8_metadata_discovery


def _current_commit(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _candidate(repo_root: Path) -> dict:
    return builder.build_candidate(_current_commit(repo_root), repo_root)


def _canonical(candidate: dict) -> bytes:
    return schema.canonical_bytes(candidate)


def test_builder_cli_requires_full_commit_oid(repo_root: Path, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        builder.main([
            "--commit",
            "HEAD",
            "--repo",
            str(repo_root),
            "--output",
            str(tmp_path / "candidate.json"),
        ])



def test_builder_api_requires_full_commit_oid(repo_root: Path) -> None:
    with pytest.raises(ValueError, match="full lowercase 40-character Git OID"):
        builder.build_candidate("HEAD", repo_root)


def test_builder_is_unresolved_and_failed_closed(repo_root: Path) -> None:
    candidate = _candidate(repo_root)

    assert candidate["status"] == "METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED"
    assert candidate["allowed_next_action"] == candidate["status"]
    assert candidate["intent"] == {
        "artifact": None,
        "metadata_url": None,
        "package_name": None,
        "selection_state": "UNRESOLVED",
        "version": None,
    }
    assert candidate["authorization"] == {
        "authorization_token_present": False,
        "metadata_discovery_authorized": False,
        "token": None,
    }
    assert all(value == 0 for value in candidate["current_effective_limits"].values())
    assert all(value == 0 for value in candidate["execution_counts"].values())
    assert candidate["qa"] == {
        "adversarial": "PASS",
        "builder_internal": "PASS",
        "max_rounds": 3,
        "round": 1,
    }


def test_builder_reads_only_fixed_committed_evidence(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    paths = [item["path"] for item in candidate["evidence"]]

    assert paths == list(builder.EVIDENCE_PATHS)
    assert all(".." not in path.split("/") for path in paths)
    assert all("\\" not in path for path in paths)
    assert all(item["byte_count"] == len(
        subprocess.run(
            ["git", "cat-file", "blob", item["git_blob_oid"]],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
    ) for item in candidate["evidence"])


def test_reviewer_recomputes_git_binding_and_preserves_status(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    report = reviewer.validate_review_package(_canonical(candidate), repo_root)

    assert report["decision"] == "METADATA_DISCOVERY_CANDIDATE_READY_FOR_EXTERNAL_INDEPENDENT_REVIEW"
    assert report["status"] == candidate["status"]
    assert report["execution_counts"] == candidate["execution_counts"]
    assert report["candidate_sha256"] == hashlib.sha256(_canonical(candidate)).hexdigest()


def test_reviewer_rejects_tampered_evidence_digest(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["evidence"][0]["sha256"] = "0" * 64

    with pytest.raises(schema.MetadataGovernanceError, match="evidence digest mismatch"):
        reviewer.validate_review_package(_canonical(candidate), repo_root)


def test_schema_rejects_duplicate_keys() -> None:
    data = b'{"a":1,"a":2}'

    with pytest.raises(schema.MetadataGovernanceError, match="duplicate"):
        schema.strict_loads(data)


def test_schema_rejects_non_finite_numbers() -> None:
    with pytest.raises(schema.MetadataGovernanceError, match="non-finite"):
        schema.strict_loads(b'{"value":NaN}')


def test_schema_rejects_surrogates() -> None:
    with pytest.raises(schema.MetadataGovernanceError, match="surrogate"):
        schema.strict_loads(b'{"value":"\\ud800"}')


def test_schema_rejects_non_canonical_bytes(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    noncanonical = json.dumps(candidate, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"

    with pytest.raises(schema.MetadataGovernanceError, match="canonical"):
        schema.parse_canonical_document(noncanonical)


def test_schema_rejects_unknown_candidate_field(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["unexpected"] = True

    with pytest.raises(schema.MetadataGovernanceError, match="keys are not exact"):
        schema.validate_candidate(candidate)


def test_schema_rejects_nonzero_current_limit(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["current_effective_limits"]["metadata_requests"] = 1

    with pytest.raises(schema.MetadataGovernanceError, match="effective limits"):
        schema.validate_candidate(candidate)


def test_schema_rejects_nonzero_proposed_limit(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["proposed_discovery_limits"]["metadata_requests"] = 1

    with pytest.raises(schema.MetadataGovernanceError, match="proposed discovery limits"):
        schema.validate_candidate(candidate)


def test_schema_rejects_alternate_next_action(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["allowed_next_action"] = "RUN_METADATA_DISCOVERY"

    with pytest.raises(schema.MetadataGovernanceError, match="Owner selection"):
        schema.validate_candidate(candidate)


def test_schema_rejects_failed_builder_qa(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["qa"]["adversarial"] = "FAIL"

    with pytest.raises(schema.MetadataGovernanceError, match="QA must pass"):
        schema.validate_candidate(candidate)


def test_schema_rejects_qa_round_above_bound(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["qa"]["round"] = 4

    with pytest.raises(schema.MetadataGovernanceError, match="round bound"):
        schema.validate_candidate(candidate)


def test_schema_requires_exact_forbidden_actions(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["forbidden_actions"].remove("network")

    with pytest.raises(schema.MetadataGovernanceError, match="not exact"):
        schema.validate_candidate(candidate)


def test_schema_rejects_execution_count(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["execution_counts"]["metadata"] = 1

    with pytest.raises(schema.MetadataGovernanceError, match="execution counts"):
        schema.validate_candidate(candidate)


@pytest.mark.parametrize(
    "token",
    [
        "metadata_discovery_authorization_approved",
        " METADATA_DISCOVERY_AUTHORIZATION_APPROVED",
        "METADATA_DISCOVERY_AUTHORIZATION_APPROVED ",
        "XMETADATA_DISCOVERY_AUTHORIZATION_APPROVED",
        "METADATA_DISCOVERY_AUTHORIZATION_APPROVEDX",
        None,
        True,
    ],
)
def test_authorization_requires_exact_token(token: object) -> None:
    assert not schema.validate_authorization_token(token)


def test_exact_authorization_token_is_only_a_predicate() -> None:
    assert schema.validate_authorization_token(schema.AUTHORIZATION_TOKEN)
    assert schema.AUTHORIZATION_TOKEN == "METADATA_DISCOVERY_AUTHORIZATION_APPROVED"


def test_schema_rejects_values_on_unresolved_intent(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["intent"].update({
        "artifact": "guessed-package-9.9.9.whl",
        "metadata_url": "https://example.invalid/guessed-package",
        "package_name": "guessed-package",
        "version": "9.9.9",
    })

    with pytest.raises(
        schema.MetadataGovernanceError,
        match="unresolved intent must not contain",
    ):
        reviewer.validate_review_package(_canonical(candidate), repo_root)


def test_reviewer_rejects_selected_intent(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["intent"]["selection_state"] = "OWNER_SELECTED"
    candidate["intent"]["package_name"] = "guessed-package"

    with pytest.raises(schema.MetadataGovernanceError, match="candidate|selection|select"):
        reviewer.validate_review_package(_canonical(candidate), repo_root)


def test_git_binding_is_full_and_non_self_referential(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    binding = candidate["git_binding"]

    assert len(binding["commit"]) == 40
    assert len(binding["parent"]) == 40
    assert len(binding["tree"]) == 40
    assert binding["commit"] != binding["parent"]
    assert candidate["source_commit"] == binding["commit"]

"""Stage-isolated tests for the selected pypdf M8 scope governance cycle."""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
from pathlib import Path

import pytest

from tools import m8_build_metadata_discovery_scope_candidate as builder
from tools import m8_git_object_reader as git_reader
from tools import m8_metadata_discovery_schema as schema
from tools import m8_validate_metadata_discovery_scope_review as scope_reviewer


pytestmark = pytest.mark.m8_metadata_discovery


def _commit(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _candidate(repo_root: Path) -> dict:
    return builder.build_scope_candidate(_commit(repo_root), repo_root)


def _candidate_bytes(repo_root: Path) -> bytes:
    return schema.canonical_bytes(_candidate(repo_root))


def _run_git(repo_root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        input=input_bytes,
    ).stdout


def _commit_file(repo_root: Path, path: str, data: bytes, message: str) -> str:
    target = repo_root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    _run_git(repo_root, "add", "--", path)
    _run_git(
        repo_root,
        "-c", "user.name=Scope Governance Tests",
        "-c", "user.email=scope-governance-tests@example.invalid",
        "commit", "-m", message,
    )
    return _run_git(repo_root, "rev-parse", "HEAD").decode("ascii").strip()


def _publication_binding(repo_root: Path, commit: str, path: str) -> dict[str, object]:
    identity = scope_reviewer._commit_binding(commit, repo_root)
    oid, data = scope_reviewer._read_blob(commit, path, repo_root)
    return {
        **identity,
        "path": path,
        "git_blob_oid": oid,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _stage_governance() -> dict[str, object]:
    return {
        "authorization": {
            "installation_authorized": False,
            "metadata_discovery_authorized": False,
            "network_access_authorized": False,
            "resolver_execution_authorized": False,
            "token": None,
            "wheel_download_authorized": False,
        },
        "current_effective_limits": {key: 0 for key in schema.SCOPE_LIMIT_KEYS},
        "execution_counts": {key: 0 for key in schema.SCOPE_EXECUTION_KEYS},
        "m8_status": "BLOCKED / NOT_STARTED",
    }


def _stage_ref(record: dict[str, object]) -> dict[str, object]:
    publication = record["publication"]
    assert isinstance(publication, dict)
    return {
        "stage": record["stage"],
        "record_id": record["record_id"],
        **publication,
    }


def _stage_payload(
    stage: str,
    records: list[dict[str, object]],
    candidate: dict[str, object],
) -> dict[str, object]:
    by_stage = {record["stage"]: record for record in records}
    common = {
        "canonicalization_id": schema.CANONICALIZATION_ID,
        "cycle_id": schema.SCOPE_CYCLE_ID,
        "governance": _stage_governance(),
        "stage": stage,
    }
    candidate_binding = _stage_ref(by_stage["candidate_publication"])
    if stage == "builder_self_check":
        return {
            **common,
            "candidate_binding": candidate_binding,
            "checks": {
                key: True for key in schema.SCOPE_REVIEW_REQUIRED_CHECKS[:-2]
            },
            "commit_policy": schema.SCOPE_SINGLE_PARENT_POLICY,
            "decision": schema.SCOPE_SELF_CHECK_DECISION,
            "format": schema.SCOPE_SELF_CHECK_FORMAT,
            "independent_review_completed": False,
        }
    if stage == "review_request":
        return {
            **common,
            "candidate_binding": candidate_binding,
            "format": schema.SCOPE_REVIEW_REQUEST_FORMAT,
            "protocol_binding": {
                "protocol_id": schema.SCOPE_REVIEW_PROTOCOL_ID,
                "sha256": schema.SCOPE_REVIEW_PROTOCOL_SHA256,
            },
            "request_id": "m8-scope-review-request-20260920-r02",
            "requested_reviewer_role": schema.SCOPE_REVIEW_ROLE,
            "review_completed": False,
            "self_check_binding": _stage_ref(by_stage["builder_self_check"]),
            "status": schema.SCOPE_REVIEW_REQUIRED,
        }
    if stage == "review_prompt":
        return {
            **common,
            "candidate_binding": candidate_binding,
            "format": schema.SCOPE_REVIEW_PROMPT_FORMAT,
            "protocol": schema.SCOPE_REVIEW_PROTOCOL,
            "protocol_sha256": schema.SCOPE_REVIEW_PROTOCOL_SHA256,
            "request_binding": _stage_ref(by_stage["review_request"]),
            "review_not_completed": True,
        }
    if stage == "review_target":
        return {
            **common,
            "candidate_binding": candidate_binding,
            "format": schema.SCOPE_REVIEW_TARGET_FORMAT,
            "prompt_binding": _stage_ref(by_stage["review_prompt"]),
            "protocol_binding": {
                "protocol_id": schema.SCOPE_REVIEW_PROTOCOL_ID,
                "sha256": schema.SCOPE_REVIEW_PROTOCOL_SHA256,
            },
            "request_binding": _stage_ref(by_stage["review_request"]),
            "self_check_binding": _stage_ref(by_stage["builder_self_check"]),
            "status": schema.SCOPE_REVIEW_REQUIRED,
            "target_id": "m8-scope-review-target-20260920-r02",
        }
    assert stage == "dispatch_manifest"
    return {
        **common,
        "candidate_binding": candidate_binding,
        "dispatch_id": "m8-scope-dispatch-20260920-r02",
        "format": schema.SCOPE_DISPATCH_FORMAT,
        "prompt_binding": _stage_ref(by_stage["review_prompt"]),
        "protocol_binding": {
            "protocol_id": schema.SCOPE_REVIEW_PROTOCOL_ID,
            "sha256": schema.SCOPE_REVIEW_PROTOCOL_SHA256,
        },
        "request_binding": _stage_ref(by_stage["review_request"]),
        "selected_target_count": 1,
        "self_check_binding": _stage_ref(by_stage["builder_self_check"]),
        "status": schema.SCOPE_READY_FOR_EXTERNAL_REVIEW,
        "target_binding": _stage_ref(by_stage["review_target"]),
    }


def _init_linear_chain_repo(
    tmp_path: Path,
    stage_payload_overrides: dict[str, bytes | dict[str, object]] | None = None,
) -> tuple[Path, list[dict[str, object]]]:
    repo = tmp_path / "chain-repo"
    repo.mkdir()
    _run_git(repo, "init", "-b", "master")
    _commit_file(repo, "bootstrap.txt", b"bootstrap\n", "bootstrap")

    records: list[dict[str, object]] = []
    candidate = _candidate(Path(__file__).resolve().parents[2])
    overrides = stage_payload_overrides or {}
    for stage in schema.SCOPE_CHAIN_STAGES:
        path = schema.SCOPE_CHAIN_PATHS[stage]
        if stage in overrides:
            payload = overrides[stage]
            payload_bytes = (
                payload
                if type(payload) is bytes
                else schema.canonical_bytes(payload)
            )
        elif stage == "candidate_publication":
            payload = candidate
            payload_bytes = schema.canonical_bytes(payload)
        else:
            payload = _stage_payload(stage, records, candidate)
            payload_bytes = schema.canonical_bytes(payload)
        commit = _commit_file(repo, path, payload_bytes, stage)
        predecessors = [
            _stage_ref(next(record for record in records if record["stage"] == predecessor))
            for predecessor in schema.SCOPE_CHAIN_PREDECESSORS[stage]
        ]
        records.append({
            "canonicalization_id": schema.CANONICALIZATION_ID,
            "format": schema.SCOPE_CHAIN_FORMAT,
            "non_authorizing": True,
            "predecessors": predecessors,
            "publication": _publication_binding(repo, commit, path),
            "record_id": f"record-{stage}",
            "stage": stage,
        })
    return repo, records


def test_scope_candidate_freezes_only_owner_selected_pypdf_scope(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    assert candidate["scope"] == {
        "artifact": None,
        "artifact_selection_state": "NOT_SELECTED",
        "consumer_format": "pdf",
        "dependency_scope": ["pypdf"],
        "distribution_name": "pypdf",
        "endpoint_selection_state": "NOT_SELECTED",
        "exact_requirement": "pypdf==6.0.0",
        "exact_version": "6.0.0",
        "import_name": "pypdf",
        "metadata_request_authorized": False,
        "metadata_url": None,
        "parser_id": "pypdf",
        "parser_version": "6.0.0",
        "project_url": None,
        "purpose": "M7_PDF_PARSER_RUNTIME_DEPENDENCY_METADATA_DISCOVERY_ONLY",
        "scope_origin": "USER_REQUIREMENT",
        "scope_state": "OWNER_SUPPLIED_EXACT_SCOPE",
    }
    assert candidate["status"] == schema.SCOPE_REVIEW_REQUIRED
    assert candidate["m8_status"] == "BLOCKED / NOT_STARTED"
    assert candidate["qa"]["independent_review_completed"] is False


def test_scope_candidate_does_not_expand_dependencies(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    assert candidate["scope"]["dependency_scope"] == ["pypdf"]
    assert candidate["scope"]["artifact"] is None
    assert candidate["scope"]["metadata_url"] is None
    assert candidate["scope"]["project_url"] is None
    requirements = subprocess.run(
        ["git", "show", f"{_commit(repo_root)}:platform/requirements.txt"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    other_requirements = {
        line.split("==", 1)[0]
        for line in requirements.splitlines()
        if line and not line.startswith("#") and line != "pypdf==6.0.0"
    }
    assert other_requirements
    assert other_requirements.isdisjoint(candidate["scope"]["dependency_scope"])


def test_scope_candidate_policy_is_finite_but_not_effective(repo_root: Path) -> None:
    policy = _candidate(repo_root)["proposed_metadata_policy"]
    assert policy["policy_state"] == "PROPOSED_NOT_EFFECTIVE"
    assert policy["host_allowlist"] == ["pypi.org"]
    assert policy["methods"] == ["GET"]
    assert policy["redirects"] == 0
    assert policy["retries"] == 0
    assert policy["max_responses"] == 1
    assert policy["follows_file_urls"] is False
    assert policy["authorization_granted"] is False


def test_scope_candidate_has_zero_authority_and_execution(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    assert all(value == 0 for value in candidate["current_effective_limits"].values())
    assert all(value == 0 for value in candidate["execution_counts"].values())
    assert all(value is False for key, value in candidate["authorization"].items() if key != "token")
    assert candidate["authorization"]["token"] is None


def test_scope_builder_requires_full_lowercase_commit_oid(repo_root: Path) -> None:
    for expression in ("HEAD", _commit(repo_root)[:12], _commit(repo_root).upper()):
        with pytest.raises(ValueError, match="full lowercase 40-character Git OID"):
            builder.build_scope_candidate(expression, repo_root)


def test_scope_builder_cli_rejects_revision_expression(repo_root: Path, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        builder.main([
            "--commit", "HEAD", "--repo", str(repo_root),
            "--output", str(tmp_path / "candidate.json"),
        ])


def test_scope_evidence_is_committed_and_digest_bound(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    assert [item["path"] for item in candidate["evidence"]] == list(builder.SCOPE_EVIDENCE_PATHS)
    for item in candidate["evidence"]:
        data = subprocess.run(
            ["git", "cat-file", "blob", item["git_blob_oid"]],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
        assert len(data) == item["byte_count"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"]


def test_scope_candidate_rejects_noncanonical_assertion_definitions(
    repo_root: Path,
) -> None:
    mutations = (
        ("assertion_id", "invented-assertion"),
        ("claim", "An unrelated claim selected by the Builder."),
        ("required_utf8_fragment", "pypdf"),
    )
    for field, value in mutations:
        candidate = _candidate(repo_root)
        candidate["scope_assertion_bindings"][0][field] = value
        with pytest.raises(
            schema.MetadataGovernanceError,
            match="assertion definition is not exact",
        ):
            schema.validate_scope_candidate(candidate)


def test_scope_candidate_rejects_unknown_and_nonzero_fields(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["unexpected"] = True
    with pytest.raises(schema.MetadataGovernanceError, match="keys are not exact"):
        schema.validate_scope_candidate(candidate)

    candidate = _candidate(repo_root)
    candidate["current_effective_limits"]["metadata_requests"] = 1
    with pytest.raises(schema.MetadataGovernanceError, match="current effective limits"):
        schema.validate_scope_candidate(candidate)


def test_scope_candidate_rejects_artifact_or_url_facts(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["scope"]["metadata_url"] = "https://pypi.org/"
    with pytest.raises(schema.MetadataGovernanceError, match="scope assertion"):
        schema.validate_scope_candidate(candidate)


def test_scope_candidate_rejects_proposed_policy_expansion(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    candidate["proposed_metadata_policy"]["host_allowlist"] = ["*"]
    with pytest.raises(schema.MetadataGovernanceError, match="host proposal"):
        schema.validate_scope_candidate(candidate)


def test_scope_candidate_rejects_noninteger_policy_numbers(
    repo_root: Path,
) -> None:
    mutations = (
        ("redirects", False),
        ("retries", False),
        ("max_responses", True),
        ("response_size_cap_bytes", 2097152.0),
    )
    for field, value in mutations:
        candidate = _candidate(repo_root)
        candidate["proposed_metadata_policy"][field] = value
        with pytest.raises(
            schema.MetadataGovernanceError,
            match="must be integers",
        ):
            schema.validate_scope_candidate(candidate)

    for field, value in (("connect", False), ("read", 10.0)):
        candidate = _candidate(repo_root)
        candidate["proposed_metadata_policy"]["timeouts_seconds"][field] = value
        with pytest.raises(
            schema.MetadataGovernanceError,
            match="timeouts must be integers",
        ):
            schema.validate_scope_candidate(candidate)


def test_scope_candidate_is_canonical_and_rejects_duplicate_or_unknown_json_keys(repo_root: Path) -> None:
    data = _candidate_bytes(repo_root)
    parsed = schema.parse_canonical_document(data)
    assert schema.canonical_bytes(parsed) == data
    with pytest.raises(schema.MetadataGovernanceError, match="duplicate"):
        schema.strict_loads(b'{"format":"x","format":"y"}')
    parsed["unexpected"] = True
    with pytest.raises(schema.MetadataGovernanceError, match="keys are not exact"):
        schema.validate_scope_candidate(parsed)


def test_scope_builder_and_validator_do_not_open_sockets(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("scope governance must not open a socket")

    monkeypatch.setattr(socket, "socket", fail_socket)
    candidate = _candidate(repo_root)
    scope_reviewer.validate_candidate_package(schema.canonical_bytes(candidate), repo_root)


def test_candidate_validation_is_not_independent_review(repo_root: Path) -> None:
    report = scope_reviewer.validate_candidate_package(_candidate_bytes(repo_root), repo_root)
    assert report["decision"] == schema.SCOPE_CANDIDATE_VALIDATED
    assert report["decision"] != schema.SCOPE_REVIEW_PASSED
    assert report["status"] == schema.SCOPE_REVIEW_REQUIRED


def test_independent_review_requires_different_reviewer(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    publication = {
        "byte_count": 1,
        "commit": "0" * 40,
        "git_blob_oid": "0" * 40,
        "parent": "1" * 40,
        "path": "m8/metadata-discovery/scope-candidate.json",
        "sha256": "0" * 64,
        "tree": "2" * 40,
    }
    with pytest.raises(schema.MetadataGovernanceError, match="provenance is unavailable"):
        scope_reviewer.build_review_record(
            schema.canonical_bytes(candidate), publication,
            candidate["source_git_binding"], candidate["builder_id"],
        )


def test_review_record_is_non_authorizing_and_stops_at_owner_gate(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    review = {
        "allowed_next_action": schema.SCOPE_OWNER_GATE_READY,
        "authorization": {
            "installation_authorized": False,
            "metadata_discovery_authorized": False,
            "network_access_authorized": False,
            "resolver_execution_authorized": False,
            "token": None,
            "wheel_download_authorized": False,
        },
        "builder_id": candidate["builder_id"],
        "candidate_publication_binding": {
            "byte_count": 1,
            "commit": "0" * 40,
            "git_blob_oid": "0" * 40,
            "parent": "1" * 40,
            "path": "m8/metadata-discovery/scope-candidate.json",
            "sha256": "0" * 64,
            "tree": "2" * 40,
        },
        "candidate_sha256": "0" * 64,
        "canonicalization_id": schema.CANONICALIZATION_ID,
        "checks": {
            "canonical_candidate": True, "evidence_bindings": True,
            "history_immutable": True, "no_artifact_selection": True,
            "policy_closed": True, "scope_assertions": True,
            "source_binding": True, "zero_authority": True,
        },
        "current_effective_limits": {key: 0 for key in schema.SCOPE_LIMIT_KEYS},
        "decision": schema.SCOPE_REVIEW_PASSED,
        "execution_counts": {key: 0 for key in schema.SCOPE_EXECUTION_KEYS},
        "format": schema.SCOPE_REVIEW_FORMAT,
        "m8_status": "BLOCKED / NOT_STARTED",
        "review_id": "review",
        "reviewed_source_git_binding": candidate["source_git_binding"],
        "reviewer": {
            "independence_attested": True,
            "reviewer_id": "INDEPENDENT_REVIEWER",
            "role": "INDEPENDENT_METADATA_DISCOVERY_SCOPE_REVIEWER",
        },
    }
    with pytest.raises(schema.MetadataGovernanceError, match="provenance is unverified"):
        schema.validate_scope_review(review)
    assert review["authorization"]["token"] is None


def test_scope_review_rejects_self_review(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    review = {
        "canonicalization_id": schema.CANONICALIZATION_ID,
        "format": schema.SCOPE_REVIEW_FORMAT,
        "m8_status": "BLOCKED / NOT_STARTED",
        "review_id": "review",
        "builder_id": candidate["builder_id"],
        "reviewer": {
            "reviewer_id": candidate["builder_id"],
            "role": "INDEPENDENT_METADATA_DISCOVERY_SCOPE_REVIEWER",
            "independence_attested": True,
        },
        "candidate_sha256": "0" * 64,
        "candidate_publication_binding": {
            "commit": "0" * 40, "parent": "1" * 40, "tree": "2" * 40,
            "path": "candidate.json", "git_blob_oid": "0" * 40,
            "byte_count": 1, "sha256": "0" * 64,
        },
        "reviewed_source_git_binding": candidate["source_git_binding"],
        "checks": {},
        "decision": schema.SCOPE_REVIEW_PASSED,
        "authorization": {},
        "current_effective_limits": {},
        "execution_counts": {},
        "allowed_next_action": schema.SCOPE_OWNER_GATE_READY,
    }
    with pytest.raises(schema.MetadataGovernanceError, match="provenance is unverified"):
        schema.validate_scope_review(review)



def test_scope_chain_accepts_exact_forward_only_publication_order() -> None:
    def publication(commit: str, parent: str) -> dict[str, object]:
        return {
            "byte_count": 1,
            "commit": commit,
            "git_blob_oid": "a" * 40,
            "parent": parent,
            "path": schema.SCOPE_CHAIN_PATHS[stage],
            "sha256": "b" * 64,
            "tree": "c" * 40,
        }

    stages = list(schema.SCOPE_CHAIN_STAGES)
    records: list[dict[str, object]] = []
    commits = [f"{index:x}" * 40 for index in range(1, len(stages) + 1)]
    parents = ["0" * 40, *commits[:-1]]
    for index, stage in enumerate(stages):
        predecessors = []
        for predecessor_stage in schema.SCOPE_CHAIN_PREDECESSORS[stage]:
            predecessor = records[stages.index(predecessor_stage)]
            predecessor_publication = predecessor["publication"]
            assert isinstance(predecessor_publication, dict)
            predecessors.append({
                "stage": predecessor_stage,
                "record_id": predecessor["record_id"],
                **predecessor_publication,
            })
        records.append({
            "canonicalization_id": schema.CANONICALIZATION_ID,
            "format": schema.SCOPE_CHAIN_FORMAT,
            "non_authorizing": True,
            "predecessors": predecessors,
            "publication": publication(commits[index], parents[index]),
            "record_id": f"record-{stage}",
            "stage": stage,
        })

    schema.validate_scope_chain(records)


def test_scope_chain_rejects_forward_and_self_references(tmp_path: Path) -> None:
    _, records = _init_linear_chain_repo(tmp_path)
    forward = records[2]
    records[1]["predecessors"] = [_stage_ref(forward)]
    with pytest.raises(schema.MetadataGovernanceError, match="predecessor stages|forward or deferred"):
        schema.validate_scope_chain(records)

    records[1]["predecessors"] = [_stage_ref(records[1])]
    with pytest.raises(schema.MetadataGovernanceError, match="self-reference|predecessor stages"):
        schema.validate_scope_chain(records)


def test_scope_chain_rejects_wrong_parent_and_tampered_predecessor() -> None:
    def build_records() -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        stages = list(schema.SCOPE_CHAIN_STAGES)
        commits = [f"{index:x}" * 40 for index in range(1, len(stages) + 1)]
        for index, stage in enumerate(stages):
            predecessors = []
            for predecessor_stage in schema.SCOPE_CHAIN_PREDECESSORS[stage]:
                predecessor = records[stages.index(predecessor_stage)]
                predecessor_publication = predecessor["publication"]
                assert isinstance(predecessor_publication, dict)
                predecessors.append({
                    "stage": predecessor_stage,
                    "record_id": predecessor["record_id"],
                    **predecessor_publication,
                })
            records.append({
                "canonicalization_id": schema.CANONICALIZATION_ID,
                "format": schema.SCOPE_CHAIN_FORMAT,
                "non_authorizing": True,
                "predecessors": predecessors,
                "publication": {
                    "byte_count": 1,
                    "commit": commits[index],
                    "git_blob_oid": "a" * 40,
                    "parent": "0" * 40 if index == 0 else commits[index - 1],
                    "path": schema.SCOPE_CHAIN_PATHS[stage],
                    "sha256": "b" * 64,
                    "tree": "c" * 40,
                },
                "record_id": f"record-{stage}",
                "stage": stage,
            })
        return records

    records = build_records()
    records[1]["publication"]["parent"] = "9" * 40
    with pytest.raises(schema.MetadataGovernanceError, match="direct forward step"):
        schema.validate_scope_chain(records)

    records = build_records()
    records[1]["predecessors"][0]["sha256"] = "a" * 64
    with pytest.raises(schema.MetadataGovernanceError, match="predecessor binding"):
        schema.validate_scope_chain(records)


def test_scope_chain_git_bindings_verify_committed_objects(tmp_path: Path) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    scope_reviewer.validate_scope_chain_git_bindings(records, repo)


def test_scope_chain_git_bindings_rejects_nonsemantic_committed_bytes(
    tmp_path: Path,
) -> None:
    repo, records = _init_linear_chain_repo(
        tmp_path,
        {"review_prompt": b"review_prompt\n"},
    )
    with pytest.raises(schema.MetadataGovernanceError, match="invalid JSON"):
        scope_reviewer.validate_scope_chain_git_bindings(records, repo)


def test_scope_stage_payloads_are_exact_and_non_authorizing(tmp_path: Path) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    scope_reviewer.validate_scope_chain_git_bindings(records, repo)
    for record in records:
        publication = record["publication"]
        _, data = scope_reviewer._read_blob(
            publication["commit"], publication["path"], repo
        )
        payload = schema.parse_canonical_document(data)
        schema.validate_scope_stage_payload(record["stage"], payload)
        if record["stage"] != "candidate_publication":
            assert payload["governance"]["m8_status"] == "BLOCKED / NOT_STARTED"
            assert not any(payload["governance"]["execution_counts"].values())
            assert payload["governance"]["authorization"]["token"] is None


def test_scope_stage_payload_rejects_wrong_format_cycle_and_authority(
    tmp_path: Path,
) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    prompt = next(item for item in records if item["stage"] == "review_prompt")
    _, data = scope_reviewer._read_blob(
        prompt["publication"]["commit"], prompt["publication"]["path"], repo
    )
    payload = schema.parse_canonical_document(data)
    for field, value, message in (
        ("format", "wrong", "format"),
        ("cycle_id", "wrong", "cycle"),
    ):
        tampered = json.loads(json.dumps(payload))
        tampered[field] = value
        with pytest.raises(schema.MetadataGovernanceError, match=message):
            schema.validate_scope_stage_payload("review_prompt", tampered)
    tampered = json.loads(json.dumps(payload))
    tampered["governance"]["authorization"]["network_access_authorized"] = True
    with pytest.raises(schema.MetadataGovernanceError, match="authorization"):
        schema.validate_scope_stage_payload("review_prompt", tampered)


def test_scope_chain_rejects_duplicate_record_ids(tmp_path: Path) -> None:
    _, records = _init_linear_chain_repo(tmp_path)
    records[2]["record_id"] = records[1]["record_id"]
    with pytest.raises(schema.MetadataGovernanceError, match="record IDs"):
        schema.validate_scope_chain(records)


def test_dispatch_rooted_validation_closes_one_exact_target(tmp_path: Path) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    dispatch = records[-1]["publication"]
    result = scope_reviewer.validate_dispatch_publication(dispatch, repo)
    assert result["status"] == schema.SCOPE_READY_FOR_EXTERNAL_REVIEW
    assert result["m8_status"] == "BLOCKED / NOT_STARTED"
    assert not any(result["execution_counts"].values())


def test_dispatch_rooted_validation_rejects_candidate_divergence(
    tmp_path: Path,
) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    dispatch_record = records[-1]
    dispatch_publication = dispatch_record["publication"]
    _, data = scope_reviewer._read_blob(
        dispatch_publication["commit"], dispatch_publication["path"], repo
    )
    dispatch = schema.parse_canonical_document(data)
    dispatch["candidate_binding"]["sha256"] = "f" * 64
    commit = _commit_file(
        repo,
        schema.SCOPE_CHAIN_PATHS["dispatch_manifest"],
        schema.canonical_bytes(dispatch),
        "tamper dispatch candidate binding",
    )
    binding = _publication_binding(
        repo, commit, schema.SCOPE_CHAIN_PATHS["dispatch_manifest"]
    )
    with pytest.raises(schema.MetadataGovernanceError, match="publication binding"):
        scope_reviewer.validate_dispatch_publication(binding, repo)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tree", "f" * 40, "commit binding mismatch"),
        ("path", "m8/metadata-discovery/missing.json", "path is not fixed"),
        ("git_blob_oid", "f" * 40, "blob OID mismatch"),
        ("byte_count", 999, "byte count mismatch"),
        ("sha256", "f" * 64, "digest mismatch"),
    ],
)
def test_scope_chain_git_bindings_reject_tampered_publication(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    records[-1]["publication"][field] = value
    with pytest.raises((ValueError, subprocess.CalledProcessError), match=message):
        scope_reviewer.validate_scope_chain_git_bindings(records, repo)


def test_scope_chain_git_bindings_reject_nonexistent_commit(tmp_path: Path) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    records[-1]["publication"]["commit"] = "f" * 40
    with pytest.raises(schema.MetadataGovernanceError, match="Git object"):
        scope_reviewer.validate_scope_chain_git_bindings(records, repo)


def test_review_builder_rejects_fabricated_publication(repo_root: Path) -> None:
    candidate = _candidate(repo_root)
    publication = {
        "byte_count": 1,
        "commit": "f" * 40,
        "git_blob_oid": "0" * 40,
        "parent": "1" * 40,
        "path": scope_reviewer.CANDIDATE_PATH,
        "sha256": "0" * 64,
        "tree": "2" * 40,
    }
    with pytest.raises(schema.MetadataGovernanceError, match="provenance is unavailable"):
        scope_reviewer.build_review_record(
            schema.canonical_bytes(candidate),
            publication,
            candidate["source_git_binding"],
            repo_root=repo_root,
        )


def test_review_package_rechecks_published_candidate_evidence(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate(repo_root)
    review = {
        "allowed_next_action": schema.SCOPE_OWNER_GATE_READY,
        "authorization": {
            "installation_authorized": False,
            "metadata_discovery_authorized": False,
            "network_access_authorized": False,
            "resolver_execution_authorized": False,
            "token": None,
            "wheel_download_authorized": False,
        },
        "builder_id": candidate["builder_id"],
        "candidate_publication_binding": {
            "byte_count": 1,
            "commit": "0" * 40,
            "git_blob_oid": "0" * 40,
            "parent": "1" * 40,
            "path": scope_reviewer.CANDIDATE_PATH,
            "sha256": "0" * 64,
            "tree": "2" * 40,
        },
        "candidate_sha256": "0" * 64,
        "canonicalization_id": schema.CANONICALIZATION_ID,
        "checks": {},
        "current_effective_limits": {key: 0 for key in schema.SCOPE_LIMIT_KEYS},
        "decision": schema.SCOPE_REVIEW_PASSED,
        "execution_counts": {key: 0 for key in schema.SCOPE_EXECUTION_KEYS},
        "format": schema.SCOPE_REVIEW_FORMAT,
        "m8_status": "BLOCKED / NOT_STARTED",
        "review_id": "review",
        "reviewed_source_git_binding": candidate["source_git_binding"],
        "reviewer": {
            "independence_attested": True,
            "reviewer_id": "INDEPENDENT_REVIEWER",
            "role": "INDEPENDENT_METADATA_DISCOVERY_SCOPE_REVIEWER",
        },
    }
    with pytest.raises(schema.MetadataGovernanceError, match="provenance is unavailable"):
        scope_reviewer.validate_review_package(schema.canonical_bytes(review), repo_root)


def test_reviewer_cli_only_validates_candidate(
    repo_root: Path, tmp_path: Path
) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "validation.json"
    candidate_path.write_bytes(_candidate_bytes(repo_root))
    assert scope_reviewer.main([
        "--candidate", str(candidate_path),
        "--repo", str(repo_root),
        "--output", str(output_path),
    ]) == 0
    report = schema.parse_canonical_document(output_path.read_bytes())
    assert report["decision"] == schema.SCOPE_CANDIDATE_VALIDATED
    assert report["decision"] != schema.SCOPE_REVIEW_PASSED
    assert report["m8_status"] == "BLOCKED / NOT_STARTED"


def test_dispatch_cli_validates_only_committed_dispatch_root(
    tmp_path: Path,
) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    output_path = tmp_path / "dispatch-validation.json"
    dispatch_publication = records[-1]["publication"]
    assert isinstance(dispatch_publication, dict)
    dispatch_commit = dispatch_publication["commit"]
    assert isinstance(dispatch_commit, str)

    assert scope_reviewer.main([
        "--dispatch-commit", dispatch_commit,
        "--repo", str(repo),
        "--output", str(output_path),
    ]) == 0

    report = schema.parse_canonical_document(output_path.read_bytes())
    assert report == {
        "execution_counts": _stage_governance()["execution_counts"],
        "m8_status": "BLOCKED / NOT_STARTED",
        "status": schema.SCOPE_READY_FOR_EXTERNAL_REVIEW,
    }
    assert report["status"] != schema.SCOPE_REVIEW_PASSED
    assert report["status"] != schema.SCOPE_OWNER_GATE_READY


def test_git_reader_rejects_aggregate_budget_before_next_object(tmp_path: Path) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    first_commit = records[0]["publication"]["commit"]
    assert isinstance(first_commit, str)
    reader = git_reader.GitObjectReader(repo, aggregate_limit=1)
    with pytest.raises(schema.MetadataGovernanceError, match="aggregate byte bound"):
        reader.commit_binding(first_commit)


def test_git_reader_rejects_unsafe_paths_and_non_oid_inputs(tmp_path: Path) -> None:
    repo, _ = _init_linear_chain_repo(tmp_path)
    reader = git_reader.GitObjectReader(repo)
    with pytest.raises(schema.MetadataGovernanceError, match="full lowercase"):
        reader.read_object("HEAD", "commit")
    with pytest.raises(schema.MetadataGovernanceError, match="unsafe"):
        reader.read_blob("0" * 40, "../scope-candidate.json")


def test_git_reader_rejects_root_and_merge_commits(tmp_path: Path) -> None:
    repo = tmp_path / "commit-policy-repo"
    repo.mkdir()
    _run_git(repo, "init", "-b", "master")
    root_commit = _commit_file(repo, "root.txt", b"root\n", "root")
    reader = git_reader.GitObjectReader(repo)
    with pytest.raises(
        schema.MetadataGovernanceError,
        match="ordinary_single_parent_commit_only",
    ):
        reader.commit_binding(root_commit)

    _run_git(repo, "checkout", "-b", "side")
    _commit_file(repo, "side.txt", b"side\n", "side")
    _run_git(repo, "checkout", "master")
    _commit_file(repo, "main.txt", b"main\n", "main")
    _run_git(
        repo,
        "-c", "user.name=Scope Governance Tests",
        "-c", "user.email=scope-governance-tests@example.invalid",
        "merge", "--no-ff", "side", "-m", "merge",
    )
    merge_commit = _run_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    with pytest.raises(
        schema.MetadataGovernanceError,
        match="ordinary_single_parent_commit_only",
    ):
        reader.commit_binding(merge_commit)


def test_git_reader_rejects_wrong_object_type(tmp_path: Path) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    publication = records[0]["publication"]
    blob_oid = publication["git_blob_oid"]
    assert isinstance(blob_oid, str)
    reader = git_reader.GitObjectReader(repo)
    with pytest.raises(schema.MetadataGovernanceError, match="not a commit"):
        reader.read_object(blob_oid, "commit")


def test_git_reader_object_header_uses_single_object_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    first_commit = records[0]["publication"]["commit"]
    assert isinstance(first_commit, str)
    calls: list[tuple[tuple[str, ...], bytes | None]] = []
    original_capture = git_reader.GitObjectReader._capture

    def capture(
        self: git_reader.GitObjectReader,
        *args: str,
        input_bytes: bytes | None = None,
    ) -> bytes:
        calls.append((args, input_bytes))
        return original_capture(self, *args, input_bytes=input_bytes)

    monkeypatch.setattr(git_reader.GitObjectReader, "_capture", capture)
    reader = git_reader.GitObjectReader(repo)
    reader.commit_binding(first_commit)

    header_calls = [
        call
        for call in calls
        if call[0][:2] in {("cat-file", "-t"), ("cat-file", "-s")}
    ]
    assert header_calls == [
        (("cat-file", "-t", first_commit), None),
        (("cat-file", "-s", first_commit), None),
    ]


def test_git_reader_rejects_malformed_object_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    first_commit = records[0]["publication"]["commit"]
    assert isinstance(first_commit, str)
    reader = git_reader.GitObjectReader(repo)

    def capture(
        *args: str, input_bytes: bytes | None = None
    ) -> bytes:
        del input_bytes
        if args[:2] == ("cat-file", "-t"):
            return b"commit extra\n"
        if args[:2] == ("cat-file", "-s"):
            return b"1\n"
        raise AssertionError(args)

    monkeypatch.setattr(reader, "_capture", capture)
    with pytest.raises(schema.MetadataGovernanceError, match="header is malformed"):
        reader.read_object(first_commit, "commit")


def test_git_reader_rejects_invalid_declared_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, records = _init_linear_chain_repo(tmp_path)
    first_commit = records[0]["publication"]["commit"]
    assert isinstance(first_commit, str)
    reader = git_reader.GitObjectReader(repo)

    def capture(
        *args: str, input_bytes: bytes | None = None
    ) -> bytes:
        del input_bytes
        if args[:2] == ("cat-file", "-t"):
            return b"commit\n"
        if args[:2] == ("cat-file", "-s"):
            return b"not-an-integer\n"
        raise AssertionError(args)

    monkeypatch.setattr(reader, "_capture", capture)
    with pytest.raises(schema.MetadataGovernanceError, match="size is invalid"):
        reader.read_object(first_commit, "commit")

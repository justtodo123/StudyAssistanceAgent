"""Validate the independent, offline-only M8 metadata-discovery scope review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from tools.m8_metadata_discovery_schema import (
        CANONICALIZATION_ID,
        SCOPE_CANDIDATE_VALIDATED,
        SCOPE_REVIEW_FORMAT,
        SCOPE_REVIEW_PASSED,
        SCOPE_OWNER_GATE_READY,
        canonical_bytes,
        parse_canonical_document,
        validate_scope_candidate,
        validate_scope_review,
        validate_scope_chain,
        validate_scope_stage_payload,
        MAX_DOCUMENT_BYTES,
        MAX_CHAIN_BYTES,
        MetadataGovernanceError,
        SCOPE_CHAIN_PATHS,
        SCOPE_CHAIN_STAGES,
        SCOPE_CHAIN_PREDECESSORS,
        SCOPE_CHAIN_FORMAT,
        SCOPE_CHAIN_BINDING_KEYS,
        SCOPE_READY_FOR_EXTERNAL_REVIEW,
    )
except ImportError:  # pragma: no cover
    from m8_metadata_discovery_schema import (
        CANONICALIZATION_ID,
        SCOPE_CANDIDATE_VALIDATED,
        SCOPE_REVIEW_FORMAT,
        SCOPE_REVIEW_PASSED,
        SCOPE_OWNER_GATE_READY,
        canonical_bytes,
        parse_canonical_document,
        validate_scope_candidate,
        validate_scope_review,
        validate_scope_chain,
        validate_scope_stage_payload,
        MAX_DOCUMENT_BYTES,
        MAX_CHAIN_BYTES,
        MetadataGovernanceError,
        SCOPE_CHAIN_PATHS,
        SCOPE_CHAIN_STAGES,
        SCOPE_CHAIN_PREDECESSORS,
        SCOPE_CHAIN_FORMAT,
        SCOPE_CHAIN_BINDING_KEYS,
        SCOPE_READY_FOR_EXTERNAL_REVIEW,
    )

try:
    from tools.m8_git_object_reader import GitObjectReader
except ImportError:  # pragma: no cover
    from m8_git_object_reader import GitObjectReader

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = "m8/metadata-discovery/scope-candidate.json"
REVIEWER_ID = "M8_METADATA_DISCOVERY_SCOPE_INDEPENDENT_REVIEWER"


def git(
    *args: str,
    repo_root: Path = ROOT,
    input_bytes: bytes | None = None,
) -> bytes:
    """Read only explicitly named local Git objects."""
    return subprocess.run(
        ["git", "--no-replace-objects", "--no-lazy-fetch", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        input=input_bytes,
        timeout=15,
    ).stdout


def _read_blob(
    commit: str,
    path: str,
    repo_root: Path,
    reader: GitObjectReader | None = None,
) -> tuple[str, bytes]:
    """Read one bounded blob only after Git reports its object type and size."""
    active_reader = reader or GitObjectReader(repo_root)
    return active_reader.read_blob(commit, path)


def _commit_binding(
    commit: str,
    repo_root: Path,
    reader: GitObjectReader | None = None,
) -> dict[str, str]:
    active_reader = reader or GitObjectReader(repo_root)
    return active_reader.commit_binding(commit)


def _verify_candidate_evidence(
    candidate: dict[str, Any],
    repo_root: Path,
    reader: GitObjectReader | None = None,
) -> None:
    active_reader = reader or GitObjectReader(repo_root)
    source = candidate["source_commit"]
    if candidate["source_git_binding"] != _commit_binding(source, repo_root, active_reader):
        raise MetadataGovernanceError("source Git binding does not match the committed source")
    evidence_by_path = {item["path"]: item for item in candidate["evidence"]}
    if len(evidence_by_path) != len(candidate["evidence"]):
        raise MetadataGovernanceError("candidate evidence inventory contains duplicate paths")
    for path, item in evidence_by_path.items():
        oid, data = _read_blob(source, path, repo_root, active_reader)
        if oid != item["git_blob_oid"]:
            raise MetadataGovernanceError(f"evidence blob OID mismatch for {path}")
        if len(data) != item["byte_count"]:
            raise MetadataGovernanceError(f"evidence byte count mismatch for {path}")
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise MetadataGovernanceError(f"evidence digest mismatch for {path}")
    for assertion in candidate["scope_assertion_bindings"]:
        path = assertion["evidence_path"]
        _, data = _read_blob(source, path, repo_root, active_reader)
        text = data.decode("utf-8")
        if text.count(assertion["required_utf8_fragment"]) != assertion["expected_occurrences"]:
            raise MetadataGovernanceError(f"scope assertion occurrence mismatch for {path}")
        if assertion["git_blob_oid"] != evidence_by_path[path]["git_blob_oid"]:
            raise MetadataGovernanceError(f"scope assertion blob binding mismatch for {path}")
        if assertion["sha256"] != evidence_by_path[path]["sha256"]:
            raise MetadataGovernanceError(f"scope assertion digest binding mismatch for {path}")


def validate_candidate_package(candidate_bytes: bytes, repo_root: Path = ROOT) -> dict[str, Any]:
    """Validate a candidate and its committed evidence without performing discovery."""
    candidate = parse_canonical_document(candidate_bytes)
    validate_scope_candidate(candidate)
    root = repo_root.resolve()
    _verify_candidate_evidence(candidate, root, GitObjectReader(root))
    return {
        "canonicalization_id": CANONICALIZATION_ID,
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "decision": SCOPE_CANDIDATE_VALIDATED,
        "execution_counts": candidate["execution_counts"],
        "m8_status": candidate["m8_status"],
        "status": candidate["status"],
    }


def validate_scope_chain_git_bindings(
    records: list[dict[str, Any]], repo_root: Path = ROOT
) -> None:
    """Verify staged publications, their payloads, and committed Git bindings."""
    validate_scope_chain(records)
    root = repo_root.resolve()
    reader = GitObjectReader(root)
    for record in records:
        publication = record["publication"]
        commit = publication["commit"]
        expected_commit = _commit_binding(commit, root, reader)
        if {
            key: publication[key] for key in ("commit", "parent", "tree")
        } != expected_commit:
            raise MetadataGovernanceError(
                f"scope chain commit binding mismatch for {record['stage']}"
            )
        oid, data = _read_blob(
            commit,
            publication["path"],
            root,
            reader,
        )
        if oid != publication["git_blob_oid"]:
            raise MetadataGovernanceError(
                f"scope chain blob OID mismatch for {record['stage']}"
            )
        if len(data) != publication["byte_count"]:
            raise MetadataGovernanceError(
                f"scope chain byte count mismatch for {record['stage']}"
            )
        if hashlib.sha256(data).hexdigest() != publication["sha256"]:
            raise MetadataGovernanceError(
                f"scope chain digest mismatch for {record['stage']}"
            )
        payload = parse_canonical_document(data)
        validate_scope_stage_payload(record["stage"], payload)


def _validate_stage_payload_bindings(
    records: list[dict[str, Any]],
    payloads: dict[str, dict[str, Any]],
) -> None:
    """Close every stage payload over the exact predecessor publications."""
    by_stage = {record["stage"]: record for record in records}
    binding_keys = {
        "candidate_publication": {"candidate_binding": "candidate_publication"},
        "builder_self_check": {"candidate_binding": "candidate_publication"},
        "review_request": {
            "candidate_binding": "candidate_publication",
            "self_check_binding": "builder_self_check",
        },
        "review_prompt": {
            "candidate_binding": "candidate_publication",
            "request_binding": "review_request",
        },
        "review_target": {
            "candidate_binding": "candidate_publication",
            "self_check_binding": "builder_self_check",
            "request_binding": "review_request",
            "prompt_binding": "review_prompt",
        },
        "dispatch_manifest": {
            "candidate_binding": "candidate_publication",
            "self_check_binding": "builder_self_check",
            "request_binding": "review_request",
            "prompt_binding": "review_prompt",
            "target_binding": "review_target",
        },
    }
    for stage, expected_bindings in binding_keys.items():
        if stage == "candidate_publication":
            continue
        payload = payloads[stage]
        predecessors = {
            ref["stage"]: ref
            for ref in by_stage[stage]["predecessors"]
        }
        for field, predecessor_stage in expected_bindings.items():
            if payload[field] != predecessors[predecessor_stage]:
                raise MetadataGovernanceError(
                    f"{stage} payload binding does not match predecessor"
                )
    candidate = payloads["candidate_publication"]
    for stage in SCOPE_CHAIN_STAGES[1:]:
        if payloads[stage]["candidate_binding"] != {
            "stage": "candidate_publication",
            "record_id": by_stage["candidate_publication"]["record_id"],
            **by_stage["candidate_publication"]["publication"],
        }:
            raise MetadataGovernanceError("candidate binding continuity is invalid")
        if payloads[stage].get("cycle_id") != candidate["cycle_id"]:
            raise MetadataGovernanceError("stage cycle continuity is invalid")


def validate_dispatch_publication(
    dispatch_publication: dict[str, Any],
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    """Validate one dispatch-rooted chain using only committed references."""
    root = repo_root.resolve()
    if type(dispatch_publication) is not dict:
        raise MetadataGovernanceError("dispatch publication must be an object")
    if set(dispatch_publication) != SCOPE_CHAIN_BINDING_KEYS:
        raise MetadataGovernanceError("dispatch publication keys are not exact")
    if dispatch_publication["path"] != SCOPE_CHAIN_PATHS["dispatch_manifest"]:
        raise MetadataGovernanceError("dispatch publication path is not fixed")
    reader = GitObjectReader(root)

    def load(stage: str, publication: dict[str, Any]) -> dict[str, Any]:
        if type(publication) is not dict or set(publication) != SCOPE_CHAIN_BINDING_KEYS:
            raise MetadataGovernanceError(f"{stage} publication keys are not exact")
        if publication["path"] != SCOPE_CHAIN_PATHS[stage]:
            raise MetadataGovernanceError(f"{stage} publication path is not fixed")
        expected_commit = _commit_binding(publication["commit"], root, reader)
        if {
            key: publication[key] for key in ("commit", "parent", "tree")
        } != expected_commit:
            raise MetadataGovernanceError(f"{stage} commit binding mismatch")
        oid, data = _read_blob(
            publication["commit"],
            publication["path"],
            root,
            reader,
        )
        if (
            oid != publication["git_blob_oid"]
            or len(data) != publication["byte_count"]
            or hashlib.sha256(data).hexdigest() != publication["sha256"]
        ):
            raise MetadataGovernanceError(f"{stage} publication binding mismatch")
        payload = parse_canonical_document(data)
        validate_scope_stage_payload(stage, payload)
        return payload

    payloads: dict[str, dict[str, Any]] = {}
    publications: dict[str, dict[str, Any]] = {
        "dispatch_manifest": dispatch_publication,
    }
    dispatch = load("dispatch_manifest", dispatch_publication)
    payloads["dispatch_manifest"] = dispatch
    field_by_stage = {
        "candidate_publication": "candidate_binding",
        "builder_self_check": "self_check_binding",
        "review_request": "request_binding",
        "review_prompt": "prompt_binding",
        "review_target": "target_binding",
    }
    record_ids: dict[str, str] = {}
    for stage, field in field_by_stage.items():
        ref = dispatch[field]
        publication = {key: ref[key] for key in SCOPE_CHAIN_BINDING_KEYS}
        publications[stage] = publication
        record_ids[stage] = ref["record_id"]
        payloads[stage] = load(stage, publication)
    record_ids["dispatch_manifest"] = "dispatch-root"

    records: list[dict[str, Any]] = []
    for stage in SCOPE_CHAIN_STAGES:
        if stage == "candidate_publication":
            predecessors: list[dict[str, Any]] = []
        else:
            payload = payloads[stage]
            predecessor_fields = {
                "builder_self_check": ("candidate_binding",),
                "review_request": ("candidate_binding", "self_check_binding"),
                "review_prompt": ("candidate_binding", "request_binding"),
                "review_target": (
                    "candidate_binding", "self_check_binding",
                    "request_binding", "prompt_binding",
                ),
                "dispatch_manifest": (
                    "candidate_binding", "self_check_binding", "request_binding",
                    "prompt_binding", "target_binding",
                ),
            }[stage]
            predecessors = [payload[field] for field in predecessor_fields]
        records.append({
            "canonicalization_id": CANONICALIZATION_ID,
            "format": SCOPE_CHAIN_FORMAT,
            "non_authorizing": True,
            "predecessors": predecessors,
            "publication": publications[stage],
            "record_id": record_ids[stage],
            "stage": stage,
        })
    validate_scope_chain(records)
    _validate_stage_payload_bindings(records, payloads)
    return {
        "status": SCOPE_READY_FOR_EXTERNAL_REVIEW,
        "m8_status": "BLOCKED / NOT_STARTED",
        "execution_counts": dispatch["governance"]["execution_counts"],
    }


def _verify_publication_binding(
    binding: dict[str, Any], repo_root: Path,
    reader: GitObjectReader | None = None,
) -> dict[str, Any]:
    if type(binding) is not dict:
        raise MetadataGovernanceError("candidate publication binding must be an object")
    if binding.get("path") != CANDIDATE_PATH:
        raise MetadataGovernanceError("candidate publication path is not fixed")
    active_reader = reader or GitObjectReader(repo_root)
    commit = binding["commit"]
    expected_binding = _commit_binding(commit, repo_root, active_reader)
    if {key: binding[key] for key in ("commit", "parent", "tree")} != expected_binding:
        raise MetadataGovernanceError("candidate publication commit binding mismatch")
    oid, data = _read_blob(commit, binding["path"], repo_root, active_reader)
    if oid != binding["git_blob_oid"]:
        raise MetadataGovernanceError("candidate publication blob OID mismatch")
    if len(data) != binding["byte_count"]:
        raise MetadataGovernanceError("candidate publication byte count mismatch")
    digest = hashlib.sha256(data).hexdigest()
    if digest != binding["sha256"]:
        raise MetadataGovernanceError("candidate publication digest mismatch")
    candidate = parse_canonical_document(data)
    validate_scope_candidate(candidate)
    return candidate


def validate_review_package(
    review_bytes: bytes, repo_root: Path = ROOT
) -> dict[str, Any]:
    """Reject legacy self-attested review packages as unverifiable provenance."""
    del review_bytes, repo_root
    raise MetadataGovernanceError(
        "independent review provenance is unavailable; legacy self-attestation "
        "cannot establish an independent review"
    )


def build_review_record(
    candidate_bytes: bytes,
    publication: dict[str, Any],
    source_git_binding: dict[str, str],
    reviewer_id: str = REVIEWER_ID,
    review_id: str = "m8-metadata-discovery-scope-review-20260920-r02",
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    """Reject caller-authored identity as unverifiable review provenance."""
    del candidate_bytes, publication, source_git_binding, reviewer_id, review_id, repo_root
    raise MetadataGovernanceError(
        "independent review provenance is unavailable; "
        "use the dispatch-rooted READY_FOR_EXTERNAL_INDEPENDENT_REVIEW flow"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--candidate", type=Path)
    group.add_argument(
        "--dispatch-commit",
        help="full dispatch publication commit OID",
    )
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.dispatch_commit is not None:
        reader = GitObjectReader(args.repo.resolve())
        dispatch_commit = reader.require_oid(args.dispatch_commit, "dispatch commit")
        publication = {
            "byte_count": 0,
            "commit": dispatch_commit,
            "git_blob_oid": "",
            "parent": "",
            "path": SCOPE_CHAIN_PATHS["dispatch_manifest"],
            "sha256": "",
            "tree": "",
        }
        binding = reader.commit_binding(dispatch_commit)
        oid, data = reader.read_blob(dispatch_commit, publication["path"])
        publication.update(
            binding,
            byte_count=len(data),
            git_blob_oid=oid,
            sha256=hashlib.sha256(data).hexdigest(),
        )
        report = validate_dispatch_publication(publication, args.repo)
    else:
        report = validate_candidate_package(args.candidate.read_bytes(), args.repo)
    args.output.write_bytes(canonical_bytes(report))
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

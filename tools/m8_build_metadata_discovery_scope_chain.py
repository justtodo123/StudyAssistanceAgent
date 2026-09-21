"""Build and commit the offline six-stage M8 metadata-discovery scope publication chain.

This Builder freezes the Owner-selected ``pypdf==6.0.0`` candidate and its five
non-authorizing pre-review stages (builder self-check, review request, review
prompt, review target, dispatch manifest) as a direct-parent, forward-only Git
commit chain under ``m8/metadata-discovery/``.

It performs no network, DNS, PyPI, download, resolver, installer, or collector
work.  The final dispatch manifest can only reach
``READY_FOR_EXTERNAL_INDEPENDENT_REVIEW``; it never produces independent
approval, Owner Gate readiness, or metadata-discovery authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from tools.m8_build_metadata_discovery_scope_candidate import build_scope_candidate
    from tools.m8_git_object_reader import GitObjectReader
    from tools.m8_metadata_discovery_schema import (
        CANONICALIZATION_ID,
        SCOPE_CHAIN_FORMAT,
        SCOPE_CHAIN_PATHS,
        SCOPE_CHAIN_PREDECESSORS,
        SCOPE_CHAIN_STAGES,
        SCOPE_CYCLE_ID,
        SCOPE_DISPATCH_FORMAT,
        SCOPE_EXECUTION_KEYS,
        SCOPE_LIMIT_KEYS,
        SCOPE_READY_FOR_EXTERNAL_REVIEW,
        SCOPE_REVIEW_PROMPT_FORMAT,
        SCOPE_REVIEW_PROTOCOL,
        SCOPE_REVIEW_PROTOCOL_ID,
        SCOPE_REVIEW_PROTOCOL_SHA256,
        SCOPE_REVIEW_REQUIRED,
        SCOPE_REVIEW_REQUIRED_CHECKS,
        SCOPE_REVIEW_REQUEST_FORMAT,
        SCOPE_REVIEW_ROLE,
        SCOPE_REVIEW_TARGET_FORMAT,
        SCOPE_SELF_CHECK_DECISION,
        SCOPE_SELF_CHECK_FORMAT,
        SCOPE_SINGLE_PARENT_POLICY,
        canonical_bytes,
        validate_scope_stage_payload,
    )
    from tools.m8_validate_metadata_discovery_scope_review import validate_dispatch_publication
except ImportError:  # pragma: no cover
    from m8_build_metadata_discovery_scope_candidate import build_scope_candidate
    from m8_git_object_reader import GitObjectReader
    from m8_metadata_discovery_schema import (
        CANONICALIZATION_ID,
        SCOPE_CHAIN_FORMAT,
        SCOPE_CHAIN_PATHS,
        SCOPE_CHAIN_PREDECESSORS,
        SCOPE_CHAIN_STAGES,
        SCOPE_CYCLE_ID,
        SCOPE_DISPATCH_FORMAT,
        SCOPE_EXECUTION_KEYS,
        SCOPE_LIMIT_KEYS,
        SCOPE_READY_FOR_EXTERNAL_REVIEW,
        SCOPE_REVIEW_PROMPT_FORMAT,
        SCOPE_REVIEW_PROTOCOL,
        SCOPE_REVIEW_PROTOCOL_ID,
        SCOPE_REVIEW_PROTOCOL_SHA256,
        SCOPE_REVIEW_REQUIRED,
        SCOPE_REVIEW_REQUIRED_CHECKS,
        SCOPE_REVIEW_REQUEST_FORMAT,
        SCOPE_REVIEW_ROLE,
        SCOPE_REVIEW_TARGET_FORMAT,
        SCOPE_SELF_CHECK_DECISION,
        SCOPE_SELF_CHECK_FORMAT,
        SCOPE_SINGLE_PARENT_POLICY,
        canonical_bytes,
        validate_scope_stage_payload,
    )
    from m8_validate_metadata_discovery_scope_review import validate_dispatch_publication

ROOT = Path(__file__).resolve().parents[1]
REQUEST_ID = "m8-scope-review-request-20260920-r02"
TARGET_ID = "m8-scope-review-target-20260920-r02"
DISPATCH_ID = "m8-scope-dispatch-20260920-r02"


def _run_git(repo_root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def _commit_file(repo_root: Path, path: str, data: bytes, message: str) -> str:
    """Write one canonical stage file and commit it, returning its commit OID."""
    target = repo_root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    _run_git(repo_root, "add", "--", path)
    _run_git(repo_root, "commit", "-m", message)
    return _run_git(repo_root, "rev-parse", "HEAD").decode("ascii").strip()


def _publication_binding(
    repo_root: Path,
    commit: str,
    path: str,
    reader: GitObjectReader,
) -> dict[str, Any]:
    binding = reader.commit_binding(commit)
    oid, data = reader.read_blob(commit, path)
    return {
        **binding,
        "path": path,
        "git_blob_oid": oid,
        "byte_count": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _stage_governance() -> dict[str, Any]:
    return {
        "authorization": {
            "installation_authorized": False,
            "metadata_discovery_authorized": False,
            "network_access_authorized": False,
            "resolver_execution_authorized": False,
            "token": None,
            "wheel_download_authorized": False,
        },
        "current_effective_limits": {key: 0 for key in SCOPE_LIMIT_KEYS},
        "execution_counts": {key: 0 for key in SCOPE_EXECUTION_KEYS},
        "m8_status": "BLOCKED / NOT_STARTED",
    }


def _stage_ref(record: dict[str, Any]) -> dict[str, Any]:
    publication = record["publication"]
    return {
        "stage": record["stage"],
        "record_id": record["record_id"],
        **publication,
    }


def _stage_payload(
    stage: str,
    records: list[dict[str, Any]],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    by_stage = {record["stage"]: record for record in records}
    common = {
        "canonicalization_id": CANONICALIZATION_ID,
        "cycle_id": SCOPE_CYCLE_ID,
        "governance": _stage_governance(),
        "stage": stage,
    }
    candidate_binding = _stage_ref(by_stage["candidate_publication"])
    if stage == "builder_self_check":
        return {
            **common,
            "candidate_binding": candidate_binding,
            "checks": {key: True for key in SCOPE_REVIEW_REQUIRED_CHECKS[:-2]},
            "commit_policy": SCOPE_SINGLE_PARENT_POLICY,
            "decision": SCOPE_SELF_CHECK_DECISION,
            "format": SCOPE_SELF_CHECK_FORMAT,
            "independent_review_completed": False,
        }
    if stage == "review_request":
        return {
            **common,
            "candidate_binding": candidate_binding,
            "format": SCOPE_REVIEW_REQUEST_FORMAT,
            "protocol_binding": {
                "protocol_id": SCOPE_REVIEW_PROTOCOL_ID,
                "sha256": SCOPE_REVIEW_PROTOCOL_SHA256,
            },
            "request_id": REQUEST_ID,
            "requested_reviewer_role": SCOPE_REVIEW_ROLE,
            "review_completed": False,
            "self_check_binding": _stage_ref(by_stage["builder_self_check"]),
            "status": SCOPE_REVIEW_REQUIRED,
        }
    if stage == "review_prompt":
        return {
            **common,
            "candidate_binding": candidate_binding,
            "format": SCOPE_REVIEW_PROMPT_FORMAT,
            "protocol": SCOPE_REVIEW_PROTOCOL,
            "protocol_sha256": SCOPE_REVIEW_PROTOCOL_SHA256,
            "request_binding": _stage_ref(by_stage["review_request"]),
            "review_not_completed": True,
        }
    if stage == "review_target":
        return {
            **common,
            "candidate_binding": candidate_binding,
            "format": SCOPE_REVIEW_TARGET_FORMAT,
            "prompt_binding": _stage_ref(by_stage["review_prompt"]),
            "protocol_binding": {
                "protocol_id": SCOPE_REVIEW_PROTOCOL_ID,
                "sha256": SCOPE_REVIEW_PROTOCOL_SHA256,
            },
            "request_binding": _stage_ref(by_stage["review_request"]),
            "self_check_binding": _stage_ref(by_stage["builder_self_check"]),
            "status": SCOPE_REVIEW_REQUIRED,
            "target_id": TARGET_ID,
        }
    assert stage == "dispatch_manifest"
    return {
        **common,
        "candidate_binding": candidate_binding,
        "dispatch_id": DISPATCH_ID,
        "format": SCOPE_DISPATCH_FORMAT,
        "prompt_binding": _stage_ref(by_stage["review_prompt"]),
        "protocol_binding": {
            "protocol_id": SCOPE_REVIEW_PROTOCOL_ID,
            "sha256": SCOPE_REVIEW_PROTOCOL_SHA256,
        },
        "request_binding": _stage_ref(by_stage["review_request"]),
        "selected_target_count": 1,
        "self_check_binding": _stage_ref(by_stage["builder_self_check"]),
        "status": SCOPE_READY_FOR_EXTERNAL_REVIEW,
        "target_binding": _stage_ref(by_stage["review_target"]),
    }


def build_scope_chain(
    candidate: dict[str, Any],
    repo_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Commit the six-stage chain and return its records plus the dispatch binding."""
    repo_root = repo_root.resolve()
    reader = GitObjectReader(repo_root)
    records: list[dict[str, Any]] = []
    for stage in SCOPE_CHAIN_STAGES:
        path = SCOPE_CHAIN_PATHS[stage]
        if stage == "candidate_publication":
            payload = candidate
        else:
            payload = _stage_payload(stage, records, candidate)
        validate_scope_stage_payload(stage, payload)
        data = canonical_bytes(payload)
        commit = _commit_file(repo_root, path, data, f"chore(m8): publish {stage}")
        publication = _publication_binding(repo_root, commit, path, reader)
        predecessors = [
            _stage_ref(next(record for record in records if record["stage"] == predecessor))
            for predecessor in SCOPE_CHAIN_PREDECESSORS[stage]
        ]
        records.append({
            "canonicalization_id": CANONICALIZATION_ID,
            "format": SCOPE_CHAIN_FORMAT,
            "non_authorizing": True,
            "predecessors": predecessors,
            "publication": publication,
            "record_id": f"record-{stage}",
            "stage": stage,
        })
    dispatch = records[-1]["publication"]
    validate_dispatch_publication(dispatch, repo_root)
    return records, dispatch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="full source commit OID")
    parser.add_argument("--repo", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    if re.fullmatch(r"[0-9a-f]{40}", args.commit) is None:
        parser.error("--commit must be a full lowercase 40-character Git OID")
    repo_root = args.repo.resolve()
    candidate = build_scope_candidate(args.commit, repo_root)
    records, dispatch = build_scope_chain(candidate, repo_root)
    summary = {
        "dispatch_commit": dispatch["commit"],
        "stages": [
            {
                "stage": record["stage"],
                "path": record["publication"]["path"],
                "commit": record["publication"]["commit"],
                "git_blob_oid": record["publication"]["git_blob_oid"],
                "byte_count": record["publication"]["byte_count"],
                "sha256": record["publication"]["sha256"],
            }
            for record in records
        ],
        "status": SCOPE_READY_FOR_EXTERNAL_REVIEW,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

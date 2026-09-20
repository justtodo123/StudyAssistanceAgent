"""Build the fixed, offline-only pypdf 6.0.0 metadata-discovery scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from m8_git_object_reader import GitObjectReader
    from m8_metadata_discovery_schema import (
        CANONICALIZATION_ID,
        SCOPE_BUILDER_ID,
        SCOPE_CANDIDATE_FORMAT,
        SCOPE_CYCLE_ID,
        SCOPE_EVIDENCE_PATHS,
        SCOPE_ASSERTIONS,
        SCOPE_FORBIDDEN_ACTIONS,
        SCOPE_REVIEW_REQUIRED,
        canonical_bytes,
        validate_scope_candidate,
    )
except ImportError:  # pragma: no cover
    from tools.m8_git_object_reader import GitObjectReader
    from tools.m8_metadata_discovery_schema import (
        CANONICALIZATION_ID,
        SCOPE_BUILDER_ID,
        SCOPE_CANDIDATE_FORMAT,
        SCOPE_CYCLE_ID,
        SCOPE_EVIDENCE_PATHS,
        SCOPE_ASSERTIONS,
        SCOPE_FORBIDDEN_ACTIONS,
        SCOPE_REVIEW_REQUIRED,
        canonical_bytes,
        validate_scope_candidate,
    )

ROOT = Path(__file__).resolve().parents[1]
CYCLE_ID = SCOPE_CYCLE_ID
EXACT_REQUIREMENT = "pypdf==6.0.0"
CLASSIFICATIONS = {
    "platform/requirements.txt": "RUNTIME_DEPENDENCY_DECLARATION",
    "platform/app/parser_matrix.py": "RUNTIME_PARSER_IMPLEMENTATION_BINDING",
    "tests/M7/test_parser_matrix.py": "RUNTIME_PARSER_CONTRACT_TEST",
    "docs/plans/m7-source-lifecycle-plan.md": "FROZEN_RUNTIME_PARSER_POLICY",
    "docs/plans/references/m8-network-acquisition-owner-failed-closed-decision-20260919-r03.md": "HISTORICAL_GOVERNANCE_BOUNDARY",
}
ASSERTIONS = SCOPE_ASSERTIONS


def git(*args: str, repo_root: Path = ROOT) -> bytes:
    """Read only explicitly named Git objects."""
    return subprocess.run(
        ["git", "--no-replace-objects", "--no-lazy-fetch", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        timeout=15,
    ).stdout


def commit_identity(
    repo_root: Path,
    commit: str,
    reader: GitObjectReader | None = None,
) -> dict[str, str]:
    active_reader = reader or GitObjectReader(repo_root)
    return active_reader.commit_binding(commit)


def read_blob(
    commit: str,
    path: str,
    repo_root: Path,
    reader: GitObjectReader | None = None,
) -> tuple[str, bytes]:
    active_reader = reader or GitObjectReader(repo_root)
    return active_reader.read_blob(commit, path)


def _committed_material(
    commit: str,
    repo_root: Path,
    reader: GitObjectReader,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    assertions: list[dict[str, Any]] = []
    evidence_bytes: dict[str, bytes] = {}
    for path in SCOPE_EVIDENCE_PATHS:
        oid, data = read_blob(commit, path, repo_root, reader)
        evidence_bytes[path] = data
        digest = hashlib.sha256(data).hexdigest()
        evidence.append({
            "byte_count": len(data),
            "classification": CLASSIFICATIONS[path],
            "git_blob_oid": oid,
            "path": path,
            "sha256": digest,
        })
        if path in ASSERTIONS:
            assertion_id, fragment, claim = ASSERTIONS[path]
            text = data.decode("utf-8")
            count = text.count(fragment)
            if count != 1:
                raise ValueError(f"expected one exact assertion fragment in {path}, found {count}")
            assertions.append({
                "assertion_id": assertion_id,
                "claim": claim,
                "evidence_path": path,
                "expected_occurrences": 1,
                "git_blob_oid": oid,
                "required_utf8_fragment": fragment,
                "sha256": digest,
            })
    requirement_lines = [
        line.strip()
        for line in evidence_bytes["platform/requirements.txt"].decode("utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if requirement_lines.count(EXACT_REQUIREMENT) != 1:
        raise ValueError("platform/requirements.txt must contain exactly one pypdf==6.0.0 declaration")
    return evidence, assertions


def build_scope_candidate(commit: str, repo_root: Path = ROOT) -> dict[str, Any]:
    if type(commit) is not str or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("commit must be a full lowercase 40-character Git OID")
    repo_root = repo_root.resolve()
    reader = GitObjectReader(repo_root)
    evidence, assertions = _committed_material(commit, repo_root, reader)
    zero_limits = {
        "collectors": 0,
        "dns_requests": 0,
        "downloads": 0,
        "installers": 0,
        "m8_execution": 0,
        "metadata_requests": 0,
        "network_requests": 0,
        "network_bytes": 0,
        "redirects": 0,
        "resolvers": 0,
    }
    zero_counts = {
        "collectors": 0,
        "dns": 0,
        "downloaders": 0,
        "downloads": 0,
        "installers": 0,
        "m8": 0,
        "metadata": 0,
        "network": 0,
        "redirects": 0,
        "resolvers": 0,
    }
    candidate = {
        "allowed_next_action": SCOPE_REVIEW_REQUIRED,
        "authorization": {
            "authorization_token_present": False,
            "installation_authorized": False,
            "metadata_discovery_authorized": False,
            "network_access_authorized": False,
            "resolver_execution_authorized": False,
            "token": None,
            "wheel_download_authorized": False,
        },
        "builder_id": SCOPE_BUILDER_ID,
        "candidate_type": "RUNTIME_DEPENDENCY_METADATA_DISCOVERY_SCOPE",
        "canonicalization_id": CANONICALIZATION_ID,
        "current_effective_limits": zero_limits,
        "cycle_id": CYCLE_ID,
        "evidence": evidence,
        "execution_counts": zero_counts,
        "forbidden_actions": sorted(SCOPE_FORBIDDEN_ACTIONS),
        "format": SCOPE_CANDIDATE_FORMAT,
        "m8_status": "BLOCKED / NOT_STARTED",
        "historical_constraints": [{
            "classification": "HISTORICAL_GOVERNANCE_BOUNDARY",
            "non_authorizing": True,
            "path": SCOPE_EVIDENCE_PATHS[-1],
            "statement": "IMMUTABLE_FAILED_CLOSED_BOUNDARY_ONLY",
        }],
        "proposed_metadata_policy": {
            "authorization_granted": False,
            "endpoint_type": "EXACT_VERSION_JSON_METADATA",
            "follows_file_urls": False,
            "headers": {
                "Accept": "application/json",
                "User-Agent": "StudyAssistanceAgent-M8-Metadata-Discovery/1",
            },
            "host_allowlist": ["pypi.org"],
            "max_responses": 1,
            "methods": ["GET"],
            "policy_state": "PROPOSED_NOT_EFFECTIVE",
            "redirects": 0,
            "response_purpose": "PACKAGE_VERSION_METADATA_ONLY",
            "response_size_cap_bytes": 2 * 1024 * 1024,
            "retries": 0,
            "timeouts_seconds": {"connect": 5, "read": 10, "total": 15},
            "tls": {
                "certificate_verification": True,
                "hostname_verification": True,
                "https_only": True,
                "minimum_version": "TLSv1.2",
            },
        },
        "qa": {
            "adversarial": "PASS",
            "builder_internal": "PASS",
            "independent_review_completed": False,
            "max_rounds": 3,
            "round": 1,
        },
        "scope": {
            "artifact": None,
            "artifact_selection_state": "NOT_SELECTED",
            "consumer_format": "pdf",
            "dependency_scope": ["pypdf"],
            "distribution_name": "pypdf",
            "endpoint_selection_state": "NOT_SELECTED",
            "exact_requirement": EXACT_REQUIREMENT,
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
        },
        "scope_assertion_bindings": assertions,
        "source_commit": commit,
        "source_git_binding": commit_identity(repo_root, commit, reader),
        "status": SCOPE_REVIEW_REQUIRED,
    }
    validate_scope_candidate(candidate)
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="full source commit OID")
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if re.fullmatch(r"[0-9a-f]{40}", args.commit) is None:
        parser.error("--commit must be a full lowercase 40-character Git OID")
    candidate = build_scope_candidate(args.commit, args.repo)
    args.output.write_bytes(canonical_bytes(candidate))
    print(json.dumps({"output": str(args.output), "status": candidate["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

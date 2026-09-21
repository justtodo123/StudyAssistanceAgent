"""Validate and independently re-check an offline metadata-discovery candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from tools.m8_metadata_discovery_schema import (
        MetadataGovernanceError,
        canonical_bytes,
        parse_canonical_document,
        validate_candidate,
    )
except ImportError:  # pragma: no cover
    from m8_metadata_discovery_schema import (
        MetadataGovernanceError,
        canonical_bytes,
        parse_canonical_document,
        validate_candidate,
    )

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str, repo_root: Path) -> bytes:
    return subprocess.run(
        ["git", "--no-replace-objects", "--no-lazy-fetch", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        timeout=15,
    ).stdout


def validate_git_object(candidate: dict[str, Any], repo_root: Path) -> None:
    binding = candidate["git_binding"]
    commit = binding["commit"]
    actual_parent = git("rev-list", "--parents", "-n", "1", commit, repo_root=repo_root).decode("ascii").split()
    if actual_parent != [commit, binding["parent"]]:
        raise MetadataGovernanceError("commit parent binding mismatch")
    actual_tree = git("show", "-s", "--format=%T", commit, repo_root=repo_root).decode("ascii").strip()
    if actual_tree != binding["tree"]:
        raise MetadataGovernanceError("commit tree binding mismatch")
    for item in candidate["evidence"]:
        oid = git("rev-parse", f"{commit}:{item['path']}", repo_root=repo_root).decode("ascii").strip()
        if oid != item["git_blob_oid"]:
            raise MetadataGovernanceError(f"evidence blob binding mismatch: {item['path']}")
        data = git("cat-file", "blob", oid, repo_root=repo_root)
        if len(data) != item["byte_count"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise MetadataGovernanceError(f"evidence digest mismatch: {item['path']}")


def validate_review_package(candidate_bytes: bytes, repo_root: Path = ROOT) -> dict[str, Any]:
    candidate = parse_canonical_document(candidate_bytes)
    validate_candidate(candidate)
    validate_git_object(candidate, repo_root.resolve())
    if candidate["status"] != "METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED":
        raise MetadataGovernanceError("candidate must remain failed closed")
    if candidate["intent"]["selection_state"] != "UNRESOLVED":
        raise MetadataGovernanceError("review cannot select project intent")
    return {
        "canonicalization_id": candidate["canonicalization_id"],
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "decision": "METADATA_DISCOVERY_CANDIDATE_READY_FOR_EXTERNAL_INDEPENDENT_REVIEW",
        "execution_counts": candidate["execution_counts"],
        "status": candidate["status"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = validate_review_package(args.candidate.read_bytes(), args.repo)
    payload = canonical_bytes(report)
    if args.output:
        args.output.write_bytes(payload)
    else:
        print(payload.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

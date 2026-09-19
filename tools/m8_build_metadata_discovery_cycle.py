"""Build a Git-bound, offline-only M8 metadata-discovery governance candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from m8_metadata_discovery_schema import (
        CANONICALIZATION_ID,
        canonical_bytes,
        validate_candidate,
    )
except ImportError:  # pragma: no cover - supports package-style imports
    from tools.m8_metadata_discovery_schema import (
        CANONICALIZATION_ID,
        canonical_bytes,
        validate_candidate,
    )

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATHS = (
    "README.md",
    "package.json",
    "platform/app/main.py",
    "platform/requirements.txt",
    "platform/requirements-dev.txt",
    "docs/PLAN.md",
    "docs/plans/references/m8-network-acquisition-owner-failed-closed-decision-20260919-r03.md",
)
CLASSIFICATIONS = {
    "README.md": "PROJECT_DESCRIPTION",
    "package.json": "PRIVATE_TOOLING_METADATA",
    "platform/app/main.py": "API_PRESENTATION_METADATA",
    "platform/requirements.txt": "RUNTIME_DEPENDENCY_DECLARATION",
    "platform/requirements-dev.txt": "DEVELOPMENT_DEPENDENCY_DECLARATION",
    "docs/PLAN.md": "PROJECT_DESCRIPTION",
    "docs/plans/references/m8-network-acquisition-owner-failed-closed-decision-20260919-r03.md": "HISTORICAL_GOVERNANCE_BOUNDARY",
}


def git(*args: str, repo_root: Path = ROOT) -> bytes:
    """Read only a named Git object; never consult the worktree."""
    return subprocess.run(
        ["git", "--no-replace-objects", "--no-lazy-fetch", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        timeout=15,
    ).stdout


def commit_identity(repo_root: Path, commit: str) -> dict[str, str]:
    parent = git("rev-list", "--parents", "-n", "1", commit, repo_root=repo_root).decode("ascii").split()
    if len(parent) != 2:
        raise ValueError("source commit must have exactly one parent")
    tree = git("show", "-s", "--format=%T", commit, repo_root=repo_root).decode("ascii").strip()
    return {"commit": commit, "parent": parent[1], "tree": tree}


def read_blob(commit: str, path: str, repo_root: Path) -> tuple[str, bytes]:
    oid = git("rev-parse", f"{commit}:{path}", repo_root=repo_root).decode("ascii").strip()
    data = git("cat-file", "blob", oid, repo_root=repo_root)
    expected = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
    if expected != oid:
        raise ValueError(f"Git blob mismatch for {path}")
    return oid, data


def evidence(commit: str, repo_root: Path) -> list[dict[str, Any]]:
    items = []
    for path in EVIDENCE_PATHS:
        oid, data = read_blob(commit, path, repo_root)
        items.append({
            "byte_count": len(data),
            "classification": CLASSIFICATIONS[path],
            "git_blob_oid": oid,
            "path": path,
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return items


def build_candidate(commit: str, repo_root: Path = ROOT) -> dict[str, Any]:
    if type(commit) is not str or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("commit must be a full lowercase 40-character Git OID")
    candidate = {
        "allowed_next_action": "METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED",
        "authorization": {
            "authorization_token_present": False,
            "metadata_discovery_authorized": False,
            "token": None,
        },
        "canonicalization_id": CANONICALIZATION_ID,
        "current_effective_limits": {
            "downloads": 0,
            "dns_requests": 0,
            "installers": 0,
            "metadata_requests": 0,
            "network_requests": 0,
            "resolvers": 0,
        },
        "cycle_id": "m8-metadata-discovery-20260919-r01",
        "evidence": evidence(commit, repo_root),
        "execution_counts": {
            "collectors": 0,
            "dns": 0,
            "downloaders": 0,
            "downloads": 0,
            "installers": 0,
            "m8": 0,
            "metadata": 0,
            "network": 0,
            "resolvers": 0,
        },
        "forbidden_actions": [
            "network", "dns", "http", "https", "pypi", "metadata_request",
            "download", "resolver", "installation", "collector", "m8_execution",
        ],
        "format": "m8-metadata-discovery-candidate-v1",
        "git_binding": commit_identity(repo_root, commit),
        "intent": {
            "artifact": None,
            "metadata_url": None,
            "package_name": None,
            "selection_state": "UNRESOLVED",
            "version": None,
        },
        "proposed_discovery_limits": {
            "downloads": 0,
            "dns_requests": 0,
            "installers": 0,
            "metadata_requests": 0,
            "network_requests": 0,
            "resolvers": 0,
        },
        "qa": {
            "adversarial": "PASS",
            "builder_internal": "PASS",
            "max_rounds": 3,
            "round": 1,
        },
        "source_commit": commit,
        "status": "METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED",
    }
    validate_candidate(candidate)
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="full commit OID")
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        parser.error("--commit must be a full lowercase 40-character Git OID")
    candidate = build_candidate(args.commit, args.repo.resolve())
    args.output.write_bytes(canonical_bytes(candidate))
    print(json.dumps({"status": candidate["status"], "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

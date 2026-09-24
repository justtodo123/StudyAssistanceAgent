"""Fail-closed M11 candidate normalization orchestration.

This module deliberately stops before source lifecycle publication. It consumes only
caller-provided local bytes and frozen candidate evidence.
"""
from __future__ import annotations

import ast
import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .normalized_document import CHUNK_SCHEMA_VERSION, NormalizedDocument, normalize_document
from .parser_matrix import ParserMatrixError, parse_document, parser_availability
from .source_policy import IngestStatus, SourceType
from .source_registry import validate_user_source_id

_ALLOWED_CHUNK_SCHEMAS = {CHUNK_SCHEMA_VERSION}
_REQUIRED_SOURCES = {
    "mit-ocw-6-004-2017",
    "opendsa-main",
    "rfc-editor-index",
    "iana-registries",
}
_DIGEST_EVIDENCE = Path(__file__).resolve().parents[2] / "data" / "manifests" / "m11-p0-digest-evidence-v1.json"
_OPENDSA_PATH_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "manifests"
    / "sources"
    / "m11-opendsa-rst-paths-v1.json"
)
_FORMAT_BY_SUFFIX = {
    ".md": "md",
    ".txt": "txt",
    ".pdf": "pdf",
    ".csv": "txt",
    ".xml": "txt",
    ".rst": "txt",
}


class CandidatePipelineError(ValueError):
    """Raised when candidate input fails a fail-closed boundary."""


@dataclass(frozen=True, slots=True)
class CandidateResult:
    source_label: str
    source_id: str
    asset_id: str
    status: str
    document_id: str | None
    content_fingerprint: str | None
    normalized_path: str | None
    candidate_path: str | None
    rejected_path: str | None
    reason: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "source_label": self.source_label,
            "source_id": self.source_id,
            "asset_id": self.asset_id,
            "status": self.status,
            "document_id": self.document_id,
            "content_fingerprint": self.content_fingerprint,
            "normalized_path": self.normalized_path,
            "candidate_path": self.candidate_path,
            "rejected_path": self.rejected_path,
            "reason": self.reason,
            "ingest_status": (
                IngestStatus.CANDIDATE.value
                if self.status == "CANDIDATE"
                else IngestStatus.REJECTED.value
            ),
            "approved": False,
            "published": False,
        }


def load_digest_evidence(path: Path | None = None) -> Mapping[str, Any]:
    payload = _read_json(path or _DIGEST_EVIDENCE)
    if payload.get("status") != "DIGESTS_CAPTURED_CANDIDATE_PIPELINE_AUTHORIZED":
        raise CandidatePipelineError("digest evidence is not authorized for candidate pipeline")
    assets = payload.get("assets")
    if not isinstance(assets, list) or not assets:
        raise CandidatePipelineError("digest evidence assets are missing")
    return payload


def lookup_digest_asset(source_label: str, asset_id: str, path: Path | None = None) -> Mapping[str, Any]:
    payload = load_digest_evidence(path)
    matches = [
        item for item in payload["assets"]
        if item.get("source_id") == source_label and item.get("asset_id") == asset_id
    ]
    if len(matches) != 1:
        raise CandidatePipelineError("DIGEST_EVIDENCE_ASSET_NOT_FOUND")
    asset = matches[0]
    digest = asset.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise CandidatePipelineError("DIGEST_EVIDENCE_SHA256_INVALID")
    return asset


def lookup_opendsa_path_asset(
    source_label: str,
    asset_id: str,
    path: Path | None = None,
) -> Mapping[str, Any]:
    """Return pinned OpenDSA path metadata without treating a Git blob ID as SHA-256."""
    if source_label != "opendsa-main":
        raise CandidatePipelineError("DIGEST_EVIDENCE_ASSET_NOT_FOUND")
    payload = _read_json(path or _OPENDSA_PATH_MANIFEST)
    if payload.get("status") != "CANDIDATE_PIPELINE_AUTHORIZED":
        raise CandidatePipelineError("CANDIDATE_METADATA_ROOT_INVALID")
    if payload.get("source_id") != source_label:
        raise CandidatePipelineError("DIGEST_EVIDENCE_ASSET_NOT_FOUND")

    files = payload.get("files")
    revision = payload.get("revision")
    candidate_root = payload.get("candidate_root")
    if (
        not isinstance(files, list)
        or not files
        or payload.get("file_count") != len(files)
        or not isinstance(revision, str)
        or len(revision) != 40
        or any(char not in "0123456789abcdef" for char in revision)
        or candidate_root != "RST/en/"
    ):
        raise CandidatePipelineError("DIGEST_EVIDENCE_GIT_BLOB_INVALID")

    validated: dict[str, Mapping[str, Any]] = {}
    for item in files:
        item_path = item.get("path") if isinstance(item, Mapping) else None
        blob_sha = item.get("blob_sha") if isinstance(item, Mapping) else None
        size = item.get("size") if isinstance(item, Mapping) else None
        if not isinstance(item_path, str):
            raise CandidatePipelineError("DIGEST_EVIDENCE_GIT_BLOB_INVALID")
        try:
            safe_path = _safe_identifier(
                item_path,
                error_code="ASSET_ID_INVALID",
            )
        except CandidatePipelineError as exc:
            raise CandidatePipelineError("DIGEST_EVIDENCE_GIT_BLOB_INVALID") from exc
        if (
            safe_path in validated
            or not safe_path.startswith(candidate_root)
            or not safe_path.endswith(".rst")
            or not isinstance(blob_sha, str)
            or len(blob_sha) != 40
            or any(char not in "0123456789abcdef" for char in blob_sha)
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
        ):
            raise CandidatePipelineError("DIGEST_EVIDENCE_GIT_BLOB_INVALID")
        validated[safe_path] = item

    asset = validated.get(asset_id)
    if asset is None:
        raise CandidatePipelineError("DIGEST_EVIDENCE_ASSET_NOT_FOUND")
    return {
        "asset_id": asset_id,
        "source_id": source_label,
        "git_blob_sha1": asset["blob_sha"],
        "revision": revision,
        "candidate_root": candidate_root,
    }


def parser_status_for_candidates() -> dict[str, bool]:
    """Report M7 parser availability for every format the candidate pipeline may request."""
    formats = sorted({fmt for fmt in _FORMAT_BY_SUFFIX.values()})
    status = {fmt: parser_availability(fmt) for fmt in formats}
    if not status:
        raise CandidatePipelineError("candidate parser status set is empty")
    return status


def declared_format_for(asset_id: str, url: str | None = None) -> str:
    name = str(url or asset_id).replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix, fmt in _FORMAT_BY_SUFFIX.items():
        if name.endswith(suffix):
            return fmt
    raise CandidatePipelineError("DECLARED_FORMAT_UNSUPPORTED")


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidatePipelineError("CANDIDATE_METADATA_UNREADABLE") from exc
    if not isinstance(payload, Mapping):
        raise CandidatePipelineError("CANDIDATE_METADATA_ROOT_INVALID")
    return payload


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _candidate_source_id(source_label: str) -> str:
    """Derive a stable runtime-shaped ID without registering a source.

    The value is UUIDv7-shaped so M7 identity validators accept it, but every
    bit after the version/variant nibble is taken from a digest of the inventory
    label. Reruns of the same candidate therefore keep the same source_id
    without writing anything to the Source Registry.
    """
    digest = hashlib.sha256(source_label.encode("utf-8")).digest()
    timestamp_ms = int.from_bytes(digest[:6], "big") & ((1 << 48) - 1)
    random_a = int.from_bytes(digest[6:8], "big") & 0x0FFF
    random_b = int.from_bytes(digest[8:16], "big") & ((1 << 62) - 1)
    value = (timestamp_ms << 80) | (0x7 << 76) | (random_a << 64) | (0b10 << 62) | random_b
    return validate_user_source_id(f"user-{uuid.UUID(int=value)}")


def _safe_identifier(value: str, *, error_code: str, allow_path: bool = True) -> str:
    """Validate metadata used in artifact names and candidate identity."""
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise CandidatePipelineError(error_code)
    if value != value.strip() or any(ord(char) < 32 for char in value):
        raise CandidatePipelineError(error_code)
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    if not allow_path and len(parts) != 1:
        raise CandidatePipelineError(error_code)
    if normalized.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise CandidatePipelineError(error_code)
    if ":" in normalized:
        raise CandidatePipelineError(error_code)
    return normalized


def _safe_public_identifier(
    value: str,
    *,
    error_code: str,
    allow_path: bool = True,
) -> str:
    try:
        return _safe_identifier(
            value,
            error_code=error_code,
            allow_path=allow_path,
        )
    except CandidatePipelineError:
        return f"invalid-{hashlib.sha256(str(value).encode('utf-8', 'replace')).hexdigest()[:16]}"


def _artifact_name(source_label: str, asset_id: str) -> str:
    safe_source = _safe_identifier(
        source_label,
        error_code="SOURCE_LABEL_INVALID",
        allow_path=False,
    )
    safe_asset = _safe_identifier(asset_id, error_code="ASSET_ID_INVALID").replace("/", "__")
    return f"{safe_source}-{safe_asset}.json"


def _safe_reason(exc: Exception) -> str:
    """Return a stable rejection code without exposing exception details or paths."""
    if isinstance(exc, OSError):
        return "IO_ERROR"
    if isinstance(exc, CandidatePipelineError):
        known = {
            "CONTENT_DIGEST_MISMATCH",
            "SOURCE_PARSER_UNAVAILABLE",
            "EMPTY_NORMALIZED_DOCUMENT",
            "CHUNK_SCHEMA_NOT_ALLOWED",
            "DECLARED_FORMAT_UNSUPPORTED",
            "DIGEST_EVIDENCE_ASSET_NOT_FOUND",
            "DIGEST_EVIDENCE_SHA256_INVALID",
            "DIGEST_EVIDENCE_GIT_BLOB_INVALID",
            "CANDIDATE_METADATA_UNREADABLE",
            "CANDIDATE_METADATA_ROOT_INVALID",
            "CANDIDATE_RESULT_SET_EMPTY",
            "DUPLICATE_CANDIDATE_DOCUMENT_ID",
            "UNKNOWN_CANDIDATE_RESULT_STATUS",
            "SOURCE_NOT_ALLOWLISTED",
            "SOURCE_LABEL_INVALID",
            "ASSET_ID_INVALID",
        }
        code = str(exc)
        return code if code in known else "CANDIDATE_PIPELINE_ERROR"
    return "INVALID_CANDIDATE_INPUT"


def _write_rejection(root: Path, result: CandidateResult) -> str:
    root.mkdir(parents=True, exist_ok=True)
    path = root / _artifact_name(result.source_label, result.asset_id)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.as_posix()


def _write_candidate(
    root: Path,
    document: NormalizedDocument,
    result: CandidateResult,
    *,
    canonical_url: str | None,
    license_status: str = "review_required",
) -> str:
    root.mkdir(parents=True, exist_ok=True)
    path = root / _artifact_name(result.source_label, result.asset_id)
    chunks = list(document.chunks())
    payload = {
        "schema": "sa.m11.candidate.normalized.v1",
        "source_label": result.source_label,
        "source_id": document.source_id,
        "asset_id": result.asset_id,
        "canonical_url": canonical_url,
        "content_digest": result.content_fingerprint,
        "document": {
            "source_id": document.source_id,
            "document_id": document.document_id,
            "logical_uri": document.logical_uri,
            "format": document.format,
            "content_fingerprint": document.content_fingerprint,
            "chunk_count": len(chunks),
        },
        "chunks": [
            {
                "source_id": chunk.source_id,
                "document_id": chunk.document_id,
                "logical_uri": chunk.logical_uri,
                "chunk_key": chunk.chunk_key,
                "chunk_id": chunk.chunk_id,
                "chunk_schema": chunk.chunk_schema,
                "content_digest": hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
                "title": chunk.title,
                "unit_kind": chunk.unit_kind,
                "ordinal": chunk.ordinal,
            }
            for chunk in chunks
        ],
        "license_status": license_status,
        "ingest_status": IngestStatus.CANDIDATE.value,
        "source_type": SourceType.USER_REGISTERED.value,
        "approved": False,
        "published": False,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.as_posix()


def _normalize_candidate(
    *,
    source_label: str,
    asset_id: str,
    raw_path: str | Path,
    declared_format: str,
    expected_digest: str,
    normalized_root: str | Path,
    candidate_root: str | Path,
    rejected_root: str | Path,
    canonical_url: str | None = None,
    license_status: str = "review_required",
    raw_data: bytes | None = None,
) -> CandidateResult:
    """Hermetic normalization helper; public callers must use frozen evidence."""
    try:
        safe_source_label = _safe_identifier(
            source_label,
            error_code="SOURCE_LABEL_INVALID",
            allow_path=False,
        )
        safe_asset_id = _safe_identifier(asset_id, error_code="ASSET_ID_INVALID")
    except CandidatePipelineError as exc:
        reason = _safe_reason(exc)
        public_source = _safe_public_identifier(
            source_label,
            error_code="SOURCE_LABEL_INVALID",
            allow_path=False,
        )
        public_asset = _safe_public_identifier(
            asset_id,
            error_code="ASSET_ID_INVALID",
        )
        result = CandidateResult(
            public_source,
            "",
            public_asset,
            "REJECTED",
            None,
            None,
            None,
            None,
            None,
            reason,
        )
        rejected_path = _write_rejection(Path(rejected_root), result)
        return CandidateResult(
            public_source,
            "",
            public_asset,
            "REJECTED",
            None,
            None,
            None,
            None,
            Path(rejected_path).name,
            reason,
        )

    source_label = safe_source_label
    asset_id = safe_asset_id
    if source_label not in _REQUIRED_SOURCES:
        result = CandidateResult(
            source_label,
            "",
            asset_id,
            "REJECTED",
            None,
            None,
            None,
            None,
            None,
            "SOURCE_NOT_ALLOWLISTED",
        )
        rejected_path = _write_rejection(Path(rejected_root), result)
        return CandidateResult(
            source_label,
            "",
            asset_id,
            "REJECTED",
            None,
            None,
            None,
            None,
            Path(rejected_path).name,
            "SOURCE_NOT_ALLOWLISTED",
        )

    source_id = _candidate_source_id(source_label)
    path = Path(raw_path)
    try:
        data = raw_data if raw_data is not None else path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_digest:
            raise CandidatePipelineError("CONTENT_DIGEST_MISMATCH")
        if not parser_availability(declared_format):
            raise CandidatePipelineError("SOURCE_PARSER_UNAVAILABLE")
        parsed = parse_document(data, declared_format, filename=path.name)
        document = normalize_document(
            parsed,
            source_id=source_id,
            document_id=hashlib.sha256(
                f"{source_id}\0{asset_id}".encode("utf-8")
            ).hexdigest()[:32],
            logical_uri=asset_id,
            format=declared_format,
            content_fingerprint=digest,
            parser_id=parsed.parser_id,
            parser_version=parsed.parser_version,
        )
        chunks = document.chunks()
        if not chunks:
            raise CandidatePipelineError("EMPTY_NORMALIZED_DOCUMENT")
        schemas = {chunk.chunk_schema for chunk in chunks}
        if schemas != _ALLOWED_CHUNK_SCHEMAS:
            raise CandidatePipelineError("CHUNK_SCHEMA_NOT_ALLOWED")
        result = CandidateResult(
            source_label,
            source_id,
            asset_id,
            "CANDIDATE",
            document.document_id,
            digest,
            None,
            None,
            None,
            None,
        )
        artifact_name = _artifact_name(source_label, asset_id)
        normalized = Path(normalized_root) / artifact_name
        normalized.parent.mkdir(parents=True, exist_ok=True)
        normalized.write_bytes(document.canonical_bytes())
        _write_candidate(
            Path(candidate_root),
            document,
            result,
            canonical_url=canonical_url,
            license_status=license_status,
        )
        return CandidateResult(
            source_label,
            source_id,
            asset_id,
            "CANDIDATE",
            document.document_id,
            digest,
            artifact_name,
            artifact_name,
            None,
            None,
        )
    except ParserMatrixError as exc:
        reason = exc.code.value
    except (OSError, CandidatePipelineError, ValueError) as exc:
        reason = _safe_reason(exc)

    result = CandidateResult(
        source_label,
        source_id,
        asset_id,
        "REJECTED",
        None,
        locals().get("digest"),
        None,
        None,
        None,
        reason,
    )
    rejected_path = _write_rejection(Path(rejected_root), result)
    return CandidateResult(
        source_label,
        source_id,
        asset_id,
        "REJECTED",
        None,
        result.content_fingerprint,
        None,
        None,
        Path(rejected_path).name,
        reason,
    )


def summarize_candidate_results(results: list[CandidateResult]) -> dict[str, object]:
    """Return a privacy-safe candidate-only count report."""
    if not results:
        raise CandidatePipelineError("candidate result set is empty")
    document_ids = [item.document_id for item in results if item.document_id]
    if len(document_ids) != len(set(document_ids)):
        raise CandidatePipelineError("DUPLICATE_CANDIDATE_DOCUMENT_ID")
    report = {
        "schema": "sa.m11.candidate.report.v1",
        "asset_count": len(results),
        "candidate_count": sum(item.status == "CANDIDATE" for item in results),
        "rejected_count": sum(item.status == "REJECTED" for item in results),
        "approved_count": 0,
        "published_count": 0,
        "document_count": len(document_ids),
        "rejection_reasons": sorted({item.reason for item in results if item.reason}),
        "host_paths_included": False,
        "bodies_included": False,
    }
    if report["candidate_count"] + report["rejected_count"] != report["asset_count"]:
        raise CandidatePipelineError("UNKNOWN_CANDIDATE_RESULT_STATUS")
    return report


def assert_no_publication_or_replace_all() -> None:
    """Fail closed if this orchestration module grows a publication or replace_all path."""
    source = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(source):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    forbidden = {"publish", "replace_all", "complete_sync_run", "_activate_generation"}
    leaked = names & forbidden
    if leaked:
        raise CandidatePipelineError("candidate pipeline must not publish or replace_all")


def normalize_bound_candidate(
    *,
    source_label: str,
    asset_id: str,
    raw_path: str | Path,
    normalized_root: str | Path,
    candidate_root: str | Path,
    rejected_root: str | Path,
    digest_evidence_path: Path | None = None,
    opendsa_path_manifest_path: Path | None = None,
) -> CandidateResult:
    """Normalize a local file only if it matches frozen digest evidence."""
    try:
        safe_source_label = _safe_identifier(
            source_label,
            error_code="SOURCE_LABEL_INVALID",
            allow_path=False,
        )
        safe_asset_id = _safe_identifier(asset_id, error_code="ASSET_ID_INVALID")
        evidence_url: str | None = None
        raw_bytes: bytes | None = None
        if safe_source_label == "opendsa-main":
            evidence = lookup_opendsa_path_asset(
                safe_source_label,
                safe_asset_id,
                opendsa_path_manifest_path,
            )
            raw_bytes = Path(raw_path).read_bytes()
            if _git_blob_sha1(raw_bytes) != evidence["git_blob_sha1"]:
                raise CandidatePipelineError("CONTENT_DIGEST_MISMATCH")
            expected_digest = hashlib.sha256(raw_bytes).hexdigest()
        else:
            evidence = lookup_digest_asset(
                safe_source_label,
                safe_asset_id,
                digest_evidence_path,
            )
            evidence_url_value = evidence.get("url")
            evidence_url = evidence_url_value if isinstance(evidence_url_value, str) else None
            expected_digest = str(evidence["sha256"])
        declared_format = declared_format_for(safe_asset_id, evidence_url)
        return _normalize_candidate(
            source_label=safe_source_label,
            asset_id=safe_asset_id,
            raw_path=raw_path,
            declared_format=declared_format,
            expected_digest=expected_digest,
            normalized_root=normalized_root,
            candidate_root=candidate_root,
            rejected_root=rejected_root,
            canonical_url=evidence_url,
            raw_data=raw_bytes if safe_source_label == "opendsa-main" else None,
        )
    except (OSError, CandidatePipelineError) as exc:
        public_source = _safe_public_identifier(
            source_label,
            error_code="SOURCE_LABEL_INVALID",
            allow_path=False,
        )
        public_asset = _safe_public_identifier(
            asset_id,
            error_code="ASSET_ID_INVALID",
        )
        reason = _safe_reason(exc)
        result = CandidateResult(
            public_source,
            "",
            public_asset,
            "REJECTED",
            None,
            None,
            None,
            None,
            None,
            reason,
        )
        rejected_path = _write_rejection(Path(rejected_root), result)
        return CandidateResult(
            public_source,
            "",
            public_asset,
            "REJECTED",
            None,
            None,
            None,
            None,
            Path(rejected_path).name,
            reason,
        )


__all__ = [
    "CandidatePipelineError",
    "CandidateResult",
    "assert_no_publication_or_replace_all",
    "declared_format_for",
    "parser_status_for_candidates",
    "summarize_candidate_results",
    "load_digest_evidence",
    "lookup_digest_asset",
    "normalize_bound_candidate",
]

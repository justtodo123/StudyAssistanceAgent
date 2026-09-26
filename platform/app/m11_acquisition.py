"""Frozen-scope acquisition contracts for M11 P0.

The module provides deterministic asset resolution and a bounded fake-transport
boundary.  It does not perform network I/O itself and never writes lifecycle,
registry, index, or publication state.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .m11_execution_authority import ExecutionAuthority, ExecutionAuthorityError, assert_batch_authorized

ACQUISITION_SCHEMA = "sa.m11.acquisition-receipt.v1"
ACQUIRED = "ACQUIRED"
REFUSED = "REFUSED"
_ALLOWED_HOSTS = frozenset({
    "ocw.mit.edu", "www.rfc-editor.org", "www.iana.org",
    "github.com", "raw.githubusercontent.com",
})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_RECEIPT_FIELDS = frozenset({
    "schema", "status", "source_id", "asset_id", "canonical_url", "revision",
    "captured_at", "bytes", "sha256", "source_blob_sha1", "authority_id",
    "scope_digest", "refusal_code",
})


class AcquisitionError(ValueError):
    """A frozen-scope acquisition request or receipt was refused."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class FrozenAsset:
    source_id: str
    asset_id: str
    canonical_url: str
    revision: str
    sha256: str | None = None
    source_blob_sha1: str | None = None


@dataclass(frozen=True, slots=True)
class FetchResponse:
    final_url: str
    body: bytes


@dataclass(frozen=True, slots=True)
class AcquisitionReceipt:
    status: str
    source_id: str
    asset_id: str
    canonical_url: str
    revision: str
    captured_at: str
    bytes: int
    sha256: str | None
    source_blob_sha1: str | None
    authority_id: str
    scope_digest: str
    refusal_code: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": ACQUISITION_SCHEMA,
            "status": self.status,
            "source_id": self.source_id,
            "asset_id": self.asset_id,
            "canonical_url": self.canonical_url,
            "revision": self.revision,
            "captured_at": self.captured_at,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "source_blob_sha1": self.source_blob_sha1,
            "authority_id": self.authority_id,
            "scope_digest": self.scope_digest,
            "refusal_code": self.refusal_code,
        }


from typing import Any, NoReturn

def _fail(code: str) -> NoReturn:
    raise AcquisitionError(code)


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError("ACQUISITION_MANIFEST_UNREADABLE") from exc
    if not isinstance(value, Mapping):
        _fail("ACQUISITION_MANIFEST_INVALID")
    return value


def _host_allowed(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in _ALLOWED_HOSTS


def _digest_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _git_blob_sha1(body: bytes) -> str:
    return hashlib.sha1(f"blob {len(body)}\0".encode() + body).hexdigest()


def _asset_from_digest(record: Mapping[str, Any]) -> FrozenAsset:
    try:
        return FrozenAsset(
            source_id=str(record["source_id"]), asset_id=str(record["asset_id"]),
            canonical_url=str(record["url"]), revision=str(record["sha256"]),
            sha256=str(record["sha256"]),
        )
    except (KeyError, TypeError) as exc:
        raise AcquisitionError("ACQUISITION_MANIFEST_INVALID") from exc


def resolve_frozen_asset(repo_root: Path, source_id: str, asset_id: str) -> FrozenAsset:
    """Resolve an asset only from the committed P0 candidate/evidence manifests."""
    if source_id == "opendsa-main":
        manifest = _load_json(repo_root / "data/manifests/sources/m11-opendsa-rst-paths-v1.json")
        raw_files = manifest.get("files")
        if not isinstance(raw_files, list):
            _fail("ACQUISITION_MANIFEST_INVALID")
        for item in raw_files:
            if isinstance(item, Mapping) and item.get("path") == asset_id:
                revision_value = manifest.get("revision")
                if not isinstance(revision_value, str) or not revision_value:
                    _fail("ACQUISITION_MANIFEST_INVALID")
                blob_value = item.get("blob_sha")
                if not isinstance(blob_value, str) or not blob_value:
                    _fail("ACQUISITION_MANIFEST_INVALID")
                return FrozenAsset(
                    source_id=source_id, asset_id=asset_id,
                    canonical_url=f"https://raw.githubusercontent.com/OpenDSA/OpenDSA/{revision_value}/{asset_id}",
                    revision=revision_value, source_blob_sha1=blob_value,
                )
        _fail("ACQUISITION_ASSET_NOT_ALLOWLISTED")

    candidate = _load_json(repo_root / "data/manifests/sources/m11-p0-candidate-assets-v1.json")
    sources = candidate.get("sources")
    source = sources.get(source_id) if isinstance(sources, Mapping) else None
    if not isinstance(source, Mapping):
        _fail("ACQUISITION_SOURCE_NOT_ALLOWLISTED")
    records = source.get("assets") or source.get("candidate_rfcs") or source.get("candidate_registries")
    if not isinstance(records, list):
        _fail("ACQUISITION_MANIFEST_INVALID")
    for record in records:
        if not isinstance(record, Mapping):
            continue
        candidate_id = record.get("asset_id")
        url = record.get("url") or record.get("canonical_url")
        if candidate_id is None and "rfc" in record:
            candidate_id = f"rfc{record['rfc']}"
        if candidate_id is None and isinstance(record.get("name"), str):
            for ext in ("csv", "xml", "txt"):
                if asset_id == f"{record['name']}-{ext}" and isinstance(record.get(ext), str):
                    candidate_id = asset_id
                    url = record[ext]
                    break
        if candidate_id is None and "url" in record:
            candidate_id = str(record["url"]).rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if candidate_id == asset_id:
            if not isinstance(url, str):
                _fail("ACQUISITION_MANIFEST_INVALID")
            digest_manifest = _load_json(repo_root / "data/manifests/m11-p0-digest-evidence-v1.json")
            raw_evidence = digest_manifest.get("assets")
            if not isinstance(raw_evidence, list):
                _fail("ACQUISITION_MANIFEST_INVALID")
            for evidence in raw_evidence:
                if (
                    isinstance(evidence, Mapping)
                    and evidence.get("source_id") == source_id
                    and evidence.get("asset_id") == asset_id
                ):
                    return _asset_from_digest(evidence)
            _fail("ACQUISITION_EVIDENCE_MISSING")
    _fail("ACQUISITION_ASSET_NOT_ALLOWLISTED")


def resolve_authorized_assets(
    repo_root: Path,
    authority: ExecutionAuthority,
) -> dict[tuple[str, str], FrozenAsset]:
    """Resolve exactly the acquisition asset batch authorized by an authority."""
    if not isinstance(authority, ExecutionAuthority):
        _fail("ACQUISITION_AUTHORITY_INVALID")
    if authority.operation != "acquisition":
        _fail("ACQUISITION_AUTHORITY_INVALID")
    resolved: dict[tuple[str, str], FrozenAsset] = {}
    for source_id in authority.source_ids:
        for asset_id in sorted(authority.assets_for(source_id)):
            asset = resolve_frozen_asset(repo_root, source_id, asset_id)
            key = (source_id, asset_id)
            if key in resolved or (asset.source_id, asset.asset_id) != key:
                _fail("ACQUISITION_ASSET_MISMATCH")
            resolved[key] = asset
    if not resolved:
        _fail("ACQUISITION_BATCH_EMPTY")
    return dict(sorted(resolved.items()))


def validate_receipt(payload: Mapping[str, object]) -> AcquisitionReceipt:
    if not isinstance(payload, Mapping) or set(payload) != _RECEIPT_FIELDS:
        _fail("ACQUISITION_RECEIPT_FIELDS_INVALID")
    if any(key in payload for key in ("body", "content", "raw_path", "credentials", "token")):
        _fail("ACQUISITION_RECEIPT_PRIVACY_FIELD")
    if payload["schema"] != ACQUISITION_SCHEMA:
        _fail("ACQUISITION_RECEIPT_SCHEMA_INVALID")
    status = payload["status"]
    if status not in {ACQUIRED, REFUSED}:
        _fail("ACQUISITION_RECEIPT_STATUS_INVALID")
    for key in ("source_id", "asset_id", "canonical_url", "revision", "captured_at", "authority_id", "scope_digest"):
        if not isinstance(payload[key], str) or not payload[key]:
            _fail("ACQUISITION_RECEIPT_FIELDS_INVALID")
    if not _host_allowed(str(payload["canonical_url"])):
        _fail("ACQUISITION_URL_INVALID")
    if not isinstance(payload["bytes"], int) or isinstance(payload["bytes"], bool) or payload["bytes"] < 0:
        _fail("ACQUISITION_BYTE_COUNT_INVALID")
    for key, pattern in (("sha256", _SHA256), ("source_blob_sha1", _SHA1)):
        value = payload[key]
        if value is not None and (not isinstance(value, str) or not pattern.fullmatch(value)):
            _fail("ACQUISITION_DIGEST_INVALID")
    refusal = payload["refusal_code"]
    if status == ACQUIRED and refusal is not None:
        _fail("ACQUISITION_RECEIPT_STATUS_INVALID")
    if status == REFUSED and (not isinstance(refusal, str) or not refusal):
        _fail("ACQUISITION_RECEIPT_STATUS_INVALID")
    return AcquisitionReceipt(**{key: payload[key] for key in _RECEIPT_FIELDS if key != "schema"})  # type: ignore[arg-type]


def validate_receipt_for_asset(
    receipt: AcquisitionReceipt,
    asset: FrozenAsset,
) -> AcquisitionReceipt:
    """Bind a validated receipt to its frozen asset metadata and evidence."""
    if not isinstance(receipt, AcquisitionReceipt) or not isinstance(asset, FrozenAsset):
        _fail("ACQUISITION_RECEIPT_ASSET_INVALID")
    if (
        receipt.source_id != asset.source_id
        or receipt.asset_id != asset.asset_id
        or receipt.canonical_url != asset.canonical_url
        or receipt.revision != asset.revision
    ):
        _fail("ACQUISITION_RECEIPT_ASSET_MISMATCH")
    if receipt.status == ACQUIRED:
        if asset.sha256 is not None and receipt.sha256 != asset.sha256:
            _fail("ACQUISITION_RECEIPT_DIGEST_MISMATCH")
        if asset.source_blob_sha1 is not None and receipt.source_blob_sha1 != asset.source_blob_sha1:
            _fail("ACQUISITION_RECEIPT_BLOB_MISMATCH")
    return receipt


def validate_receipt_batch(
    receipts: Sequence[AcquisitionReceipt],
    assets: Mapping[tuple[str, str], FrozenAsset],
    *,
    authority: ExecutionAuthority | None = None,
) -> tuple[AcquisitionReceipt, ...]:
    """Validate a complete, duplicate-free receipt batch against frozen assets."""
    if not isinstance(receipts, Sequence) or not isinstance(assets, Mapping):
        _fail("ACQUISITION_RECEIPT_BATCH_INVALID")
    expected = set(assets)
    seen: set[tuple[str, str]] = set()
    validated: list[AcquisitionReceipt] = []
    authority_id = authority.authority_id if authority is not None else None
    scope = authority.scope_digest if authority is not None else None
    for receipt in receipts:
        if not isinstance(receipt, AcquisitionReceipt):
            _fail("ACQUISITION_RECEIPT_BATCH_INVALID")
        key = _receipt_key(receipt)
        if key not in expected:
            _fail("ACQUISITION_RECEIPT_OUT_OF_SCOPE")
        if key in seen:
            _fail("ACQUISITION_RECEIPT_DUPLICATE")
        if authority_id is not None and receipt.authority_id != authority_id:
            _fail("ACQUISITION_RECEIPT_AUTHORITY_MISMATCH")
        if scope is not None and receipt.scope_digest != scope:
            _fail("ACQUISITION_RECEIPT_SCOPE_MISMATCH")
        validate_receipt_for_asset(receipt, assets[key])
        seen.add(key)
        validated.append(receipt)
    if seen != expected:
        _fail("ACQUISITION_RECEIPT_BATCH_INCOMPLETE")
    return tuple(sorted(validated, key=_receipt_key))


def acquire_asset(
    asset: FrozenAsset,
    *,
    authority: ExecutionAuthority,
    transport: Callable[[str], FetchResponse],
    captured_at: datetime | None = None,
    max_bytes: int = 8 * 1024 * 1024,
) -> tuple[bytes | None, AcquisitionReceipt]:
    """Fetch one already-resolved asset through an injected bounded transport."""
    try:
        assert_batch_authorized(authority, {asset.source_id: [asset.asset_id]})
    except ExecutionAuthorityError as exc:
        return None, _refused(asset, authority, exc.code, captured_at)
    if not _host_allowed(asset.canonical_url):
        return None, _refused(asset, authority, "ACQUISITION_URL_INVALID", captured_at)
    try:
        response = transport(asset.canonical_url)
    except Exception:
        return None, _refused(asset, authority, "ACQUISITION_TRANSPORT_FAILED", captured_at)
    if not isinstance(response, FetchResponse) or not _host_allowed(response.final_url):
        return None, _refused(asset, authority, "ACQUISITION_REDIRECT_OUTSIDE_ALLOWLIST", captured_at)
    body = response.body
    if not isinstance(body, bytes) or len(body) > max_bytes:
        return None, _refused(asset, authority, "ACQUISITION_RESPONSE_TOO_LARGE", captured_at)
    sha256 = _digest_sha256(body)
    blob = _git_blob_sha1(body) if asset.source_blob_sha1 is not None else None
    if asset.sha256 is not None and sha256 != asset.sha256:
        return None, _refused(asset, authority, "ACQUISITION_DIGEST_MISMATCH", captured_at)
    if asset.source_blob_sha1 is not None and blob != asset.source_blob_sha1:
        return None, _refused(asset, authority, "ACQUISITION_GIT_BLOB_MISMATCH", captured_at)
    receipt = AcquisitionReceipt(ACQUIRED, asset.source_id, asset.asset_id, asset.canonical_url,
                                 asset.revision, _time(captured_at), len(body), sha256, blob,
                                 authority.authority_id, authority.scope_digest)
    validate_receipt(receipt.as_dict())
    validate_receipt_for_asset(receipt, asset)
    return body, receipt


def _time(value: datetime | None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat()


def _refused(asset: FrozenAsset, authority: ExecutionAuthority, code: str,
             captured_at: datetime | None) -> AcquisitionReceipt:
    receipt = AcquisitionReceipt(REFUSED, asset.source_id, asset.asset_id, asset.canonical_url,
                                asset.revision, _time(captured_at), 0, None, None,
                                authority.authority_id, authority.scope_digest, code)
    validate_receipt(receipt.as_dict())
    validate_receipt_for_asset(receipt, asset)
    return receipt


def bounded_https_transport(
    url: str,
    *,
    timeout: float = 20.0,
    max_bytes: int = 8 * 1024 * 1024,
) -> FetchResponse:
    """Fetch one allowlisted HTTPS URL with bounded timeout and response bytes."""
    if not _host_allowed(url):
        _fail("ACQUISITION_URL_INVALID")
    if timeout <= 0 or max_bytes <= 0:
        _fail("ACQUISITION_BOUNDS_INVALID")
    request = Request(url, headers={"User-Agent": "StudyAssistanceAgent-M11/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            if not _host_allowed(final_url):
                _fail("ACQUISITION_REDIRECT_OUTSIDE_ALLOWLIST")
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) > max_bytes:
                _fail("ACQUISITION_RESPONSE_TOO_LARGE")
            body = response.read(max_bytes + 1)
    except AcquisitionError:
        raise
    except (OSError, ValueError) as exc:
        raise AcquisitionError("ACQUISITION_TRANSPORT_FAILED") from exc
    if len(body) > max_bytes:
        _fail("ACQUISITION_RESPONSE_TOO_LARGE")
    return FetchResponse(final_url, body)


def write_raw_atomically(
    body: bytes,
    *,
    destination: Path,
    external_root: Path,
) -> Path:
    """Write verified raw bytes beneath an external root using atomic rename."""
    if not isinstance(body, bytes):
        _fail("ACQUISITION_RAW_INPUT_INVALID")
    target = _path_under_root(destination, external_root, invalid_code="ACQUISITION_RAW_PATH_INVALID")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    try:
        temporary.write_bytes(body)
        temporary.replace(target)
    except OSError as exc:
        raise AcquisitionError("ACQUISITION_RAW_WRITE_FAILED") from exc
    return target


def _path_under_root(path: Path, root: Path, *, invalid_code: str) -> Path:
    if not isinstance(path, Path) or not isinstance(root, Path):
        _fail(invalid_code)
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise AcquisitionError(invalid_code) from exc
    return resolved_path


def load_receipt(
    receipt_path: Path,
    *,
    receipt_root: Path | None = None,
) -> AcquisitionReceipt:
    """Load and validate one persisted receipt from the optional receipt root."""
    if not isinstance(receipt_path, Path):
        _fail("ACQUISITION_RECEIPT_PATH_INVALID")
    if receipt_root is not None:
        receipt_path = _path_under_root(
            receipt_path,
            receipt_root,
            invalid_code="ACQUISITION_RECEIPT_PATH_INVALID",
        )
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError("ACQUISITION_RECEIPT_INVALID") from exc
    try:
        return validate_receipt(payload)
    except AcquisitionError as exc:
        raise AcquisitionError("ACQUISITION_RECEIPT_INVALID") from exc


def _receipt_key(receipt: AcquisitionReceipt) -> tuple[str, str]:
    return receipt.source_id, receipt.asset_id


def load_receipts(receipt_root: Path) -> tuple[AcquisitionReceipt, ...]:
    """Load a deterministic, duplicate-free receipt set from an external root."""
    if not isinstance(receipt_root, Path):
        _fail("ACQUISITION_RECEIPT_PATH_INVALID")
    root = receipt_root.resolve()
    if not root.exists() or not root.is_dir():
        _fail("ACQUISITION_RECEIPT_ROOT_INVALID")
    loaded: list[AcquisitionReceipt] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(root.rglob("*.json")):
        try:
            receipt = load_receipt(path, receipt_root=root)
        except AcquisitionError as exc:
            raise AcquisitionError("ACQUISITION_RECEIPT_INVALID") from exc
        key = _receipt_key(receipt)
        if key in seen:
            _fail("ACQUISITION_RECEIPT_DUPLICATE")
        seen.add(key)
        loaded.append(receipt)
    return tuple(sorted(loaded, key=_receipt_key))


def persist_receipt(
    receipt: AcquisitionReceipt,
    *,
    receipt_path: Path,
    receipt_root: Path | None = None,
) -> Path:
    """Persist one validated receipt without overwriting a conflicting record."""
    if not isinstance(receipt_path, Path):
        _fail("ACQUISITION_RECEIPT_PATH_INVALID")
    if receipt_root is not None:
        receipt_path = _path_under_root(
            receipt_path,
            receipt_root,
            invalid_code="ACQUISITION_RECEIPT_PATH_INVALID",
        )
    payload = receipt.as_dict()
    validate_receipt(payload)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if receipt_path.exists():
        try:
            existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AcquisitionError("ACQUISITION_RECEIPT_CONFLICT") from exc
        if existing != payload:
            raise AcquisitionError("ACQUISITION_RECEIPT_CONFLICT")
        return receipt_path
    temporary = receipt_path.with_name(f".{receipt_path.name}.tmp")
    try:
        temporary.write_bytes(encoded)
        temporary.replace(receipt_path)
    except OSError as exc:
        raise AcquisitionError("ACQUISITION_RECEIPT_WRITE_FAILED") from exc
    return receipt_path


def acquire_and_store_asset(
    asset: FrozenAsset,
    *,
    authority: ExecutionAuthority,
    raw_path: Path,
    raw_root: Path,
    receipt_path: Path,
    receipt_root: Path | None = None,
    transport: Callable[[str], FetchResponse] = bounded_https_transport,
    captured_at: datetime | None = None,
    max_bytes: int = 8 * 1024 * 1024,
) -> AcquisitionReceipt:
    """Acquire, verify, atomically store raw bytes, and persist its receipt."""
    body, receipt = acquire_asset(
        asset,
        authority=authority,
        transport=transport,
        captured_at=captured_at,
        max_bytes=max_bytes,
    )
    if receipt_root is not None:
        receipt_path = _path_under_root(
            receipt_path,
            receipt_root,
            invalid_code="ACQUISITION_RECEIPT_PATH_INVALID",
        )
    if receipt_path.exists():
        try:
            existing = load_receipt(receipt_path, receipt_root=receipt_root)
        except AcquisitionError as exc:
            raise AcquisitionError("ACQUISITION_RECEIPT_CONFLICT") from exc
        if existing != receipt:
            raise AcquisitionError("ACQUISITION_RECEIPT_CONFLICT")
    if receipt.status == ACQUIRED:
        if body is None:
            _fail("ACQUISITION_BODY_MISSING")
        assert body is not None
        write_raw_atomically(body, destination=raw_path, external_root=raw_root)
    persist_receipt(receipt, receipt_path=receipt_path, receipt_root=receipt_root)
    return receipt


def acquire_authorized_batch(
    repo_root: Path,
    authority: ExecutionAuthority,
    *,
    raw_root: Path,
    receipt_root: Path,
    transport: Callable[[str], FetchResponse] = bounded_https_transport,
    captured_at: datetime | None = None,
    max_bytes: int = 8 * 1024 * 1024,
) -> tuple[AcquisitionReceipt, ...]:
    """Acquire one explicit authority batch without normalization or lifecycle mutation."""
    assets = resolve_authorized_assets(repo_root, authority)
    receipts: list[AcquisitionReceipt] = []
    for (source_id, asset_id), asset in assets.items():
        receipt = acquire_and_store_asset(
            asset,
            authority=authority,
            raw_path=raw_root / source_id / f"{asset_id}.raw",
            raw_root=raw_root,
            receipt_path=receipt_root / source_id / f"{asset_id}.json",
            receipt_root=receipt_root,
            transport=transport,
            captured_at=captured_at,
            max_bytes=max_bytes,
        )
        receipts.append(receipt)
    return validate_receipt_batch(receipts, assets, authority=authority)

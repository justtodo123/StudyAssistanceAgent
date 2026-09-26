from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.m11_acquisition import (
    ACQUIRED,
    REFUSED,
    AcquisitionError,
    FetchResponse,
    FrozenAsset,
    acquire_asset,
    acquire_authorized_batch,
    resolve_authorized_assets,
    resolve_frozen_asset,
    validate_receipt,
    validate_receipt_batch,
    validate_receipt_for_asset,
)
from app.m11_execution_authority import (
    ExecutionAuthority,
    scope_digest,
    validate_execution_authority,
)

pytestmark = pytest.mark.m11


def _authority(asset_id: str) -> ExecutionAuthority:
    source_ids = ["rfc-editor-index"]
    assets = {"rfc-editor-index": [asset_id]}
    digest = scope_digest({"sources": source_ids, "assets": assets, "version": 1})
    return validate_execution_authority({
        "schema": "sa.m11.execution-authority.v1", "operation": "acquisition",
        "authority_id": "authority-1", "issued_by": "owner",
        "issued_at": "2026-09-25T00:00:00Z", "expires_at": "2026-09-26T00:00:00Z",
        "scope_digest": digest, "source_ids": source_ids, "asset_ids": assets,
        "metadata_only": False, "publication_authorized": False, "status": "AUTHORIZED",
    }, operation="acquisition", expected_scope_digest=digest,
       now=datetime(2026, 9, 25, 12, tzinfo=timezone.utc))


from app.m11_acquisition import (
    FetchResponse,
    bounded_https_transport,
    persist_receipt,
    write_raw_atomically,
)

from app.m11_acquisition import acquire_and_store_asset

def test_resolve_frozen_rfc_asset(repo_root):
    asset = resolve_frozen_asset(repo_root, "rfc-editor-index", "rfc9110")
    assert asset.canonical_url == "https://www.rfc-editor.org/rfc/rfc9110.txt"
    assert asset.sha256 == "21c1cdce6ab0e5509b04d84a28000836c7a087cf786efe6f04877ebfff47232a"


def test_resolve_rejects_unallowlisted_asset(repo_root):
    with pytest.raises(AcquisitionError, match="ACQUISITION_ASSET_NOT_ALLOWLISTED"):
        resolve_frozen_asset(repo_root, "rfc-editor-index", "rfc1034-extra")


def test_acquire_validates_digest_and_returns_privacy_safe_receipt(repo_root):
    asset = resolve_frozen_asset(repo_root, "rfc-editor-index", "rfc9110")
    body = b"not the frozen RFC"
    received, receipt = acquire_asset(
        asset, authority=_authority("rfc9110"),
        transport=lambda url: FetchResponse(url, body),
        captured_at=datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
    )
    assert received is None
    assert receipt.status == REFUSED
    assert receipt.refusal_code == "ACQUISITION_DIGEST_MISMATCH"
    assert "body" not in receipt.as_dict()


def test_acquire_success_uses_injected_transport_and_no_path(tmp_path):
    body = b"candidate bytes"
    digest = hashlib.sha256(body).hexdigest()
    from app.m11_acquisition import FrozenAsset
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", digest, digest)
    received, receipt = acquire_asset(
        asset, authority=_authority("rfc9110"),
        transport=lambda url: FetchResponse(url, body),
    )
    assert received == body
    assert receipt.status == ACQUIRED
    assert receipt.bytes == len(body)
    assert validate_receipt(receipt.as_dict()) == receipt
    assert str(tmp_path) not in json_text(receipt.as_dict())


def test_acquire_refuses_redirect_and_oversize():
    from app.m11_acquisition import FrozenAsset
    body = b"candidate"
    digest = hashlib.sha256(body).hexdigest()
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", digest, digest)
    received, receipt = acquire_asset(asset, authority=_authority("rfc9110"),
                                      transport=lambda url: FetchResponse("https://evil.example/", body))
    assert received is None and receipt.refusal_code == "ACQUISITION_REDIRECT_OUTSIDE_ALLOWLIST"


def json_text(value):
    import json
    return json.dumps(value)


def test_raw_write_is_external_and_atomic(tmp_path):
    root = tmp_path / "external-raw"
    target = root / "source" / "asset.bin"
    result = write_raw_atomically(b"raw bytes", destination=target, external_root=root)
    assert result == target
    assert target.read_bytes() == b"raw bytes"
    assert not list(root.rglob("*.tmp"))


def test_raw_write_rejects_escape(tmp_path):
    with pytest.raises(AcquisitionError, match="ACQUISITION_RAW_PATH_INVALID"):
        write_raw_atomically(b"raw", destination=tmp_path / ".." / "escape.bin", external_root=tmp_path / "raw")


def test_receipt_persistence_is_idempotent_and_rejects_conflict(tmp_path):
    body = b"candidate bytes"
    digest = hashlib.sha256(body).hexdigest()
    from app.m11_acquisition import FrozenAsset, load_receipt
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", digest, digest)
    _, receipt = acquire_asset(asset, authority=_authority("rfc9110"), transport=lambda url: FetchResponse(url, body))
    root = tmp_path / "receipts"
    path = root / "rfc9110.json"
    assert persist_receipt(receipt, receipt_path=path, receipt_root=root) == path
    assert persist_receipt(receipt, receipt_path=path, receipt_root=root) == path
    assert load_receipt(path, receipt_root=root) == receipt
    changed = replace(receipt, revision="changed")
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_CONFLICT"):
        persist_receipt(changed, receipt_path=path, receipt_root=root)


def test_receipt_path_rejects_escape(tmp_path):
    body = b"candidate bytes"
    digest = hashlib.sha256(body).hexdigest()
    from app.m11_acquisition import FrozenAsset
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", digest, digest)
    _, receipt = acquire_asset(asset, authority=_authority("rfc9110"), transport=lambda url: FetchResponse(url, body))
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_PATH_INVALID"):
        persist_receipt(receipt, receipt_path=tmp_path / ".." / "escape.json", receipt_root=tmp_path / "receipts")


def test_malformed_receipt_does_not_write_raw(tmp_path):
    body = b"candidate bytes"
    digest = hashlib.sha256(body).hexdigest()
    from app.m11_acquisition import FrozenAsset
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", digest, digest)
    receipt_path = tmp_path / "receipts" / "rfc9110.json"
    receipt_path.parent.mkdir()
    receipt_path.write_text("{}", encoding="utf-8")
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_CONFLICT"):
        acquire_and_store_asset(
            asset,
            authority=_authority("rfc9110"),
            raw_path=tmp_path / "external" / "raw" / "rfc9110.txt",
            raw_root=tmp_path / "external" / "raw",
            receipt_path=receipt_path,
            receipt_root=tmp_path / "receipts",
            transport=lambda url: FetchResponse(url, body),
        )
    assert not (tmp_path / "external" / "raw" / "rfc9110.txt").exists()


def test_bounded_transport_rejects_unallowlisted_url():
    with pytest.raises(AcquisitionError, match="ACQUISITION_URL_INVALID"):
        bounded_https_transport("https://evil.example/")


def test_acquire_and_store_rejects_receipt_conflict_before_raw_write(tmp_path):
    body = b"candidate bytes"
    digest = hashlib.sha256(body).hexdigest()
    from app.m11_acquisition import FrozenAsset
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", digest, digest)
    receipt_path = tmp_path / "receipts" / "rfc9110.json"
    receipt_path.parent.mkdir()
    receipt_path.write_text("{}", encoding="utf-8")
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_CONFLICT"):
        acquire_and_store_asset(
            asset,
            authority=_authority("rfc9110"),
            raw_path=tmp_path / "external" / "raw" / "rfc9110.txt",
            raw_root=tmp_path / "external" / "raw",
            receipt_path=receipt_path,
            transport=lambda url: FetchResponse(url, body),
        )
    assert not (tmp_path / "external" / "raw" / "rfc9110.txt").exists()


def test_acquire_and_store_persists_verified_raw_and_receipt(tmp_path):
    body = b"stored candidate bytes"
    digest = hashlib.sha256(body).hexdigest()
    from app.m11_acquisition import FrozenAsset
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", digest, digest)
    receipt = acquire_and_store_asset(
        asset,
        authority=_authority("rfc9110"),
        raw_path=tmp_path / "external" / "raw" / "rfc9110.txt",
        raw_root=tmp_path / "external" / "raw",
        receipt_path=tmp_path / "receipts" / "rfc9110.json",
        transport=lambda url: FetchResponse(url, body),
    )
    assert receipt.status == ACQUIRED
    assert (tmp_path / "external" / "raw" / "rfc9110.txt").read_bytes() == body
    assert validate_receipt(__import__("json").loads((tmp_path / "receipts" / "rfc9110.json").read_text())) == receipt


def test_acquire_and_store_refusal_does_not_create_raw(tmp_path):
    from app.m11_acquisition import FrozenAsset
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", "f" * 64, "f" * 64)
    receipt = acquire_and_store_asset(
        asset,
        authority=_authority("rfc9110"),
        raw_path=tmp_path / "external" / "raw" / "rfc9110.txt",
        raw_root=tmp_path / "external" / "raw",
        receipt_path=tmp_path / "receipts" / "rfc9110.json",
        transport=lambda url: FetchResponse(url, b"wrong"),
    )
    assert receipt.status == REFUSED
    assert not (tmp_path / "external" / "raw" / "rfc9110.txt").exists()
    assert (tmp_path / "receipts" / "rfc9110.json").exists()


def test_load_receipts_is_sorted_and_rejects_duplicate_asset_revisions(tmp_path):
    body = b"candidate bytes"
    digest = hashlib.sha256(body).hexdigest()
    from app.m11_acquisition import FrozenAsset, load_receipts
    root = tmp_path / "receipts"
    asset = FrozenAsset("rfc-editor-index", "rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt", digest, digest)
    _, receipt = acquire_asset(asset, authority=_authority("rfc9110"), transport=lambda url: FetchResponse(url, body))
    persist_receipt(receipt, receipt_path=root / "nested" / "b.json", receipt_root=root)
    assert load_receipts(root) == (receipt,)
    persist_receipt(receipt, receipt_path=root / "a.json", receipt_root=root)
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_DUPLICATE"):
        load_receipts(root)


def test_load_receipts_rejects_malformed_json(tmp_path):
    root = tmp_path / "receipts"
    root.mkdir()
    (root / "bad.json").write_text("{}", encoding="utf-8")
    from app.m11_acquisition import load_receipts
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_INVALID"):
        load_receipts(root)


def _matching_receipt_and_asset():
    body = b"candidate bytes"
    digest = hashlib.sha256(body).hexdigest()
    asset = FrozenAsset(
        "rfc-editor-index",
        "rfc9110",
        "https://www.rfc-editor.org/rfc/rfc9110.txt",
        "rfc9110",
        digest,
        None,
    )
    _, receipt = acquire_asset(
        asset,
        authority=_authority("rfc9110"),
        transport=lambda url: FetchResponse(url, body),
    )
    return asset, receipt


def test_receipt_asset_linkage_rejects_revision_drift():
    asset, receipt = _matching_receipt_and_asset()
    drifted = replace(asset, revision="other-revision")
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_ASSET_MISMATCH"):
        validate_receipt_for_asset(receipt, drifted)


def test_receipt_asset_linkage_rejects_digest_drift():
    asset, receipt = _matching_receipt_and_asset()
    drifted = replace(asset, sha256="f" * 64)
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_DIGEST_MISMATCH"):
        validate_receipt_for_asset(receipt, drifted)


def test_receipt_batch_requires_exact_assets_and_authority():
    asset, receipt = _matching_receipt_and_asset()
    authority = _authority("rfc9110")
    assert validate_receipt_batch(
        [receipt],
        {(asset.source_id, asset.asset_id): asset},
        authority=authority,
    ) == (receipt,)
    other = replace(receipt, authority_id="other-authority")
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_AUTHORITY_MISMATCH"):
        validate_receipt_batch(
            [other],
            {(asset.source_id, asset.asset_id): asset},
            authority=authority,
        )


def test_receipt_batch_rejects_missing_and_unexpected_assets():
    asset, receipt = _matching_receipt_and_asset()
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_BATCH_INCOMPLETE"):
        validate_receipt_batch([], {(asset.source_id, asset.asset_id): asset})
    extra = replace(receipt, asset_id="rfc9999")
    with pytest.raises(AcquisitionError, match="ACQUISITION_RECEIPT_OUT_OF_SCOPE"):
        validate_receipt_batch(
            [extra],
            {(asset.source_id, asset.asset_id): asset},
        )



def _batch_authority(asset_ids: list[str]) -> ExecutionAuthority:
    source_ids = ["rfc-editor-index"]
    assets = {"rfc-editor-index": asset_ids}
    digest = scope_digest({"sources": source_ids, "assets": assets, "version": 1})
    return validate_execution_authority({
        "schema": "sa.m11.execution-authority.v1", "operation": "acquisition",
        "authority_id": "authority-batch", "issued_by": "owner",
        "issued_at": "2026-09-25T00:00:00Z", "expires_at": "2026-09-26T00:00:00Z",
        "scope_digest": digest, "source_ids": source_ids, "asset_ids": assets,
        "metadata_only": False, "publication_authorized": False, "status": "AUTHORIZED",
    }, operation="acquisition", expected_scope_digest=digest,
       now=datetime(2026, 9, 25, 12, tzinfo=timezone.utc))


def test_resolve_authorized_assets_is_exact_and_sorted(repo_root):
    authority = _batch_authority(["rfc9293", "rfc9110"])
    resolved = resolve_authorized_assets(repo_root, authority)
    assert list(resolved) == [
        ("rfc-editor-index", "rfc9110"),
        ("rfc-editor-index", "rfc9293"),
    ]
    assert set(resolved) == {("rfc-editor-index", "rfc9110"), ("rfc-editor-index", "rfc9293")}


def test_resolve_authorized_assets_rejects_empty_or_wrong_operation(repo_root):
    empty_authority = replace(_authority("rfc9110"), source_ids=("rfc-editor-index",), asset_ids=())
    with pytest.raises(AcquisitionError, match="ACQUISITION_BATCH_EMPTY"):
        resolve_authorized_assets(repo_root, empty_authority)
    authority = _authority("rfc9110")
    wrong = replace(authority, operation="gate0")
    with pytest.raises(AcquisitionError, match="ACQUISITION_AUTHORITY_INVALID"):
        resolve_authorized_assets(repo_root, wrong)


def test_acquire_authorized_batch_returns_exact_sorted_refusals(repo_root, tmp_path):
    bodies = {
        "https://www.rfc-editor.org/rfc/rfc9110.txt": b"rfc-9110",
        "https://www.rfc-editor.org/rfc/rfc9293.txt": b"rfc-9293",
    }
    authority = _batch_authority(["rfc9293", "rfc9110"])
    receipts = acquire_authorized_batch(
        repo_root,
        authority,
        raw_root=tmp_path / "raw",
        receipt_root=tmp_path / "receipts",
        transport=lambda url: FetchResponse(url, bodies[url]),
        captured_at=datetime(2026, 9, 25, 12, tzinfo=timezone.utc),
    )
    assert all(receipt.status == REFUSED for receipt in receipts)
    assert not list((tmp_path / "raw").rglob("*.raw"))
    assert [receipt.asset_id for receipt in receipts] == ["rfc9110", "rfc9293"]
    assert sorted(path.name for path in (tmp_path / "receipts" / "rfc-editor-index").glob("*.json")) == ["rfc9110.json", "rfc9293.json"]


def test_acquire_authorized_batch_refusal_receipts_are_idempotent(repo_root, tmp_path):
    authority = _batch_authority(["rfc9110"])
    transport = lambda url: FetchResponse(url, b"not-frozen")
    captured_at = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)
    first = acquire_authorized_batch(
        repo_root, authority, raw_root=tmp_path / "raw", receipt_root=tmp_path / "receipts",
        transport=transport, captured_at=captured_at,
    )
    second = acquire_authorized_batch(
        repo_root, authority, raw_root=tmp_path / "raw", receipt_root=tmp_path / "receipts",
        transport=transport, captured_at=captured_at,
    )
    assert first == second
    assert not (tmp_path / "raw" / "rfc-editor-index" / "rfc9110.raw").exists()

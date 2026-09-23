from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.generation_publication import candidate_generation
from app.knowledge_pack_manifest import (
    KnowledgePackManifest,
    KnowledgePackManifestCode,
    KnowledgePackManifestError,
    build_knowledge_pack_manifest,
)
from app.protocols import SourceChunk, SourceDescriptor, SourceIdentity, SourceType
from app.sources.markdown_pack import MarkdownPackSnapshot

pytestmark = pytest.mark.m10


def _snapshot(*, generation: str = "pack-generation-v1", reverse: bool = False) -> MarkdownPackSnapshot:
    descriptor = SourceDescriptor(
        source_id="knowledge-pack",
        source_type=SourceType.HUMAN_MARKDOWN,
        revision="revision-v1",
        fingerprint="f" * 64,
        generation=generation,
    )
    chunks = (
        SourceChunk(SourceIdentity("knowledge-pack", "os/process.md"), "h2:2", "SECRET BODY TWO"),
        SourceChunk(SourceIdentity("knowledge-pack", "os/process.md"), "h2:1", "SECRET BODY ONE"),
        SourceChunk(SourceIdentity("knowledge-pack", "ds/tree.md"), "h2:1", "SECRET TREE BODY"),
    )
    return MarkdownPackSnapshot(descriptor, tuple(reversed(chunks)) if reverse else chunks)


def test_the_same_pack_builds_byte_identical_canonical_manifests() -> None:
    first = build_knowledge_pack_manifest(_snapshot())
    second = build_knowledge_pack_manifest(_snapshot(reverse=True))

    assert first.document_count > 0
    assert first.chunk_count > 0
    assert first.manifest_digest == second.manifest_digest
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.canonical_bytes().startswith(b'{"canonicalization"')
    assert not first.canonical_bytes().startswith(b"\xef\xbb\xbf")


def test_the_manifest_reuses_the_existing_pack_identity() -> None:
    snapshot = _snapshot()
    manifest = build_knowledge_pack_manifest(snapshot)
    source = manifest.to_dict()["source"]

    assert source == {
        "source_id": snapshot.descriptor.source_id,
        "source_type": snapshot.descriptor.source_type.value,
        "revision": snapshot.descriptor.revision,
        "fingerprint": snapshot.descriptor.fingerprint,
        "generation": snapshot.descriptor.generation,
    }
    assert source["generation"] != candidate_generation(manifest.manifest_digest)


def test_an_identity_change_changes_only_the_pack_manifest_digest() -> None:
    first = build_knowledge_pack_manifest(_snapshot(generation="pack-generation-v1"))
    second = build_knowledge_pack_manifest(_snapshot(generation="pack-generation-v2"))

    assert first.manifest_digest != second.manifest_digest
    assert first.documents == second.documents


def test_the_manifest_round_trips_and_checks_its_digest() -> None:
    manifest = build_knowledge_pack_manifest(_snapshot())
    payload = json.loads(manifest.canonical_bytes())

    rebuilt = KnowledgePackManifest.from_dict(payload)

    assert rebuilt == manifest
    assert rebuilt.canonical_bytes() == manifest.canonical_bytes()

    payload["integrity"]["digest"] = "0" * 64
    with pytest.raises(KnowledgePackManifestError) as error:
        KnowledgePackManifest.from_dict(payload)
    assert error.value.code is KnowledgePackManifestCode.DIGEST_MISMATCH


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda payload: payload.update(schema_version=2), KnowledgePackManifestCode.SCHEMA_UNSUPPORTED),
        (lambda payload: payload.update(extra=True), KnowledgePackManifestCode.INVALID),
        (lambda payload: payload.pop("inventory"), KnowledgePackManifestCode.INVALID),
        (
            lambda payload: payload["inventory"].update(document_count=999),
            KnowledgePackManifestCode.IDENTITY_CONFLICT,
        ),
    ],
)
def test_malformed_or_unsupported_manifests_fail_closed(mutation, code) -> None:
    payload = json.loads(build_knowledge_pack_manifest(_snapshot()).canonical_bytes())
    mutation(payload)

    with pytest.raises(KnowledgePackManifestError) as error:
        KnowledgePackManifest.from_dict(payload)
    assert error.value.code is code


def test_duplicate_inventory_identities_fail_closed() -> None:
    payload = json.loads(build_knowledge_pack_manifest(_snapshot()).canonical_bytes())
    payload["inventory"]["documents"].append(payload["inventory"]["documents"][0])
    payload["inventory"]["document_count"] += 1

    with pytest.raises(KnowledgePackManifestError) as error:
        KnowledgePackManifest.from_dict(payload)
    assert error.value.code is KnowledgePackManifestCode.IDENTITY_CONFLICT


def test_the_manifest_contains_metadata_not_paths_credentials_or_content(tmp_path) -> None:
    manifest = build_knowledge_pack_manifest(_snapshot())
    encoded = manifest.canonical_bytes()

    assert manifest.document_count > 0
    for forbidden in (
        str(tmp_path).encode(),
        b"SECRET BODY",
        b"SECRET TREE BODY",
        b"token",
        b"password",
        b"created_at",
        b"sqlite",
        b"lancedb",
        b"qdrant",
    ):
        assert forbidden.lower() not in encoded.lower()


def test_forged_inventory_identities_are_rejected_even_with_a_recomputed_digest() -> None:
    import hashlib

    from app.source_manifest import canonical_json

    payload = json.loads(build_knowledge_pack_manifest(_snapshot()).canonical_bytes())
    document = payload["inventory"]["documents"][0]
    document["document_id"] = "0" * 32
    document["chunks"][0]["chunk_id"] = "1" * 32
    unsigned = dict(payload)
    unsigned.pop("integrity")
    payload["integrity"]["digest"] = hashlib.sha256(canonical_json(unsigned)).hexdigest()

    with pytest.raises(KnowledgePackManifestError) as error:
        KnowledgePackManifest.from_dict(payload)
    assert error.value.code is KnowledgePackManifestCode.IDENTITY_CONFLICT


def test_building_a_manifest_does_not_mutate_snapshot_or_identity() -> None:
    snapshot = _snapshot()
    before = replace(snapshot.descriptor)
    chunk_ids = tuple(chunk.chunk_id for chunk in snapshot.chunks)

    build_knowledge_pack_manifest(snapshot)

    assert snapshot.descriptor == before
    assert tuple(chunk.chunk_id for chunk in snapshot.chunks) == chunk_ids

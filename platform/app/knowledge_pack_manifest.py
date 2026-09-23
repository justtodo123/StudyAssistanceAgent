"""Canonical, content-free manifest for one materialized knowledge pack.

The manifest describes an existing ``MarkdownPackSnapshot``.  It deliberately
reuses the snapshot's source and generation identity instead of minting a
parallel publication identity.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from .protocols import (
    ProtocolValidationError,
    SourceDescriptor,
    logical_chunk_id,
    logical_document_id,
    normalize_logical_uri,
)
from .source_manifest import canonical_json
from .sources.markdown_pack import MarkdownPackSnapshot
from .tool_registry import PREVIEW_TOOL_ALLOWLIST

SCHEMA_NAME = "sa.knowledge-pack.manifest.v1"
SCHEMA_VERSION = 1
CANONICALIZATION = "sa-json-c14n-v1"
PROVENANCE_POLICY = "logical-identities-only"
COMPATIBILITY_POLICY = "manifest-does-not-alter-learning-state-v1"
SIGNATURE_POLICY = "unsigned-sha256"

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_name",
        "schema_version",
        "canonicalization",
        "source",
        "inventory",
        "capabilities",
        "policies",
        "integrity",
    }
)
_SOURCE_KEYS = frozenset({"source_id", "source_type", "revision", "fingerprint", "generation"})
_INVENTORY_KEYS = frozenset({"documents", "document_count", "chunk_count"})
_DOCUMENT_KEYS = frozenset({"document_id", "logical_uri", "chunks"})
_CHUNK_KEYS = frozenset({"chunk_id", "chunk_key", "chunk_schema"})
_POLICY_KEYS = frozenset({"provenance", "compatibility", "signature"})
_INTEGRITY_KEYS = frozenset({"algorithm", "digest"})


class KnowledgePackManifestCode(StrEnum):
    INVALID = "KNOWLEDGE_PACK_MANIFEST_INVALID"
    SCHEMA_UNSUPPORTED = "KNOWLEDGE_PACK_MANIFEST_SCHEMA_UNSUPPORTED"
    IDENTITY_CONFLICT = "KNOWLEDGE_PACK_MANIFEST_IDENTITY_CONFLICT"
    DIGEST_MISMATCH = "KNOWLEDGE_PACK_MANIFEST_DIGEST_MISMATCH"


class KnowledgePackManifestError(ValueError):
    """Stable, content-free validation failure."""

    def __init__(self, code: KnowledgePackManifestCode) -> None:
        super().__init__("The knowledge-pack manifest is invalid.")
        self.code = code


@dataclass(frozen=True, slots=True)
class PackChunkEntry:
    chunk_id: str
    chunk_key: str
    chunk_schema: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value for value in (self.chunk_id, self.chunk_key, self.chunk_schema)):
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)

    def to_dict(self) -> dict[str, str]:
        return {
            "chunk_id": self.chunk_id,
            "chunk_key": self.chunk_key,
            "chunk_schema": self.chunk_schema,
        }


@dataclass(frozen=True, slots=True)
class PackDocumentEntry:
    document_id: str
    logical_uri: str
    chunks: tuple[PackChunkEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.document_id, str) or not self.document_id:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)
        try:
            uri = normalize_logical_uri(self.logical_uri)
        except ValueError as exc:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID) from exc
        entries = tuple(self.chunks)
        if not entries or any(not isinstance(entry, PackChunkEntry) for entry in entries):
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)
        ids = [entry.chunk_id for entry in entries]
        keys = [entry.chunk_key for entry in entries]
        if len(ids) != len(set(ids)) or len(keys) != len(set(keys)):
            raise KnowledgePackManifestError(KnowledgePackManifestCode.IDENTITY_CONFLICT)
        object.__setattr__(self, "logical_uri", uri)
        object.__setattr__(self, "chunks", tuple(sorted(entries, key=lambda entry: entry.chunk_id)))

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "logical_uri": self.logical_uri,
            "chunks": [entry.to_dict() for entry in self.chunks],
        }


@dataclass(frozen=True, slots=True)
class KnowledgePackManifest:
    descriptor: SourceDescriptor
    documents: tuple[PackDocumentEntry, ...]
    capabilities: tuple[str, ...]
    manifest_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.descriptor, SourceDescriptor):
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)
        documents = tuple(self.documents)
        if not documents or any(not isinstance(document, PackDocumentEntry) for document in documents):
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)
        for document in documents:
            try:
                expected_document_id = logical_document_id(
                    self.descriptor.source_id, document.logical_uri
                )
                if document.document_id != expected_document_id:
                    raise KnowledgePackManifestError(KnowledgePackManifestCode.IDENTITY_CONFLICT)
                for chunk in document.chunks:
                    expected_chunk_id = logical_chunk_id(
                        document.document_id, chunk.chunk_key, chunk.chunk_schema
                    )
                    if chunk.chunk_id != expected_chunk_id:
                        raise KnowledgePackManifestError(KnowledgePackManifestCode.IDENTITY_CONFLICT)
            except ProtocolValidationError as exc:
                raise KnowledgePackManifestError(KnowledgePackManifestCode.IDENTITY_CONFLICT) from exc
        document_ids = [document.document_id for document in documents]
        logical_uris = [document.logical_uri.casefold() for document in documents]
        if len(document_ids) != len(set(document_ids)) or len(logical_uris) != len(set(logical_uris)):
            raise KnowledgePackManifestError(KnowledgePackManifestCode.IDENTITY_CONFLICT)
        capabilities = tuple(sorted(set(self.capabilities)))
        if not capabilities or any(name not in PREVIEW_TOOL_ALLOWLIST for name in capabilities):
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)
        object.__setattr__(self, "documents", tuple(sorted(documents, key=lambda item: item.document_id)))
        object.__setattr__(self, "capabilities", capabilities)
        digest = hashlib.sha256(canonical_json(self.to_dict(include_digest=False))).hexdigest()
        object.__setattr__(self, "manifest_digest", digest)

    @property
    def document_count(self) -> int:
        return len(self.documents)

    @property
    def chunk_count(self) -> int:
        return sum(len(document.chunks) for document in self.documents)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "canonicalization": CANONICALIZATION,
            "source": {
                "source_id": self.descriptor.source_id,
                "source_type": self.descriptor.source_type.value,
                "revision": self.descriptor.revision,
                "fingerprint": self.descriptor.fingerprint,
                "generation": self.descriptor.generation,
            },
            "inventory": {
                "documents": [document.to_dict() for document in self.documents],
                "document_count": self.document_count,
                "chunk_count": self.chunk_count,
            },
            "capabilities": list(self.capabilities),
            "policies": {
                "provenance": PROVENANCE_POLICY,
                "compatibility": COMPATIBILITY_POLICY,
                "signature": SIGNATURE_POLICY,
            },
        }
        if include_digest:
            result["integrity"] = {"algorithm": "sha256", "digest": self.manifest_digest}
        return result

    def canonical_bytes(self) -> bytes:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "KnowledgePackManifest":
        if not isinstance(payload, Mapping) or frozenset(payload) != _TOP_LEVEL_KEYS:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)
        if payload.get("schema_name") != SCHEMA_NAME or payload.get("schema_version") != SCHEMA_VERSION:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.SCHEMA_UNSUPPORTED)
        if payload.get("canonicalization") != CANONICALIZATION:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.SCHEMA_UNSUPPORTED)

        source = _mapping(payload.get("source"), _SOURCE_KEYS)
        inventory = _mapping(payload.get("inventory"), _INVENTORY_KEYS)
        policies = _mapping(payload.get("policies"), _POLICY_KEYS)
        integrity = _mapping(payload.get("integrity"), _INTEGRITY_KEYS)
        if policies != {
            "provenance": PROVENANCE_POLICY,
            "compatibility": COMPATIBILITY_POLICY,
            "signature": SIGNATURE_POLICY,
        }:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.SCHEMA_UNSUPPORTED)
        if integrity.get("algorithm") != "sha256":
            raise KnowledgePackManifestError(KnowledgePackManifestCode.SCHEMA_UNSUPPORTED)

        try:
            from .protocols import SourceType

            descriptor = SourceDescriptor(
                source_id=source["source_id"],
                source_type=SourceType(source["source_type"]),
                revision=source["revision"],
                fingerprint=source["fingerprint"],
                generation=source["generation"],
            )
            raw_documents = inventory["documents"]
            raw_capabilities = payload["capabilities"]
            if not isinstance(raw_documents, list) or not isinstance(raw_capabilities, list):
                raise TypeError
            documents = tuple(_document_from_dict(item) for item in raw_documents)
            manifest = cls(descriptor, documents, tuple(raw_capabilities))
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, KnowledgePackManifestError):
                raise
            raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID) from exc

        if inventory.get("document_count") != manifest.document_count or inventory.get("chunk_count") != manifest.chunk_count:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.IDENTITY_CONFLICT)
        if integrity.get("digest") != manifest.manifest_digest:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.DIGEST_MISMATCH)
        return manifest


def _mapping(value: object, keys: frozenset[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or frozenset(value) != keys:
        raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)
    return dict(value)


def _document_from_dict(value: object) -> PackDocumentEntry:
    document = _mapping(value, _DOCUMENT_KEYS)
    chunks = document["chunks"]
    if not isinstance(chunks, list):
        raise KnowledgePackManifestError(KnowledgePackManifestCode.INVALID)
    entries: list[PackChunkEntry] = []
    for value in chunks:
        entry = _mapping(value, _CHUNK_KEYS)
        entries.append(PackChunkEntry(entry["chunk_id"], entry["chunk_key"], entry["chunk_schema"]))
    return PackDocumentEntry(document["document_id"], document["logical_uri"], tuple(entries))


def build_knowledge_pack_manifest(
    snapshot: MarkdownPackSnapshot,
    *,
    capabilities: tuple[str, ...] = tuple(sorted(PREVIEW_TOOL_ALLOWLIST)),
) -> KnowledgePackManifest:
    """Build a deterministic metadata-only manifest from a materialized pack."""
    documents: dict[str, list[PackChunkEntry]] = {}
    identities: dict[str, tuple[str, str]] = {}
    for chunk in snapshot.chunks:
        identity = chunk.identity
        previous = identities.setdefault(identity.document_id, (identity.source_id, identity.logical_uri))
        if previous != (identity.source_id, identity.logical_uri) or identity.source_id != snapshot.descriptor.source_id:
            raise KnowledgePackManifestError(KnowledgePackManifestCode.IDENTITY_CONFLICT)
        documents.setdefault(identity.document_id, []).append(
            PackChunkEntry(chunk.chunk_id, chunk.chunk_key, chunk.chunk_schema)
        )
    entries = tuple(
        PackDocumentEntry(document_id, identities[document_id][1], tuple(chunks))
        for document_id, chunks in documents.items()
    )
    return KnowledgePackManifest(snapshot.descriptor, entries, capabilities)


def validate_knowledge_pack_manifest(payload: Mapping[str, Any]) -> KnowledgePackManifest:
    return KnowledgePackManifest.from_dict(payload)


__all__ = [
    "CANONICALIZATION",
    "SCHEMA_NAME",
    "SCHEMA_VERSION",
    "KnowledgePackManifest",
    "KnowledgePackManifestCode",
    "KnowledgePackManifestError",
    "PackChunkEntry",
    "PackDocumentEntry",
    "build_knowledge_pack_manifest",
    "validate_knowledge_pack_manifest",
]

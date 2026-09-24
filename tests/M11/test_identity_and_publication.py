from __future__ import annotations

import hashlib

import pytest

from app.generation_publication import GenerationCandidate, GenerationGate, manifest_digest
from app.normalized_document import CHUNK_SCHEMA_VERSION
from app.protocols import logical_chunk_id, logical_document_id

pytestmark = pytest.mark.m11


def test_chunk_identity_reuses_protocol_helpers():
    source_id = "m11-source"
    logical_uri = "docs/example.md"
    chunk_key = "section-1"
    document_id = logical_document_id(source_id, logical_uri)

    expected_document_id = hashlib.sha256(
        f"{source_id}\0{logical_uri}".encode("utf-8")
    ).hexdigest()[:32]
    expected_chunk_id = hashlib.sha256(
        f"{document_id}\0{chunk_key}\0{CHUNK_SCHEMA_VERSION}".encode("utf-8")
    ).hexdigest()[:32]

    assert document_id == expected_document_id
    assert logical_chunk_id(document_id, chunk_key, CHUNK_SCHEMA_VERSION) == expected_chunk_id


def test_candidate_is_not_visible_before_publication(tmp_path):
    gate = GenerationGate(tmp_path)
    units = ["chunk-1", "chunk-2"]
    candidate = GenerationCandidate("m11-source", manifest_digest(units), len(units))
    gate.stage(candidate, units)
    assert gate.visible("m11-source") is None
    assert gate.visible_unit_count("m11-source") == 0

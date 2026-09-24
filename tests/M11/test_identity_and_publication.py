from __future__ import annotations

import pytest

from app.generation_publication import GenerationCandidate, GenerationGate, manifest_digest
from app.protocols import logical_chunk_id, logical_document_id

pytestmark = pytest.mark.m11


def test_chunk_identity_reuses_protocol_helpers():
    document_id = logical_document_id("m11-source", "docs/example.md")
    assert logical_chunk_id(document_id, "section-1") == logical_chunk_id(document_id, "section-1")


def test_candidate_is_not_visible_before_publication(tmp_path):
    gate = GenerationGate(tmp_path)
    units = ["chunk-1", "chunk-2"]
    candidate = GenerationCandidate("m11-source", manifest_digest(units), len(units))
    gate.stage(candidate, units)
    assert gate.visible("m11-source") is None
    assert gate.visible_unit_count("m11-source") == 0

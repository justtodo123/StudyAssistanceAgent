"""Pure constants and identity rules for serialized M11 candidate artifacts."""

from __future__ import annotations

import hashlib
import uuid


CANDIDATE_ARTIFACT_SCHEMA = "sa.m11.candidate.normalized.v1"


def candidate_source_id_for_label(source_label: str) -> str:
    """Derive the stable UUIDv7-shaped source ID used by candidate artifacts."""
    digest = hashlib.sha256(source_label.encode("utf-8")).digest()
    timestamp_ms = int.from_bytes(digest[:6], "big") & ((1 << 48) - 1)
    random_a = int.from_bytes(digest[6:8], "big") & 0x0FFF
    random_b = int.from_bytes(digest[8:16], "big") & ((1 << 62) - 1)
    value = (
        (timestamp_ms << 80)
        | (0x7 << 76)
        | (random_a << 64)
        | (0b10 << 62)
        | random_b
    )
    return f"user-{uuid.UUID(int=value)}"

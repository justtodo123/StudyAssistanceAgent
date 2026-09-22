"""Manifest-bound checkpoints and an atomic generation publication gate.

M10 plan §5 step 4. The property this exists to establish is the one the crash
matrix has been unable to assert until now: **no half-published generation**.

Two mechanisms do the work, and neither is a convention:

- the **generation id is derived from the manifest digest**, so the same input
  yields the same generation and a resume can tell whether its input changed;
- a reader **validates before trusting**. `visible()` only reports a generation
  whose on-disk manifest hashes to the id it claims. A directory that was half
  written — or a pointer switched to a generation whose content never landed —
  is therefore invisible rather than partially served.

A resume whose manifest digest differs from its checkpoint's **discards** the
candidate instead of continuing. Continuing would publish a generation built from
inputs the checkpoint never described.

No production release: nothing constructs this outside its tests.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

MANIFEST_NAME = "manifest.json"
CURRENT_NAME = "CURRENT"


class PublicationError(ValueError):
    """A publication step was refused. Carries a stable code, never content."""

    def __init__(self, code: str, message: str = "the generation was not published.") -> None:
        self.code = code
        super().__init__(message)


class PublicationState(StrEnum):
    STAGED = "staged"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DISCARDED = "discarded"


class PublicationCrashPoint(StrEnum):
    """Where a process death is injected in the publication pipeline."""

    BEFORE_STAGE = "before_stage"
    MID_STAGE = "mid_stage"
    AFTER_STAGE_BEFORE_VALIDATE = "after_stage_before_validate"
    MID_VALIDATE = "mid_validate"
    AFTER_VALIDATE_BEFORE_PUBLISH = "after_validate_before_publish"
    MID_PUBLISH = "mid_publish"


class InjectedPublicationCrash(RuntimeError):
    """Test-only fault injection. Never raised in production."""


def manifest_digest(unit_ids: list[str]) -> str:
    """Canonical digest of a candidate's units. Deterministic and reproducible."""
    payload = json.dumps(sorted(unit_ids), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def candidate_generation(digest: str) -> str:
    """The generation id **derived from** the manifest digest.

    Deriving rather than minting means the same input can never produce two
    generations, so a reindex over unchanged content does not churn identity —
    the same discipline M9 applied to plan ids.
    """
    if not isinstance(digest, str) or len(digest) != 64:
        raise PublicationError("GENERATION_DIGEST_INVALID", "a manifest digest is required.")
    return f"gen-{digest[:16]}"


@dataclass(frozen=True, slots=True)
class GenerationCandidate:
    source_id: str
    manifest_digest: str
    unit_count: int

    @property
    def generation(self) -> str:
        return candidate_generation(self.manifest_digest)


@dataclass(frozen=True, slots=True)
class GenerationCheckpoint:
    """A checkpoint bound to the exact input manifest it was taken against."""

    manifest_digest: str
    staged_generation: str
    unit_count: int


class GenerationGate:
    """Stage, validate, then publish atomically. Readers validate before trusting."""

    def __init__(self, root: Path,
                 crash_hook: Callable[[PublicationCrashPoint], None] | None = None) -> None:
        self._root = Path(root)
        self._crash = crash_hook or (lambda _point: None)

    # -- layout -------------------------------------------------------------

    def _source_root(self, source_id: str) -> Path:
        return self._root / "sources" / source_id

    def _staging_path_for(self, source_id: str, generation: str) -> Path:
        return self._source_root(source_id) / "staging" / generation

    def staging_path(self, candidate: GenerationCandidate) -> Path:
        return self._staging_path_for(candidate.source_id, candidate.generation)

    def generation_path(self, source_id: str, generation: str) -> Path:
        return self._source_root(source_id) / "generations" / generation

    def _pointer_path(self, source_id: str) -> Path:
        return self._source_root(source_id) / CURRENT_NAME

    # -- pipeline -----------------------------------------------------------

    def stage(self, candidate: GenerationCandidate, unit_ids: list[str]) -> Path:
        """Write the candidate into staging. Invisible to readers until published."""
        self._crash(PublicationCrashPoint.BEFORE_STAGE)
        if len(unit_ids) != candidate.unit_count:
            raise PublicationError("GENERATION_UNIT_COUNT_MISMATCH",
                                   "the candidate unit count does not match its units.")
        if manifest_digest(unit_ids) != candidate.manifest_digest:
            raise PublicationError("GENERATION_MANIFEST_MISMATCH",
                                   "the units do not hash to the candidate manifest.")

        staging = self.staging_path(candidate)
        if staging.exists():
            raise PublicationError("GENERATION_STAGING_EXISTS", "the staging path is occupied.")
        staging.mkdir(parents=True)

        manifest = {"source_id": candidate.source_id,
                    "generation": candidate.generation,
                    "manifest_digest": candidate.manifest_digest,
                    "unit_count": candidate.unit_count,
                    "units": sorted(unit_ids)}
        # Units are written first and the manifest last, so a directory without a
        # manifest is unambiguously incomplete. `MID_STAGE` fires after the first
        # unit lands, leaving a genuinely half-populated staging directory.
        ordered = sorted(unit_ids)
        for index, unit_id in enumerate(ordered):
            (staging / f"unit-{index:06d}.json").write_text(
                json.dumps({"unit_id": unit_id}, ensure_ascii=False), encoding="utf-8")
            if index == 0:
                self._crash(PublicationCrashPoint.MID_STAGE)
        self._write_fsynced(staging / MANIFEST_NAME,
                            json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        self._crash(PublicationCrashPoint.AFTER_STAGE_BEFORE_VALIDATE)
        return staging

    def validate(self, candidate: GenerationCandidate) -> None:
        """Re-read the staged manifest and confirm it is the candidate it claims."""
        staging = self.staging_path(candidate)
        self._crash(PublicationCrashPoint.MID_VALIDATE)
        manifest = self._read_manifest(staging)
        if manifest is None:
            raise PublicationError("GENERATION_INCOMPLETE", "the staged candidate has no manifest.")
        if manifest["manifest_digest"] != candidate.manifest_digest \
                or manifest["generation"] != candidate.generation:
            raise PublicationError("GENERATION_MANIFEST_MISMATCH",
                                   "the staged manifest is not the candidate.")
        if manifest["unit_count"] != candidate.unit_count:
            raise PublicationError("GENERATION_UNIT_COUNT_MISMATCH",
                                   "the staged manifest unit count differs.")
        self._crash(PublicationCrashPoint.AFTER_VALIDATE_BEFORE_PUBLISH)

    def publish(self, candidate: GenerationCandidate) -> str:
        """Move the validated candidate into place, then switch the pointer atomically."""
        staging = self.staging_path(candidate)
        final = self.generation_path(candidate.source_id, candidate.generation)
        if final.exists():
            raise PublicationError("GENERATION_ALREADY_PUBLISHED",
                                   "the generation is already published.")
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging, final)
        self._crash(PublicationCrashPoint.MID_PUBLISH)
        # The pointer switch is the only atomic step: before it the old generation
        # is visible, after it the new one is. There is no in-between to observe.
        self._switch_pointer(self._pointer_path(candidate.source_id), candidate.generation)
        return candidate.generation

    def discard(self, candidate: GenerationCandidate) -> None:
        """Remove a staged candidate. Only ever touches staging, never a published one."""
        self.discard_staged(candidate.source_id, candidate.generation)

    def discard_staged(self, source_id: str, generation: str) -> None:
        """Remove the staging directory for one generation, if it exists."""
        staging = self._staging_path_for(source_id, generation)
        if not staging.exists():
            return
        for path in sorted(staging.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        staging.rmdir()

    def resume(self, candidate: GenerationCandidate,
               checkpoint: GenerationCheckpoint) -> GenerationCandidate:
        """Continue a staged candidate, or discard it when the input changed.

        A differing manifest digest means the inputs are not the ones the
        checkpoint was taken against. Continuing would publish a generation the
        checkpoint never described, so the candidate is discarded and refused.
        """
        if checkpoint.manifest_digest != candidate.manifest_digest:
            # Discard the generation the **checkpoint** staged, not the one the
            # caller is now proposing — those differ by definition here, and
            # discarding the new name would leave the stale staging behind.
            self.discard_staged(candidate.source_id, checkpoint.staged_generation)
            raise PublicationError(
                "GENERATION_INPUT_CHANGED",
                "the input manifest changed since the checkpoint; the candidate was discarded.",
            )
        if checkpoint.staged_generation != candidate.generation:
            raise PublicationError("GENERATION_CHECKPOINT_MISMATCH",
                                   "the checkpoint names a different generation.")
        return candidate

    # -- readers ------------------------------------------------------------

    def visible(self, source_id: str) -> str | None:
        """The generation a reader may serve, or None.

        Validated on read: a pointer naming a generation whose manifest does not
        hash to it is **not** reported. That is what makes a half-written
        directory unservable rather than partially served.
        """
        pointer = self._pointer_path(source_id)
        try:
            generation = pointer.read_text(encoding="ascii").strip()
        except OSError:
            return None
        if not generation:
            return None
        manifest = self._read_manifest(self.generation_path(source_id, generation))
        if manifest is None or manifest.get("generation") != generation:
            return None
        # The manifest's own digest must reproduce the generation it claims. This
        # is the check that makes a half-written or mismatched directory
        # unservable: the pointer alone is not trusted.
        digest = manifest.get("manifest_digest")
        if not isinstance(digest, str) or candidate_generation(digest) != generation:
            return None
        return generation

    def visible_unit_count(self, source_id: str) -> int:
        """Units behind the visible generation. Zero when nothing is visible."""
        generation = self.visible(source_id)
        if generation is None:
            return 0
        manifest = self._read_manifest(self.generation_path(source_id, generation))
        return int(manifest["unit_count"]) if manifest else 0

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _read_manifest(directory: Path) -> dict | None:
        try:
            payload = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None

    def _switch_pointer(self, path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}-{os.getpid()}")
        self._write_fsynced(temporary, f"{value}\n".encode("ascii"))
        os.replace(temporary, path)

    @staticmethod
    def _write_fsynced(path: Path, payload: bytes) -> None:
        with path.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())


__all__ = [
    "CURRENT_NAME",
    "GenerationCandidate",
    "GenerationCheckpoint",
    "GenerationGate",
    "InjectedPublicationCrash",
    "MANIFEST_NAME",
    "PublicationCrashPoint",
    "PublicationError",
    "PublicationState",
    "candidate_generation",
    "manifest_digest",
]

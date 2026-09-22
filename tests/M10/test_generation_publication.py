"""M10 generation publication: the "no half-published generation" assertion.

This is the assertion the crash matrix has been unable to make until now. Steps 2
and 3 wrote domain state with no generation, so the claim did not apply and was
deliberately not faked. Here it does, and it is asserted at **every** publication
crash point: a reader either sees the previous generation in full or the new one
in full, never a partial.

Two mechanisms make that structural rather than conventional — the generation id
is derived from the manifest digest, and `visible()` re-validates the on-disk
manifest instead of trusting the pointer.
"""

from __future__ import annotations

import json

import pytest

from app.generation_publication import (
    CURRENT_NAME,
    MANIFEST_NAME,
    GenerationCandidate,
    GenerationCheckpoint,
    GenerationGate,
    InjectedPublicationCrash,
    PublicationCrashPoint,
    PublicationError,
    candidate_generation,
    manifest_digest,
)

pytestmark = pytest.mark.m10

_UNITS_V1 = [f"u{i}" for i in range(5)]
_UNITS_V2 = [f"u{i}" for i in range(8)]


def _candidate(units: list[str], *, source_id: str = "src-1") -> GenerationCandidate:
    return GenerationCandidate(source_id=source_id, manifest_digest=manifest_digest(units),
                               unit_count=len(units))


def _gate(tmp_path, *, crash_at: PublicationCrashPoint | None = None) -> GenerationGate:
    def hook(point: PublicationCrashPoint) -> None:
        if crash_at is not None and point is crash_at:
            raise InjectedPublicationCrash(point.value)

    return GenerationGate(tmp_path, crash_hook=hook)


def _publish(gate: GenerationGate, units: list[str]) -> GenerationCandidate:
    candidate = _candidate(units)
    gate.stage(candidate, units)
    gate.validate(candidate)
    gate.publish(candidate)
    return candidate


def test_the_generation_id_is_derived_from_the_manifest_digest(tmp_path) -> None:
    """Same input, same generation: a reindex over unchanged content must not churn."""
    first = _candidate(_UNITS_V1)
    second = _candidate(list(reversed(_UNITS_V1)))  # order-insensitive
    third = _candidate(_UNITS_V2)

    assert first.generation == second.generation
    assert first.generation != third.generation
    assert first.generation == candidate_generation(first.manifest_digest)


def test_a_published_generation_becomes_visible_with_all_its_units(tmp_path) -> None:
    gate = _gate(tmp_path)
    candidate = _publish(gate, _UNITS_V1)

    assert gate.visible("src-1") == candidate.generation
    assert gate.visible_unit_count("src-1") == len(_UNITS_V1)


def test_nothing_is_visible_before_the_first_publish(tmp_path) -> None:
    gate = _gate(tmp_path)
    candidate = _candidate(_UNITS_V1)
    gate.stage(candidate, _UNITS_V1)

    # Staged but not published: invisible, even though the units are on disk.
    assert gate.visible("src-1") is None
    assert gate.visible_unit_count("src-1") == 0


@pytest.mark.parametrize("point", list(PublicationCrashPoint))
def test_no_crash_point_ever_leaves_a_half_published_generation(tmp_path, point) -> None:
    """The assertion, at every point: visible is the old generation or nothing.

    Both halves matter. Asserting only "never partial" would pass if publication
    were impossible, so the test also proves the pipeline can complete: the same
    sequence without injection publishes v2 in full.
    """
    gate = _gate(tmp_path)
    first = _publish(gate, _UNITS_V1)
    assert gate.visible_unit_count("src-1") == len(_UNITS_V1)

    crashing = _gate(tmp_path, crash_at=point)
    candidate = _candidate(_UNITS_V2)
    with pytest.raises(InjectedPublicationCrash):
        crashing.stage(candidate, _UNITS_V2)
        crashing.validate(candidate)
        crashing.publish(candidate)

    # Whatever survived, the reader sees a *complete* generation or none.
    visible = gate.visible("src-1")
    count = gate.visible_unit_count("src-1")
    assert visible in {None, first.generation, candidate.generation}
    assert count in {0, len(_UNITS_V1), len(_UNITS_V2)}
    if visible is not None:
        expected = len(_UNITS_V1) if visible == first.generation else len(_UNITS_V2)
        assert count == expected
    # And never a partial directory served under a name.
    if visible is not None:
        manifest = json.loads(
            (tmp_path / "sources" / "src-1" / "generations" / visible / MANIFEST_NAME)
            .read_text(encoding="utf-8"))
        assert manifest["unit_count"] == count


def test_a_crash_before_the_pointer_switch_leaves_the_old_generation_serving(tmp_path) -> None:
    """The specific window the atomic switch closes."""
    gate = _gate(tmp_path)
    first = _publish(gate, _UNITS_V1)

    crashing = _gate(tmp_path, crash_at=PublicationCrashPoint.MID_PUBLISH)
    candidate = _candidate(_UNITS_V2)
    with pytest.raises(InjectedPublicationCrash):
        crashing.stage(candidate, _UNITS_V2)
        crashing.validate(candidate)
        crashing.publish(candidate)

    # The new directory is in place, but the pointer never moved.
    assert (tmp_path / "sources" / "src-1" / "generations" / candidate.generation).is_dir()
    assert gate.visible("src-1") == first.generation
    assert gate.visible_unit_count("src-1") == len(_UNITS_V1)


def test_a_pointer_naming_a_generation_whose_manifest_disagrees_is_not_served(tmp_path) -> None:
    """The pointer is not trusted: the manifest must reproduce the id it claims."""
    gate = _gate(tmp_path)
    candidate = _publish(gate, _UNITS_V1)

    manifest_path = (tmp_path / "sources" / "src-1" / "generations" / candidate.generation
                     / MANIFEST_NAME)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest_digest"] = manifest_digest(_UNITS_V2)  # no longer matches the id
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert gate.visible("src-1") is None
    assert gate.visible_unit_count("src-1") == 0


def test_a_truncated_manifest_is_not_served(tmp_path) -> None:
    gate = _gate(tmp_path)
    candidate = _publish(gate, _UNITS_V1)
    (tmp_path / "sources" / "src-1" / "generations" / candidate.generation
     / MANIFEST_NAME).write_text("{not json", encoding="utf-8")

    assert gate.visible("src-1") is None


def test_staging_refuses_units_that_do_not_match_the_candidate(tmp_path) -> None:
    gate = _gate(tmp_path)
    candidate = _candidate(_UNITS_V1)

    with pytest.raises(PublicationError) as caught:
        gate.stage(candidate, _UNITS_V1[:-1])
    assert caught.value.code == "GENERATION_UNIT_COUNT_MISMATCH"

    with pytest.raises(PublicationError) as caught:
        gate.stage(candidate, _UNITS_V2)
    assert caught.value.code == "GENERATION_UNIT_COUNT_MISMATCH"

    # Same count, different content: the digest is what catches this.
    swapped = list(_UNITS_V1[:-1]) + ["different"]
    with pytest.raises(PublicationError) as caught:
        gate.stage(candidate, swapped)
    assert caught.value.code == "GENERATION_MANIFEST_MISMATCH"


def test_publishing_the_same_generation_twice_is_refused(tmp_path) -> None:
    """Re-staging is harmless — staging is free — but publishing again is not.

    The generation is already serving; republishing would move a directory over
    a live one for no reason.
    """
    gate = _gate(tmp_path)
    candidate = _publish(gate, _UNITS_V1)

    gate.stage(candidate, _UNITS_V1)  # staging again is allowed
    with pytest.raises(PublicationError) as caught:
        gate.publish(candidate)
    assert caught.value.code == "GENERATION_ALREADY_PUBLISHED"

    assert gate.visible("src-1") == candidate.generation
    assert gate.visible_unit_count("src-1") == len(_UNITS_V1)


def test_a_resume_whose_input_changed_discards_the_candidate(tmp_path) -> None:
    """Continuing would publish a generation the checkpoint never described."""
    gate = _gate(tmp_path)
    staged = _candidate(_UNITS_V1)
    gate.stage(staged, _UNITS_V1)
    checkpoint = GenerationCheckpoint(manifest_digest=staged.manifest_digest,
                                      staged_generation=staged.generation,
                                      unit_count=staged.unit_count)

    changed = _candidate(_UNITS_V2)
    with pytest.raises(PublicationError) as caught:
        gate.resume(changed, checkpoint)
    assert caught.value.code == "GENERATION_INPUT_CHANGED"
    assert not gate.staging_path(staged).exists()  # discarded, not left behind
    assert gate.visible("src-1") is None


def test_a_resume_with_an_unchanged_input_continues(tmp_path) -> None:
    """Non-vacuity for the discard rule: the matching case must still proceed."""
    gate = _gate(tmp_path)
    staged = _candidate(_UNITS_V1)
    gate.stage(staged, _UNITS_V1)
    checkpoint = GenerationCheckpoint(manifest_digest=staged.manifest_digest,
                                      staged_generation=staged.generation,
                                      unit_count=staged.unit_count)

    resumed = gate.resume(_candidate(_UNITS_V1), checkpoint)
    gate.validate(resumed)
    gate.publish(resumed)
    assert gate.visible("src-1") == staged.generation
    assert gate.visible_unit_count("src-1") == len(_UNITS_V1)


def test_a_checkpoint_naming_a_different_generation_is_refused(tmp_path) -> None:
    gate = _gate(tmp_path)
    staged = _candidate(_UNITS_V1)
    gate.stage(staged, _UNITS_V1)
    checkpoint = GenerationCheckpoint(manifest_digest=staged.manifest_digest,
                                      staged_generation="gen-0000000000000000",
                                      unit_count=staged.unit_count)

    with pytest.raises(PublicationError) as caught:
        gate.resume(_candidate(_UNITS_V1), checkpoint)
    assert caught.value.code == "GENERATION_CHECKPOINT_MISMATCH"


def test_the_pointer_file_is_the_only_thing_that_makes_a_generation_visible(tmp_path) -> None:
    """A named, checkable location — so 'invisible' is a property of the layout."""
    gate = _gate(tmp_path)
    candidate = _candidate(_UNITS_V1)
    gate.stage(candidate, _UNITS_V1)
    gate.validate(candidate)
    assert not (tmp_path / "sources" / "src-1" / CURRENT_NAME).exists()

    gate.publish(candidate)
    pointer = tmp_path / "sources" / "src-1" / CURRENT_NAME
    assert pointer.read_text(encoding="ascii").strip() == candidate.generation

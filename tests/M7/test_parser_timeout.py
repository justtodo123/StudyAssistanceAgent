"""M7 parser wall-clock bound: a parser that loops internally must still fail closed.

Regression: the byte and unit limits bound what a parser is *given*, not how long
it runs. `pypdf` 6.0.0 has two published DoS advisories (CVE-2026-59935 /
CVE-2026-59936, unterminated inline images) whose whole impact is an infinite
loop. A loop raises nothing, so `_parse_pdf`'s `except Exception` and every other
`except` clause in the parse path were blind to it — the call simply never
returned, and with the repo's single-worker lock that wedges the whole process.
`PARSE_TIMEOUT_SECONDS` is the bound that makes the fail-closed contract hold for
that case.

These cases drive a real looping callable through the real `parse_document` seam
rather than asserting the constant, so removing the bound turns them red.
"""

from __future__ import annotations

import threading
import time

import pytest

from tests.M7.real_fixtures import fixture_bytes

from app.parser_matrix import (
    MAX_FILE_BYTES,
    PARSE_TIMEOUT_SECONDS,
    ParserErrorCode,
    ParserMatrixError,
    parse_document,
    parse_file,
    parser_availability,
)

pytestmark = pytest.mark.m7

_MARKDOWN = b"# Heading\n\nBody text.\n"


class _Spinner:
    """A callable that spins until released, then exits on its own.

    It must **outlive** the timeout under test, but it must not keep burning a
    core for the rest of the session, so the test releases it once the assertion
    has been made. `started` is what makes the guard non-vacuous: it proves the
    callable really ran instead of the timeout firing before it was reached.
    """

    def __init__(self) -> None:
        self.started = threading.Event()
        self._release = threading.Event()

    def __call__(self) -> tuple:
        self.started.set()
        while not self._release.is_set():
            time.sleep(0.001)
        raise AssertionError("the spinning parser was released but still returned")

    def release(self) -> None:
        self._release.set()


_PARSERS = ("_parse_markdown", "_parse_text", "_parse_pdf", "_parse_pptx", "_parse_docx")


def _install_spinner(monkeypatch, spinner: _Spinner, formats: tuple[str, ...] = _PARSERS) -> None:
    """Make the named parsers loop, leaving the real `_run_bounded` under test.

    Patching the parsers rather than `_run_bounded` is the point: replacing the
    bound itself would delete the behaviour under test and hang the suite.
    """
    for name in formats:
        monkeypatch.setattr(f"app.parser_matrix.{name}", lambda *a, _s=spinner, **k: _s())


def test_a_looping_parser_fails_closed_instead_of_hanging(monkeypatch) -> None:
    spinner = _Spinner()
    _install_spinner(monkeypatch, spinner)

    started = time.monotonic()
    with pytest.raises(ParserMatrixError) as caught:
        parse_document(_MARKDOWN, "md", timeout_seconds=0.2)
    elapsed = time.monotonic() - started
    spinner.release()

    assert caught.value.code is ParserErrorCode.PARSE_TIMEOUT
    # The guard is non-vacuous only if the looping callable actually ran.
    assert spinner.started.is_set()
    # And it returned near the bound rather than waiting for the loop to end.
    assert elapsed < PARSE_TIMEOUT_SECONDS


def test_the_bound_applies_to_every_format(monkeypatch) -> None:
    """The seam is format-agnostic, so no format is left unbounded.

    Each format needs bytes that pass its own declaration check, otherwise the
    rejection would come from `_validate_declaration` and prove nothing. Formats
    whose parser is unavailable on this interpreter are skipped rather than
    asserted — the `txt` parser is bound to an exact CPython version, so
    `require_parser` rejects it here before the bound is ever reached, and this
    file must not add to that documented baseline failure.
    """

    spinner = _Spinner()
    _install_spinner(monkeypatch, spinner)

    exercised = []
    for declared_format in ("md", "txt", "pdf", "pptx", "docx"):
        if not parser_availability(declared_format):
            continue
        with pytest.raises(ParserMatrixError) as caught:
            parse_document(fixture_bytes(declared_format), declared_format,
                           timeout_seconds=0.2)
        assert caught.value.code is ParserErrorCode.PARSE_TIMEOUT, declared_format
        exercised.append(declared_format)
    spinner.release()

    # Non-vacuity: at least one format must have reached the bound, and the
    # looping parser must really have run.
    assert len(exercised) >= 4
    assert spinner.started.is_set()


def test_parse_file_passes_the_bound_through(monkeypatch, tmp_path) -> None:
    spinner = _Spinner()
    _install_spinner(monkeypatch, spinner)
    path = tmp_path / "note.md"
    path.write_bytes(_MARKDOWN)

    with pytest.raises(ParserMatrixError) as caught:
        parse_file(path, timeout_seconds=0.2)
    spinner.release()

    assert caught.value.code is ParserErrorCode.PARSE_TIMEOUT


def test_the_bound_can_only_be_tightened() -> None:
    for rejected in (0, -1, PARSE_TIMEOUT_SECONDS + 1, float("inf"), float("nan"),
                     True, "5", None):
        with pytest.raises(ParserMatrixError) as caught:
            parse_document(_MARKDOWN, "md", timeout_seconds=rejected)
        assert caught.value.code is ParserErrorCode.PARSE_LIMIT_EXCEEDED


def test_the_default_bound_is_the_ceiling() -> None:
    assert PARSE_TIMEOUT_SECONDS > 0
    assert PARSE_TIMEOUT_SECONDS <= 60


def test_a_fast_parse_is_unchanged_by_the_bound() -> None:
    """The bound is behaviour-preserving for documents that parse normally."""

    document = parse_document(_MARKDOWN, "md")
    assert document.format == "md"
    assert [unit.text.strip() for unit in document.units] == ["Heading", "Body text."]

    tightened = parse_document(_MARKDOWN, "md", timeout_seconds=PARSE_TIMEOUT_SECONDS)
    assert tightened.units == document.units
    assert tightened.parser_id == document.parser_id


def test_parser_errors_still_propagate_unchanged() -> None:
    """The bound must not swallow the typed rejection the callers rely on."""

    with pytest.raises(ParserMatrixError) as caught:
        parse_document(b"x" * (MAX_FILE_BYTES + 1), "md")
    assert caught.value.code is ParserErrorCode.PARSE_LIMIT_EXCEEDED

    with pytest.raises(ParserMatrixError) as caught:
        parse_document(_MARKDOWN, "epub")
    assert caught.value.code is ParserErrorCode.FORMAT_UNSUPPORTED

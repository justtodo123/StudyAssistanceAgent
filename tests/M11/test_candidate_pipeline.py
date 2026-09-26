from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.m11_candidate_pipeline import (
    CandidatePipelineError,
    assert_no_publication_or_replace_all,
    declared_format_for,
    lookup_digest_asset,
    normalize_bound_candidate,
    _normalize_candidate,
    parser_status_for_candidates,
    summarize_candidate_results,
)
from app.normalized_document import CHUNK_SCHEMA_VERSION
from app.source_policy import IngestStatus, is_indexable_frontmatter

pytestmark = pytest.mark.m11


def _fixture(path, content=b"# Title\n\nCandidate content\n"):
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def test_candidate_pipeline_normalizes_without_approval_or_publication(m11_data_tree):
    raw = m11_data_tree["raw"] / "example.md"
    digest = _fixture(raw)
    result = _normalize_candidate(
        source_label="mit-ocw-6-004-2017",
        asset_id="example.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    assert result.status == "CANDIDATE"
    assert result.source_id.startswith("user-")
    assert result.document_id
    assert result.normalized_path == "mit-ocw-6-004-2017-example.md.json"
    assert result.candidate_path == "mit-ocw-6-004-2017-example.md.json"
    assert ":" not in result.normalized_path
    assert "\\" not in result.candidate_path
    assert not list(m11_data_tree["approved"].iterdir())
    assert not list(m11_data_tree["snapshots"].iterdir())
    payload_text = (
        m11_data_tree["candidates"] / "mit-ocw-6-004-2017-example.md.json"
    ).read_text(encoding="utf-8")
    assert '"ingest_status": "candidate"' in payload_text
    assert '"approved": false' in payload_text
    assert '"published": false' in payload_text
    payload = json.loads(payload_text)
    document = payload["document"]
    assert document["document_id"] == hashlib.sha256(
        f"{document['source_id']}\0{document['logical_uri']}".encode("utf-8")
    ).hexdigest()[:32]
    chunks = payload["chunks"]
    assert chunks
    assert {item["chunk_schema"] for item in chunks} == {CHUNK_SCHEMA_VERSION}
    assert all(
        item["chunk_id"] == hashlib.sha256(
            (
                f"{document['document_id']}\0{item['chunk_key']}"
                f"\0{item['chunk_schema']}"
            ).encode("utf-8")
        ).hexdigest()[:32]
        for item in chunks
    )
    assert all("content" not in item for item in chunks)
    assert all(item["content_digest"] for item in chunks)
    assert not is_indexable_frontmatter({
        "course": "os",
        "source_type": "user_registered",
        "ingest_status": IngestStatus.CANDIDATE.value,
    })


def test_candidate_rejects_mixed_chunk_schemas(m11_data_tree, monkeypatch):
    import app.m11_candidate_pipeline as pipeline

    raw = m11_data_tree["raw"] / "mixed.md"
    digest = _fixture(raw)
    original_normalize = pipeline.normalize_document

    def mixed_normalize(*args, **kwargs):
        document = original_normalize(*args, **kwargs)
        chunks = document.chunks()
        forged = object.__new__(type(chunks[0]))
        for field in (
            "source_id", "document_id", "logical_uri", "chunk_key",
            "content", "title", "unit_kind", "ordinal", "chunk_id",
        ):
            object.__setattr__(forged, field, getattr(chunks[0], field))
        object.__setattr__(forged, "chunk_schema", "unknown-schema")

        class MixedDocument:
            def __init__(self, wrapped):
                self._wrapped = wrapped

            def __getattr__(self, name):
                return getattr(self._wrapped, name)

            def chunks(self):
                return (forged, *chunks[1:])

        return MixedDocument(document)

    monkeypatch.setattr(pipeline, "normalize_document", mixed_normalize)
    result = _normalize_candidate(
        source_label="mit-ocw-6-004-2017",
        asset_id="mixed.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )

    assert result.status == "REJECTED"
    assert result.reason == "CHUNK_SCHEMA_NOT_ALLOWED"
    assert not list(m11_data_tree["candidates"].iterdir())


def test_candidate_rejects_forged_chunk_identity(m11_data_tree, monkeypatch):
    import app.m11_candidate_pipeline as pipeline

    raw = m11_data_tree["raw"] / "forged.md"
    digest = _fixture(raw)
    original_normalize = pipeline.normalize_document

    def forged_normalize(*args, **kwargs):
        document = original_normalize(*args, **kwargs)
        chunks = document.chunks()
        forged = object.__new__(type(chunks[0]))
        for field in (
            "source_id", "document_id", "logical_uri", "chunk_key",
            "content", "title", "unit_kind", "ordinal", "chunk_schema",
        ):
            object.__setattr__(forged, field, getattr(chunks[0], field))
        object.__setattr__(forged, "chunk_id", "0" * 32)

        class ForgedDocument:
            def __init__(self, wrapped):
                self._wrapped = wrapped

            def __getattr__(self, name):
                return getattr(self._wrapped, name)

            def chunks(self):
                return (forged, *chunks[1:])

        return ForgedDocument(document)

    monkeypatch.setattr(pipeline, "normalize_document", forged_normalize)
    result = _normalize_candidate(
        source_label="mit-ocw-6-004-2017",
        asset_id="forged.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )

    assert result.status == "REJECTED"
    assert result.reason == "CHUNK_IDENTITY_MISMATCH"
    assert not list(m11_data_tree["candidates"].iterdir())
    assert not list(m11_data_tree["normalized"].iterdir())


def test_candidate_rejects_forged_document_identity(m11_data_tree, monkeypatch):
    import app.m11_candidate_pipeline as pipeline

    raw = m11_data_tree["raw"] / "forged-document.md"
    digest = _fixture(raw)
    original_normalize = pipeline.normalize_document

    def forged_normalize(*args, **kwargs):
        document = original_normalize(*args, **kwargs)

        class ForgedDocument:
            def __init__(self, wrapped):
                self._wrapped = wrapped
                self.document_id = "0" * 32

            def __getattr__(self, name):
                return getattr(self._wrapped, name)

            def chunks(self):
                return self._wrapped.chunks()

        return ForgedDocument(document)

    monkeypatch.setattr(pipeline, "normalize_document", forged_normalize)
    result = _normalize_candidate(
        source_label="mit-ocw-6-004-2017",
        asset_id="forged-document.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )

    assert result.status == "REJECTED"
    assert result.reason == "CHUNK_IDENTITY_MISMATCH"
    assert not list(m11_data_tree["candidates"].iterdir())
    assert not list(m11_data_tree["normalized"].iterdir())


def test_non_allowlisted_source_is_rejected_without_partial_candidate(m11_data_tree):
    raw = m11_data_tree["raw"] / "example.md"
    digest = _fixture(raw)
    result = _normalize_candidate(
        source_label="network-candidates",
        asset_id="example.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    assert result.status == "REJECTED"
    assert result.reason == "SOURCE_NOT_ALLOWLISTED"
    assert not list(m11_data_tree["normalized"].iterdir())
    assert not list(m11_data_tree["candidates"].iterdir())
    assert result.rejected_path == "network-candidates-example.md.json"
    rejection = json.loads((m11_data_tree["rejected"] / result.rejected_path).read_text(encoding="utf-8"))
    assert rejection["ingest_status"] == "rejected"


def test_digest_mismatch_is_rejected_without_candidate(m11_data_tree):
    raw = m11_data_tree["raw"] / "example.md"
    _fixture(raw)
    result = _normalize_candidate(
        source_label="rfc-editor-index",
        asset_id="example.md",
        raw_path=raw,
        declared_format="md",
        expected_digest="0" * 64,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    assert result.status == "REJECTED"
    assert result.reason == "CONTENT_DIGEST_MISMATCH"
    assert not list(m11_data_tree["candidates"].iterdir())


def test_rejection_reason_does_not_expose_host_path(m11_data_tree):
    missing = m11_data_tree["raw"] / "missing.md"
    result = _normalize_candidate(
        source_label="rfc-editor-index",
        asset_id="missing.md",
        raw_path=missing,
        declared_format="md",
        expected_digest="0" * 64,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    assert result.status == "REJECTED"
    assert result.reason == "IO_ERROR"
    assert str(missing) not in json.dumps(result.to_dict())


@pytest.mark.parametrize(
    ("source_label", "asset_id", "reason"),
    [
        ("../../outside", "safe.md", "SOURCE_LABEL_INVALID"),
        ("..\\..\\outside", "safe.md", "SOURCE_LABEL_INVALID"),
        ("C:\\secret", "safe.md", "SOURCE_LABEL_INVALID"),
        ("rfc-editor-index", "../../secret.md", "ASSET_ID_INVALID"),
        ("rfc-editor-index", "RST/en/../../secret.rst", "ASSET_ID_INVALID"),
        ("rfc-editor-index", "C:\\secret.md", "ASSET_ID_INVALID"),
        ("rfc-editor-index", "secret\nvalue.md", "ASSET_ID_INVALID"),
    ],
)
def test_candidate_identifiers_cannot_escape_rejected_root(
    m11_data_tree,
    source_label,
    asset_id,
    reason,
):
    raw = m11_data_tree["raw"] / "safe.md"
    digest = _fixture(raw)

    result = _normalize_candidate(
        source_label=source_label,
        asset_id=asset_id,
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )

    rejected = m11_data_tree["rejected"] / result.rejected_path
    assert result.status == "REJECTED"
    assert result.reason == reason
    assert rejected.resolve().is_relative_to(m11_data_tree["rejected"].resolve())
    serialized = rejected.read_text(encoding="utf-8")
    if reason == "SOURCE_LABEL_INVALID":
        assert source_label not in serialized
        assert asset_id in serialized
    else:
        assert source_label in serialized
        assert asset_id not in serialized
    assert not list(m11_data_tree["normalized"].iterdir())
    assert not list(m11_data_tree["candidates"].iterdir())


def test_parser_failure_is_rejected_with_reason_only(m11_data_tree):
    raw = m11_data_tree["raw"] / "example.bin"
    digest = _fixture(raw, b"not a supported document")
    result = _normalize_candidate(
        source_label="iana-registries",
        asset_id="example.bin",
        raw_path=raw,
        declared_format="bin",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    assert result.status == "REJECTED"
    assert result.rejected_path
    assert not list(m11_data_tree["candidates"].iterdir())
    rejection = (m11_data_tree["rejected"] / "iana-registries-example.bin.json").read_text(encoding="utf-8")
    assert "not a supported document" not in rejection


def test_same_candidate_rerun_keeps_source_and_document_identity(m11_data_tree):
    raw = m11_data_tree["raw"] / "example.md"
    digest = _fixture(raw)
    first = _normalize_candidate(
        source_label="opendsa-main",
        asset_id="RST/en/example.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    second = _normalize_candidate(
        source_label="opendsa-main",
        asset_id="RST/en/example.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    assert first.status == second.status == "CANDIDATE"
    assert first.source_id == second.source_id
    assert first.document_id == second.document_id
    assert first.content_fingerprint == second.content_fingerprint


def test_empty_document_is_rejected_without_candidate(m11_data_tree):
    raw = m11_data_tree["raw"] / "empty.md"
    digest = _fixture(raw, b"")
    result = _normalize_candidate(
        source_label="rfc-editor-index",
        asset_id="empty.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    assert result.status == "REJECTED"
    assert not list(m11_data_tree["candidates"].iterdir())
    assert result.rejected_path


def test_candidate_pipeline_does_not_touch_learning_state(m11_data_tree, tmp_path):
    sentinel = tmp_path / "learning_state.sqlite3"
    sentinel.write_bytes(b"learning-state-sentinel")
    before = sentinel.read_bytes()
    raw = m11_data_tree["raw"] / "example.md"
    digest = _fixture(raw)
    result = _normalize_candidate(
        source_label="iana-registries",
        asset_id="example.md",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
    )
    assert result.status == "CANDIDATE"
    assert sentinel.read_bytes() == before


def test_candidate_pipeline_source_does_not_publish_or_replace_all():
    assert_no_publication_or_replace_all()


def test_candidate_pipeline_exposes_only_manifest_bound_normalization():
    import app.m11_candidate_pipeline as pipeline

    assert "normalize_bound_candidate" in pipeline.__all__
    assert "normalize_candidate" not in pipeline.__all__
    assert not hasattr(pipeline, "normalize_candidate")


def test_candidate_report_is_count_only_and_fail_closed(tmp_path):
    raw_path = Path("tests") / "M11" / "__init__.py"
    artifact_root = tmp_path / "artifacts"
    candidate = _normalize_candidate(
        source_label="mit-ocw-6-004-2017",
        asset_id="example.md",
        raw_path=raw_path,
        declared_format="md",
        expected_digest=hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        normalized_root=artifact_root / "m11-test-normalized",
        candidate_root=artifact_root / "m11-test-candidates",
        rejected_root=artifact_root / "m11-test-rejected",
    )
    report = summarize_candidate_results([candidate])
    assert report["asset_count"] == 1
    assert report["candidate_count"] + report["rejected_count"] == 1
    assert report["approved_count"] == 0
    assert report["published_count"] == 0
    assert report["host_paths_included"] is False
    assert report["bodies_included"] is False


def test_parser_status_for_candidates_is_non_empty_and_covers_requested_formats():
    status = parser_status_for_candidates()
    assert status
    assert set(status) == {"md", "pdf", "txt"}
    assert all(isinstance(value, bool) for value in status.values())
    assert status["md"] is True


def test_declared_format_covers_rfc_iana_and_opendsa_suffixes():
    assert declared_format_for("rfc9110", "https://www.rfc-editor.org/rfc/rfc9110.txt") == "txt"
    assert declared_format_for("service-names-port-numbers-csv", "https://www.iana.org/assignments/x.csv") == "txt"
    assert declared_format_for("service-names-port-numbers-xml", "https://www.iana.org/assignments/x.xml") == "txt"
    assert declared_format_for("RST/en/List/ListIntro.rst") == "txt"
    assert declared_format_for("beta_answers", "https://ocw.mit.edu/x.pdf") == "pdf"


def test_lookup_digest_asset_is_exact_and_non_empty(repo_root):
    rfc = lookup_digest_asset("rfc-editor-index", "rfc9110", repo_root / "data/manifests/m11-p0-digest-evidence-v1.json")
    assert rfc["sha256"]
    assert rfc["url"].startswith("https://www.rfc-editor.org/")
    with pytest.raises(CandidatePipelineError, match="DIGEST_EVIDENCE_ASSET_NOT_FOUND"):
        lookup_digest_asset("rfc-editor-index", "rfc-not-listed", repo_root / "data/manifests/m11-p0-digest-evidence-v1.json")


def test_lookup_digest_asset_rejects_non_hex_sha256(tmp_path):
    evidence = tmp_path / "malformed-digests.json"
    evidence.write_text(json.dumps({
        "status": "DIGESTS_CAPTURED_CANDIDATE_PIPELINE_AUTHORIZED",
        "assets": [{
            "source_id": "rfc-editor-index",
            "asset_id": "rfc9110",
            "sha256": "g" * 64,
            "url": "https://www.rfc-editor.org/rfc/rfc9110.txt",
        }],
    }), encoding="utf-8")

    with pytest.raises(CandidatePipelineError, match="DIGEST_EVIDENCE_SHA256_INVALID"):
        lookup_digest_asset("rfc-editor-index", "rfc9110", evidence)


def test_bound_candidate_rejects_unknown_digest_asset(m11_data_tree, repo_root):
    raw = m11_data_tree["raw"] / "unknown.md"
    _fixture(raw)
    result = normalize_bound_candidate(
        source_label="rfc-editor-index",
        asset_id="rfc-not-listed",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        digest_evidence_path=repo_root / "data/manifests/m11-p0-digest-evidence-v1.json",
    )
    assert result.status == "REJECTED"
    assert result.reason == "DIGEST_EVIDENCE_ASSET_NOT_FOUND"
    assert not list(m11_data_tree["candidates"].iterdir())


def test_candidate_records_canonical_url_and_digest(m11_data_tree):
    raw = m11_data_tree["raw"] / "example.md"
    digest = _fixture(raw)
    result = _normalize_candidate(
        source_label="rfc-editor-index",
        asset_id="rfc9110",
        raw_path=raw,
        declared_format="md",
        expected_digest=digest,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        canonical_url="https://www.rfc-editor.org/rfc/rfc9110.txt",
    )
    assert result.status == "CANDIDATE"
    payload = json.loads((m11_data_tree["candidates"] / "rfc-editor-index-rfc9110.json").read_text(encoding="utf-8"))
    assert payload["canonical_url"] == "https://www.rfc-editor.org/rfc/rfc9110.txt"
    assert payload["content_digest"] == digest
    assert payload["license_status"] == "review_required"
    assert payload["ingest_status"] == "candidate"


def _write_digest_evidence(path, source_id, asset_id, url, sha256):
    asset = {
        "asset_id": asset_id,
        "source_id": source_id,
        "sha256": sha256,
    }
    if url is not None:
        asset["url"] = url
    path.write_text(json.dumps({
        "status": "DIGESTS_CAPTURED_CANDIDATE_PIPELINE_AUTHORIZED",
        "assets": [asset],
    }), encoding="utf-8")


def _write_opendsa_path_manifest(path, asset_id, content):
    blob_sha = hashlib.sha1(
        f"blob {len(content)}\0".encode("ascii") + content
    ).hexdigest()
    path.write_text(json.dumps({
        "status": "CANDIDATE_PIPELINE_AUTHORIZED",
        "source_id": "opendsa-main",
        "revision": "4c183682bbd84b951f2324a36399a3a077250bb9",
        "candidate_root": "RST/en/",
        "file_count": 1,
        "files": [{
            "path": asset_id,
            "blob_sha": blob_sha,
            "size": len(content),
        }],
    }), encoding="utf-8")


def test_bound_candidate_rfc_txt_follows_parser_availability(m11_data_tree, tmp_path):
    raw = m11_data_tree["raw"] / "rfc9110.txt"
    digest = _fixture(raw, b"Network Working Group\n\nHTTP Semantics\n")
    evidence = tmp_path / "digest.json"
    _write_digest_evidence(
        evidence,
        "rfc-editor-index",
        "rfc9110",
        "https://www.rfc-editor.org/rfc/rfc9110.txt",
        digest,
    )
    result = normalize_bound_candidate(
        source_label="rfc-editor-index",
        asset_id="rfc9110",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        digest_evidence_path=evidence,
    )
    from app.parser_matrix import parser_availability
    if parser_availability("txt"):
        assert result.status == "CANDIDATE", result.reason
        payload = json.loads((m11_data_tree["candidates"] / "rfc-editor-index-rfc9110.json").read_text(encoding="utf-8"))
        assert payload["canonical_url"] == "https://www.rfc-editor.org/rfc/rfc9110.txt"
        assert payload["content_digest"] == digest
        assert payload["document"]["format"] == "txt"
    else:
        assert result.status == "REJECTED"
        assert result.reason == "SOURCE_PARSER_UNAVAILABLE"
        assert not list(m11_data_tree["candidates"].iterdir())


def test_bound_candidate_iana_csv_follows_parser_availability(m11_data_tree, tmp_path):
    raw = m11_data_tree["raw"] / "service-names-port-numbers.csv"
    digest = _fixture(raw, b"Service Name,Port Number,Transport Protocol\nhttps,443,tcp\n")
    evidence = tmp_path / "digest.json"
    _write_digest_evidence(
        evidence,
        "iana-registries",
        "service-names-port-numbers-csv",
        "https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.csv",
        digest,
    )
    result = normalize_bound_candidate(
        source_label="iana-registries",
        asset_id="service-names-port-numbers-csv",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        digest_evidence_path=evidence,
    )
    from app.parser_matrix import parser_availability
    if parser_availability("txt"):
        assert result.status == "CANDIDATE", result.reason
        payload = json.loads(
            (m11_data_tree["candidates"] / "iana-registries-service-names-port-numbers-csv.json").read_text(encoding="utf-8")
        )
        assert payload["document"]["format"] == "txt"
        assert payload["chunks"][0]["content_digest"]
        assert "content" not in payload["chunks"][0]
    else:
        assert result.status == "REJECTED"
        assert result.reason == "SOURCE_PARSER_UNAVAILABLE"
        assert not list(m11_data_tree["candidates"].iterdir())


def test_bound_candidate_opendsa_rst_follows_parser_availability(m11_data_tree, tmp_path):
    raw = m11_data_tree["raw"] / "ListIntro.rst"
    content = b"Lists\n=====\n\nA list stores ordered items.\n"
    _fixture(raw, content)
    path_manifest = tmp_path / "opendsa-paths.json"
    _write_opendsa_path_manifest(
        path_manifest,
        "RST/en/List/ListIntro.rst",
        content,
    )
    result = normalize_bound_candidate(
        source_label="opendsa-main",
        asset_id="RST/en/List/ListIntro.rst",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        opendsa_path_manifest_path=path_manifest,
    )
    from app.parser_matrix import parser_availability
    if parser_availability("txt"):
        assert result.status == "CANDIDATE", result.reason
        payload = json.loads(
            (m11_data_tree["candidates"] / "opendsa-main-RST__en__List__ListIntro.rst.json").read_text(encoding="utf-8")
        )
        assert payload["document"]["format"] == "txt"
        assert payload["document"]["logical_uri"] == "RST/en/List/ListIntro.rst"
    else:
        assert result.status == "REJECTED"
        assert result.reason == "SOURCE_PARSER_UNAVAILABLE"
        assert not list(m11_data_tree["candidates"].iterdir())


def test_bound_candidate_rejects_opendsa_git_blob_mismatch(m11_data_tree, tmp_path):
    raw = m11_data_tree["raw"] / "ListIntro.rst"
    content = b"Lists\n=====\n\nA list stores ordered items.\n"
    _fixture(raw, content)
    path_manifest = tmp_path / "opendsa-paths.json"
    _write_opendsa_path_manifest(
        path_manifest,
        "RST/en/List/ListIntro.rst",
        b"different bytes",
    )

    result = normalize_bound_candidate(
        source_label="opendsa-main",
        asset_id="RST/en/List/ListIntro.rst",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        opendsa_path_manifest_path=path_manifest,
    )

    assert result.status == "REJECTED"
    assert result.reason == "CONTENT_DIGEST_MISMATCH"
    assert not list(m11_data_tree["normalized"].iterdir())
    assert not list(m11_data_tree["candidates"].iterdir())


def test_pdf_bound_candidate_follows_parser_availability(m11_data_tree, tmp_path):
    from app.parser_matrix import parser_availability

    raw = m11_data_tree["raw"] / "beta_answers.pdf"
    if parser_availability("pdf"):
        from tests.M7.real_fixtures import pdf_bytes
        digest = _fixture(raw, pdf_bytes())
    else:
        digest = _fixture(raw, b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    evidence = tmp_path / "digest.json"
    _write_digest_evidence(
        evidence,
        "mit-ocw-6-004-2017",
        "beta_answers",
        "https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/a90106bf60ae4647445e2176f1d93dc1_beta_answers.pdf",
        digest,
    )
    result = normalize_bound_candidate(
        source_label="mit-ocw-6-004-2017",
        asset_id="beta_answers",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        digest_evidence_path=evidence,
    )
    if parser_availability("pdf"):
        assert result.status == "CANDIDATE", result.reason
        payload = json.loads(
            (m11_data_tree["candidates"] / "mit-ocw-6-004-2017-beta_answers.json").read_text(encoding="utf-8")
        )
        assert payload["document"]["format"] == "pdf"
        assert payload["approved"] is False
    else:
        assert result.status == "REJECTED"
        assert result.reason == "SOURCE_PARSER_UNAVAILABLE"
        assert not list(m11_data_tree["candidates"].iterdir())
        assert result.rejected_path


def test_bound_candidate_rejects_local_bytes_that_do_not_match_evidence(m11_data_tree, tmp_path):
    raw = m11_data_tree["raw"] / "rfc9110.txt"
    _fixture(raw, b"Network Working Group\n\nHTTP Semantics\n")
    evidence = tmp_path / "digest.json"
    _write_digest_evidence(
        evidence,
        "rfc-editor-index",
        "rfc9110",
        "https://www.rfc-editor.org/rfc/rfc9110.txt",
        "0" * 64,
    )
    result = normalize_bound_candidate(
        source_label="rfc-editor-index",
        asset_id="rfc9110",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        digest_evidence_path=evidence,
    )
    assert result.status == "REJECTED"
    assert result.reason == "CONTENT_DIGEST_MISMATCH"
    assert not list(m11_data_tree["candidates"].iterdir())


def test_bound_candidate_iana_xml_follows_parser_availability(m11_data_tree, tmp_path):
    raw = m11_data_tree["raw"] / "service-names-port-numbers.xml"
    digest = _fixture(raw, b"<registry><record><name>https</name><port>443</port></record></registry>\n")
    evidence = tmp_path / "digest.json"
    _write_digest_evidence(
        evidence,
        "iana-registries",
        "service-names-port-numbers-xml",
        "https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xml",
        digest,
    )
    result = normalize_bound_candidate(
        source_label="iana-registries",
        asset_id="service-names-port-numbers-xml",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        digest_evidence_path=evidence,
    )
    from app.parser_matrix import parser_availability
    if parser_availability("txt"):
        assert result.status == "CANDIDATE", result.reason
        payload = json.loads(
            (m11_data_tree["candidates"] / "iana-registries-service-names-port-numbers-xml.json").read_text(encoding="utf-8")
        )
        assert payload["document"]["format"] == "txt"
        assert payload["chunks"][0]["content_digest"]
        assert "content" not in payload["chunks"][0]
    else:
        assert result.status == "REJECTED"
        assert result.reason == "SOURCE_PARSER_UNAVAILABLE"
        assert not list(m11_data_tree["candidates"].iterdir())


def test_bound_candidate_requires_provenance_identity(m11_data_tree, tmp_path):
    raw = m11_data_tree["raw"] / "rfc9110.md"
    digest = _fixture(raw)
    evidence = tmp_path / "digest.json"
    _write_digest_evidence(evidence, "rfc-editor-index", "rfc9110", None, digest)

    result = normalize_bound_candidate(
        source_label="rfc-editor-index",
        asset_id="rfc9110",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        digest_evidence_path=evidence,
    )

    assert result.status == "REJECTED"
    assert result.reason == "PROVENANCE_IDENTITY_INCOMPLETE"
    assert not list(m11_data_tree["candidates"].iterdir())
    payload = json.loads((m11_data_tree["rejected"] / result.rejected_path).read_text(encoding="utf-8"))
    assert payload["approved"] is False
    assert payload["published"] is False
    assert "raw_path" not in payload


def test_bound_candidate_opendsa_records_https_revision_locator(m11_data_tree, tmp_path):
    raw = m11_data_tree["raw"] / "ListIntro.rst"
    content = b"Lists\n=====\n\nA list stores ordered items.\n"
    _fixture(raw, content)
    path_manifest = tmp_path / "opendsa-paths.json"
    _write_opendsa_path_manifest(path_manifest, "RST/en/List/ListIntro.rst", content)

    result = normalize_bound_candidate(
        source_label="opendsa-main",
        asset_id="RST/en/List/ListIntro.rst",
        raw_path=raw,
        normalized_root=m11_data_tree["normalized"],
        candidate_root=m11_data_tree["candidates"],
        rejected_root=m11_data_tree["rejected"],
        opendsa_path_manifest_path=path_manifest,
    )

    from app.parser_matrix import parser_availability
    if parser_availability("txt"):
        assert result.status == "CANDIDATE", result.reason
        payload = json.loads((m11_data_tree["candidates"] / result.candidate_path).read_text(encoding="utf-8"))
        assert payload["canonical_url"].startswith("https://github.com/OpenDSA/OpenDSA@")
        assert payload["license_status"] == "review_required"
        assert payload["approved"] is False
    else:
        assert result.status == "REJECTED"
        assert result.reason == "SOURCE_PARSER_UNAVAILABLE"

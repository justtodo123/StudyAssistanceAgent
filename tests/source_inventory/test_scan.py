"""Read-only scan behavior and true-scale accounting."""

from __future__ import annotations

from pathlib import Path

from tools.source_inventory import InventoryLimits, scan_source_tree


def _mtimes(root: Path) -> dict[str, float]:
    mapping = {}
    for path in root.rglob("*"):
        if path.is_file():
            mapping[path.relative_to(root).as_posix()] = path.stat().st_mtime_ns
    return mapping


class TestScanAccounting:
    def test_unity_and_build_junk_are_excluded_from_records(self, sample_root: Path):
        report = scan_source_tree(sample_root, limits=InventoryLimits(archive_max_bytes=50))
        uris = {item["logical_uri"] for item in report["records"]}
        assert "操作系统/lecture.pdf" in uris
        assert "操作系统/notes.md" in uris
        assert "My unity/Alice/manual.docx" in uris
        assert "data_science/intro.md" in uris
        assert "c/hello.c" in uris
        assert not any("Library/" in uri for uri in uris)
        assert not any("Temp/" in uri for uri in uris)
        assert not any("Logs/" in uri for uri in uris)
        assert not any("node_modules/" in uri for uri in uris)
        assert not any(".venv/" in uri for uri in uris)
        assert not any("__pycache__/" in uri for uri in uris)
        assert "操作系统/VMware.exe" not in uris
        assert "My unity/Alice/Assets/Textures/hero.png" not in uris

    def test_summary_separates_engineering_files_from_study_candidates(self, sample_root: Path):
        report = scan_source_tree(sample_root, limits=InventoryLimits(archive_max_bytes=50))
        summary = report["summary"]
        assert summary["files_seen"] > summary["unique_candidates"]
        assert summary["files_excluded"] >= summary["unique_candidates"]
        assert summary["exclusion_counts"]["unity_cache"]["files"] >= 3
        assert summary["exclusion_counts"]["build_artifact"]["files"] >= 1
        assert summary["exclusion_counts"]["venv"]["files"] >= 1
        assert summary["exclusion_counts"]["node_modules"]["files"] >= 1
        assert summary["exclusion_counts"]["pycache"]["files"] >= 1
        assert summary["exclusion_counts"]["oversized_archive"]["files"] >= 1
        assert summary["exclusion_counts"]["virtual_disk"]["files"] >= 1
        assert summary["classification_counts"]["study_document"] >= 3
        assert summary["course_counts"]["os"] >= 1

    def test_duplicates_are_marked_and_excluded_from_unique_count(self, sample_root: Path):
        report = scan_source_tree(sample_root, limits=InventoryLimits(archive_max_bytes=50))
        by_uri = {item["logical_uri"]: item for item in report["records"]}
        lecture = by_uri["操作系统/lecture.pdf"]
        copy = by_uri["操作系统/copy.pdf"]
        statuses = {lecture["duplicate_status"], copy["duplicate_status"]}
        assert statuses == {"primary", "duplicate"}
        assert report["summary"]["duplicate_groups"] == 1
        assert report["summary"]["unique_candidates"] == report["summary"]["files_inventoried"]

    def test_notable_exclusions_keep_virtual_disks_and_oversized_archives(self, sample_root: Path):
        report = scan_source_tree(sample_root, limits=InventoryLimits(archive_max_bytes=50))
        notable = {item["logical_uri"]: item for item in report["notable_exclusions"]}
        assert "操作系统/disk.vmdk" in notable
        assert "virtual_disk" in notable["操作系统/disk.vmdk"]["risk_flags"]
        assert "操作系统/huge.zip" in notable
        assert "oversized_archive" in notable["操作系统/huge.zip"]["risk_flags"]

    def test_scan_does_not_modify_source_tree(self, sample_root: Path):
        before = _mtimes(sample_root)
        marker = sample_root / "操作系统" / "notes.md"
        original = marker.read_text(encoding="utf-8")
        scan_source_tree(sample_root, limits=InventoryLimits(archive_max_bytes=50))
        after = _mtimes(sample_root)
        assert before == after
        assert marker.read_text(encoding="utf-8") == original

    def test_missing_root_returns_empty_report(self, tmp_path: Path):
        missing = tmp_path / "no-such-root"
        report = scan_source_tree(missing)
        assert report["root_present"] is False
        assert report["records"] == []
        assert report["summary"]["files_seen"] == 0

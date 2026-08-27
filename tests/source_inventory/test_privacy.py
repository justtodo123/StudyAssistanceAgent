"""Inventory output must stay portable and avoid host paths."""

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.source_inventory import InventoryLimits, scan_source_tree, write_report

_ABS_WIN = re.compile(r"[A-Za-z]:[\\/]")


class TestPathPrivacy:
    def test_report_has_no_host_absolute_paths(self, sample_root: Path, tmp_path: Path):
        report = scan_source_tree(sample_root, limits=InventoryLimits(archive_max_bytes=50))
        output = tmp_path / "out" / "source-inventory.json"
        write_report(report, output)
        payload = output.read_text(encoding="utf-8")
        assert _ABS_WIN.search(payload) is None
        assert "111_Others_Subjects" not in payload
        parsed = json.loads(payload)
        for record in parsed["records"] + parsed["notable_exclusions"]:
            assert not Path(record["logical_uri"]).is_absolute()
            assert "\\" not in record["logical_uri"]
            assert record["logical_uri"]
        required = {
            "logical_uri",
            "course_candidate",
            "format",
            "size",
            "fingerprint",
            "classification",
            "extraction_support",
            "duplicate_status",
            "risk_flags",
        }
        for record in parsed["records"]:
            assert required <= set(record)

    def test_scan_does_not_parse_or_index(self, sample_root: Path):
        report = scan_source_tree(sample_root, limits=InventoryLimits(archive_max_bytes=50))
        assert report["copied_files"] is False
        assert report["parsed_full_text"] is False
        assert report["modified_source_root"] is False
        assert report["built_vector_index"] is False
        assert report["read_only"] is True

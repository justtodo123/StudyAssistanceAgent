"""CLI defaults and write isolation for source inventory."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.source_inventory import (
    DEFAULT_ROOT,
    SCHEMA_VERSION,
    assert_output_outside_root,
    main,
    parse_args,
)


class TestCli:
    def test_defaults_point_at_external_root_and_reports(self):
        args = parse_args([])
        assert Path(args.root) == DEFAULT_ROOT
        assert args.output.endswith("source-inventory.json")
        assert "reports" in Path(args.output).as_posix()

    def test_refuses_to_write_inside_source_root(self, sample_root: Path):
        inside = sample_root / "inventory.json"
        with pytest.raises(ValueError, match="source root"):
            assert_output_outside_root(inside, sample_root)

    def test_main_writes_report_outside_source(self, sample_root: Path, tmp_path: Path):
        output = tmp_path / "reports" / "source-inventory.json"
        code = main(["--root", str(sample_root), "--output", str(output), "--archive-max-bytes", "50"])
        assert code == 0
        payload = output.read_text(encoding="utf-8")
        assert SCHEMA_VERSION in payload
        assert output.exists()
        assert not (sample_root / "source-inventory.json").exists()

    def test_missing_root_exits_nonzero(self, tmp_path: Path):
        output = tmp_path / "empty.json"
        code = main(["--root", str(tmp_path / "missing"), "--output", str(output)])
        assert code == 2
        assert output.exists()

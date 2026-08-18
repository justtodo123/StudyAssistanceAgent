"""CLI argument parsing for the unified evaluation runner."""

from __future__ import annotations

import pytest


@pytest.mark.m5a
class TestParseTopKs:
    def test_parses_comma_separated_values(self, eval_module):
        assert eval_module.parse_top_ks("1,3,5") == [1, 3, 5]

    def test_rejects_empty_list(self, eval_module):
        with pytest.raises(ValueError, match="empty"):
            eval_module.parse_top_ks(" , ")

    def test_rejects_non_positive_values(self, eval_module):
        with pytest.raises(ValueError, match="positive"):
            eval_module.parse_top_ks("1,0,5")


@pytest.mark.m5a
class TestParseCourses:
    def test_all_selects_known_courses(self, eval_module):
        assert eval_module.parse_courses("all") == ["os", "ds", "co"]

    def test_filters_and_deduplicates(self, eval_module):
        assert eval_module.parse_courses("ds, os, ds") == ["ds", "os"]

    def test_rejects_unknown_course(self, eval_module):
        with pytest.raises(ValueError, match="unknown course"):
            eval_module.parse_courses("os,ml")


@pytest.mark.m5a
class TestParseArgs:
    def test_defaults_are_offline_and_all_courses(self, eval_module):
        args = eval_module.parse_args([])
        assert args.courses == "all"
        assert args.top_ks == "1,3,5"
        assert args.test_set is None
        assert args.report is None
        assert args.use_vector is False

    def test_use_vector_is_opt_in(self, eval_module):
        args = eval_module.parse_args(["--use-vector", "--courses", "os", "--report", "out.json"])
        assert args.use_vector is True
        assert args.courses == "os"
        assert args.report == "out.json"

    def test_test_set_mode_is_preserved(self, eval_module):
        args = eval_module.parse_args(["--test-set", "tools/evaluations/os.json"])
        assert args.test_set == "tools/evaluations/os.json"

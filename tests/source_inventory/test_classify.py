"""Classification and skip rules for source inventory."""

from __future__ import annotations

from tools.source_inventory import InventoryLimits, classify_file, course_candidate_for, skip_dir_reason


class TestClassifyFile:
    def test_study_pdf_is_candidate(self):
        decision = classify_file("lecture.pdf", 2048, InventoryLimits())
        assert decision.disposition == "candidate"
        assert decision.classification == "study_document"
        assert decision.extraction_support == "pdf"
        assert decision.format == "pdf"

    def test_exe_and_dll_are_build_artifacts(self):
        exe = classify_file("setup.exe", 1024, InventoryLimits())
        dll = classify_file("engine.dll", 1024, InventoryLimits())
        assert exe.disposition == "counted_only"
        assert dll.exclusion_reason == "build_artifact"
        assert "build_artifact" in exe.risk_flags

    def test_virtual_disk_is_notable_exclusion(self):
        decision = classify_file("disk.vmdk", 5_000_000, InventoryLimits())
        assert decision.disposition == "notable_exclusion"
        assert decision.exclusion_reason == "virtual_disk"

    def test_model_weight_is_notable_exclusion(self):
        decision = classify_file("bge.safetensors", 8_000_000, InventoryLimits())
        assert decision.exclusion_reason == "model_binary"

    def test_oversized_archive_uses_limit(self):
        limits = InventoryLimits(archive_max_bytes=50)
        decision = classify_file("notes.zip", 80, limits)
        assert decision.disposition == "notable_exclusion"
        assert decision.exclusion_reason == "oversized_archive"
        assert "oversized_archive" in decision.risk_flags

    def test_small_archive_remains_candidate(self):
        limits = InventoryLimits(archive_max_bytes=50)
        decision = classify_file("notes.zip", 20, limits)
        assert decision.disposition == "candidate"
        assert decision.classification == "archive"

    def test_html_is_webpage_not_study_document(self):
        decision = classify_file("tutorial.html", 2048, InventoryLimits())
        assert decision.disposition == "candidate"
        assert decision.classification == "webpage"
        assert decision.extraction_support == "plain_text"


class TestSkipAndCourse:
    def test_skips_unity_and_dependency_dirs(self):
        siblings = ["Assets", "Library", "ProjectSettings", "manual.docx"]
        assert skip_dir_reason("Library", siblings) == "unity_cache"
        assert skip_dir_reason("Temp", siblings) == "unity_cache"
        assert skip_dir_reason("Logs", siblings) == "unity_cache"
        assert skip_dir_reason("Assets", siblings) == "engine_asset"
        assert skip_dir_reason(".venv", []) == "venv"
        assert skip_dir_reason("site-packages", []) == "venv"
        assert skip_dir_reason("node_modules", []) == "node_modules"
        assert skip_dir_reason("__pycache__", []) == "pycache"

    def test_course_candidate_maps_known_roots(self):
        assert course_candidate_for("操作系统/lecture.pdf") == "os"
        assert course_candidate_for("data_science/intro.md") == "data-science"
        assert course_candidate_for("c/hello.c") == "misc"
        assert course_candidate_for("NIPS-paper.pdf") == "unmapped"

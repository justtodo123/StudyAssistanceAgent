#!/usr/bin/env python3
"""Read-only inventory of an external study-source tree.

This tool scans a user data root such as D:\\111_Others_Subjects and writes a
machine-readable file-level manifest. It does not copy files, parse document
text, modify the source tree, or build a vector index.

Usage:
    python tools/source_inventory.py
    python tools/source_inventory.py --root "D:\\111_Others_Subjects"
    python tools/source_inventory.py --output reports/source-inventory.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "sa.source-inventory.v1"
SOURCE_LABEL = "others-subjects"
DEFAULT_ROOT = Path(r"D:\111_Others_Subjects")
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "source-inventory.json"
DEFAULT_ARCHIVE_MAX_BYTES = 64 * 1024 * 1024
DEFAULT_LARGE_BINARY_MAX_BYTES = 100 * 1024 * 1024
DEFAULT_FINGERPRINT_SAMPLE_BYTES = 64 * 1024
PRUNED_DIRECTORY_LIMIT = 20

COURSE_CANDIDATES: dict[str, str] = {
    "操作系统": "os",
    "数据结构复习": "ds",
    "计算机组成原理": "co",
    "数据库系统": "db",
    "算法设计与分析": "algo",
    "ComputingNet": "network",
    "Bian_Yi_subject": "compiler",
    "数字逻辑": "digital-logic",
    "微机原理": "microcomputer",
    "软件工程理论与实践": "se",
    "data_science": "data-science",
    "人工智能导论": "ai",
    "ComputerGraph": "cg",
    "数字图像处理": "dip",
    "softwareTesting": "software-testing",
    "CloudComputing": "cloud",
    "系统分析与设计": "sad",
    "软件体系结构": "software-architecture",
    "软件设计综合实践": "se-design",
    "《网络安全实用技术》2版PPT-清华-贾": "security",
    "软件前沿技术讲座-光谱数据实验": "seminar",
    "My unity": "misc",
    "EengineeringIntership_three": "misc",
    "softwareProject课程设计": "misc",
    "软件工程课程设计": "misc",
    "[1]实验1": "misc",
    "c": "misc",
    "TencentMeeting": "misc",
    "MobileFile": "misc",
    "学生会": "misc",
    "心理作业": "misc",
    "批判性思维": "misc",
    "毛概": "misc",
    "英语": "misc",
    "物理": "misc",
    "社会实践": "misc",
    "报名": "misc",
}

SKIP_DIR_NAMES: dict[str, str] = {
    "library": "unity_cache",
    "temp": "unity_cache",
    "logs": "unity_cache",
    ".venv": "venv",
    "venv": "venv",
    "site-packages": "venv",
    "node_modules": "node_modules",
    "__pycache__": "pycache",
    ".git": "vcs",
    ".svn": "vcs",
    ".hg": "vcs",
    ".vs": "ide",
    ".idea": "ide",
    "projectsettings": "unity_cache",
    "usersettings": "unity_cache",
}

UNITY_SIBLING_SKIP_DIRS: dict[str, str] = {
    "assets": "engine_asset",
    "packages": "unity_cache",
    "obj": "build_artifact",
}

NOISE_FILES = {
    "thumbs.db",
    "desktop.ini",
    ".ds_store",
    "ehthumbs.db",
}

BUILD_ARTIFACT_EXTS = {
    ".dll",
    ".exe",
    ".sys",
    ".com",
    ".scr",
    ".msi",
    ".obj",
    ".pdb",
    ".lib",
    ".so",
    ".dylib",
    ".a",
    ".o",
    ".ilk",
    ".exp",
    ".pch",
    ".idb",
    ".ipch",
    ".pyc",
    ".pyo",
    ".class",
    ".jar",
    ".war",
    ".nupkg",
    ".whl",
    ".egg",
    ".apk",
    ".deb",
    ".rpm",
    ".tlog",
    ".lastbuildstate",
    ".iobj",
    ".ipdb",
    ".gch",
    ".recipe",
    ".rsp",
}

ENGINE_ASSET_EXTS = {
    ".hlsl",
    ".shadergraph",
    ".shadersubgraph",
    ".uss",
    ".uxml",
    ".frag",
    ".vert",
    ".geom",
    ".compute",
    ".tesc",
    ".tese",
    ".raytrace",
    ".glsl",
    ".glslinc",
    ".meta",
    ".prefab",
    ".unity",
    ".asset",
    ".mat",
    ".shader",
    ".cginc",
    ".controller",
    ".anim",
    ".overridecontroller",
    ".mixer",
    ".rendertexture",
    ".cubemap",
    ".fbx",
    ".blend",
    ".3ds",
    ".max",
    ".ma",
    ".mb",
    ".unitypackage",
    ".asmdef",
    ".asmref",
}

VIRTUAL_DISK_EXTS = {
    ".vmdk",
    ".vdi",
    ".vhd",
    ".vhdx",
    ".qcow2",
    ".iso",
    ".img",
    ".dmg",
    ".vfd",
    ".ova",
    ".ovf",
}

MODEL_EXTS = {
    ".pt",
    ".pth",
    ".ckpt",
    ".safetensors",
    ".onnx",
    ".gguf",
    ".ggml",
    ".h5",
    ".tflite",
    ".pb",
    ".pkl",
    ".pickle",
    ".npy",
    ".npz",
    ".joblib",
}

ARCHIVE_EXTS = {
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".cab",
    ".zst",
}

STUDY_DOC_EXTS = {
    ".pdf",
    ".ppt",
    ".pptx",
    ".doc",
    ".docx",
    ".odt",
    ".odp",
    ".md",
    ".markdown",
    ".txt",
    ".rtf",
    ".epub",
}

WEBPAGE_EXTS = {".html", ".htm"}

SPREADSHEET_EXTS = {".xls", ".xlsx", ".xlsm", ".csv", ".ods"}
NOTEBOOK_EXTS = {".ipynb"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".svg"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
SOURCE_CODE_EXTS = {
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".java",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".cs",
    ".go",
    ".rs",
    ".sql",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
    ".lua",
    ".r",
    ".m",
    ".swift",
    ".kt",
    ".php",
    ".rb",
}
DATA_EXTS = {".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".conf"}
PLAIN_TEXT_EXTS = {".md", ".markdown", ".txt", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".html", ".htm"} | SOURCE_CODE_EXTS
OFFICE_OPENXML_EXTS = {".docx", ".pptx", ".xlsx"}
OFFICE_LEGACY_EXTS = {".doc", ".ppt", ".xls", ".rtf"}


@dataclass(frozen=True)
class InventoryLimits:
    archive_max_bytes: int = DEFAULT_ARCHIVE_MAX_BYTES
    large_binary_max_bytes: int = DEFAULT_LARGE_BINARY_MAX_BYTES
    fingerprint_sample_bytes: int = DEFAULT_FINGERPRINT_SAMPLE_BYTES


@dataclass
class InventoryRecord:
    logical_uri: str
    course_candidate: str
    format: str
    size: int
    fingerprint: str
    classification: str
    extraction_support: str
    duplicate_status: str
    risk_flags: list[str]


@dataclass
class ClassificationDecision:
    format: str
    classification: str
    extraction_support: str
    risk_flags: list[str]
    disposition: str
    exclusion_reason: str | None = None


@dataclass
class InventoryTotals:
    files_seen: int = 0
    bytes_seen: int = 0
    dirs_pruned: int = 0
    files_excluded: int = 0
    bytes_excluded: int = 0
    files_inventoried: int = 0
    bytes_inventoried: int = 0
    unique_candidates: int = 0
    duplicate_groups: int = 0
    exclusion_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    pruned_directories: list[dict[str, Any]] = field(default_factory=list)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only inventory of an external study-source tree"
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("SA_SOURCE_ROOT", str(DEFAULT_ROOT)),
        help="External source root. Default: D:\\111_Others_Subjects",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="JSON report path. Default: reports/source-inventory.json",
    )
    parser.add_argument(
        "--archive-max-bytes",
        type=int,
        default=DEFAULT_ARCHIVE_MAX_BYTES,
        help="Archives larger than this are excluded. Default: 64MiB",
    )
    parser.add_argument(
        "--large-binary-max-bytes",
        type=int,
        default=DEFAULT_LARGE_BINARY_MAX_BYTES,
        help="Non-document binaries larger than this are excluded. Default: 100MiB",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def _strip_extended_prefix(value: str) -> str:
    prefix = chr(92) * 2 + "?" + chr(92)
    prefix_unc = prefix + "UNC" + chr(92)
    if value.startswith(prefix_unc):
        return chr(92) * 2 + value[len(prefix_unc):]
    if value.startswith(prefix):
        return value[len(prefix):]
    return value


def walk_root(path: Path) -> Path:
    resolved = path.resolve()
    if os.name != "nt":
        return resolved
    text = str(resolved)
    prefix = chr(92) * 2 + "?" + chr(92)
    if text.startswith(prefix):
        return resolved
    if text.startswith(chr(92) * 2):
        return Path(prefix + "UNC" + chr(92) + text[2:])
    return Path(prefix + text)


def emit_progress(seen: int, *, force: bool = False) -> None:
    if force or (seen and seen % 20000 == 0):
        print(f"scanned {seen} files", file=sys.stderr, flush=True)


def display_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.name


def to_logical_uri(path: Path, root: Path) -> str:
    path_text = _strip_extended_prefix(str(path.resolve(strict=False)))
    root_text = _strip_extended_prefix(str(root.resolve(strict=False)))
    relative = Path(path_text).relative_to(Path(root_text))
    uri = unicodedata.normalize("NFC", relative.as_posix())
    if uri == ".":
        raise ValueError("logical_uri must be a file inside the source root")
    if uri.startswith("/") or uri.startswith("//"):
        raise ValueError("logical_uri must be relative")
    return uri


def course_candidate_for(logical_uri: str) -> str:
    first = logical_uri.split("/", 1)[0]
    if first == logical_uri and "." in first:
        return "unmapped"
    return COURSE_CANDIDATES.get(first, "unmapped")


def _format_name(suffix: str) -> str:
    if not suffix:
        return "none"
    return suffix.lower().lstrip(".")


def classify_file(name: str, size: int, limits: InventoryLimits) -> ClassificationDecision:
    lowered = name.lower()
    suffix = Path(lowered).suffix
    fmt = _format_name(suffix)
    flags: list[str] = []
    if size == 0:
        flags.append("empty")

    if lowered in NOISE_FILES:
        return ClassificationDecision(fmt, "os_noise", "none", flags, "counted_only", "os_noise")
    if suffix in VIRTUAL_DISK_EXTS:
        flags.append("virtual_disk")
        return ClassificationDecision(fmt, "virtual_disk", "none", flags, "notable_exclusion", "virtual_disk")
    if suffix in MODEL_EXTS or (suffix == ".bin" and size >= limits.large_binary_max_bytes):
        flags.append("model_binary")
        return ClassificationDecision(fmt, "model_binary", "none", flags, "notable_exclusion", "model_binary")
    if suffix in BUILD_ARTIFACT_EXTS:
        flags.append("build_artifact")
        return ClassificationDecision(fmt, "build_artifact", "none", flags, "counted_only", "build_artifact")
    if suffix in ENGINE_ASSET_EXTS:
        flags.append("engine_asset")
        return ClassificationDecision(fmt, "engine_asset", "none", flags, "counted_only", "engine_asset")
    if suffix in ARCHIVE_EXTS:
        if size > limits.archive_max_bytes:
            flags.append("oversized_archive")
            return ClassificationDecision(fmt, "archive", "archive", flags, "notable_exclusion", "oversized_archive")
        return ClassificationDecision(fmt, "archive", "archive", flags, "candidate")
    if suffix in STUDY_DOC_EXTS:
        extraction = extraction_support_for(suffix)
        if size > limits.large_binary_max_bytes:
            flags.append("large_document")
        return ClassificationDecision(fmt, "study_document", extraction, flags, "candidate")
    if suffix in WEBPAGE_EXTS:
        return ClassificationDecision(fmt, "webpage", "plain_text", flags, "candidate")
    if suffix in NOTEBOOK_EXTS:
        return ClassificationDecision(fmt, "notebook", "plain_text", flags, "candidate")
    if suffix in SPREADSHEET_EXTS:
        return ClassificationDecision(fmt, "spreadsheet", extraction_support_for(suffix), flags, "candidate")
    if suffix in IMAGE_EXTS:
        return ClassificationDecision(fmt, "image", "image_ocr", flags, "candidate")
    if suffix in AUDIO_EXTS:
        return ClassificationDecision(fmt, "audio", "audio_transcript", flags, "candidate")
    if suffix in VIDEO_EXTS:
        if size > limits.large_binary_max_bytes:
            flags.append("large_binary")
            return ClassificationDecision(fmt, "video", "video_transcript", flags, "notable_exclusion", "large_binary")
        return ClassificationDecision(fmt, "video", "video_transcript", flags, "candidate")
    if suffix in SOURCE_CODE_EXTS:
        return ClassificationDecision(fmt, "source_code", "plain_text", flags, "candidate")
    if suffix in DATA_EXTS:
        return ClassificationDecision(fmt, "data", "plain_text", flags, "candidate")
    if size > limits.large_binary_max_bytes:
        flags.append("large_binary")
        return ClassificationDecision(fmt, "binary", "none", flags, "notable_exclusion", "large_binary")
    return ClassificationDecision(fmt, "other", "none", flags, "candidate")


def extraction_support_for(suffix: str) -> str:
    if suffix in PLAIN_TEXT_EXTS:
        if suffix in {".md", ".markdown"}:
            return "markdown"
        return "plain_text"
    if suffix == ".pdf":
        return "pdf"
    if suffix in OFFICE_OPENXML_EXTS:
        return "office_openxml"
    if suffix in OFFICE_LEGACY_EXTS:
        return "office_legacy"
    if suffix in IMAGE_EXTS:
        return "image_ocr"
    if suffix in ARCHIVE_EXTS:
        return "archive"
    return "none"


def skip_dir_reason(name: str, sibling_names: Iterable[str]) -> str | None:
    lowered = name.lower()
    if lowered in SKIP_DIR_NAMES:
        return SKIP_DIR_NAMES[lowered]
    siblings = {item.lower() for item in sibling_names}
    unity_like = "assets" in siblings and (
        "library" in siblings or "projectsettings" in siblings or "packages" in siblings
    )
    if unity_like and lowered in UNITY_SIBLING_SKIP_DIRS:
        return UNITY_SIBLING_SKIP_DIRS[lowered]
    return None


def _add_exclusion(totals: InventoryTotals, reason: str, files: int, nbytes: int) -> None:
    bucket = totals.exclusion_counts.setdefault(reason, {"files": 0, "bytes": 0})
    bucket["files"] += files
    bucket["bytes"] += nbytes
    totals.files_excluded += files
    totals.bytes_excluded += nbytes


def count_tree(path: Path) -> tuple[int, int]:
    files = 0
    nbytes = 0
    for dirpath, dirnames, filenames in os.walk(path, topdown=True, followlinks=False):
        dirnames[:] = [name for name in dirnames if not _is_symlink(Path(dirpath) / name)]
        for filename in filenames:
            file_path = Path(dirpath) / filename
            if _is_symlink(file_path):
                files += 1
                continue
            try:
                size = file_path.stat().st_size
            except OSError:
                files += 1
                continue
            files += 1
            nbytes += size
    return files, nbytes


def _is_symlink(path: Path) -> bool:
    try:
        return path.is_symlink()
    except OSError:
        return False


def fingerprint_file(path: Path, size: int, sample_bytes: int) -> str:
    if size == 0:
        return "sha256:" + hashlib.sha256(b"").hexdigest()
    with path.open("rb") as handle:
        first = handle.read(sample_bytes)
        if size <= sample_bytes * 2:
            payload = first + handle.read()
            return "sha256:" + hashlib.sha256(payload).hexdigest()
        handle.seek(max(0, size - sample_bytes))
        last = handle.read(sample_bytes)
    digest = hashlib.sha256()
    digest.update(size.to_bytes(8, "little"))
    digest.update(first)
    digest.update(last)
    return "sha256-sampled:" + digest.hexdigest()


def apply_duplicate_status(records: list[InventoryRecord]) -> int:
    groups: dict[str, list[InventoryRecord]] = defaultdict(list)
    for record in records:
        if record.fingerprint.startswith("unreadable"):
            record.duplicate_status = "unique"
            continue
        groups[record.fingerprint].append(record)
    duplicate_groups = 0
    for group in groups.values():
        if len(group) == 1:
            group[0].duplicate_status = "unique"
            continue
        duplicate_groups += 1
        ordered = sorted(group, key=lambda item: item.logical_uri)
        ordered[0].duplicate_status = "primary"
        for duplicate in ordered[1:]:
            duplicate.duplicate_status = "duplicate"
            if "duplicate" not in duplicate.risk_flags:
                duplicate.risk_flags.append("duplicate")
    return duplicate_groups


def scan_source_tree(
    root: Path,
    *,
    limits: InventoryLimits | None = None,
) -> dict[str, Any]:
    limits = limits or InventoryLimits()
    generated_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_label": SOURCE_LABEL,
        "root_present": False,
        "read_only": True,
        "copied_files": False,
        "parsed_full_text": False,
        "modified_source_root": False,
        "built_vector_index": False,
        "limits": asdict(limits),
        "summary": {},
        "records": [],
        "notable_exclusions": [],
    }
    if not root.exists() or not root.is_dir():
        report["summary"] = _empty_summary()
        return report

    resolved_root = walk_root(root)
    totals = InventoryTotals()
    records: list[InventoryRecord] = []
    notable: list[InventoryRecord] = []
    pruned_dirs: list[dict[str, Any]] = []

    for dirpath, dirnames, filenames in os.walk(resolved_root, topdown=True, followlinks=False):
        current = Path(dirpath)
        siblings = list(dirnames)
        kept: list[str] = []
        for name in dirnames:
            child = current / name
            if _is_symlink(child):
                files, nbytes = 1, 0
                totals.files_seen += files
                _add_exclusion(totals, "symlink", files, nbytes)
                totals.dirs_pruned += 1
                continue
            reason = skip_dir_reason(name, siblings)
            if reason is None:
                kept.append(name)
                continue
            files, nbytes = count_tree(child)
            totals.files_seen += files
            totals.bytes_seen += nbytes
            totals.dirs_pruned += 1
            _add_exclusion(totals, reason, files, nbytes)
            try:
                logical = to_logical_uri(child, resolved_root)
            except ValueError:
                logical = unicodedata.normalize("NFC", name)
            pruned_dirs.append(
                {
                    "logical_uri": logical,
                    "reason": reason,
                    "files": files,
                    "bytes": nbytes,
                }
            )
        dirnames[:] = kept

        for filename in filenames:
            file_path = current / filename
            totals.files_seen += 1
            if _is_symlink(file_path):
                _add_exclusion(totals, "symlink", 1, 0)
                continue
            try:
                size = file_path.stat().st_size
            except OSError:
                _add_exclusion(totals, "unreadable", 1, 0)
                continue
            totals.bytes_seen += size
            try:
                logical_uri = to_logical_uri(file_path, resolved_root)
            except ValueError:
                _add_exclusion(totals, "unreadable", 1, size)
                continue
            decision = classify_file(filename, size, limits)
            if decision.disposition == "counted_only":
                _add_exclusion(totals, decision.exclusion_reason or decision.classification, 1, size)
                continue
            fingerprint = "unreadable"
            risk_flags = list(decision.risk_flags)
            try:
                if decision.disposition == "notable_exclusion" and (
                    decision.exclusion_reason in {"virtual_disk", "model_binary", "large_binary"}
                    or size > limits.large_binary_max_bytes
                ):
                    fingerprint = f"size-only:{size}"
                else:
                    fingerprint = fingerprint_file(file_path, size, limits.fingerprint_sample_bytes)
            except OSError:
                fingerprint = "unreadable"
                risk_flags.append("unreadable")
            record = InventoryRecord(
                logical_uri=logical_uri,
                course_candidate=course_candidate_for(logical_uri),
                format=decision.format,
                size=size,
                fingerprint=fingerprint,
                classification=decision.classification,
                extraction_support=decision.extraction_support,
                duplicate_status="unique",
                risk_flags=risk_flags,
            )
            if decision.disposition == "notable_exclusion":
                _add_exclusion(totals, decision.exclusion_reason or decision.classification, 1, size)
                notable.append(record)
                continue
            records.append(record)
            totals.files_inventoried += 1
            totals.bytes_inventoried += size

    records.sort(key=lambda item: item.logical_uri)
    notable.sort(key=lambda item: item.logical_uri)
    duplicate_groups = apply_duplicate_status(records)
    unique_candidates = sum(1 for item in records if item.duplicate_status in {"unique", "primary"})
    duplicate_files = sum(1 for item in records if item.duplicate_status == "duplicate")
    if duplicate_files:
        _add_exclusion(totals, "duplicate", duplicate_files, sum(item.size for item in records if item.duplicate_status == "duplicate"))
        totals.files_inventoried -= duplicate_files
        totals.bytes_inventoried -= sum(item.size for item in records if item.duplicate_status == "duplicate")
    totals.unique_candidates = unique_candidates
    totals.duplicate_groups = duplicate_groups
    pruned_dirs.sort(key=lambda item: item["files"], reverse=True)
    totals.pruned_directories = pruned_dirs[:PRUNED_DIRECTORY_LIMIT]
    counted_records = [item for item in records if item.duplicate_status != "duplicate"]

    report["root_present"] = True
    report["summary"] = {
        "files_seen": totals.files_seen,
        "bytes_seen": totals.bytes_seen,
        "dirs_pruned": totals.dirs_pruned,
        "files_excluded": totals.files_excluded,
        "bytes_excluded": totals.bytes_excluded,
        "files_inventoried": totals.files_inventoried,
        "bytes_inventoried": totals.bytes_inventoried,
        "unique_candidates": totals.unique_candidates,
        "duplicate_groups": totals.duplicate_groups,
        "exclusion_counts": dict(sorted(totals.exclusion_counts.items())),
        "classification_counts": _count_field(counted_records, "classification"),
        "course_counts": _count_field(counted_records, "course_candidate"),
        "format_counts": _count_field(counted_records, "format"),
        "extraction_support_counts": _count_field(counted_records, "extraction_support"),
        "pruned_directories": totals.pruned_directories,
    }
    report["records"] = [asdict(item) for item in records]
    report["notable_exclusions"] = [asdict(item) for item in notable]
    return report


def _count_field(records: list[InventoryRecord], field_name: str) -> dict[str, int]:
    counter: Counter[str] = Counter(getattr(item, field_name) for item in records)
    return dict(counter.most_common())


def _empty_summary() -> dict[str, Any]:
    return {
        "files_seen": 0,
        "bytes_seen": 0,
        "dirs_pruned": 0,
        "files_excluded": 0,
        "bytes_excluded": 0,
        "files_inventoried": 0,
        "bytes_inventoried": 0,
        "unique_candidates": 0,
        "duplicate_groups": 0,
        "exclusion_counts": {},
        "classification_counts": {},
        "course_counts": {},
        "format_counts": {},
        "extraction_support_counts": {},
        "pruned_directories": [],
    }


def assert_output_outside_root(output: Path, root: Path) -> None:
    if not root.exists():
        return
    try:
        output.resolve().relative_to(root.resolve())
    except ValueError:
        return
    raise ValueError("refusing to write inventory output inside the source root")


def write_report(report: Mapping[str, Any], output: Path, *, repo_root: Path = REPO_ROOT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path = output.with_name(f"{output.stem}-summary.json")
    summary_doc = {key: value for key, value in report.items() if key != "records"}
    summary_path.write_text(json.dumps(summary_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def render_summary(report: Mapping[str, Any], output: Path | None = None, *, repo_root: Path = REPO_ROOT) -> str:
    summary = report["summary"]
    lines = [
        f"Source inventory ({report['schema']})",
        f"root: {report['source_label']} ({'present' if report['root_present'] else 'missing'})",
        f"files_seen: {summary['files_seen']}",
        f"excluded: {summary['files_excluded']}",
        f"inventoried: {summary['files_inventoried']} (unique_candidates={summary['unique_candidates']}, duplicate_groups={summary['duplicate_groups']})",
    ]
    exclusion = summary.get("exclusion_counts") or {}
    if exclusion:
        parts = [f"{name}={item['files']}" for name, item in exclusion.items()]
        lines.append("exclusion_counts: " + ", ".join(parts))
    classification = summary.get("classification_counts") or {}
    if classification:
        parts = [f"{name}={count}" for name, count in classification.items()]
        lines.append("classification_counts: " + ", ".join(parts))
    if output is not None:
        lines.append(f"wrote: {display_path(output, repo_root)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root)
    output = Path(args.output)
    limits = InventoryLimits(
        archive_max_bytes=args.archive_max_bytes,
        large_binary_max_bytes=args.large_binary_max_bytes,
    )
    assert_output_outside_root(output, root)
    report = scan_source_tree(root, limits=limits)
    write_report(report, output)
    print(render_summary(report, output))
    return 0 if report["root_present"] else 2


if __name__ == "__main__":
    sys.exit(main())

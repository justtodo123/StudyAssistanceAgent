"""Hermetic policy observers for the M8 network-acquisition authority candidate.

This module validates declared acquisition events only.  It performs no network I/O,
starts no child process, and writes no wheelhouse.  A future executor must supply
observed events from an independently accepted collector implementation.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PureWindowsPath
from typing import Any, Mapping
from urllib.parse import urlsplit

CANONICALIZATION_ID = "sa-json-c14n-v1"
OBSERVER_FORMAT = "m8-network-acquisition-observer-candidate-v1"
ALLOWED_INITIAL_HOSTS = {"pypi.org"}
ALLOWED_REDIRECT_HOSTS = {"pypi.org", "files.pythonhosted.org"}
ALLOWED_EXECUTABLE = r"C:\Program Files\Git\mingw64\bin\curl.exe"
PREPARATION_ROOT = PureWindowsPath(r"D:\面试实习\m8-network-acquisition-cycle-20260918-r01")
PERSISTENT_RELATIVE_FILES = {
    "authority.json",
    "inventory.json",
    "provenance.json",
    "events/network.jsonl",
    "events/process.jsonl",
    "events/redaction.jsonl",
    "events/write.jsonl",
}
FORBIDDEN_ROOTS = tuple(
    PureWindowsPath(value)
    for value in (
        r"D:\Git Demo\StudyAssistanceAgent",
        r"D:\111_Others_Subjects",
        r"C:\Users\Lenovo\AppData\Local\pip\Cache",
    )
)
ERROR_CODES = (
    "M8ACQ_E001_INVALID_EVENT",
    "M8ACQ_E002_NON_HTTPS",
    "M8ACQ_E003_INITIAL_HOST_DENIED",
    "M8ACQ_E004_REDIRECT_HOST_DENIED",
    "M8ACQ_E005_REDIRECT_LIMIT",
    "M8ACQ_E006_TLS_UNVERIFIED",
    "M8ACQ_E007_CERT_BYPASS",
    "M8ACQ_E008_PROXY_PRESENT",
    "M8ACQ_E009_AUTH_PRESENT",
    "M8ACQ_E010_METHOD_DENIED",
    "M8ACQ_E011_PROCESS_DENIED",
    "M8ACQ_E012_PROCESS_COUNT",
    "M8ACQ_E013_SHELL_ENABLED",
    "M8ACQ_E014_WRITE_OUTSIDE_ROOT",
    "M8ACQ_E015_FORBIDDEN_ROOT",
    "M8ACQ_E016_REPARSE_POINT",
    "M8ACQ_E017_FILE_TYPE_DENIED",
    "M8ACQ_E018_LIMIT_EXCEEDED",
    "M8ACQ_E019_DIGEST_MISMATCH",
    "M8ACQ_E020_REDACTION_MATCH",
    "M8ACQ_E021_OBSERVER_INCOMPLETE",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)authorization\s*:"),
    re.compile(r"(?i)proxy-authorization\s*:"),
    re.compile(r"(?i)(token|password|passwd|secret|api[_-]?key)\s*[=:]"),
    re.compile(r"(?i)https?://[^/\s:@]+:[^/\s@]+@"),
)


class ObservationError(ValueError):
    """Stable fail-closed observation error."""

    def __init__(self, code: str, detail: str) -> None:
        if code not in ERROR_CODES:
            raise ValueError("unknown observer error code")
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise ObservationError(code, detail)


def _host(url: str, *, initial: bool) -> str:
    parsed = urlsplit(url)
    _require(parsed.scheme == "https", "M8ACQ_E002_NON_HTTPS", url)
    _require(not parsed.username and not parsed.password, "M8ACQ_E009_AUTH_PRESENT", url)
    host = (parsed.hostname or "").lower()
    allowed = ALLOWED_INITIAL_HOSTS if initial else ALLOWED_REDIRECT_HOSTS
    code = "M8ACQ_E003_INITIAL_HOST_DENIED" if initial else "M8ACQ_E004_REDIRECT_HOST_DENIED"
    _require(host in allowed, code, host)
    return host


def observe_network(event: Mapping[str, Any]) -> dict[str, Any]:
    required = {"method", "initial_url", "redirect_chain", "final_url", "tls_verified", "certificate_bypass", "proxy", "authentication"}
    _require(required <= set(event), "M8ACQ_E001_INVALID_EVENT", "network fields")
    _require(event["method"] == "GET", "M8ACQ_E010_METHOD_DENIED", str(event["method"]))
    _host(str(event["initial_url"]), initial=True)
    chain = event["redirect_chain"]
    _require(isinstance(chain, list), "M8ACQ_E001_INVALID_EVENT", "redirect_chain")
    _require(len(chain) <= 3, "M8ACQ_E005_REDIRECT_LIMIT", str(len(chain)))
    for url in chain:
        _host(str(url), initial=False)
    final_host = _host(str(event["final_url"]), initial=False)
    _require(event["tls_verified"] is True, "M8ACQ_E006_TLS_UNVERIFIED", "tls")
    _require(event["certificate_bypass"] is False, "M8ACQ_E007_CERT_BYPASS", "certificate")
    _require(event["proxy"] in (None, ""), "M8ACQ_E008_PROXY_PRESENT", "proxy")
    _require(event["authentication"] in (None, ""), "M8ACQ_E009_AUTH_PRESENT", "authentication")
    return {"observer": "network", "status": "PASS", "final_host": final_host, "redirect_count": len(chain)}


def observe_process(event: Mapping[str, Any]) -> dict[str, Any]:
    required = {"executable", "process_count", "shell"}
    _require(required <= set(event), "M8ACQ_E001_INVALID_EVENT", "process fields")
    _require(str(event["executable"]).casefold() == ALLOWED_EXECUTABLE.casefold(), "M8ACQ_E011_PROCESS_DENIED", str(event["executable"]))
    _require(event["process_count"] == 1, "M8ACQ_E012_PROCESS_COUNT", str(event["process_count"]))
    _require(event["shell"] is False, "M8ACQ_E013_SHELL_ENABLED", "shell")
    return {"observer": "process", "status": "PASS", "process_count": 1}


_WINDOWS_RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
_WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"|?*')


def _has_unsafe_raw_path_syntax(raw_path: str) -> bool:
    """Reject spellings that PureWindowsPath would silently normalize."""
    if "\x00" in raw_path:
        return True
    if raw_path.startswith("\\\\"):
        return True
    if len(raw_path) >= 3 and raw_path[1] == ":" and raw_path[0].isalpha():
        body = raw_path[2:]
        leading_separators = len(body) - len(body.lstrip("\\/"))
        if leading_separators != 1:
            return True
        body = body[1:]
    else:
        body = raw_path
    if "\\" in body and "/" in body:
        return True
    components = re.split(r"[\\/]", body)
    return any(component in {"", "."} for component in components)


def _has_unsafe_component(path: PureWindowsPath) -> bool:
    for component in path.parts:
        if component in {path.anchor, "\\"}:
            continue
        if ".." in component:
            return True
        if any(ord(character) < 32 or character in _WINDOWS_FORBIDDEN_CHARACTERS for character in component):
            return True
        if component.endswith((".", " ")):
            return True
        stem = component.split(".", 1)[0].casefold()
        if stem in _WINDOWS_RESERVED_NAMES:
            return True
    return False


def _within(path: PureWindowsPath, root: PureWindowsPath) -> bool:
    if _has_unsafe_component(path):
        return False
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _allowed_relative_path(relative_path: str, kind: str) -> bool:
    if relative_path in PERSISTENT_RELATIVE_FILES:
        return kind == "evidence"
    if relative_path.startswith("wheels/"):
        filename = relative_path.removeprefix("wheels/")
        if "/" in filename or not filename:
            return False
        if kind == "wheel":
            return filename.endswith(".whl")
        if kind == "partial":
            return filename.endswith(".whl.partial")
    return False


def _bounded_int(value: Any, maximum: int, detail: str) -> int:
    _require(
        isinstance(value, int) and not isinstance(value, bool),
        "M8ACQ_E001_INVALID_EVENT",
        detail,
    )
    _require(0 <= value <= maximum, "M8ACQ_E018_LIMIT_EXCEEDED", detail)
    return value


def observe_write(event: Mapping[str, Any]) -> dict[str, Any]:
    required = {"path", "is_reparse_point", "kind", "byte_size", "total_byte_size", "file_count"}
    _require(required <= set(event), "M8ACQ_E001_INVALID_EVENT", "write fields")
    raw_path = str(event["path"])
    _require(not _has_unsafe_raw_path_syntax(raw_path), "M8ACQ_E014_WRITE_OUTSIDE_ROOT", raw_path)
    path = PureWindowsPath(raw_path)
    _require(not _has_unsafe_component(path), "M8ACQ_E014_WRITE_OUTSIDE_ROOT", str(path))
    for root in FORBIDDEN_ROOTS:
        _require(not _within(path, root), "M8ACQ_E015_FORBIDDEN_ROOT", str(path))
    _require(_within(path, PREPARATION_ROOT), "M8ACQ_E014_WRITE_OUTSIDE_ROOT", str(path))
    _require(event["is_reparse_point"] is False, "M8ACQ_E016_REPARSE_POINT", str(path))
    _require(event["kind"] in {"wheel", "partial", "evidence"}, "M8ACQ_E017_FILE_TYPE_DENIED", str(event["kind"]))
    relative_path = str(path.relative_to(PREPARATION_ROOT)).replace("\\", "/")
    _require(_allowed_relative_path(relative_path, str(event["kind"])), "M8ACQ_E017_FILE_TYPE_DENIED", relative_path)
    _bounded_int(event["byte_size"], 536870912, "single bytes")
    _bounded_int(event["total_byte_size"], 2147483648, "total bytes")
    _bounded_int(event["file_count"], 256, "file count")
    return {"observer": "write", "status": "PASS", "relative_path": relative_path}


def observe_redaction(event: Mapping[str, Any]) -> dict[str, Any]:
    required = {"text", "declared_sha256", "content_bytes"}
    _require(required <= set(event), "M8ACQ_E001_INVALID_EVENT", "redaction fields")
    content = event["content_bytes"]
    _require(isinstance(content, bytes), "M8ACQ_E001_INVALID_EVENT", "content_bytes")
    _require(sha256_bytes(content) == event["declared_sha256"], "M8ACQ_E019_DIGEST_MISMATCH", "sha256")
    text = str(event["text"])
    for pattern in SECRET_PATTERNS:
        _require(pattern.search(text) is None, "M8ACQ_E020_REDACTION_MATCH", pattern.pattern)
    return {"observer": "redaction", "status": "PASS", "byte_size": len(content)}


def observe_all(events: Mapping[str, Mapping[str, Any]]) -> bytes:
    _require(set(events) == {"network", "process", "write", "redaction"}, "M8ACQ_E021_OBSERVER_INCOMPLETE", "four observers required")
    result = {
        "canonicalization_id": CANONICALIZATION_ID,
        "error_code_registry": list(ERROR_CODES),
        "format": OBSERVER_FORMAT,
        "results": [
            observe_network(events["network"]),
            observe_process(events["process"]),
            observe_redaction(events["redaction"]),
            observe_write(events["write"]),
        ],
    }
    return canonical_bytes(result)

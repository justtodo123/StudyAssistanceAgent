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
    re.compile(r"(?i)authorization\s*[=:]"),
    re.compile(r"(?i)proxy-authorization\s*[=:]"),
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
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        raise ObservationError("M8ACQ_E001_INVALID_EVENT", "canonical json") from None
    return encoded + b"\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise ObservationError(code, detail)


def _require_mapping(value: Any, detail: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), "M8ACQ_E001_INVALID_EVENT", detail)
    return value


def _host(url: str, *, initial: bool) -> str:
    code = "M8ACQ_E003_INITIAL_HOST_DENIED" if initial else "M8ACQ_E004_REDIRECT_HOST_DENIED"
    _require(
        isinstance(url, str)
        and bool(url)
        and not any(character.isspace() or ord(character) < 32 for character in url),
        "M8ACQ_E001_INVALID_EVENT",
        "url syntax",
    )
    try:
        parsed = urlsplit(url)
        has_userinfo = bool(parsed.username or parsed.password)
        host = (parsed.hostname or "").casefold()
        port = parsed.port
    except (TypeError, ValueError):
        raise ObservationError("M8ACQ_E001_INVALID_EVENT", "url syntax") from None
    _require(parsed.scheme == "https", "M8ACQ_E002_NON_HTTPS", "scheme")
    _require(not has_userinfo, "M8ACQ_E009_AUTH_PRESENT", "url credentials")
    _require(
        host != "" and parsed.path != "" and parsed.query == "" and parsed.fragment == "",
        "M8ACQ_E001_INVALID_EVENT",
        "url form",
    )
    _require(port is None or port == 443, "M8ACQ_E001_INVALID_EVENT", "url port")
    allowed = ALLOWED_INITIAL_HOSTS if initial else ALLOWED_REDIRECT_HOSTS
    _require(host in allowed, code, host)
    return host


def observe_network(event: Mapping[str, Any]) -> dict[str, Any]:
    event = _require_mapping(event, "network event")
    required = {
        "method", "initial_url", "redirect_chain", "final_url",
        "tls_verified", "certificate_bypass", "proxy", "authentication",
    }
    _require(set(event) == required, "M8ACQ_E001_INVALID_EVENT", "network fields")
    _require(event["method"] == "GET", "M8ACQ_E010_METHOD_DENIED", "method")
    initial_url = event["initial_url"]
    _host(initial_url, initial=True)
    chain = event["redirect_chain"]
    _require(isinstance(chain, list), "M8ACQ_E001_INVALID_EVENT", "redirect_chain")
    _require(len(chain) <= 3, "M8ACQ_E005_REDIRECT_LIMIT", str(len(chain)))
    for url in chain:
        _host(url, initial=False)
    final_url = event["final_url"]
    final_host = _host(final_url, initial=False)
    expected_final_url = initial_url if not chain else chain[-1]
    _require(final_url == expected_final_url, "M8ACQ_E001_INVALID_EVENT", "redirect binding")
    _require(event["tls_verified"] is True, "M8ACQ_E006_TLS_UNVERIFIED", "tls")
    _require(event["certificate_bypass"] is False, "M8ACQ_E007_CERT_BYPASS", "certificate")
    _require(event["proxy"] in (None, ""), "M8ACQ_E008_PROXY_PRESENT", "proxy")
    _require(event["authentication"] in (None, ""), "M8ACQ_E009_AUTH_PRESENT", "authentication")
    return {"observer": "network", "status": "PASS", "final_host": final_host, "redirect_count": len(chain)}


def observe_process(event: Mapping[str, Any]) -> dict[str, Any]:
    event = _require_mapping(event, "process event")
    required = {"executable", "process_count", "shell"}
    _require(set(event) == required, "M8ACQ_E001_INVALID_EVENT", "process fields")
    executable = event["executable"]
    _require(isinstance(executable, str), "M8ACQ_E001_INVALID_EVENT", "executable")
    _require(executable.casefold() == ALLOWED_EXECUTABLE.casefold(), "M8ACQ_E011_PROCESS_DENIED", "executable")
    _require(isinstance(event["process_count"], int) and not isinstance(event["process_count"], bool), "M8ACQ_E001_INVALID_EVENT", "process_count")
    _require(event["process_count"] == 1, "M8ACQ_E012_PROCESS_COUNT", "process_count")
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
        if len(component) > 255:
            return True
        if "(" in component:
            return True
        if ".." in component:
            return True
        if any(ord(character) < 32 or character in _WINDOWS_FORBIDDEN_CHARACTERS for character in component):
            return True
        if component.endswith((".", " ")):
            return True
        stem = component.split(".", 1)[0].casefold()
        if stem in _WINDOWS_RESERVED_NAMES or stem in {"conin$", "conout$"}:
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
    _require(isinstance(value, int) and not isinstance(value, bool), "M8ACQ_E001_INVALID_EVENT", detail)
    _require(0 <= value <= maximum, "M8ACQ_E018_LIMIT_EXCEEDED", detail)
    return value


def observe_write(event: Mapping[str, Any]) -> dict[str, Any]:
    event = _require_mapping(event, "write event")
    required = {"path", "is_reparse_point", "kind", "byte_size", "total_byte_size", "file_count"}
    _require(set(event) == required, "M8ACQ_E001_INVALID_EVENT", "write fields")
    _require(isinstance(event["path"], str), "M8ACQ_E001_INVALID_EVENT", "path")
    raw_path = event["path"]
    _require(not _has_unsafe_raw_path_syntax(raw_path), "M8ACQ_E014_WRITE_OUTSIDE_ROOT", "path syntax")
    path = PureWindowsPath(raw_path)
    _require(not _has_unsafe_component(path), "M8ACQ_E014_WRITE_OUTSIDE_ROOT", "path component")
    for root in FORBIDDEN_ROOTS:
        _require(not _within(path, root), "M8ACQ_E015_FORBIDDEN_ROOT", "forbidden root")
    _require(_within(path, PREPARATION_ROOT), "M8ACQ_E014_WRITE_OUTSIDE_ROOT", "write root")
    _require(event["is_reparse_point"] is False, "M8ACQ_E016_REPARSE_POINT", "reparse point")
    _require(event["kind"] in {"wheel", "partial", "evidence"}, "M8ACQ_E017_FILE_TYPE_DENIED", "kind")
    relative_path = str(path.relative_to(PREPARATION_ROOT)).replace("\\", "/")
    _require(_allowed_relative_path(relative_path, event["kind"]), "M8ACQ_E017_FILE_TYPE_DENIED", relative_path)
    byte_size = _bounded_int(event["byte_size"], 536870912, "single bytes")
    total_byte_size = _bounded_int(event["total_byte_size"], 2147483648, "total bytes")
    file_count = _bounded_int(event["file_count"], 256, "file count")
    _require(file_count >= 1, "M8ACQ_E018_LIMIT_EXCEEDED", "file count")
    _require(total_byte_size >= byte_size, "M8ACQ_E018_LIMIT_EXCEEDED", "total bytes")
    return {"observer": "write", "status": "PASS", "relative_path": relative_path}


def observe_redaction(event: Mapping[str, Any]) -> dict[str, Any]:
    event = _require_mapping(event, "redaction event")
    required = {"text", "declared_sha256", "content_bytes"}
    _require(set(event) == required, "M8ACQ_E001_INVALID_EVENT", "redaction fields")
    content = event["content_bytes"]
    _require(isinstance(content, bytes), "M8ACQ_E001_INVALID_EVENT", "content_bytes")
    declared_sha256 = event["declared_sha256"]
    _require(isinstance(declared_sha256, str), "M8ACQ_E001_INVALID_EVENT", "declared_sha256")
    _require(sha256_bytes(content) == declared_sha256, "M8ACQ_E019_DIGEST_MISMATCH", "sha256")
    try:
        decoded_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ObservationError("M8ACQ_E001_INVALID_EVENT", "content encoding") from None
    for pattern in SECRET_PATTERNS:
        _require(pattern.search(decoded_content) is None, "M8ACQ_E020_REDACTION_MATCH", pattern.pattern)
    text = event["text"]
    _require(isinstance(text, str), "M8ACQ_E001_INVALID_EVENT", "text")
    _require(decoded_content == text, "M8ACQ_E001_INVALID_EVENT", "text/content binding")
    return {"observer": "redaction", "status": "PASS", "byte_size": len(content)}


def observe_all(events: Mapping[str, Mapping[str, Any]]) -> bytes:
    _require_mapping(events, "observer events")
    _require(set(events) == {"network", "process", "write", "redaction"}, "M8ACQ_E021_OBSERVER_INCOMPLETE", "four observers required")
    for name in ("network", "process", "write", "redaction"):
        _require_mapping(events[name], f"{name} event")
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

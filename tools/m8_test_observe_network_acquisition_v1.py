"""Hermetic tests for the M8 network-acquisition observer candidate."""
from __future__ import annotations

import hashlib
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools.m8_observe_network_acquisition_v1 import (
    ERROR_CODES,
    ObservationError,
    observe_all,
    observe_network,
    observe_process,
    observe_redaction,
    observe_write,
    PREPARATION_ROOT,
)


def expect_code(code: str, callback) -> None:
    try:
        callback()
    except ObservationError as exc:
        if exc.code != code:
            raise RuntimeError(f"expected {code}, got {exc.code}") from exc
    else:
        raise RuntimeError(f"expected {code}")


def fixtures() -> dict[str, dict[str, object]]:
    content = b'{"status":"candidate"}\n'
    return {
        "network": {
            "method": "GET",
            "initial_url": "https://pypi.org/pypi/numpy/2.4.6/json",
            "redirect_chain": [],
            "final_url": "https://pypi.org/pypi/numpy/2.4.6/json",
            "tls_verified": True,
            "certificate_bypass": False,
            "proxy": None,
            "authentication": None,
        },
        "process": {
            "executable": r"C:\Program Files\Git\mingw64\bin\curl.exe",
            "process_count": 1,
            "shell": False,
        },
        "write": {
            "path": r"D:\面试实习\m8-network-acquisition-cycle-20260918-r01\wheels\numpy.whl.partial",
            "is_reparse_point": False,
            "kind": "partial",
            "byte_size": 1024,
            "total_byte_size": 1024,
            "file_count": 1,
        },
        "redaction": {
            "text": content.decode("utf-8"),
            "declared_sha256": hashlib.sha256(content).hexdigest(),
            "content_bytes": content,
        },
    }


def main() -> None:
    if len(ERROR_CODES) != 21 or len(set(ERROR_CODES)) != 21:
        raise RuntimeError("error-code registry must contain 21 unique codes")
    data = observe_all(fixtures())
    if not data.endswith(b"\n") or b"\r" in data:
        raise RuntimeError("canonical output must be LF terminated and CR-free")
    if b'"status":"PASS"' not in data:
        raise RuntimeError("canonical output must contain PASS results")

    event = fixtures()["network"].copy()
    event["initial_url"] = "http://pypi.org/pypi/numpy/json"
    expect_code("M8ACQ_E002_NON_HTTPS", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["initial_url"] = "https://example.com/numpy"
    expect_code("M8ACQ_E003_INITIAL_HOST_DENIED", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["redirect_chain"] = ["https://evil.example/numpy.whl"]
    expect_code("M8ACQ_E004_REDIRECT_HOST_DENIED", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["redirect_chain"] = ["https://pypi.org/a"] * 4
    expect_code("M8ACQ_E005_REDIRECT_LIMIT", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["redirect_chain"] = ["https://files.pythonhosted.org/packages/a.whl"]
    expect_code("M8ACQ_E001_INVALID_EVENT", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["tls_verified"] = False
    expect_code("M8ACQ_E006_TLS_UNVERIFIED", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["certificate_bypass"] = True
    expect_code("M8ACQ_E007_CERT_BYPASS", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["proxy"] = "http://proxy"
    expect_code("M8ACQ_E008_PROXY_PRESENT", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["authentication"] = "present"
    expect_code("M8ACQ_E009_AUTH_PRESENT", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["method"] = "POST"
    expect_code("M8ACQ_E010_METHOD_DENIED", lambda: observe_network(event))
    for url in (
        "https://user:secret@pypi.org/pkg",
        "https://[not-a-valid-host",
        "https://pypi.org:444/pkg",
        "https://pypi.org/pkg?token=secret",
        "https://pypi.org/pkg#fragment",
    ):
        event = fixtures()["network"].copy()
        event["initial_url"] = url
        try:
            observe_network(event)
        except ObservationError as exc:
            if "secret" in str(exc).casefold() or "token" in str(exc).casefold():
                raise RuntimeError("URL error details must not disclose credentials") from exc
        else:
            raise RuntimeError("malformed or noncanonical URL unexpectedly passed")

    event = fixtures()["network"].copy()
    event["mirror"] = "https://evil.example/simple"
    expect_code("M8ACQ_E001_INVALID_EVENT", lambda: observe_network(event))
    event = fixtures()["network"].copy()
    event["extra_index"] = "https://evil.example/simple"
    expect_code("M8ACQ_E001_INVALID_EVENT", lambda: observe_network(event))
    event = fixtures()["redaction"].copy()
    event["text"] = "Authorization=Bearer hidden\n"
    event["content_bytes"] = event["text"].encode("utf-8")
    event["declared_sha256"] = hashlib.sha256(event["content_bytes"]).hexdigest()
    expect_code("M8ACQ_E020_REDACTION_MATCH", lambda: observe_redaction(event))
    for value in (float("nan"), chr(0xD800)):
        try:
            from tools.m8_observe_network_acquisition_v1 import canonical_bytes
            canonical_bytes(value)
        except ObservationError as exc:
            if exc.code != "M8ACQ_E001_INVALID_EVENT":
                raise RuntimeError("canonical edge case returned wrong code") from exc
        else:
            raise RuntimeError("non-canonical JSON value unexpectedly passed")

    event = fixtures()["process"].copy()
    event["executable"] = "pip.exe"
    expect_code("M8ACQ_E011_PROCESS_DENIED", lambda: observe_process(event))
    event = fixtures()["process"].copy()
    event["executable"] = pathlib.Path(r"C:\Program Files\Git\mingw64\bin\curl.exe")
    expect_code("M8ACQ_E001_INVALID_EVENT", lambda: observe_process(event))
    event = fixtures()["process"].copy()
    event["process_count"] = 2
    expect_code("M8ACQ_E012_PROCESS_COUNT", lambda: observe_process(event))
    for value in (True, 1.0, "1"):
        event = fixtures()["process"].copy()
        event["process_count"] = value
        expect_code("M8ACQ_E001_INVALID_EVENT", lambda event=event: observe_process(event))
    event = fixtures()["process"].copy()
    event["shell"] = True
    expect_code("M8ACQ_E013_SHELL_ENABLED", lambda: observe_process(event))

    base_path = str(PREPARATION_ROOT).replace("/", "\\")
    accepted = (
        ("authority.json", "evidence"),
        ("inventory.json", "evidence"),
        ("provenance.json", "evidence"),
        ("events/network.jsonl", "evidence"),
        ("events/process.jsonl", "evidence"),
        ("events/redaction.jsonl", "evidence"),
        ("events/write.jsonl", "evidence"),
        ("wheels/numpy.whl", "wheel"),
        ("wheels/numpy.whl.partial", "partial"),
    )
    for relative_path, kind in accepted:
        event = fixtures()["write"].copy()
        event["path"] = base_path + "\\" + relative_path.replace("/", "\\")
        event["kind"] = kind
        if observe_write(event)["relative_path"] != relative_path:
            raise RuntimeError(f"accepted path mismatch: {relative_path}")

    for relative_path in (
        "random.txt", "events/random.bin", "events/random.jsonl",
        "events/network.txt", "secret/unknown.json",
        "wheels/not-a-wheel.txt", "wheels/package.tar.gz", "wheels/package.zip",
        "wheels/package.whl.tmp", "wheels/subdir/package.whl",
    ):
        event = fixtures()["write"].copy()
        event["path"] = base_path + "\\" + relative_path.replace("/", "\\")
        expect_code("M8ACQ_E017_FILE_TYPE_DENIED", lambda event=event: observe_write(event))

    for relative_path, kind in (
        ("authority.json", "wheel"), ("inventory.json", "partial"),
        ("wheels/numpy.whl", "evidence"), ("wheels/numpy.whl.partial", "wheel"),
    ):
        event = fixtures()["write"].copy()
        event["path"] = base_path + "\\" + relative_path.replace("/", "\\")
        event["kind"] = kind
        expect_code("M8ACQ_E017_FILE_TYPE_DENIED", lambda event=event: observe_write(event))

    event = fixtures()["write"].copy()
    event["path"] = r"D:\outside\numpy.whl"
    expect_code("M8ACQ_E014_WRITE_OUTSIDE_ROOT", lambda: observe_write(event))
    event = fixtures()["write"].copy()
    event["path"] = base_path + r"\..\outside\numpy.whl"
    expect_code("M8ACQ_E014_WRITE_OUTSIDE_ROOT", lambda: observe_write(event))
    event = fixtures()["write"].copy()
    event["path"] = r"D:\Git Demo\StudyAssistanceAgent\numpy.whl"
    event["kind"] = "evidence"
    expect_code("M8ACQ_E015_FORBIDDEN_ROOT", lambda: observe_write(event))
    for unsafe_path in (
        base_path + r"\..\outside\x.whl",
        base_path + r"\wheels\..\..\outside\x.whl",
        base_path + r"\wheels\.. \outside\x.whl",
        base_path + r"\wheels\abc..def\x.whl",
        base_path + r"\wheels\foo.. \x.whl",
        base_path + r"\wheels\x.whl:payload",
        base_path + r"\wheels\x.whl::$DATA",
        base_path + r"\events\event.jsonl:stream",
        base_path + r"\wheels\NUL",
        base_path + r"\wheels\NUL.whl",
        base_path + r"\wheels\CON",
        base_path + r"\wheels\CON.whl",
        base_path + r"\wheels\CONIN$",
        base_path + r"\wheels\CONIN$.whl",
        base_path + r"\wheels\CONOUT$",
        base_path + r"\wheels\CONOUT$.whl",
        base_path + r"\wheels\PRN.txt",
        base_path + r"\wheels\AUX.data",
        base_path + r"\wheels\COM1.log",
        base_path + r"\wheels\LPT1.tmp",
        base_path + r"\wheels\payload?.whl",
        base_path + r"\wheels\payload*.whl",
        base_path + r"\wheels\payload<.whl",
        base_path + r"\wheels\payload>.whl",
        base_path + r'\wheels\payload".whl',
        base_path + r"\wheels\payload|.whl",
        base_path + r"\wheels\x.whl.",
        base_path + r"\wheels\x.whl ",
        base_path + r"\wheels\folder.\x.whl",
        base_path + r"\wheels\folder \x.whl",
        base_path + "\\wheels\\payload" + "\x00" + ".whl",
        base_path + "\\wheels\\payload\n.whl",
        base_path + "\\wheels\\" + "a" * 256 + ".whl",
        r"relative\path\x.whl",
        r"D:\outside\x.whl",
        r"C:\temp\x.whl",
        r"\\server\share\x.whl",
        base_path + r"\wheels\numpy.whl\\\x.whl",
    ):
        event = fixtures()["write"].copy()
        event["path"] = unsafe_path
        expect_code("M8ACQ_E014_WRITE_OUTSIDE_ROOT", lambda event=event: observe_write(event))

    event = fixtures()["write"].copy()
    event["path"] = base_path + r"\wheels\payload(.whl"
    event["kind"] = "wheel"
    expect_code("M8ACQ_E014_WRITE_OUTSIDE_ROOT", lambda: observe_write(event))
    event = fixtures()["write"].copy()
    event["is_reparse_point"] = True
    expect_code("M8ACQ_E016_REPARSE_POINT", lambda: observe_write(event))
    event = fixtures()["write"].copy()
    event["kind"] = "sdist"
    expect_code("M8ACQ_E017_FILE_TYPE_DENIED", lambda: observe_write(event))
    event = fixtures()["write"].copy()
    event["byte_size"] = 536870913
    expect_code("M8ACQ_E018_LIMIT_EXCEEDED", lambda: observe_write(event))
    for field, value in (
        ("byte_size", -1), ("total_byte_size", -1),
        ("total_byte_size", 2147483649), ("file_count", -1),
        ("file_count", 257), ("file_count", 0), ("total_byte_size", 1),
    ):
        event = fixtures()["write"].copy()
        event[field] = value
        expect_code("M8ACQ_E018_LIMIT_EXCEEDED", lambda event=event: observe_write(event))
    for field, value in (
        ("byte_size", "not-a-number"), ("total_byte_size", None),
        ("file_count", 1.9), ("file_count", True),
    ):
        event = fixtures()["write"].copy()
        event[field] = value
        expect_code("M8ACQ_E001_INVALID_EVENT", lambda event=event: observe_write(event))
    event = fixtures()["write"].copy()
    event["byte_size"] = 100
    event["total_byte_size"] = 99
    expect_code("M8ACQ_E018_LIMIT_EXCEEDED", lambda: observe_write(event))

    event = fixtures()["redaction"].copy()
    event["declared_sha256"] = "0" * 64
    expect_code("M8ACQ_E019_DIGEST_MISMATCH", lambda: observe_redaction(event))
    event = fixtures()["redaction"].copy()
    event["text"] = "Authorization: Bearer hidden"
    expect_code("M8ACQ_E001_INVALID_EVENT", lambda: observe_redaction(event))
    event = fixtures()["redaction"].copy()
    event["content_bytes"] = b"Authorization: Bearer secret\n"
    event["declared_sha256"] = hashlib.sha256(event["content_bytes"]).hexdigest()
    event["text"] = "{}"
    expect_code("M8ACQ_E020_REDACTION_MATCH", lambda: observe_redaction(event))
    events = fixtures()
    del events["redaction"]
    expect_code("M8ACQ_E021_OBSERVER_INCOMPLETE", lambda: observe_all(events))
    events: dict[str, Any] = fixtures()
    events["network"] = None
    expect_code("M8ACQ_E001_INVALID_EVENT", lambda: observe_all(events))

    print("PASS: 21 network-acquisition observer fail-closed controls")


if __name__ == "__main__":
    main()

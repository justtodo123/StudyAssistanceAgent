"""Hermetic tests for the M8 network-acquisition observer candidate."""
from __future__ import annotations

import hashlib
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools.m8_observe_network_acquisition_v1 import (
    ERROR_CODES,
    ObservationError,
    observe_all,
    observe_network,
    observe_process,
    observe_redaction,
    observe_write,
)


def expect_code(code: str, callback) -> None:
    try:
        callback()
    except ObservationError as exc:
        assert exc.code == code, (exc.code, code)
    else:
        raise AssertionError(f"expected {code}")


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
    assert len(ERROR_CODES) == 21
    assert len(set(ERROR_CODES)) == 21
    data = observe_all(fixtures())
    assert data.endswith(b"\n") and b"\r" not in data
    assert b'"status":"PASS"' in data

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

    event = fixtures()["process"].copy()
    event["executable"] = "pip.exe"
    expect_code("M8ACQ_E011_PROCESS_DENIED", lambda: observe_process(event))
    event = fixtures()["process"].copy()
    event["process_count"] = 2
    expect_code("M8ACQ_E012_PROCESS_COUNT", lambda: observe_process(event))
    event = fixtures()["process"].copy()
    event["shell"] = True
    expect_code("M8ACQ_E013_SHELL_ENABLED", lambda: observe_process(event))

    event = fixtures()["write"].copy()
    event["path"] = r"D:\outside\numpy.whl"
    expect_code("M8ACQ_E014_WRITE_OUTSIDE_ROOT", lambda: observe_write(event))
    event = fixtures()["write"].copy()
    event["path"] = r"D:\面试实习\m8-network-acquisition-cycle-20260918-r01\..\outside\numpy.whl"
    expect_code("M8ACQ_E014_WRITE_OUTSIDE_ROOT", lambda: observe_write(event))
    event = fixtures()["write"].copy()
    event["path"] = r"D:\Git Demo\StudyAssistanceAgent\numpy.whl"
    expect_code("M8ACQ_E015_FORBIDDEN_ROOT", lambda: observe_write(event))
    for unsafe_path in (
        r"D:\面试实习\m8-network-acquisition-cycle-20260918-r01\wheels\.. \\outside\x.whl",
        r"D:\面试实习\m8-network-acquisition-cycle-20260918-r01\wheels\x.whl:payload",
        r"D:\面试实习\m8-network-acquisition-cycle-20260918-r01\wheels\NUL.whl",
        r"D:\面试实习\m8-network-acquisition-cycle-20260918-r01\wheels\CON",
    ):
        event = fixtures()["write"].copy()
        event["path"] = unsafe_path
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

    event = fixtures()["redaction"].copy()
    event["declared_sha256"] = "0" * 64
    expect_code("M8ACQ_E019_DIGEST_MISMATCH", lambda: observe_redaction(event))
    event = fixtures()["redaction"].copy()
    event["text"] = "Authorization: Bearer hidden"
    expect_code("M8ACQ_E020_REDACTION_MATCH", lambda: observe_redaction(event))
    events = fixtures()
    del events["redaction"]
    expect_code("M8ACQ_E021_OBSERVER_INCOMPLETE", lambda: observe_all(events))

    print("PASS: 21 network-acquisition observer fail-closed controls")


if __name__ == "__main__":
    main()

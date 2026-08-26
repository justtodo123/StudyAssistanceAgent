"""M6a-3 single-process service lock and worker topology tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.worker_topology import (
    DEFAULT_LOCK_TIMEOUT_S,
    LOCK_SCHEMA,
    ServiceLock,
    WorkerTopologyError,
    enforce_single_worker_topology,
    service_lock_path,
)

pytestmark = pytest.mark.m6a

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import start_local  # noqa: E402


def test_default_timeout_is_five_seconds() -> None:
    assert DEFAULT_LOCK_TIMEOUT_S == 5.0


def test_worker_env_not_equal_to_one_fails() -> None:
    with pytest.raises(WorkerTopologyError) as web_concurrency:
        enforce_single_worker_topology({"WEB_CONCURRENCY": "2"})
    with pytest.raises(WorkerTopologyError) as uvicorn_workers:
        enforce_single_worker_topology({"UVICORN_WORKERS": "4"})
    assert web_concurrency.value.code == "WORKER_TOPOLOGY_UNSUPPORTED"
    assert uvicorn_workers.value.code == "WORKER_TOPOLOGY_UNSUPPORTED"


def test_readonly_replica_is_rejected() -> None:
    with pytest.raises(WorkerTopologyError) as caught:
        enforce_single_worker_topology({"SA_INDEX_READONLY": "true"})
    assert caught.value.code == "WORKER_TOPOLOGY_UNSUPPORTED"


def test_single_worker_and_unset_env_are_allowed() -> None:
    enforce_single_worker_topology({})
    enforce_single_worker_topology({"WEB_CONCURRENCY": "1", "UVICORN_WORKERS": "1"})


def test_service_lock_payload_has_no_host_paths(tmp_path: Path) -> None:
    lock = ServiceLock(tmp_path / "index" / "service.lock")
    info = lock.acquire(timeout=0.2)
    try:
        payload = lock.read_payload()
        encoded = str(payload)
        assert payload == {
            "schema": LOCK_SCHEMA,
            "pid": info.pid,
            "nonce": info.nonce,
            "started_at": info.started_at,
        }
        assert payload["pid"] == os.getpid()
        assert len(str(payload["nonce"])) == 32
        assert "T" in str(payload["started_at"])
        assert str(tmp_path) not in encoded
        assert "knowledge" not in encoded
        assert service_lock_path(tmp_path / "index").name == "service.lock"
    finally:
        lock.release()


def test_same_process_can_reenter_service_lock(tmp_path: Path) -> None:
    path = tmp_path / "service.lock"
    first = ServiceLock(path)
    second = ServiceLock(path)
    first.acquire(timeout=0.2)
    second.acquire(timeout=0.2)
    first.release()
    payload = second.read_payload()
    assert payload["pid"] == os.getpid()
    second.release()


def test_second_process_cannot_take_service_lock(
    tmp_path: Path,
    platform_dir: Path,
) -> None:
    lock_path = tmp_path / "service.lock"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(platform_dir) + os.pathsep + env.get("PYTHONPATH", "")
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import time\n"
                "from pathlib import Path\n"
                "from app.worker_topology import ServiceLock\n"
                f"lock = ServiceLock(Path({str(lock_path)!r}))\n"
                "lock.acquire(timeout=1)\n"
                "print('READY', flush=True)\n"
                "time.sleep(30)\n"
            ),
        ],
        cwd=str(platform_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        line = holder.stdout.readline()
        if "READY" not in line:
            stderr = holder.stderr.read() if holder.stderr is not None else ""
            raise AssertionError(f"lock holder failed: {line!r} {stderr!r}")
        with pytest.raises(WorkerTopologyError) as caught:
            ServiceLock(lock_path).acquire(timeout=0.3)
        assert caught.value.code == "WORKER_TOPOLOGY_UNSUPPORTED"
    finally:
        holder.terminate()
        try:
            holder.wait(timeout=5)
        except subprocess.TimeoutExpired:
            holder.kill()
            holder.wait(timeout=5)


def test_start_local_uses_single_worker_command() -> None:
    command = start_local.build_server_command("127.0.0.1", 8000)
    assert command[command.index("--workers") + 1] == "1"
    assert "--reload" not in command
    env = start_local.apply_single_worker_env({"WEB_CONCURRENCY": "4"})
    assert env["WEB_CONCURRENCY"] == "1"
    assert env["UVICORN_WORKERS"] == "1"

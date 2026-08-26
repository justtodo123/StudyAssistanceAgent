"""Single-process, single-worker topology gate for M6a retrieval publication."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Mapping

DEFAULT_LOCK_TIMEOUT_S = 5.0
LOCK_SCHEMA = "sa.service-lock.v1"
_WORKER_COUNT_VARS = ("WEB_CONCURRENCY", "UVICORN_WORKERS")
_HELD_LOCKS: dict[str, "_HeldLock"] = {}


class WorkerTopologyError(RuntimeError):
    """Startup failure when the process is not a single writable service worker."""

    code = "WORKER_TOPOLOGY_UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class ServiceLockInfo:
    pid: int
    nonce: str
    started_at: str


@dataclass
class _HeldLock:
    handle: IO[bytes]
    info: ServiceLockInfo
    refcount: int


def enforce_single_worker_topology(
    environment: Mapping[str, str] | None = None,
) -> None:
    """Reject multi-worker, read-only, or otherwise unsupported service topologies."""
    env = os.environ if environment is None else environment
    if _flag_enabled(env.get("SA_INDEX_READONLY")):
        raise WorkerTopologyError("read-only worker topology is not supported")
    for name in _WORKER_COUNT_VARS:
        raw = env.get(name)
        if raw is None or str(raw).strip() == "":
            continue
        if str(raw).strip() != "1":
            raise WorkerTopologyError("only a single uvicorn worker is supported")


def service_lock_path(cache_root: Path | None = None) -> Path:
    """Return the lifetime lock path under the index cache root."""
    if cache_root is None:
        from . import config

        cache_root = config.INDEX_CACHE_PATH
    return Path(cache_root) / "service.lock"


class ServiceLock:
    """Process-lifetime exclusive lock with same-process re-entry."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._key: str | None = None

    @property
    def info(self) -> ServiceLockInfo | None:
        if self._key is None:
            return None
        held = _HELD_LOCKS.get(self._key)
        return None if held is None else held.info

    def acquire(self, timeout: float = DEFAULT_LOCK_TIMEOUT_S) -> ServiceLockInfo:
        """Take or re-enter the lock. A second process fails after timeout."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        key = str(self.path.resolve())
        held = _HELD_LOCKS.get(key)
        if held is not None:
            held.refcount += 1
            self._key = key
            return held.info

        deadline = time.monotonic() + max(timeout, 0.0)
        last_error: OSError | None = None
        while True:
            try:
                info = self._try_acquire(key)
                self._key = key
                return info
            except OSError as exc:
                last_error = exc
            if time.monotonic() >= deadline:
                raise WorkerTopologyError(
                    "another service process holds the index lock"
                ) from last_error
            time.sleep(0.05)

    def release(self) -> None:
        if self._key is None:
            return
        held = _HELD_LOCKS.get(self._key)
        self._key = None
        if held is None:
            return
        held.refcount -= 1
        if held.refcount > 0:
            return
        key = str(self.path.resolve())
        _HELD_LOCKS.pop(key, None)
        try:
            _unlock_file(held.handle)
        finally:
            held.handle.close()

    def read_payload(self) -> dict[str, object]:
        if self._key is not None:
            held = _HELD_LOCKS.get(self._key)
            if held is not None:
                held.handle.seek(0)
                raw = held.handle.read()
                return json.loads(raw.decode("utf-8"))
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _try_acquire(self, key: str) -> ServiceLockInfo:
        handle = self.path.open("a+b")
        try:
            _lock_file(handle)
            info = ServiceLockInfo(
                pid=os.getpid(),
                nonce=uuid.uuid4().hex,
                started_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            payload = {
                "schema": LOCK_SCHEMA,
                "pid": info.pid,
                "nonce": info.nonce,
                "started_at": info.started_at,
            }
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            handle.seek(0)
            handle.truncate()
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            handle.close()
            raise
        _HELD_LOCKS[key] = _HeldLock(handle=handle, info=info, refcount=1)
        return info


def _flag_enabled(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _lock_file(handle: IO[bytes]) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\n")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(handle: IO[bytes]) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = [
    "DEFAULT_LOCK_TIMEOUT_S",
    "LOCK_SCHEMA",
    "ServiceLock",
    "ServiceLockInfo",
    "WorkerTopologyError",
    "enforce_single_worker_topology",
    "service_lock_path",
]

from __future__ import annotations

import os
import threading
from pathlib import Path

_locks: dict[str, threading.RLock] = {}
_guard = threading.Lock()


def operation_lock(cache_root: str | Path) -> threading.RLock:
    """Return the process-local operation lock shared by source stores."""
    key = os.path.normcase(str(Path(cache_root).resolve()))
    with _guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _locks[key] = lock
        return lock

#!/usr/bin/env python3
"""One-command local start and health check for the learning workbench.

Default mode stays offline: SA_USE_VECTOR=false and no LLM key is required.
Use --use-vector only after the optional BGE model is cached locally.

Usage:
    python tools/start_local.py
    python tools/start_local.py --check
    python tools/start_local.py --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_DIR = REPO_ROOT / "platform"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_TIMEOUT = 30.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start the local learning workbench")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port. Default: 8000")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only probe /health and exit. Do not start the server.",
    )
    parser.add_argument(
        "--use-vector",
        action="store_true",
        help="Allow optional BGE retrieval. Default is offline BM25.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Seconds to wait for /health after start. Default: 30",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def health_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/health"


def workbench_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/"


def apply_offline_defaults(use_vector: bool, env: dict[str, str] | None = None) -> dict[str, str]:
    """Keep the demo path free of Hugging Face downloads and LLM keys."""
    target = os.environ if env is None else env
    target.setdefault("SA_USE_VECTOR", "true" if use_vector else "false")
    if use_vector:
        return target
    target.setdefault("HF_HUB_OFFLINE", "1")
    target.setdefault("TRANSFORMERS_OFFLINE", "1")
    return target


def probe_health(url: str, timeout: float = 2.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    status = str(payload.get("status", "")).upper()
    return {"ok": status == "UP", "payload": payload}


def wait_for_health(url: str, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {"ok": False, "error": "health check timed out"}
    while time.monotonic() < deadline:
        last = probe_health(url)
        if last.get("ok"):
            return last
        time.sleep(0.2)
    return last


def start_server(host: str, port: int, use_vector: bool) -> subprocess.Popen[Any]:
    env = apply_offline_defaults(use_vector, os.environ.copy())
    env["SA_USE_VECTOR"] = "true" if use_vector else "false"
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    return subprocess.Popen(command, cwd=str(PLATFORM_DIR), env=env)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    url = health_url(args.host, args.port)
    if args.check:
        result = probe_health(url)
        if result.get("ok"):
            payload = result.get("payload") or {}
            print(f"health: {payload.get('status', 'UP')}")
            print(f"workbench: {workbench_url(args.host, args.port)}")
            return 0
        print(f"health: DOWN ({result.get('error', 'unknown error')})", file=sys.stderr)
        return 1

    apply_offline_defaults(args.use_vector)
    process = start_server(args.host, args.port, args.use_vector)
    try:
        result = wait_for_health(url, args.timeout)
        if not result.get("ok"):
            print(f"error: server did not become healthy: {result.get('error')}", file=sys.stderr)
            process.terminate()
            return 1
        payload = result.get("payload") or {}
        print(f"health: {payload.get('status', 'UP')}")
        print(f"workbench: {workbench_url(args.host, args.port)}")
        print("offline BM25 demo is ready. Press Ctrl+C to stop.")
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""One-command start script stays offline and can health-check."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import start_local


@pytest.mark.m5e
class TestStartLocal:
    def test_defaults_are_offline(self):
        args = start_local.parse_args([])
        assert args.check is False
        assert args.use_vector is False
        assert args.host == "127.0.0.1"
        assert args.port == 8000

    def test_check_mode_does_not_start_server(self):
        args = start_local.parse_args(["--check"])
        assert args.check is True

    def test_apply_offline_defaults_sets_no_download_flags(self):
        env: dict[str, str] = {}
        start_local.apply_offline_defaults(False, env)
        assert env["SA_USE_VECTOR"] == "false"
        assert env["HF_HUB_OFFLINE"] == "1"
        assert env["TRANSFORMERS_OFFLINE"] == "1"

    def test_probe_health_ok(self):
        class _Resp:
            def read(self):
                return b'{"status":"UP","index_size":1}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("start_local.urllib.request.urlopen", return_value=_Resp()):
            result = start_local.probe_health("http://127.0.0.1:8000/health")
        assert result["ok"] is True
        assert result["payload"]["status"] == "UP"

    def test_check_main_returns_error_when_down(self):
        with patch("start_local.probe_health", return_value={"ok": False, "error": "refused"}):
            assert start_local.main(["--check"]) == 1
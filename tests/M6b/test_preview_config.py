"""M6b tests for strict, tightening-only preview configuration."""

from __future__ import annotations

import importlib
import os
from dataclasses import asdict
from typing import Any

import pytest


pytestmark = pytest.mark.m6b
_PREVIEW_PREFIX = "SA_AGENT_PREVIEW_"


def _load_config(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> Any:
    import app.config as config

    for name in tuple(os.environ):
        if name.startswith(_PREVIEW_PREFIX):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for name, value in overrides.items():
        monkeypatch.setenv(name, value)
    return importlib.reload(config)


def _limits(
    monkeypatch: pytest.MonkeyPatch,
    **overrides: str,
) -> dict[str, int | float]:
    config = _load_config(monkeypatch, **overrides)
    return asdict(config.AGENT_PREVIEW_LIMITS)


def _reload_error(
    monkeypatch: pytest.MonkeyPatch,
    **overrides: str,
) -> ValueError:
    with pytest.raises(ValueError) as raised:
        _load_config(monkeypatch, **overrides)
    return raised.value


def test_defaults_match_the_frozen_preview_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _limits(monkeypatch) == {
        "deadline_seconds": 45.0,
        "max_answer_bytes": 8192,
        "max_cost_usd": 0.2,
        "max_input_tokens": 12000,
        "max_model_turns": 4,
        "max_output_tokens": 4096,
        "max_prompt_bytes": 8192,
        "max_retries": 1,
        "max_tool_calls": 3,
        "max_tool_result_bytes": 12288,
        "max_total_tool_result_bytes": 24576,
        "max_turn_output_tokens": 1024,
        "model_timeout_seconds": 20.0,
        "retry_after_cap_seconds": 2.0,
        "retry_max_seconds": 0.5,
        "retry_min_seconds": 0.2,
        "token_count_timeout_seconds": 3.0,
        "tool_timeout_seconds": 2.0,
    }


def test_approved_numeric_overrides_only_tighten_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limits = _limits(
        monkeypatch,
        SA_AGENT_PREVIEW_DEADLINE_SECONDS=" 30.5 ",
        SA_AGENT_PREVIEW_MODEL_TIMEOUT_SECONDS="10",
        SA_AGENT_PREVIEW_TOKEN_COUNT_TIMEOUT_SECONDS="2.5",
        SA_AGENT_PREVIEW_TOOL_TIMEOUT_SECONDS="1",
        SA_AGENT_PREVIEW_MAX_MODEL_TURNS="3",
        SA_AGENT_PREVIEW_MAX_TOOL_CALLS="2",
        SA_AGENT_PREVIEW_MAX_INPUT_TOKENS="8000",
        SA_AGENT_PREVIEW_MAX_OUTPUT_TOKENS="2048",
        SA_AGENT_PREVIEW_MAX_TURN_OUTPUT_TOKENS="512",
        SA_AGENT_PREVIEW_MAX_COST_USD="0.1",
        SA_AGENT_PREVIEW_MAX_PROMPT_BYTES="4096",
        SA_AGENT_PREVIEW_MAX_TOOL_RESULT_BYTES="4096",
        SA_AGENT_PREVIEW_MAX_TOTAL_TOOL_RESULT_BYTES="8192",
        SA_AGENT_PREVIEW_MAX_ANSWER_BYTES="4096",
    )

    assert limits["deadline_seconds"] == 30.5
    assert limits["max_model_turns"] == 3
    assert limits["max_turn_output_tokens"] == 512
    assert limits["max_cost_usd"] == 0.1
    assert limits["max_answer_bytes"] == 4096
    assert limits["max_retries"] == 1
    assert limits["retry_after_cap_seconds"] == 2.0


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SA_AGENT_PREVIEW_DEADLINE_SECONDS", "nan"),
        ("SA_AGENT_PREVIEW_DEADLINE_SECONDS", "inf"),
        ("SA_AGENT_PREVIEW_DEADLINE_SECONDS", "0"),
        ("SA_AGENT_PREVIEW_DEADLINE_SECONDS", "-1"),
        ("SA_AGENT_PREVIEW_DEADLINE_SECONDS", "true"),
        ("SA_AGENT_PREVIEW_DEADLINE_SECONDS", "45.1"),
        ("SA_AGENT_PREVIEW_MAX_MODEL_TURNS", "0"),
        ("SA_AGENT_PREVIEW_MAX_MODEL_TURNS", "-1"),
        ("SA_AGENT_PREVIEW_MAX_MODEL_TURNS", "+1"),
        ("SA_AGENT_PREVIEW_MAX_MODEL_TURNS", "1.0"),
        ("SA_AGENT_PREVIEW_MAX_MODEL_TURNS", "true"),
        ("SA_AGENT_PREVIEW_MAX_MODEL_TURNS", "5"),
    ],
)
def test_invalid_or_relaxed_overrides_fail_closed(
    name: str,
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = _reload_error(monkeypatch, **{name: value})

    assert name in str(error)


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "SA_AGENT_PREVIEW_MAX_OUTPUT_TOKENS": "512",
            "SA_AGENT_PREVIEW_MAX_TURN_OUTPUT_TOKENS": "1024",
        },
        {
            "SA_AGENT_PREVIEW_MAX_TOOL_RESULT_BYTES": "100",
            "SA_AGENT_PREVIEW_MAX_TOTAL_TOOL_RESULT_BYTES": "50",
        },
    ],
)
def test_incoherent_tightening_fails_closed(
    overrides: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = _reload_error(monkeypatch, **overrides)

    assert str(error) in {
        "turn output limit cannot exceed total output limit",
        "individual tool result cannot exceed the total result limit",
    }


def test_enabled_preview_requires_utf8_token_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    short = _reload_error(
        monkeypatch,
        SA_AGENT_PREVIEW_ENABLED="true",
        SA_AGENT_PREVIEW_TOKEN="短" * 10,
    )
    assert "at least 32 UTF-8 bytes" in str(short)

    config = _load_config(
        monkeypatch,
        SA_AGENT_PREVIEW_ENABLED="true",
        SA_AGENT_PREVIEW_TOKEN="短" * 11,
    )
    assert config.AGENT_PREVIEW_ENABLED is True


def test_unapproved_policy_environment_names_are_not_limit_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limits = _limits(
        monkeypatch,
        SA_AGENT_PREVIEW_MODEL="forbidden-model",
        SA_AGENT_PREVIEW_ENDPOINT="https://invalid.example",
        SA_AGENT_PREVIEW_MAX_RETRIES="0",
        SA_AGENT_PREVIEW_CAPACITY="1",
        SA_AGENT_PREVIEW_TOOL_ALLOWLIST="write",
        SA_AGENT_PREVIEW_RETRY_AFTER_CAP_SECONDS="0.1",
    )

    assert limits["max_retries"] == 1
    assert limits["retry_after_cap_seconds"] == 2.0

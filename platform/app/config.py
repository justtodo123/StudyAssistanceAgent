"""运行时配置：显式环境映射 → 冻结 Settings，兼容导出既有常量。"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Mapping

from dotenv import dotenv_values

from .plan_ai_adapter import PlanAILimits, _validate_limits
from .preview_agent import PreviewAgent, PreviewLimits

# 项目根（platform/ 的上一级）
REPO_ROOT = Path(__file__).resolve().parents[2]

_TRUE_VALUES = frozenset({"1", "true", "yes"})
_FALSE_VALUES = frozenset({"0", "false", "no"})


@dataclass(frozen=True)
class Settings:
    """One immutable runtime configuration captured before app construction."""

    repo_root: Path
    knowledge_root: Path
    top_k: int
    bm25_pool: int
    use_vector: bool
    embedding_model: str
    embedding_normalize: bool
    embedding_expected_dim: int
    chunk_min_chars: int
    vector_threshold: float
    vector_index_type: str
    rrf_k: int
    llm_temperature: float
    llm_timeout_s: float
    vector_store: str
    vector_store_path: Path
    learning_store_path: Path
    source_registry_path: Path
    index_cache_path: Path
    user_source_cache_path: Path
    expected_default_pack_revision: str | None
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    runner_enabled: bool
    agent_preview_enabled: bool
    agent_preview_token: str
    anthropic_api_key: str
    agent_preview_limits: PreviewLimits
    plan_ai_enabled: bool
    plan_ai_token: str
    plan_ai_limits: PlanAILimits
    source_environment: tuple[tuple[str, str], ...]


# Only resource budgets are configurable, and every override may tighten the frozen defaults.
_PREVIEW_LIMIT_ENV: dict[str, tuple[str, str]] = {
    "deadline_seconds": ("SA_AGENT_PREVIEW_DEADLINE_SECONDS", "float"),
    "model_timeout_seconds": ("SA_AGENT_PREVIEW_MODEL_TIMEOUT_SECONDS", "float"),
    "token_count_timeout_seconds": ("SA_AGENT_PREVIEW_TOKEN_COUNT_TIMEOUT_SECONDS", "float"),
    "tool_timeout_seconds": ("SA_AGENT_PREVIEW_TOOL_TIMEOUT_SECONDS", "float"),
    "max_model_turns": ("SA_AGENT_PREVIEW_MAX_MODEL_TURNS", "int"),
    "max_tool_calls": ("SA_AGENT_PREVIEW_MAX_TOOL_CALLS", "int"),
    "max_input_tokens": ("SA_AGENT_PREVIEW_MAX_INPUT_TOKENS", "int"),
    "max_output_tokens": ("SA_AGENT_PREVIEW_MAX_OUTPUT_TOKENS", "int"),
    "max_turn_output_tokens": ("SA_AGENT_PREVIEW_MAX_TURN_OUTPUT_TOKENS", "int"),
    "max_cost_usd": ("SA_AGENT_PREVIEW_MAX_COST_USD", "float"),
    "max_prompt_bytes": ("SA_AGENT_PREVIEW_MAX_PROMPT_BYTES", "int"),
    "max_tool_result_bytes": ("SA_AGENT_PREVIEW_MAX_TOOL_RESULT_BYTES", "int"),
    "max_total_tool_result_bytes": (
        "SA_AGENT_PREVIEW_MAX_TOTAL_TOOL_RESULT_BYTES",
        "int",
    ),
    "max_answer_bytes": ("SA_AGENT_PREVIEW_MAX_ANSWER_BYTES", "int"),
}

_PLAN_AI_LIMIT_ENV: dict[str, tuple[str, str]] = {
    "deadline_seconds": ("SA_PLAN_AI_DEADLINE_SECONDS", "float"),
    "model_timeout_seconds": ("SA_PLAN_AI_MODEL_TIMEOUT_SECONDS", "float"),
    "max_input_tokens": ("SA_PLAN_AI_MAX_INPUT_TOKENS", "int"),
    "max_output_tokens": ("SA_PLAN_AI_MAX_OUTPUT_TOKENS", "int"),
    "max_turn_output_tokens": ("SA_PLAN_AI_MAX_TURN_OUTPUT_TOKENS", "int"),
    "max_cost_usd": ("SA_PLAN_AI_MAX_COST_USD", "float"),
    "max_prompt_bytes": ("SA_PLAN_AI_MAX_PROMPT_BYTES", "int"),
    "max_answer_bytes": ("SA_PLAN_AI_MAX_ANSWER_BYTES", "int"),
}


def _value(environ: Mapping[str, str], name: str, default: str) -> str:
    raw = environ.get(name)
    return default if raw is None else str(raw)


def _bool(environ: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in _TRUE_VALUES


def _strict_bool(
    name: str,
    default: bool = False,
    *,
    environ: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environ is None else environ
    raw = source.get(name)
    if raw is None:
        return default
    normalized = str(raw).strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be a strict boolean")


def _tight_float(
    name: str,
    default: float,
    *,
    environ: Mapping[str, str] | None = None,
) -> float:
    source = os.environ if environ is None else environ
    raw = source.get(name)
    if raw is None:
        return default
    candidate = str(raw).strip()
    if not candidate or candidate.lower() in {"true", "false", "yes", "no"}:
        raise ValueError(f"{name} must be a finite positive number")
    try:
        value = float(candidate)
    except ValueError as exc:
        raise ValueError(f"{name} must be a finite positive number") from exc
    if not math.isfinite(value) or value <= 0 or value > default:
        raise ValueError(
            f"{name} must be positive and no greater than the frozen limit {default}"
        )
    return value


def _tight_int(
    name: str,
    default: int,
    *,
    environ: Mapping[str, str] | None = None,
) -> int:
    source = os.environ if environ is None else environ
    raw = source.get(name)
    if raw is None:
        return default
    candidate = str(raw).strip()
    if re.fullmatch(r"[0-9]+", candidate) is None:
        raise ValueError(f"{name} must be a positive base-10 integer")
    value = int(candidate)
    if value <= 0 or value > default:
        raise ValueError(
            f"{name} must be positive and no greater than the frozen limit {default}"
        )
    return value


def _limits_from_environment(
    defaults: PreviewLimits | PlanAILimits,
    bindings: Mapping[str, tuple[str, str]],
    environ: Mapping[str, str],
) -> dict[str, Any]:
    values = {field.name: getattr(defaults, field.name) for field in fields(defaults)}
    for field_name, (env_name, kind) in bindings.items():
        default = getattr(defaults, field_name)
        if kind == "float":
            values[field_name] = _tight_float(env_name, default, environ=environ)
        else:
            values[field_name] = _tight_int(env_name, default, environ=environ)
    return values


def _preview_limits(environ: Mapping[str, str] | None = None) -> PreviewLimits:
    source = os.environ if environ is None else environ
    limits = PreviewLimits(
        **_limits_from_environment(PreviewLimits(), _PREVIEW_LIMIT_ENV, source)
    )
    PreviewAgent.validate_limits(limits)
    return limits


def _plan_ai_limits(environ: Mapping[str, str]) -> PlanAILimits:
    limits = PlanAILimits(
        **_limits_from_environment(PlanAILimits(), _PLAN_AI_LIMIT_ENV, environ)
    )
    _validate_limits(limits)
    return limits


def load_settings(
    environ: Mapping[str, str] | None = None,
    *,
    dotenv_path: Path | None = None,
) -> Settings:
    """Build settings from an explicit environment; dotenv loading is opt-in."""
    source: dict[str, str] = {}
    if dotenv_path is not None and Path(dotenv_path).is_file():
        source.update(
            {key: value for key, value in dotenv_values(dotenv_path).items() if value is not None}
        )
    incoming = os.environ if environ is None else environ
    source.update({key: str(value) for key, value in incoming.items()})

    repo_root = REPO_ROOT
    vector_store = _value(source, "SA_VECTOR_STORE", "sqlite").lower()
    if vector_store not in {"sqlite", "linear"}:
        raise ValueError(
            f"unsupported SA_VECTOR_STORE={vector_store!r}; expected 'sqlite' or 'linear'"
        )

    preview_enabled = _strict_bool("SA_AGENT_PREVIEW_ENABLED", environ=source)
    preview_token = _value(source, "SA_AGENT_PREVIEW_TOKEN", "")
    if preview_enabled and len(preview_token.encode("utf-8")) < 32:
        raise ValueError(
            "SA_AGENT_PREVIEW_TOKEN must contain at least 32 UTF-8 bytes when preview is enabled"
        )

    anthropic_key = _value(source, "ANTHROPIC_API_KEY", "")
    plan_ai_enabled = _strict_bool("SA_PLAN_AI_ENABLED", environ=source)
    plan_ai_token = _value(source, "SA_PLAN_AI_TOKEN", "") or anthropic_key
    if plan_ai_enabled and len(plan_ai_token.encode("utf-8")) < 32:
        raise ValueError(
            "SA_PLAN_AI_TOKEN (or ANTHROPIC_API_KEY) must contain at least 32 UTF-8 bytes "
            "when the external AI planning path is enabled"
        )

    cache_root = repo_root / "platform" / ".cache"
    return Settings(
        repo_root=repo_root,
        knowledge_root=Path(_value(source, "SA_KNOWLEDGE_ROOT", str(repo_root / "knowledge"))),
        top_k=int(_value(source, "SA_TOP_K", "5")),
        bm25_pool=int(_value(source, "SA_BM25_POOL", "0")),
        use_vector=_bool(source, "SA_USE_VECTOR", True),
        embedding_model=_value(source, "SA_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
        embedding_normalize=_bool(source, "SA_EMBEDDING_NORMALIZE", True),
        embedding_expected_dim=int(_value(source, "SA_EMBEDDING_DIM", "512")),
        chunk_min_chars=int(_value(source, "SA_CHUNK_MIN_CHARS", "15")),
        vector_threshold=float(_value(source, "SA_VECTOR_THRESHOLD", "0.0")),
        vector_index_type=_value(source, "SA_VECTOR_INDEX_TYPE", "linear_cosine"),
        rrf_k=int(_value(source, "SA_RRF_K", "60")),
        llm_temperature=float(_value(source, "SA_LLM_TEMPERATURE", "0.3")),
        llm_timeout_s=float(_value(source, "SA_LLM_TIMEOUT_S", "60")),
        vector_store=vector_store,
        vector_store_path=Path(_value(source, "SA_VECTOR_STORE_PATH", str(cache_root / "vector_store.sqlite3"))),
        learning_store_path=Path(_value(source, "SA_LEARNING_STORE_PATH", str(cache_root / "learning_state.sqlite3"))),
        source_registry_path=Path(_value(source, "SA_SOURCE_REGISTRY_PATH", str(cache_root / "source_registry.sqlite3"))),
        index_cache_path=Path(_value(source, "SA_INDEX_CACHE_PATH", str(cache_root / "index"))),
        user_source_cache_path=Path(_value(source, "SA_USER_SOURCE_CACHE_PATH", str(cache_root / "user-sources"))),
        expected_default_pack_revision=source.get("SA_EXPECTED_DEFAULT_PACK_REVISION") or None,
        llm_base_url=_value(source, "SA_LLM_BASE_URL", ""),
        llm_api_key=_value(source, "SA_LLM_API_KEY", ""),
        llm_model=_value(source, "SA_LLM_MODEL", ""),
        runner_enabled=_strict_bool("SA_RUNNER", environ=source),
        agent_preview_enabled=preview_enabled,
        agent_preview_token=preview_token,
        anthropic_api_key=anthropic_key,
        agent_preview_limits=_preview_limits(source),
        plan_ai_enabled=plan_ai_enabled,
        plan_ai_token=plan_ai_token,
        plan_ai_limits=_plan_ai_limits(source),
        source_environment=tuple(
            sorted(
                (key, value)
                for key, value in source.items()
                if key.startswith("SA_SOURCE_")
                or key in {
                    "SA_EXTRA_SOURCES",
                    "SA_EXTRA_SOURCES_STRICT",
                    "SA_CRAWLER_CANDIDATE_CACHE",
                }
            )
        ),
    )


DEFAULT_SETTINGS = load_settings()

# Compatibility exports for domain modules not yet settings-injected.
KNOWLEDGE_ROOT = DEFAULT_SETTINGS.knowledge_root
TOP_K = DEFAULT_SETTINGS.top_k
BM25_POOL = DEFAULT_SETTINGS.bm25_pool
USE_VECTOR = DEFAULT_SETTINGS.use_vector
EMBEDDING_MODEL = DEFAULT_SETTINGS.embedding_model
EMBEDDING_NORMALIZE = DEFAULT_SETTINGS.embedding_normalize
EMBEDDING_EXPECTED_DIM = DEFAULT_SETTINGS.embedding_expected_dim
CHUNK_MIN_CHARS = DEFAULT_SETTINGS.chunk_min_chars
VECTOR_THRESHOLD = DEFAULT_SETTINGS.vector_threshold
VECTOR_INDEX_TYPE = DEFAULT_SETTINGS.vector_index_type
RRF_K = DEFAULT_SETTINGS.rrf_k
LLM_TEMPERATURE = DEFAULT_SETTINGS.llm_temperature
LLM_TIMEOUT_S = DEFAULT_SETTINGS.llm_timeout_s
VECTOR_STORE = DEFAULT_SETTINGS.vector_store
VECTOR_STORE_PATH = DEFAULT_SETTINGS.vector_store_path
LEARNING_STORE_PATH = DEFAULT_SETTINGS.learning_store_path
SOURCE_REGISTRY_PATH = DEFAULT_SETTINGS.source_registry_path
INDEX_CACHE_PATH = DEFAULT_SETTINGS.index_cache_path
USER_SOURCE_CACHE_PATH = DEFAULT_SETTINGS.user_source_cache_path
EXPECTED_DEFAULT_PACK_REVISION = DEFAULT_SETTINGS.expected_default_pack_revision
LLM_BASE_URL = DEFAULT_SETTINGS.llm_base_url
LLM_API_KEY = DEFAULT_SETTINGS.llm_api_key
LLM_MODEL = DEFAULT_SETTINGS.llm_model
VECTOR_ENABLED = DEFAULT_SETTINGS.use_vector
RUNNER_ENABLED = DEFAULT_SETTINGS.runner_enabled
AGENT_PREVIEW_ENABLED = DEFAULT_SETTINGS.agent_preview_enabled
AGENT_PREVIEW_TOKEN = DEFAULT_SETTINGS.agent_preview_token
ANTHROPIC_API_KEY = DEFAULT_SETTINGS.anthropic_api_key
AGENT_PREVIEW_LIMITS = DEFAULT_SETTINGS.agent_preview_limits
PLAN_AI_ENABLED = DEFAULT_SETTINGS.plan_ai_enabled
PLAN_AI_TOKEN = DEFAULT_SETTINGS.plan_ai_token

# Historical names used by tests and limit-name guards.
_AGENT_PREVIEW_TRUE = _TRUE_VALUES
_AGENT_PREVIEW_FALSE = _FALSE_VALUES


def plan_ai_limits(settings: Settings | None = None) -> PlanAILimits:
    """Return captured limits, or parse current env for compatibility callers."""
    if settings is not None:
        return settings.plan_ai_limits
    return _plan_ai_limits(os.environ)

"""运行时配置：环境变量 → 常量，模拟参考项目 AiProperties 的配置绑定。"""

from __future__ import annotations

import math
import os
import re
from dataclasses import fields
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .preview_agent import PreviewLimits

from dotenv import load_dotenv

load_dotenv()

# 项目根（platform/ 的上一级）
REPO_ROOT = Path(__file__).resolve().parents[2]
# 知识库根目录（可在 .env 中覆盖，便于指向外部整理目录）
KNOWLEDGE_ROOT = Path(os.getenv("SA_KNOWLEDGE_ROOT", REPO_ROOT / "knowledge"))

# ===== 检索 =====
TOP_K = int(os.getenv("SA_TOP_K", "5"))
# BM25 候选池大小：0 表示不限制（全库检索）。个人知识库规模（几百片）全量检索毫秒级，
# 截断候选池反而会在知识库扩容后静默丢文件（曾导致 Recall@3 从 1.000 跌到 0.650）。
BM25_POOL = int(os.getenv("SA_BM25_POOL", "0"))
USE_VECTOR = os.getenv("SA_USE_VECTOR", "true").lower() in ("1", "true", "yes")
EMBEDDING_MODEL = os.getenv("SA_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
EMBEDDING_NORMALIZE = os.getenv("SA_EMBEDDING_NORMALIZE", "true").lower() in ("1", "true", "yes")
EMBEDDING_EXPECTED_DIM = int(os.getenv("SA_EMBEDDING_DIM", "512"))
CHUNK_MIN_CHARS = int(os.getenv("SA_CHUNK_MIN_CHARS", "15"))
VECTOR_THRESHOLD = float(os.getenv("SA_VECTOR_THRESHOLD", "0.0"))
VECTOR_INDEX_TYPE = os.getenv("SA_VECTOR_INDEX_TYPE", "linear_cosine")
RRF_K = int(os.getenv("SA_RRF_K", "60"))
LLM_TEMPERATURE = float(os.getenv("SA_LLM_TEMPERATURE", "0.3"))
LLM_TIMEOUT_S = float(os.getenv("SA_LLM_TIMEOUT_S", "60"))
# Vector-store backend: sqlite persists across restarts; linear keeps the in-memory fallback.
VECTOR_STORE = os.getenv("SA_VECTOR_STORE", "sqlite").lower()
if VECTOR_STORE not in {"sqlite", "linear"}:
    raise ValueError(
        f"unsupported SA_VECTOR_STORE={VECTOR_STORE!r}; expected 'sqlite' or 'linear'"
    )
VECTOR_STORE_PATH = Path(
    os.getenv(
        "SA_VECTOR_STORE_PATH",
        str(REPO_ROOT / "platform" / ".cache" / "vector_store.sqlite3"),
    )
)
LEARNING_STORE_PATH = Path(
    os.getenv(
        "SA_LEARNING_STORE_PATH",
        str(REPO_ROOT / "platform" / ".cache" / "learning_state.sqlite3"),
    )
)
INDEX_CACHE_PATH = Path(
    os.getenv(
        "SA_INDEX_CACHE_PATH",
        str(REPO_ROOT / "platform" / ".cache" / "index"),
    )
)
EXPECTED_DEFAULT_PACK_REVISION = os.getenv("SA_EXPECTED_DEFAULT_PACK_REVISION") or None

# ===== LLM（OpenAI 兼容）=====
LLM_BASE_URL = os.getenv("SA_LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("SA_LLM_API_KEY", "")
LLM_MODEL = os.getenv("SA_LLM_MODEL", "")

# 是否启用向量检索（依赖可选安装）
VECTOR_ENABLED = USE_VECTOR

# ===== M6b read-only Agent Preview =====


def _tight_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    candidate = raw.strip()
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


def _tight_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    candidate = raw.strip()
    if re.fullmatch(r"[0-9]+", candidate) is None:
        raise ValueError(f"{name} must be a positive base-10 integer")
    value = int(candidate)
    if value <= 0 or value > default:
        raise ValueError(
            f"{name} must be positive and no greater than the frozen limit {default}"
        )
    return value
_AGENT_PREVIEW_TRUE = frozenset({"1", "true", "yes"})
_AGENT_PREVIEW_FALSE = frozenset({"0", "false", "no"})


def _strict_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _AGENT_PREVIEW_TRUE:
        return True
    if normalized in _AGENT_PREVIEW_FALSE:
        return False
    raise ValueError(f"{name} must be a strict boolean")


AGENT_PREVIEW_ENABLED = _strict_bool("SA_AGENT_PREVIEW_ENABLED")
AGENT_PREVIEW_TOKEN = os.getenv("SA_AGENT_PREVIEW_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

if AGENT_PREVIEW_ENABLED and len(AGENT_PREVIEW_TOKEN.encode("utf-8")) < 32:
    raise ValueError(
        "SA_AGENT_PREVIEW_TOKEN must contain at least 32 UTF-8 bytes when preview is enabled"
    )


# Only resource budgets are configurable, and every override may tighten the frozen defaults.
# Provider identity, retry count/jitter, capacity, pricing, and tool policy remain fixed.
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


def _preview_limits() -> PreviewLimits:
    from .preview_agent import PreviewAgent, PreviewLimits

    defaults = PreviewLimits()
    values = {field.name: getattr(defaults, field.name) for field in fields(defaults)}
    for field_name, (env_name, kind) in _PREVIEW_LIMIT_ENV.items():
        default = getattr(defaults, field_name)
        if kind == "float":
            values[field_name] = _tight_float(env_name, default)
        else:
            values[field_name] = _tight_int(env_name, default)
    limits = PreviewLimits(**values)
    PreviewAgent.validate_limits(limits)
    return limits


AGENT_PREVIEW_LIMITS = _preview_limits()

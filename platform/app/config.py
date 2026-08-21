"""运行时配置：环境变量 → 常量，模拟参考项目 AiProperties 的配置绑定。"""

from __future__ import annotations

import os
from pathlib import Path

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

# ===== LLM（OpenAI 兼容）=====
LLM_BASE_URL = os.getenv("SA_LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("SA_LLM_API_KEY", "")
LLM_MODEL = os.getenv("SA_LLM_MODEL", "")

# 是否启用向量检索（依赖可选安装）
VECTOR_ENABLED = USE_VECTOR

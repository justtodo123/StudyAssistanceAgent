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
BM25_POOL = int(os.getenv("SA_BM25_POOL", "50"))
USE_VECTOR = os.getenv("SA_USE_VECTOR", "true").lower() in ("1", "true", "yes")
EMBEDDING_MODEL = os.getenv("SA_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

# ===== LLM（OpenAI 兼容）=====
LLM_BASE_URL = os.getenv("SA_LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("SA_LLM_API_KEY", "")
LLM_MODEL = os.getenv("SA_LLM_MODEL", "")

# 是否启用向量检索（依赖可选安装）
VECTOR_ENABLED = USE_VECTOR

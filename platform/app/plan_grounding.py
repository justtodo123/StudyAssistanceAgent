"""M9 受限检索接缝：为 Planner 按需取回**有界**的 grounding 证据。

只读（领域级）：不写 Source 生命周期、不写学习会话、不写计划状态、不构建 chunk 索引、不读
目录之外的正文。权威写入仍是 `StudySessionService` / `SourceLifecycleService` / 领域仓储。

本模块**不新建检索实现**：它复用 `MultiRecallService.recall`，只在外面加四类预算与一道
独立的 fail-closed 交叉校验。

## 为什么不进计划身份、也不进计划 summary

`M9-EVALUATION` 的 `STALE_DELETED_SOURCE_ENTRY_ZERO` 是**检索路径**判据。grounding 结果依赖索引
generation，因此：

- **不进 `plan_id`**：计划 §1.1 要求「索引重建不得无故改变计划身份」，折进身份会让每次 reindex
  都 churn `plan_id`；
- **不进 `summary`**：本仓已有先例——`unorderable` 被刻意排除在计划 `summary` 之外，正是为了保住
  「同一 `plan_id` ⇒ 相同 `summary`」这条结构性不变量。

计划 §1.1 的原文恰好支持这一拆分：「PlanTask 优先引用稳定 topic/source identity；引用 chunk 时
必须绑定 revision/generation」——稳定身份在计划内，generation-bound chunk 按需取。

## 预算按 UTF-8 字节计，不按 token 计

本仓没有本地 tokenizer；M6b 对同类问题用的是 `max_prompt_bytes` / `max_answer_bytes`
（`preview_agent.py`）。凭空写一个「token 数」是估算冒充计量，故此处一律按字节计。

## 两道防线

1. **内层**：`MultiRecallService.recall` 在 principal 作用域下**绕过**外层结果缓存
   （`retrieval.py`），用户源命中经 M7 的 isolation gate、generation 绑定与
   `ensure_user_provenance` 末道检查；
2. **本模块的交叉校验**：召回后，任何 `user://{source_id}/…` chunk 的 `source_id` 不在
   `summaries(principal_id)` 的可用集合内即**丢弃**。这是独立于内层路径的第二道验证，使判据在
   Planner 接缝上可测。可用集合为空（未注入投影、无 principal、或控制面不可用）时，**所有**
   用户源 chunk 都被丢弃——fail-closed，不 fail-open。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable

from .models import RetrievalChunk
from .retrieval import RetrievalScope
from .user_source_search import USER_PROVENANCE_SCHEME

GROUNDING_SCHEMA_VERSION = "m9-plan-grounding-v1"


class GroundingBudgetError(ValueError):
    """请求的预算非法，或试图放宽冻结上限。"""


@dataclass(frozen=True, slots=True)
class GroundingBudget:
    """四类预算。字段默认值即**冻结上限**（`GROUNDING_BUDGET_CEILING`），调用方只能收紧。

    `max_user_sources` 只约束**用户源**的去重来源数，不约束默认知识包——默认包不是生命周期
    门控对象，它由 `top_k` 与 `max_evidence_bytes` 约束。
    """

    top_k: int = 5
    max_evidence_bytes: int = 16_384
    max_user_sources: int = 4
    timeout_seconds: float = 2.0


# 冻结上限：任何请求预算必须在每个维度上 ≤ 它。
GROUNDING_BUDGET_CEILING = GroundingBudget()


@dataclass(frozen=True, slots=True)
class GroundingEvidence:
    """一次 grounding 的结果。`truncated` 记录**哪些预算真的约束了结果**。"""

    chunks: tuple[RetrievalChunk, ...] = ()
    user_source_ids: tuple[str, ...] = ()
    truncated: tuple[str, ...] = ()
    dropped_unusable_sources: int = 0
    cross_checked: bool = False
    elapsed_ms: float = 0.0


@runtime_checkable
class SourceSummaryReader(Protocol):
    """对齐 `SourceSummaryProjection.summaries` 与 `LazySourceSummaryProjection.summaries`。"""

    def summaries(self, principal_id: str | None = None) -> dict[str, dict[str, Any]]: ...


def _user_source_id(file: str) -> str | None:
    """`user://{source_id}/…` → `source_id`；非用户源 → `None`。

    畸形或空的 `source_id` 原样返回：它必然不在可用集合里，因而被丢弃（fail-closed）。
    """
    prefix = f"{USER_PROVENANCE_SCHEME}://"
    if not file.startswith(prefix):
        return None
    source_id, _separator, _rest = file[len(prefix) :].partition("/")
    return source_id


class PlanGroundingService:
    """只读 grounding 接缝。刻意不缓存：证据必须反映当前 generation 与生命周期状态。"""

    def __init__(
        self,
        recall: Callable[..., tuple[list[RetrievalChunk], str]],
        *,
        source_summary: SourceSummaryReader | None = None,
        ceiling: GroundingBudget = GROUNDING_BUDGET_CEILING,
    ) -> None:
        self._recall = recall
        # 依赖是**活对象且可空**：未注入时可用集合恒为空，用户源 chunk 全部被丢弃。
        self._source_summary = source_summary
        self._ceiling = ceiling

    def ground(
        self,
        question: str,
        *,
        course: str | None = None,
        principal_id: str | None = None,
        budget: GroundingBudget | None = None,
    ) -> GroundingEvidence:
        """按预算取回 grounding 证据。预算缺省即冻结上限。"""
        started = time.perf_counter()
        requested = budget if budget is not None else self._ceiling
        self._validate(requested)

        principal = (principal_id or "").strip() or None
        if requested.top_k <= 0:
            return GroundingEvidence(cross_checked=self._source_summary is not None)

        # 可用集合一次取好：交叉校验与「无 principal 即无用户源」都由它决定。
        usable = self._usable_sources(principal)

        chunks, _mode = self._recall(
            question,
            top_k=requested.top_k,
            course=course,
            scope=RetrievalScope.DEFAULT_PLUS_EXTRAS,
            principal_id=principal,
        )

        elapsed_ms = (time.perf_counter() - started) * 1000
        # 事后截止检查，**不是**硬中断：`recall` 是同步调用且没有取消通道，一次已经卡住的召回
        # 无法被抢占。该预算约束的是 Planner **接受**多少证据，不是检索路径**做**多少工作。
        if elapsed_ms > requested.timeout_seconds * 1000:
            return GroundingEvidence(
                truncated=("timeout",),
                cross_checked=self._source_summary is not None,
                elapsed_ms=elapsed_ms,
            )

        kept, dropped, sources, truncated = self._apply_budgets(list(chunks), usable, requested)
        return GroundingEvidence(
            chunks=tuple(kept),
            user_source_ids=sources,
            truncated=truncated,
            dropped_unusable_sources=dropped,
            cross_checked=self._source_summary is not None,
            elapsed_ms=elapsed_ms,
        )

    def _usable_sources(self, principal: str | None) -> frozenset[str]:
        """当前可用于检索的用户源 id 集合。任何不确定都收敛到空集（fail-closed）。"""
        if self._source_summary is None or principal is None:
            return frozenset()
        try:
            return frozenset(self._source_summary.summaries(principal))
        except Exception:
            return frozenset()

    @staticmethod
    def _apply_budgets(
        chunks: list[RetrievalChunk],
        usable: frozenset[str],
        budget: GroundingBudget,
    ) -> tuple[list[RetrievalChunk], int, tuple[str, ...], tuple[str, ...]]:
        """按 `top_k` → 来源数 → 字节 的顺序裁剪，并丢弃不可用的用户源。

        顺序刻意固定：先砍掉最便宜的维度，保证同一输入 + 同一预算下结果可重放。
        """
        truncated: list[str] = []
        if len(chunks) >= budget.top_k:
            # 召回本身已按 top_k 截断，故「达到」即「预算可能约束了结果」。
            truncated.append("top_k")
        chunks = chunks[: budget.top_k]

        kept: list[RetrievalChunk] = []
        dropped = 0
        seen: list[str] = []
        used_bytes = 0
        for chunk in chunks:
            source_id = _user_source_id(chunk.file)
            if source_id is not None:
                if source_id not in usable:
                    dropped += 1
                    continue
                if source_id not in seen:
                    if len(seen) >= budget.max_user_sources:
                        truncated.append("max_user_sources")
                        continue
                    seen.append(source_id)
            size = len(chunk.content.encode("utf-8"))
            if used_bytes + size > budget.max_evidence_bytes:
                truncated.append("max_evidence_bytes")
                continue
            used_bytes += size
            kept.append(chunk)
        return kept, dropped, tuple(seen), tuple(dict.fromkeys(truncated))

    def _validate(self, budget: GroundingBudget) -> None:
        """只允许收紧：任何维度超出冻结上限即拒绝，不放宽。"""
        if (
            budget.top_k < 0
            or budget.max_evidence_bytes < 0
            or budget.max_user_sources < 0
            or budget.timeout_seconds <= 0
        ):
            raise GroundingBudgetError(
                "budget values must be non-negative (timeout_seconds must be positive)"
            )
        ceiling = self._ceiling
        if (
            budget.top_k > ceiling.top_k
            or budget.max_evidence_bytes > ceiling.max_evidence_bytes
            or budget.max_user_sources > ceiling.max_user_sources
            or budget.timeout_seconds > ceiling.timeout_seconds
        ):
            raise GroundingBudgetError("grounding budget may only be tightened, never widened")

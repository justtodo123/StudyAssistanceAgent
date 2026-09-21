"""M9 只读复习历史投影：哪些知识条目**已经有复习记录**。

只读：不写 `review_history`、不写会话状态、不构建 chunk 索引、不读 chunk 正文。
权威写入仍是 `ReviewSchedulerService.log_review` / 领域仓储。

## 为什么需要它（这是一处已证实的缺陷）

`main.py` 原先把 `review_history=_learning_store.all_reviews()` 传给 Planner——那是**构造时求值一次**
的快照，于是同一进程内新记录的复习**永不反映到计划上**：`reviewed` 标志、排序优先级，以及经
`_derived_digest` 参与 `plan_id` 的那部分身份，全部停在进程启动时刻。

紧邻的 mastery 投影刻意传的是**活对象**（`MasteryProjectionService(_learning_store)`），注释原文即
「使计划身份与排序随答题状态刷新」。两条同源只读输入一个实时一个冻结，是明确的不一致；本模块把复习
历史这一侧补齐，注入方式与 `mastery_projection` / `source_summary` / `topic_graph` 三者同形。

## 只回答成员资格

Planner 只用 `file in reviewed` 决定排序优先级与 `reviewed` 标志，从不读 review payload。故本投影只
返回 `frozenset[str]`，不把 payload 交出去——那会凭空给出一条调用方并不需要、也无从审计的读取路径。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

REVIEW_HISTORY_PROJECTION_SCHEMA_VERSION = "m9-review-history-projection-v1"


@runtime_checkable
class ReviewHistorySource(Protocol):
    """只依赖一次批量读，签名对齐 `SqliteLearningStore.all_reviews`。"""

    def all_reviews(self) -> dict[str, dict[str, Any]]: ...


class ReviewHistoryProjection:
    """复习历史只读投影。刻意不缓存：新记录的复习必须立刻反映到计划上。"""

    def __init__(self, source: ReviewHistorySource) -> None:
        self._source = source

    def reviewed_files(self) -> frozenset[str]:
        """已复习条目的 file 键集合（`knowledge/{course}/{topic}.md`）。

        **恰好一次**批量读：输入有界，不随 chunk 总量增长，也不按条目逐个回查。
        """
        return frozenset(self._source.all_reviews())

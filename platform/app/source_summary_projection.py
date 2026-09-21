"""M9 只读 Source 摘要投影：某个 principal 名下**可用于检索**的 Source 清单。

只读（领域级）：不写 Source 生命周期、不写学习会话、不构建 chunk 索引、不读 chunk 正文。
权威写入仍是 `SourceLifecycleService` / 领域仓储。

**不是文件系统级只读**：`SqliteSourceRegistry._configure` 对每条连接都执行
`PRAGMA journal_mode=WAL`，`_initialize_or_validate` 会 `mkdir` 且可能建表，因此本模块只声称
「无领域写入」，不声称文件系统零变更。调用方（`main.py` 的懒装配）必须先判文件存在再构造，
否则一次请求就会在缓存目录里落库。

输出字段名是 `usable`，**不是** `authorized`：M7 的
`IsolationSnapshot.authorized_source_ids`（`source_isolation.py`）等于「`list_sources` 减去隐藏态」，
**包含** REGISTERED / SYNCING / DISABLED；本投影的集合严格更小。两者混用会让「已注册但未发布」
的源被当成可检索源。

未发布、未就绪、禁用、待删、已删的 Source **不进入**摘要（`M9-EVALUATION` 的
`STALE_DELETED_SOURCE_ENTRY_ZERO` 在规则层的对应物）。隐藏态由 `list_sources` 的 WHERE 子句
构造性排除，本模块不额外读取，因此也无法报告被排除的计数——证据由测试提供。
"""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any, Protocol, runtime_checkable

from .source_registry import (
    SourceLifecycleService,
    SourceLifecycleState,
    SourceRecord,
    SqliteSourceRegistry,
)

SOURCE_SUMMARY_SCHEMA_VERSION = "m9-source-summary-v1"
# 「可用」= 已发布且状态为 READY / DEGRADED。规范来源是 `source_offline.py` 内联的同一判断
# （离线检索在取快照前用它挡未发布的源）；那里没有可 import 的谓词，本模块内联一份并记录该重复，
# 不改 M7 生产文件。两处若发生分歧，以 `source_offline.py` 为准。
_USABLE_STATES = frozenset({SourceLifecycleState.READY, SourceLifecycleState.DEGRADED})


def is_usable_for_retrieval(record: SourceRecord) -> bool:
    """该 Source 是否可被检索使用：已发布 generation 且状态在 READY / DEGRADED 内。

    纯函数、无 I/O。刻意不在此处读磁盘快照做 generation 一致性校验——那是步骤 4 的受限检索
    职责，摘要只回答「目录里能不能出现这个源」。
    """
    return record.published_generation is not None and record.state in _USABLE_STATES


@runtime_checkable
class SourceRecordReader(Protocol):
    """只依赖一次 principal 作用域的批量读，签名对齐 `SourceLifecycleService.list_sources`。"""

    def list_sources(self, *, principal_id: str) -> tuple[SourceRecord, ...]: ...


class SourceSummaryProjection:
    """Source 摘要只读投影。刻意不缓存：生命周期状态必须反映当前值。"""

    def __init__(self, reader: SourceRecordReader) -> None:
        self._reader = reader

    def summaries(self, principal_id: str | None = None) -> dict[str, dict[str, Any]]:
        """只读摘要：`source_id → {state, published_generation, updated_at}`，仅含可用源。

        - principal 为假 → 空表且**不调用** `list_sources`（对齐检索路径「无 principal 即跳过
          用户源叠加」的缺省语义，也避免把 `SOURCE_AUTH_REQUIRED` 当成故障）；
        - **恰好一次** `list_sources`：输入有界，不随 chunk 总量增长，也不按源逐个回查；
        - 任何异常 → 空表。计划生成绝不因控制面不可用而失败（fail-soft），与
          `LazyUserSourceSearch` 的降级同形。

        输出只含 JSON 安全原语：`state` 取字符串、`updated_at` 取 ISO 字符串。计划记录走
        `json.dumps` 持久化，放 `datetime` 会在写入时报 `TypeError`。
        """
        if not principal_id:
            return {}
        try:
            records = self._reader.list_sources(principal_id=principal_id)
        except Exception:
            return {}
        summaries: dict[str, dict[str, Any]] = {}
        for record in records:
            if not is_usable_for_retrieval(record):
                continue
            summaries[record.source_id] = {
                "source_id": record.source_id,
                "state": str(record.state),
                "published_generation": record.published_generation,
                "updated_at": record.updated_at.isoformat(),
            }
        return summaries


class LazySourceSummaryProjection:
    """只在 registry 库真实存在时才打开控制面。

    与 `LazyUserSourceSearch` 同形（`RLock` + sticky `_unavailable` + 异常降级），但多一条硬约束：
    **`is_file()` 必须先于构造**。`SqliteSourceRegistry.__init__` 会 `mkdir` 并建表，跳过守卫就会
    在一次普通的计划生成请求里产生文件系统副作用——「只读投影」的声称会当场失效。

    `is_file()` 未命中**不**置 `_unavailable`：库可能在进程存活期间才被创建，此后应自动可用。
    """

    def __init__(self, registry_path: str | Path) -> None:
        self._registry_path = Path(registry_path)
        self._inner: SourceSummaryProjection | None = None
        self._lock = RLock()
        self._unavailable = False

    def summaries(self, principal_id: str | None = None) -> dict[str, dict[str, Any]]:
        inner = self._get()
        if inner is None:
            return {}
        return inner.summaries(principal_id)

    def _get(self) -> SourceSummaryProjection | None:
        with self._lock:
            if self._unavailable:
                return None
            if self._inner is not None:
                return self._inner
            if not self._registry_path.is_file():
                return None
            try:
                lifecycle = SourceLifecycleService(SqliteSourceRegistry(self._registry_path))
                self._inner = SourceSummaryProjection(lifecycle)
            except Exception:
                self._unavailable = True
                return None
            return self._inner

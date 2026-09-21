"""M9 只读 mastery 投影：跨会话答题聚合 → 知识条目文件路径粒度的粗粒度掌握度。

只读：不写 mastery、不写会话状态、不构建 chunk 索引、不读 chunk 正文。
权威写入仍是 `StudySessionService` / 领域仓储（`M9-MASTERY-AUTHORITY`）。

聚合身份是**知识条目的文件路径**（`knowledge/{course}/x.md`），不是 `study_sessions.topic`
那样的自由文本；解析规则与 `StudySessionService._log_review` 同序，见 `resolve_mastery_file_key`。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

from . import config

MASTERY_PROJECTION_SCHEMA_VERSION = "m9-mastery-projection-v1"
_KNOWLEDGE_PREFIX = "knowledge/"


@runtime_checkable
class AttemptAggregateSource(Protocol):
    def aggregate_attempts_by_session(self) -> dict[str, dict[str, Any]]: ...


class MasteryProjectionService:
    """mastery 只读投影。刻意不缓存：mastery 必须反映当前状态。"""

    def __init__(
        self,
        store: AttemptAggregateSource,
        entry_exists: Callable[[str], bool] | None = None,
    ) -> None:
        self._store = store
        # 注入点：测试可替换条目存在性判定；生产缺省按知识库根做一次 stat。
        self._entry_exists = entry_exists or knowledge_entry_exists

    def mastery_by_file(self) -> dict[str, dict[str, Any]]:
        """只读 mastery 投影：`file → {attempts, correct, last_mastered}`。

        与 `ReviewSchedulerService.overdue_by_file()` 同形：纯读、无写、不构建 chunk 索引。
        不可映射的会话被**排除**而不是猜测；候选键对应的条目不存在时同样丢弃。

        `attempts` 计的是答题**行数**，因此「先答错再答对」是 attempts=2 / correct=1。
        """
        totals: dict[str, dict[str, Any]] = {}
        for session in self._store.aggregate_attempts_by_session().values():
            file_key = resolve_mastery_file_key(
                course=session["course"],
                topic=session["topic"],
                source_file=session["source_file"],
                question_source_file=session["question_source_file"],
            )
            if file_key is None or not self._entry_exists(file_key):
                continue
            bucket = totals.setdefault(
                file_key, {"attempts": 0, "correct": 0, "last_mastered": None}
            )
            bucket["attempts"] += session["attempts"]
            bucket["correct"] += session["correct"]
            last = session["last_mastered"]
            if last and (bucket["last_mastered"] is None or last > bucket["last_mastered"]):
                bucket["last_mastered"] = last
        return totals


def resolve_mastery_file_key(
    course: str,
    topic: str,
    source_file: str = "",
    question_source_file: str = "",
) -> str | None:
    """按 `StudySessionService._log_review` 的同序规则解析 mastery 聚合键。

    1. `sources[0].file`——会话持久化的检索出处；
    2. `questions[0].question.source_file`——无检索出处时的出题出处；
    3. 回退 `knowledge/{course}/{topic}.md`——**这是猜测**，调用方必须再用 `entry_exists` 校验；
       三者都取不到时返回 `None`（不可映射 → 排除）。

    纯函数、无 I/O，便于单独钉住规则；刻意不在此处做存在性判断，因为「猜测」与「校验」是两件事，
    混在一起会让回退分支无法被单独测试。
    """
    if source_file:
        return source_file
    if question_source_file:
        return question_source_file
    if course and topic:
        return f"{_KNOWLEDGE_PREFIX}{course}/{topic}.md"
    return None


def knowledge_entry_exists(file_key: str) -> bool:
    """候选键是否为真实知识条目：一次 stat，不建索引、不读正文。

    回退键由用户自由文本 topic 拼出，必须挡住 `../` 越界与非法后缀，否则
    `knowledge/os/../../x.md` 这类键会被当成条目，让宿主路径进入计划载荷。
    """
    if not file_key.startswith(_KNOWLEDGE_PREFIX) or not file_key.endswith(".md"):
        return False
    relative = file_key[len(_KNOWLEDGE_PREFIX):]
    if any(part in ("", ".", "..") for part in relative.split("/")):
        return False
    root = Path(config.KNOWLEDGE_ROOT).resolve()
    try:
        candidate = (root / relative).resolve()
    except OSError:
        return False
    if candidate != root and root not in candidate.parents:
        return False
    return candidate.is_file()

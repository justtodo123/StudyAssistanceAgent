# M9 目标驱动学习计划测试

验证确定性 Planner 的完整链路：Goal + 约束 + 只读复习与 **mastery** 投影 → 版本化、可重放的分日计划，
以及采纳 / 进度事件 / 偏差触发的版本化重规划。只读 mastery 投影（不写 mastery、不写学习状态，
不读原始 chunk 正文，不引入外部 AI）。

## 文件

| 文件 | 覆盖 |
|------|------|
| `test_goal_planner.py` | 确定性生成、版本、计划身份、输入有界与只读守卫 |
| `test_plan_lifecycle.py` | 采纳、进度事件、重规划与 revision 前向链 |
| `test_deviation_signals.py` | 跳过 + 逾期偏差信号、阈值触发与 `parent_revision_id` |
| `test_deviation_consumption.py` | 未消费阈值、`deviation_ledger` 消费台账与重复调用幂等 |
| `test_mastery_projection.py` | 跨会话答题聚合、知识条目 file 路径映射（三分支，与 `_log_review` 同序）、不可映射排除、真只读守卫、有界输入、计划身份派生输入摘要、存量计划兼容 |
| `test_source_summary_projection.py` | 「可用」规则 7 态 × 有无 generation 矩阵、隐藏态排除、恰好一次 bulk 读、只读守卫、懒装配不建库、principal 守卫、有界输入、与 Planner 的接缝 |

## 三条关键约定

- **聚合身份是知识条目的 file 路径**，不是 `study_sessions.topic` 那样的自由文本。解析顺序与
  `StudySessionService._log_review` 一致（检索出处 → 出题出处 → `knowledge/{course}/{topic}.md` 回退）；
  不可映射或条目不存在的会话被**排除而非猜测**。
- **计划身份含派生输入摘要**：`plan_id` 覆盖 goal / 目标日期 / 课程 / 每日学时 / 约束，以及最终任务列表的
  `task_id`/`reviewed`/mastery 序列。因此复习或 mastery 状态变化会得到**新的** `plan_id`；旧计划记录只读保留，
  仍可 `GET` / `adopt` / `progress` / `replan`，只是不再被重新生成命中。
- **Source 摘要里的集合叫 `usable`，不叫 `authorized`**：规则是「已发布 generation 且状态为 READY / DEGRADED」，
  规范来源是 `source_offline.py` 内联的同一判断。它**严格小于** M7 的
  `IsolationSnapshot.authorized_source_ids`（后者含 REGISTERED / SYNCING / DISABLED）。未发布、未就绪、
  禁用、待删、已删的源都不进入摘要；隐藏态由 `list_sources` 的 WHERE 子句构造性排除，
  因此投影**无法报告**被排除的计数——该证据由本目录的测试提供。

## 命令

```bash
./platform/.venv/Scripts/python -m pytest tests/M9 -v
./platform/.venv/Scripts/python -m pytest tests/M9 -m m9 -q
```

自 2026-09-21 起本套件已纳入 `.github/workflows/offline-ci.yml` 的阶段测试步骤。

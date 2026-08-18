# 问题记录库（proced_problem/）

> 记录项目开发中实际遇到的问题：症状、定位过程、根因与修复。目的是积累工程直觉，可复盘、可检索。

## 为什么叫"proced_problem"

"proced" = **Pro**blem **Rec**ord**ed** — 每一个被踩过、定位出来的问题，而不是未发生的理论风险。已经过一遍完整的问题解决闭环。

## 目录结构

```
proced_problem/
├── README.md              # 本导航文件
├── _template.md            # 记录模板
└── {序号}-{简短slug}.md    # 单条问题记录
```

## 记录列表

| 序号 | 标题 | 日期 | 标签 |
| --- | --- | --- | --- |
| 001 | [BM25 候选池截断导致 Recall 回归](001-bm25-pool-silent-truncation.md) | 2026-08-12 | retrieval, bug, recall-regression, silent-failure |
| 002 | [测试基线与项目文档统计脱节](002-test-baseline-and-documentation-drift.md) | 2026-08-17 | testing, documentation, repository-hygiene, milestone-drift |
| 003 | [M4 任务范围膨胀且缺少检查点导致长时间无可见成效](003-long-running-task-without-checkpoints.md) | 2026-08-18 | workflow, scope-control, testing, checkpoint, agent-execution |

## 如何新增记录

1. 复制 `_template.md`，按 `{序号}-{slug}.md` 命名
2. 填写各章节：症状 → 定位过程 → 根因 → 修复 → 验证 → 经验
3. 更新本 README 的记录列表
4. 触发方式：手动编写，或用 `problem-record` skill 辅助模板填写

## 关联

- RAG 评测基线：[docs/baselines.md](../docs/baselines.md)
- 项目计划：[docs/PLAN.md](../docs/PLAN.md)

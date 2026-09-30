# 迭代测试体系

根级 `tests/` 按里程碑隔离增量测试，`platform/tests/` 保留 40 项原始平台基线。详细测试矩阵、历史读数和
维护约束见 [TEST_PLAN.md](TEST_PLAN.md)。

## 目录导航

| 目录 | 作用 |
| --- | --- |
| `M0_M2/` | M0–M2 基线回归 |
| `M3a/`–`M3d/` | 向量存储、可观测性、面经库、文档完整性 |
| `M4/` | 课程知识库规模与检索优先级 |
| `M5a/`–`M5e/` | 评测、会话、持久化、工作台与离线交付 |
| `M6_crawler/`、`M6a/`、`M6b/` | crawler、Harness 骨架与只读 Agent Preview |
| `M7/` | 用户源 lifecycle、解析、检索与隔离 |
| `M8_metadata_discovery/` | M8 selected-scope metadata discovery 治理链 |
| `M9/` | 目标驱动 Planner 与外部 AI 可选路径 |
| `M10/` | Autonomous Runner、恢复与评测 |
| `M11/` | 真实数据规模化的离线治理合同 |
| `regression/` | 跨阶段回归与治理一致性 |
| `source_inventory/` | 外部资料只读盘点测试 |
| `utils/` | 跨阶段测试辅助函数 |

## 常用命令

```bash
./platform/.venv/Scripts/python -m pytest tests/ -v
./platform/.venv/Scripts/python -m pytest tests/regression/ -v
./platform/.venv/Scripts/python -m pytest tests/ -m m3d
```

阶段开发遵循“本阶段测试 → regression → 提交”的顺序。M7 的冻结五格式完整证据依赖 CPython 3.11.9；
其他环境中的已登记 TXT fail-closed 行为不得通过放宽断言规避。

# 项目文档（docs/）

> StudyAssistanceAgent 项目文档目录。包含项目计划、外部资料索引、开发规范、面试叙事。

## 文档结构

```
docs/
├── README.md              # 本导航文件
├── PLAN.md                # ★ 项目计划与路线图（里程碑、技术选型、风险）
├── reference/             # 外部参考资料索引
│   ├── README.md          # 索引总览与维护规则
│   ├── _template.md       # 新课程索引模板
│   └── {course}.md        # 各课程原始资料登记（路径、类型、状态）
├── standards/             # 开发规范
│   └── git-conventions.md # Git 提交规范（Conventional Commits）
└── interview/             # 面试叙事（AI 应用开发岗）
    └── README.md          # 一句话叙事 + 设计决策 + 考点映射 + 常见追问
```

## 各目录说明

### PLAN.md — 项目计划

核心文件。定义项目双目标（自学价值 + 面试价值）、技术选型（已拍板）、里程碑（M0~M3）、风险与缓解。
**每次会话开工前先看本文档**，明确当前里程碑与退出条件。

### reference/ — 外部资料索引

映射层：将 `D:\111_Others_Subjects` 中的原始资料目录登记为可检索的索引。
- 主索引：[reference/README.md](reference/README.md) — 按优先级分类（核心专业课 / 专业拓展 / 其他）
- 各课程索引：`reference/{course}.md` — 记录该课程原始资料的路径、文件类型、整理状态

**维护规则**：
- 新增外部资料 → 在 [reference/README.md](reference/README.md) 中加一行，并新建/追加对应课程索引文件
- 某课程已整理笔记 → 将状态改为 `📝 笔记已建`
- 更新知识库时同步刷新本索引

### standards/ — 开发规范

- [git-conventions.md](standards/git-conventions.md)：Conventional Commits 规范，含类型表、scope 约定、撤销速查

### interview/ — 面试叙事

面向 **AI 应用开发岗** 的面试备战文档：
- 一句话项目叙事
- 5 个设计决策与能力映射
- 8 个考点映射（RAG / Embedding / Chunking / 缓存 / Prompt / SSE / 降级 / 可观测）
- 数据驱动优化的实锤方案
- 常见追问与备好答案

---

## 文档维护规范

1. **每次改动后，及时更新对应的 README.md**：若改动涉及目录结构、新增文件、API 变更、状态变化，务必同步刷新从当前目录到项目根目录的各级 README。
2. **PLAN.md 随里程碑推进更新**：完成一个里程碑后标记为 ✅ 并记录关键产出。
3. **reference/ 索引与知识库同步**：笔记入库时更新对应课程索引状态。
4. **所有文档使用中文**，Markdown 格式，行宽 ≤ 120 字符。

---

*创建：2026-08-11 · 维护：随项目演进同步更新*

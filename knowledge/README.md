# 知识库（knowledge/）

> 这是本项目**核心资产**：计算机课程的精炼笔记、例题、面经与索引，全部为 Markdown，随仓库版本化。

## 为什么叫"知识库"而不是"课程资料"

- **原始资料**（PDF / PPT / 实验工程 / 论文）留在 `D:\111_Others_Subjects`，人工整理，仓库不收录。
- **本目录**只存放**精炼、可复用、带结构化导航**的笔记与索引，是 Agent 回答问题的知识底座。

## 目录结构约定

```
knowledge/
├── README.md              # 本导航文件
├── {course}/              # 每门课程一个目录（kebab-case，如 operating-system）
│   ├── README.md          # 课程导航：课程简介、章节地图、外部资料索引指针
│   └── *.md               # 主题条目，如 memory-management.md
├── interview/             # 面经知识库（课程题 + RAG/Agent + 项目追问）
│   ├── README.md          # 面经导航与写作规范
│   ├── os/                # OS 面经
│   ├── ds/                # DS 面经
│   ├── co/                # CO 面经
│   ├── rag-agent/         # RAG/Agent 工程面经
│   └── project/           # 项目介绍与系统设计面经
├── _templates/            # 条目模板（新建条目时复制）
└── _inbox/                # 待审核候选（不进入检索）
```

## 每门课程目录的 README 应包含

1. **课程简介**：学习目标、考核方式（如有）
2. **章节地图**：章节 → 对应条目文件的链接
3. **重点与难点**：高频考点、易错点速览（可随复习补充）
4. **外部资料指针**：指向 `docs/reference/` 中该课程的原始资料登记

## 条目 frontmatter（必填，写满）

```yaml
---
title: 条目标题
course: 课程简称（如 os, ds, co, interview, db, network, ai, se）
tags: [topic1, topic2]
difficulty: 入门 | 中等 | 进阶
updated: 2026-08-31
source_id: knowledge-pack
logical_uri: os/example.md
document_id: 由 source_id + logical_uri 按协议计算的 32 位十六进制 ID
provenance: project_authored_ai_assisted | external_source_derived | web_derived_ai_assisted
project_authored: true | false
canonical_url: https://example.org/original  # 非项目原创时必须填写可核验原始 URL
publisher: 发布机构（适用时）
author: 作者或 repository contributor
source_type: human_markdown
format: markdown
review_status: review | approved | rejected
ingest_status: candidate | approved | rejected
registration_method: repository_commit | manual_document_mapping | legacy_course_index
license_id: MIT 或经核验的许可证标识；未知时写 unknown
license_status: unresolved | approved | rejected | revoked
license_verified_at: 2026-08-31  # approved 时必填
provenance_evidence: docs/reference/document-mapping.json
---
```

文档级来源与许可决定以 [`docs/reference/document-mapping.json`](../docs/reference/document-mapping.json) 为
P0 治理登记。`canonical_url` 与 `project_authored: true` 必须二选一；字段缺失、来源无法核验、许可证未批准或审核未通过时，
统一保持 `candidate`，不得依赖旧默认值自动提升为可检索文档。该登记不是未来 M7 runtime `ProvenanceRecord`，也不构成
M7 准入。

### 课程条目的精简键集与 `prerequisites`

上面的 22 键规范描述的是 `network/`、`interview/` 语料（受
[`docs/reference/document-mapping.json`](../docs/reference/document-mapping.json) 治理）。`os/`、`ds/`、`co/`
三门课程的 60 条条目**实际只用 6 个键**（外加可选的 `prerequisites`）：

```yaml
---
title: 段页式存储管理
course: os
tags: [分段, 分页, 段页式, 地址转换, x86]
difficulty: 进阶
updated: 2026-09-21
source: docs/reference/os.md
prerequisites: [memory-management]
---
```

- `prerequisites`（可选）声明**先修条目**，供 M9 确定性 Planner 生成先修合法的学习顺序；
  不写该键与写 `prerequisites: []` 等价于「无先修」。期考复盘类条目不声明先修——它们是复习产物，
  不是有先修关系的知识主题。
- 值是**与本文档同目录的兄弟文件的 stem**（不含 `.md`、不含路径分隔符）。刻意不做跨目录/跨课程解析：
  `knowledge/interview/co/` 是嵌套目录，全树有多个 basename 撞名，按课程解析会把先修**静默**连到面经条目上。
- **只支持行内方括号形式**。块状 YAML（后续行写 `- a`）不匹配解析器的字段正则，会被**静默**解析成空列表——
  不报错、不告警。`tests/M9/test_topic_graph_projection.py` 按原始文件断言只用了行内形式。
- 命名空间提示：此处的 `prerequisites` 与
  [`docs/standards/stage-admission-gates.json`](../docs/standards/stage-admission-gates.json) 中**阶段**的
  `prerequisites` 同词不同义，不要混用。

## 写作规范

- **精炼**：只写核心概念、推导、易错点、例题。大段原文抄录不入库，遇到扩展内容链接到原始资料。
- **结构化**：善用标题层级、表格、代码块（代码块注明语言）。
- **可检索**：`tags` 与标题一起构成检索入口；同义词/别名在正文首次出现处标注。
- **更新驱动**：`updated` 字段在每次改动时更新；旧条目打上 `[过时请复核]` 标记而不是默默删除。
- **指向外部资料**：格式统一为 `参考原始资料：docs/reference/os.md#章节名`，**不要**直接引用 `D:\` 绝对路径作为文件链接以外的东西。

## 检索方式

1. 目录导航：逐门课程进入 `README.md`。
2. 全文检索：`Grep` 搜 `knowledge/`（如 `Grep pattern "页表" path knowledge/`）。
3. `tags` 聚合：按 difficulty / topic 查找。

## 当前已有课程

> 有内容条目的课程登记于此，随整理进展更新。

| 课程 | 简称 | 知识库入口 | 条目数 | 状态 |
| --- | --- | --- | --- | --- |
| 操作系统 | os | [os/](os/README.md) | 20 | ✅ M4 完成（新增线程、IPC、实时调度、文件分配、设备管理） |
| 数据结构 | ds | [ds/](ds/README.md) | 20 | ✅ M4 完成（新增分治、动态规划、平衡树、并查集、字符串匹配、哈希、图算法、外部排序） |
| 计算机组成原理 | co | [co/](co/README.md) | 20 | ✅ M4 完成（新增数制、乘除法、Cache、地址转换、控制器、流水线、中断、总线、性能） |
| 计算机网络 | network | [network/](network/README.md) | 31 | ✅ M1 完成（408 全章节覆盖：物理层→数据链路→网络层→传输层→应用层→网络安全） |

## 面经知识库

- [面经导航](interview/README.md)：51 条条目，覆盖 OS、DS、CO、RAG/Agent 和项目追问。
- 面经使用与课程笔记相同的 frontmatter 和 Markdown 索引流程，可被搜索与 QA 引用。


| 面经知识库 | interview | [interview/](interview/README.md) | 51 | ✅ M3c 完成（OS/DS/CO/RAG/Agent/项目追问） |

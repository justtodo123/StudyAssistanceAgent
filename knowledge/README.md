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
updated: 2026-08-10
source: 参考的外部资料路径或书目（可省略，指向 docs/reference 索引）
source_type: human_markdown  # 可选；网页候选为 web_candidate，审核后为 web_reviewed
ingest_status: approved      # 可选；candidate 不会进入检索
---
```

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

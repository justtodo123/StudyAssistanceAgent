---
title: 图的 BFS 与 DFS
course: interview
tags: [图, BFS, DFS]
difficulty: 入门
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/ds/graph-bfs-dfs.md
document_id: 883cea3d98af695ed31a0e47c4a5c833
provenance: project_authored_ai_assisted
source_type: human_markdown
format: markdown
registration_method: repository_commit
provenance_evidence: docs/reference/document-mapping.json
project_authored: true
publisher: StudyAssistanceAgent project
author: repository contributor
review_status: approved
ingest_status: approved
license_id: MIT
license_status: approved
license_verified_at: 2026-08-31
---

## 面试问题

图的 BFS 与 DFS：BFS 按层访问，适合无权图最短边数问题；DFS 沿路径深入，适合连通分量、拓扑排序和回溯。邻接表空间通常为 O(V+E)。

## 回答要点

必须记录 visited 防止环导致重复访问。递归 DFS 可能受栈深限制，工程上可改为显式栈。

## 项目结合点

知识库目录和引用关系可以看成图；文档完整性检查要避免循环链接或重复遍历。

## 继续追问

有向图如何检测环？BFS 能否做拓扑排序？

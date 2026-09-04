---
title: 栈、队列与双端队列
course: interview
tags: [栈, 队列, 数据结构]
difficulty: 入门
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/ds/stack-queue.md
document_id: 10563c1036c1a7e764a73aee78cd47cb
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

栈、队列与双端队列：栈遵循后进先出，适合函数调用、括号匹配和回溯；队列遵循先进先出，适合任务调度；双端队列支持两端插入删除，可实现滑动窗口。

## 回答要点

选择数据结构要从操作序列出发，而不是只看名字。循环队列要处理空满区分，优先队列则由堆维护最小或最大元素。

## 项目结合点

RAG 请求可以进入队列控制并发，最近 200 个延迟样本则适合用定长 deque 自动淘汰旧样本。

## 继续追问

如何用两个栈实现队列？

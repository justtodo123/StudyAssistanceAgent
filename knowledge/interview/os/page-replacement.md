---
title: 页面置换：FIFO、LRU 与近似算法
course: interview
tags: [页面置换, LRU, 缺页]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/page-replacement.md
document_id: d24f1b026aa78656f0089693cde66152
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

页面置换：FIFO、LRU 与近似算法：FIFO 按进入内存的先后淘汰页面，可能出现 Belady 异常；LRU 淘汰最久未使用页面，符合局部性但精确实现代价高；实际系统常使用时钟等近似算法。

## 回答要点

页面置换的核心不是背算法，而是理解访问局部性、缺页率与实现开销的关系。工作集稳定时，增加内存通常能降低缺页。

## 项目结合点

重复 QA 请求命中结果缓存，类似利用时间局部性；缓存容量有限时也要明确淘汰策略和命中率口径。

## 继续追问

为什么 LRU 的精确实现不适合直接用于高并发内核？

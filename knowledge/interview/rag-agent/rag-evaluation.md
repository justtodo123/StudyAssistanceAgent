---
title: RAG 评测：Recall、Precision 与延迟
course: interview
tags: [评测, Recall, 延迟]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/rag-agent/rag-evaluation.md
document_id: 56217efa3de9e147e6fc7f23b3491310
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

RAG 评测：Recall、Precision 与延迟：Recall@k 衡量相关文档是否出现在前 k 个结果中，Precision@k 衡量前 k 个结果中相关结果比例。还应记录端到端延迟、冷启动和缓存命中。

## 回答要点

评测集必须覆盖知识库内容，并固定标注口径。只看平均值会掩盖长尾，最好同时看 p95、失败率和不同查询类型。

## 项目结合点

项目 OS 评测集从 20 题扩展到覆盖 15 篇条目的 33 题；M3b 额外记录 BM25 cold 23.897ms、warm 0.060ms。

## 继续追问

为什么 Recall@3 高但回答质量仍可能差？

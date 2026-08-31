---
title: Embedding 向量检索的优点与局限
course: interview
tags: [Embedding, 向量检索, 语义]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/rag-agent/embedding.md
document_id: 3f27d7bf39acacbac660aa780751b7ca
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

Embedding 向量检索的优点与局限：Embedding 将文本映射为向量，语义相近的文本在向量空间中距离更近。向量检索能处理同义表达，但效果依赖模型、领域和切块质量。

## 回答要点

向量相似不等于事实相关，短查询可能产生主题相似但答案不匹配的结果。应保留关键词路、阈值和回退路径，并用标注评测集验证。

## 项目结合点

本项目 BGE 是可选依赖，未安装或不可用时自动降级 BM25，避免模型环境问题阻断学习助手。

## 继续追问

如何选择 embedding 模型和相似度度量？

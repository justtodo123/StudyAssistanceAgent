---
title: RAG 基本链路与边界
course: interview
tags: [RAG, 检索, 生成]
difficulty: 入门
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/rag-agent/rag-pipeline.md
document_id: d9321362cec3d6501e2e58c12f1792cb
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

RAG 基本链路与边界：RAG 通常包含文档索引、查询理解、候选召回、排序融合、上下文组装和答案生成。它把知识更新从模型参数中分离出来，适合个人知识库场景。

## 回答要点

RAG 不能自动保证正确性：召回错了会导致生成错，片段太长会稀释重点，提示词也可能被注入。必须保留来源并设置无命中降级。

## 项目结合点

本项目用 Markdown、BM25、可选 BGE 向量和 RRF，LLM 不可用时返回带出处的笔记摘要，保证链路可运行。

## 继续追问

RAG 与微调分别适合什么问题？

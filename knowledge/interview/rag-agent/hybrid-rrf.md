---
title: 混合检索与 RRF 融合
course: interview
tags: [混合检索, RRF, 排序]
difficulty: 进阶
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/rag-agent/hybrid-rrf.md
document_id: d2adb464d018fb362163bc5627caa87d
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

混合检索与 RRF 融合：混合检索同时使用关键词和向量召回，再通过 Reciprocal Rank Fusion 按各路排名累积分数。RRF 不要求不同检索器的原始分数可直接比较。

## 回答要点

融合前要统一候选对象 ID，融合后要做文件级去重并保留最高质量片段。课程过滤应尽量前置，避免无关候选占据名次。

## 项目结合点

MultiRecallService 保留 BM25 与向量两路，RRF 后按文件去重；M3a 抽象存储接口，M3b 记录 mode、耗时和 cache_hit。

## 继续追问

为什么不直接把 BM25 分数和余弦相似度相加？

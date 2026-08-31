---
title: Metadata 过滤与检索范围控制
course: interview
tags: [Metadata, 课程过滤, 检索]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/rag-agent/metadata-filtering.md
document_id: 980deebe7f66c3ffa2458cb2f1d198c5
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

Metadata 过滤与检索范围控制：metadata 过滤可以按课程、难度、标签、更新时间或文档类型缩小候选范围。过滤前置能减少无关结果和排序竞争，但过滤条件必须进入缓存 key。

## 回答要点

过滤字段要有稳定枚举和缺省行为。过滤过度会造成召回为空，因此应提供清晰的降级策略或提示用户扩大范围。

## 项目结合点

搜索请求支持 course 过滤，缓存 key 同时包含 question、top_k、threshold 和 course，避免不同课程请求错误复用结果。

## 继续追问

为什么课程过滤应在 RRF 前还是后执行？

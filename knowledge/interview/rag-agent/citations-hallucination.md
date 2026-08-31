---
title: 出处、幻觉与无命中回答
course: interview
tags: [幻觉, 出处, 可信度]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/rag-agent/citations-hallucination.md
document_id: f1fe7b35c5ab7ba1d872dae4144e95cb
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

出处、幻觉与无命中回答：出处不能自动证明答案正确，但可以让用户核查证据。没有相关片段时，系统应明确说明知识库暂无依据，而不是编造确定答案。

## 回答要点

生成提示词要限制上下文范围，答案附带来源文件；评测时检查答案是否被检索片段支持，并区分检索失败和生成失败。

## 项目结合点

QaService 在 LLM 不可用或失败时返回笔记摘要，搜索结果携带 file 和 title，形成可追溯的降级链路。

## 继续追问

如何评估一个回答是否被来源支持？

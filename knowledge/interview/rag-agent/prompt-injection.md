---
title: RAG 中的 Prompt Injection 风险
course: interview
tags: [Prompt Injection, 安全, RAG]
difficulty: 进阶
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/rag-agent/prompt-injection.md
document_id: 2ed64c8ed3f343c02fa409de36758f73
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

RAG 中的 Prompt Injection 风险：检索到的文档可能包含伪装成指令的文本，模型若把数据当成指令就会偏离系统目标。用户输入也可能要求泄露系统提示或敏感信息。

## 回答要点

应明确区分系统指令、用户问题和检索材料，要求模型只把材料当作证据；对外部内容做标记、过滤和最小权限控制。

## 项目结合点

本项目日志不记录问题正文和敏感配置，LLM 生成路径要求带出处，未配置 LLM 时不让异常文本阻断本地摘要降级。

## 继续追问

引用不可信网页时还需要哪些防护？

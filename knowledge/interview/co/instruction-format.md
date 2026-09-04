---
title: 指令格式、寻址方式与 ABI
course: interview
tags: [指令系统, 寻址, ABI]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/co/instruction-format.md
document_id: 32b3b497e3cc501f411d66698f52546b
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

指令格式、寻址方式与 ABI：指令格式描述操作码、寄存器和立即数字段；寻址方式决定操作数如何定位。ABI 规定调用约定、参数传递、寄存器保存和返回值，使不同编译单元能够协作。

## 回答要点

要把 ISA、微架构和 ABI 分开：ISA 是软件可见的指令契约，微架构是实现方式，ABI 是平台级二进制接口约定。

## 项目结合点

API 契约同样需要稳定字段和语义；即使内部换向量存储实现，也要保持搜索与 QA 的请求响应契约。

## 继续追问

API、ABI 和 ISA 三者有什么区别？

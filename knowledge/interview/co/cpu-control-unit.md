---
title: CPU 控制器与硬布线/微程序控制
course: interview
tags: [CPU, 控制器, 微程序]
difficulty: 进阶
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/co/cpu-control-unit.md
document_id: a3fd54546d7140ca328d5ebd8d37b00f
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

CPU 控制器与硬布线/微程序控制：控制器根据指令译码产生数据通路控制信号。硬布线控制速度快但修改复杂；微程序控制用控制存储器描述微操作，灵活但有额外访问成本。

## 回答要点

回答时应从控制信号、数据通路、指令周期和可维护性解释，而不是只背优缺点。现代处理器通常结合多种实现。

## 项目结合点

服务代码也把 API 路由、检索服务和模型调用分层，控制逻辑与数据处理分离有利于演进和测试。

## 继续追问

一条加法指令在数据通路中经历哪些微操作？

---
title: 系统调用与库函数的边界
course: interview
tags: [系统调用, 用户态, 内核态]
difficulty: 入门
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/syscall-vs-library.md
document_id: b934117dddb6faacd41ef8d5c3435f5c
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

系统调用与库函数的边界：系统调用是用户程序请求内核服务的受控入口，涉及权限切换和参数检查；库函数可能只是用户态封装，也可能在内部触发系统调用。

## 回答要点

比如文件读写库函数可能先访问用户态缓冲，缓冲不足时才调用 read。区分二者可以解释为什么一次 API 调用不一定对应一次内核切换。

## 项目结合点

FastAPI 端点是应用层 API，底层还会经过线程、文件、网络和日志系统；排查延迟时需要分层测量。

## 继续追问

用户态和内核态切换为什么有成本？

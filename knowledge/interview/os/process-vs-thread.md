---
title: 操作系统面试常见问题：进程与线程
course: interview
tags: [进程, 线程, 并发]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/process-vs-thread.md
document_id: 550bf65795af90625aa597f9a62c9159
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

操作系统面试常见问题：进程与线程：进程拥有独立地址空间和资源边界，线程共享进程资源但拥有独立栈、寄存器上下文与线程 ID。线程切换通常比进程切换轻，但共享内存也带来竞态与同步问题。

## 回答要点

回答时要区分资源隔离、调度单位和通信方式：进程间通信需要管道、消息队列或共享内存；线程间通信通常直接读写共享数据，但必须配合同步原语。

## 项目结合点

学习助手的检索服务使用进程内缓存时，若未来改成多线程服务，需要考虑缓存字典的并发读写和锁粒度。

## 继续追问

为什么多进程不能完全替代多线程？如何判断一个任务适合进程还是线程？

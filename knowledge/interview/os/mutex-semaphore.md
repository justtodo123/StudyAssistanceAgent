---
title: 互斥锁与信号量的区别
course: interview
tags: [同步, 互斥锁, 信号量]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/mutex-semaphore.md
document_id: 96f2aa9d411fe36801e2021803c44913
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

互斥锁与信号量的区别：互斥锁表达一个临界区的所有权，通常由加锁线程解锁；信号量维护计数，可表示可用资源数量或线程间事件通知。

## 回答要点

二者都能阻塞线程，但语义不同。用信号量代替互斥锁容易掩盖所有权错误，用锁保护共享状态时应明确临界区和不变量。

## 项目结合点

MetricsRegistry 用锁保护统计字典，统计记录是互斥访问；如果限制并发 worker 数，则更适合用计数信号量表达容量。

## 继续追问

条件变量为什么通常需要和互斥锁配合？

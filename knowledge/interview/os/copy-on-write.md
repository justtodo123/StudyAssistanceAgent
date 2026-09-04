---
title: 写时复制与 fork
course: interview
tags: [进程, 写时复制, 内存]
difficulty: 进阶
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/copy-on-write.md
document_id: 5837631f5563e46b76b3a7849e601a88
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

写时复制与 fork：fork 后父子进程先共享只读物理页，任一方写入时触发缺页并复制页面，这就是写时复制。它避免了立即复制全部地址空间。

## 回答要点

写时复制适合 fork 后很快 exec 的场景，但大量写入会产生复制开销。实现必须正确处理页权限、引用计数和异常路径。

## 项目结合点

索引结果缓存返回深拷贝，避免调用者修改共享缓存对象；这和写时复制一样，核心是控制共享状态的可变性。

## 继续追问

写时复制和不可变数据结构有什么相似与区别？

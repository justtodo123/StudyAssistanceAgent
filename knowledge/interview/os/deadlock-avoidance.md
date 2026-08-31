---
title: 死锁预防、避免、检测与恢复
course: interview
tags: [死锁, 银行家算法, 资源分配]
difficulty: 进阶
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/deadlock-avoidance.md
document_id: 82f2847dba36a1617b584540fbc9dd19
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

死锁预防、避免、检测与恢复：预防是在设计上破坏必要条件；避免是在每次分配前判断是否处于安全状态；检测允许死锁发生后寻找环；恢复则通过抢占、回滚或终止进程解除死锁。

## 回答要点

银行家算法需要知道最大资源需求，现实服务通常更偏向锁顺序、超时和故障隔离，因为它们更容易落地。

## 项目结合点

个人学习助手不需要复杂分布式锁管理，但可把请求超时、缓存失效和失败降级看作避免系统长期占用资源的工程手段。

## 继续追问

为什么银行家算法在通用操作系统中不常作为默认方案？

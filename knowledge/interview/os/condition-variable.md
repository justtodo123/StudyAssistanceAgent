---
title: 条件变量与生产者消费者模型
course: interview
tags: [条件变量, 生产者消费者, 同步]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/condition-variable.md
document_id: 061a1a13e3a3275f115e4e0de550173d
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

条件变量与生产者消费者模型：条件变量让线程在条件不满足时睡眠，在状态变化后被唤醒。等待通常写成 while 循环重新检查条件，不能用一次 if 判断替代。

## 回答要点

原因包括虚假唤醒、多个消费者竞争以及通知发生在状态检查之后。正确实现需要同一把锁保护谓词、队列和通知过程。

## 项目结合点

检索结果缓存可抽象成生产者消费者队列：索引构建是生产者，请求线程是消费者，缓存状态必须与实际数据一致。

## 继续追问

notify 与 notify_all 如何选择？如何避免丢失唤醒？

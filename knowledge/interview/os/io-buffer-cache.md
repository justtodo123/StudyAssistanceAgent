---
title: I/O 缓冲、缓存与异步 I/O
course: interview
tags: [I/O, 缓冲, 缓存]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/io-buffer-cache.md
document_id: fc7738d8daa21c89288c01da64e7d096
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

I/O 缓冲、缓存与异步 I/O：缓冲用于平滑生产者和消费者的速率差异，缓存用于复用已经读取或计算过的数据。异步 I/O 让线程提交操作后继续工作，完成时再处理结果。

## 回答要点

缓存命中不等于 I/O 结束，写缓存还涉及一致性、刷盘和崩溃恢复。应根据延迟、吞吐和数据可靠性选择同步策略。

## 项目结合点

知识库 JSON 索引缓存提高重复启动和健康检查速度，但文件修改时间变化时必须失效重建，否则会返回过期内容。

## 继续追问

page cache 和应用层缓存如何配合？

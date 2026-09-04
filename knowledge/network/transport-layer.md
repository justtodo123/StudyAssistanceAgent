---
title: 传输层概述
course: network
tags: [传输层, 端口号, 复用分用, TCP, UDP]
difficulty: 入门
updated: 2026-08-20
source_id: knowledge-pack
logical_uri: network/transport-layer.md
document_id: e4d8c2ebe014d95baed1c0625001f1a1
provenance: web_derived_ai_assisted
source_type: human_markdown
format: markdown
registration_method: legacy_course_index
provenance_evidence: docs/reference/document-mapping.json
project_authored: false
review_status: review
ingest_status: candidate
license_id: unknown
license_status: unresolved
---

## 一句话概括（TL;DR）

> 传输层提供进程间通信，端口号标识进程。熟知端口 0-1023，注册 1024-49151，动态 49152-65535。TCP 可靠/UDP 不可靠。

## 核心概念

### 端口号

- 熟知：0-1023（HTTP=80, FTP=21, DNS=53）
- 注册：1024-49151
- 动态：49152-65535

### 复用与分用

- 复用：多个进程共用传输层
- 分用：根据端口号交付到正确进程

### TCP vs UDP

| 维度 | TCP | UDP |
|---|---|---|
| 连接 | 面向连接 | 无连接 |
| 可靠 | 可靠 | 不可靠 |
| 模式 | 字节流 | 报文 |
| 首部 | 20B+ | 8B |

## 易错点 / 高频考点

- [ ] 套接字 = (IP:端口)
- [ ] TCP 首部 20B，UDP 首部 8B
- [ ] DNS 查询用 UDP，大响应用 TCP

## 经典例题

**题干**：传输层与网络层的区别？
**解答**：网络层提供主机间通信，传输层提供进程间通信（端到端）。

## 关联条目

- [[tcp-connection]]
- [[udp]]
- 参考原始资料索引：`docs/reference/network.md`

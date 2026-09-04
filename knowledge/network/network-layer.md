---
title: 网络层概述
course: network
tags: [网络层, 虚电路, 数据报, 转发]
difficulty: 入门
updated: 2026-08-20
source_id: knowledge-pack
logical_uri: network/network-layer.md
document_id: f5c611ce3c57f1b02d7184c88f9f8f1f
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

> 网络层两大任务：路由选择与分组转发。互联网采用数据报网络（无连接），SDN 把控制平面与数据平面解耦。

## 核心概念

### 虚电路 vs 数据报

| 维度 | 虚电路 | 数据报 |
|---|---|---|
| 连接 | 需建立 | 无连接 |
| 路由 | 建立时确定 | 每分组独立选路 |
| 代表 | ATM | IP |

### SDN

- 控制平面与数据平面分离
- 控制器集中计算下发流表

### 路由器结构

- 输入端口 → 交换结构 → 输出端口
- 最长前缀匹配

## 易错点 / 高频考点

- [ ] 转发是逐跳动作，路由是全局决策
- [ ] 互联网 IP 是无连接、乱序可能
- [ ] 路由器不修改 IP 地址

## 经典例题

**题干**：互联网网络层为何设计为无连接？
**解答**：网络层简单化、健壮性高，可靠传输上移给传输层（TCP），体现端到端原则。

## 关联条目

- [[ip-protocol]]
- [[routing]]
- 参考原始资料索引：`docs/reference/network.md`

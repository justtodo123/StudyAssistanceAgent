---
title: 路由算法与路由协议
course: network
tags: [RIP, OSPF, BGP, 距离向量, 链路状态]
difficulty: 进阶
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> RIP 是距离向量（贝尔曼-福德，周期整表广播，最大 15 跳），OSPF 是链路状态（Dijkstra，触发更新，分区域），BGP 是 AS 间路径向量协议。

## 核心概念

### 协议对比

| 项目 | RIP | OSPF | BGP |
|---|---|---|---|
| 范围 | IGP | IGP | EGP |
| 度量 | 跳数 | 开销 | 路径属性 |
| 更新 | 30s 周期广播 | 触发洪泛 | 触发增量 |
| 最大跳数 | 15 | 无限制 | 无限制 |
| 算法 | Bellman-Ford | Dijkstra | 路径选择 |
| 传输 | UDP 520 | IP 直封 | TCP 179 |

## 易错点 / 高频考点

- [ ] RIP 最大 15 跳，16 不可达
- [ ] RIP 用 UDP，OSPF 用 IP，BGP 用 TCP
- [ ] OSPF 支持区域划分（area 0 为骨干）

## 经典例题

**题干**：RIP 为何可能出现计数到无穷？
**解答**：周期广播+只看加一跳，坏消息需多轮传播，双方互相学习递增跳数直到 16。

## 关联条目

- [[subnetting]]
- [[network-layer]]
- 参考原始资料索引：`docs/reference/network.md`

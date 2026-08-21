---
title: NAT与IPv6
course: network
tags: [NAT, IPv6, 地址转换, 过渡技术]
difficulty: 中等
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> NAT 把私有地址映射为公有地址，NAPT 用 IP+端口做多对一转换。IPv6 128 位地址从根本上解决地址短缺，过渡技术：双栈/隧道/翻译。

## 核心概念

### NAT

- 静态 NAT：1 对 1 映射
- 动态 NAT：从地址池临时分配
- NAPT：多主机共用一个公有 IP，靠端口号区分

### IPv6

- 128 位地址，冒号十六进制
- 无 NAT、无广播、即插即用
- 过渡：双栈、隧道、翻译

## 易错点 / 高频考点

- [ ] NAPT 转换表记录五元组映射
- [ ] NAT 破坏端到端透明性
- [ ] IPv6 无 NAT，地址足够用

## 经典例题

**题干**：NAT 的主要作用和局限？
**解答**：作用是缓解 IPv4 地址短缺；局限是破坏端到端透明性，外网主动连接内网困难。

## 关联条目

- [[ip-protocol]]
- [[network-layer]]
- 参考原始资料索引：`docs/reference/network.md`

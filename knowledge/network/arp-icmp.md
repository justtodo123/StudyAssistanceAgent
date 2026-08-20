---
title: ARP与ICMP协议
course: network
tags: [ARP, ICMP, MAC地址, ping]
difficulty: 中等
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> ARP 把 IP 解析为 MAC：广播请求、单播应答、结果缓存。ICMP 报告差错与询问，ping 用回送请求，traceroute 用 TTL 超时。

## 核心概念

### ARP

- 同网：广播 ARP 请求，目标单播回复
- 跨网：解析的是网关 IP→网关 MAC
- 缓存有生存期

### ICMP

- 差错报告：目的不可达、超时、参数问题
- 询问：回送请求/应答（ping）
- traceroute：逐跳 TTL+1，路由器回 ICMP 超时

## 易错点 / 高频考点

- [ ] ARP 请求是广播，应答是单播
- [ ] ping 用 ICMP，不是 TCP/UDP
- [ ] ICMP 差错报文不再产生差错报文

## 经典例题

**题干**：A 首次 ping 同网 B，描述报文序列。
**解答**：A 广播 ARP 请求 → B 单播 ARP 应答 → A 发 ICMP 回送请求 → B 回 ICMP 回送应答。

## 关联条目

- [[ip-protocol]]
- [[subnetting]]
- 参考原始资料索引：`docs/reference/network.md`

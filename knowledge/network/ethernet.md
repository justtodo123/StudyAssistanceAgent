---
title: 以太网与VLAN
course: network
tags: [以太网, MAC地址, VLAN, STP]
difficulty: 中等
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> 以太网用 48 位 MAC 地址定位，802.1Q 标签划分 VLAN 隔离广播域，STP 生成树消除环路。

## 核心概念

### MAC 地址（48 位 = 6 字节）

- 前 24 位 OUI（厂商号），后 24 位厂商分配
- 最低位 0 → 单播，1 → 组播，全 1 → 广播

### 以太网帧格式

- DMAC(6B) + SMAC(6B) + Type(2B) + Data(46~1500B) + FCS(4B)
- 最小 64B，数据 < 46B 会填充

### VLAN（802.1Q）

- 在帧中插入 4 字节标签（12 位 VLAN ID，最多 4094）
- 不同 VLAN 需路由器/三层交换互通

## 易错点 / 高频考点

- [ ] MAC 地址 48 位/6 字节
- [ ] 帧长 64~1518B 不含前导码，含 FCS
- [ ] 不同 VLAN 不能二层互通

## 经典例题

**题干**：最小帧 64B 各部分分配？
**解答**：DMAC 6B + SMAC 6B + Type 2B + Data 46B + FCS 4B = 64B。

## 关联条目

- [[csma-cd]]
- [[ip-protocol]]
- 参考原始资料索引：`docs/reference/network.md`

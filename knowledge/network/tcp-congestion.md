---
title: TCP拥塞控制
course: network
tags: [拥塞控制, 慢启动, AIMD, 快重传, 快恢复]
difficulty: 进阶
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> 拥塞控制通过 cwnd 控制发送速率，四阶段：慢启动（指数）→ 拥塞避免（线性）→ 快重传（3 重复 ACK）→ 快恢复。Reno 比 Tahoe 多了快恢复（不从 1 重新开始）。

## 核心概念

### 四阶段

1. **慢启动**：cwnd=1，每 ACK +1（每 RTT 翻倍）
2. **拥塞避免**：每 RTT +1（线性）
3. **快重传**：3 个重复 ACK 立即重传
4. **快恢复**：ssthresh=cwnd/2, cwnd=ssthresh（Reno）

### Tahoe vs Reno

| 版本 | 超时 | 3 重复 ACK |
|---|---|---|
| Tahoe | cwnd=1 慢启动 | cwnd=1 慢启动 |
| Reno | cwnd=1 慢启动 | cwnd=ssthresh 快恢复 |

## 易错点 / 高频考点

- [ ] 慢启动的"慢"指起始窗口小，增长是指数的
- [ ] 超时：cwnd=1；3 重复 ACK：cwnd=ssthresh（Reno）
- [ ] 发送窗口 = min(rwnd, cwnd)

## 经典例题

**题干**：ssthresh=8，从 cwnd=1 开始，第几个 RTT 达到 16？超时后 ssthresh？
**解答**：慢启动 1→2→4→8（3 RTT），拥塞避免 9→16（8 RTT），共 11 RTT。超时后 ssthresh=8。

## 关联条目

- [[tcp-reliable]]
- [[tcp-connection]]
- 参考原始资料索引：`docs/reference/network.md`

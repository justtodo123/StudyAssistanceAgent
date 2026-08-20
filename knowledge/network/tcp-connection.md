---
title: TCP连接管理
course: network
tags: [TCP, 三次握手, 四次挥手, SYN洪泛]
difficulty: 中等
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> TCP 三次握手建立连接（SYN→SYN+ACK→ACK），四次挥手释放（FIN→ACK→FIN→ACK，TIME_WAIT=2MSL）。SYN 洪泛攻击利用半连接队列耗尽资源。

## 核心概念

### 三次握手

1. 客户端 → SYN, seq=x
2. 服务器 → SYN+ACK, seq=y, ack=x+1
3. 客户端 → ACK, seq=x+1, ack=y+1

### 四次挥手

1. A → FIN, seq=u
2. B → ACK, ack=u+1
3. B → FIN, seq=w
4. A → ACK, ack=w+1（进入 TIME_WAIT，等 2MSL）

### 连接状态

- LISTEN → SYN_SENT → ESTABLISHED
- FIN_WAIT_1 → FIN_WAIT_2 → TIME_WAIT → CLOSED

## 易错点 / 高频考点

- [ ] 三次握手第二次的 ack = 对方 seq + 1
- [ ] TIME_WAIT = 2MSL 确保最后 ACK 到达
- [ ] SYN 洪泛：大量 SYN 不完成握手，耗尽半连接队列

## 经典例题

**题干**：为什么是三次握手不是两次？
**解答**：两次无法防止已失效的连接请求到达服务器，导致错误建立连接。

## 关联条目

- [[tcp-reliable]]
- [[tcp-congestion]]
- 参考原始资料索引：`docs/reference/network.md`

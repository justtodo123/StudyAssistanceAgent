---
title: Socket编程基础
course: network
tags: [Socket, TCP编程, UDP编程, 网络编程]
difficulty: 中等
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> Socket = IP:端口，是传输层向应用层的端点抽象。TCP 用流式套接字（socket→bind→listen→accept→recv/send→close），UDP 用数据报套接字（socket→bind→sendto/recvfrom→close）。

## 核心概念

### TCP 编程流程

```
服务器：socket() → bind() → listen() → accept() → recv()/send() → close()
客户端：socket() → connect() → send()/recv() → close()
```

- connect() 触发三次握手，close() 触发四次挥手
- accept() 返回新套接字，原监听套接字继续

### UDP 编程流程

```
socket() → bind() → sendto()/recvfrom() → close()
```

- 无 listen/accept/connect
- sendto 一次调用即完成发送

## 易错点 / 高频考点

- [ ] accept 返回新套接字，原套接字继续监听
- [ ] TCP 无报文边界（字节流），UDP 有（数据报）
- [ ] connect 触发三次握手

## 经典例题

**题干**：accept 返回的套接字与监听套接字的关系？
**解答**：accept 从全连接队列取已完成握手的连接，返回新套接字供本次会话；原套接字继续接受新连接。

## 关联条目

- [[tcp-connection]]
- [[application-layer]]
- 参考原始资料索引：`docs/reference/network.md`

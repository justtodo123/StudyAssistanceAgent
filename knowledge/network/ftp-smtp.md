---
title: FTP与SMTP协议
course: network
tags: [FTP, SMTP, POP3, IMAP, 邮件]
difficulty: 中等
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> FTP 用控制连接(21)+数据连接(20)双连接传输文件。SMTP(25)推式发送邮件，POP3(110)下载并删除，IMAP(143)在线管理。

## 核心概念

### FTP

- 控制连接(21)全程保持，数据连接(20)按需建立
- 主动模式：服务器 20→客户端
- 被动模式：客户端→服务器随机端口

### SMTP

- 推式：HELO→MAIL FROM→RCPT TO→DATA→QUIT
- 只支持 ASCII，非 ASCII 靠 MIME

### POP3 vs IMAP

| 维度 | POP3 | IMAP |
|---|---|---|
| 方式 | 下载并删除 | 在线管理 |
| 多端同步 | 差 | 好 |

## 易错点 / 高频考点

- [ ] FTP 控制连接全程保持，数据连接按需
- [ ] SMTP 只能推不能拉
- [ ] POP3 默认下载并删除

## 经典例题

**题干**：NAT 内网客户端应选 FTP 主动还是被动模式？
**解答**：被动模式。主动模式服务器无法主动连接 NAT 内的客户端。

## 关联条目

- [[application-layer]]
- [[socket]]
- 参考原始资料索引：`docs/reference/network.md`

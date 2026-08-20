---
title: HTTP/HTTPS协议
course: network
tags: [HTTP, HTTPS, 请求响应, 持久连接, SSL]
difficulty: 中等
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> HTTP 请求-响应式协议，状态码 1xx~5xx。HTTP/1.1 默认持久连接。HTTPS 加 SSL/TLS，证书验证+密钥协商+对称加密。HTTP/2 多路复用。

## 核心概念

### 状态码

| 类 | 含义 | 典型 |
|---|---|---|
| 2xx | 成功 | 200 OK |
| 3xx | 重定向 | 301 永久/302 临时 |
| 4xx | 客户端错 | 404 Not Found |
| 5xx | 服务器错 | 500 |

### 连接方式

- HTTP/1.0：非持久（每对象新建连接）
- HTTP/1.1：持久（复用连接）

### HTTPS

- 非对称加密协商会话密钥
- 对称加密传输数据
- CA 证书验证身份

## 易错点 / 高频考点

- [ ] HTTP/1.1 默认持久连接
- [ ] HTTPS = HTTP + SSL/TLS，端口 443
- [ ] 访问 N 个对象：非持久需 N+1 次连接

## 经典例题

**题干**：HTTP/1.0 访问含 4 张图片的页面需几次连接？
**解答**：5 次（每对象 1 次）。HTTP/1.1 持久只需 1 次。

## 关联条目

- [[dns]]
- [[tcp-connection]]
- 参考原始资料索引：`docs/reference/network.md`

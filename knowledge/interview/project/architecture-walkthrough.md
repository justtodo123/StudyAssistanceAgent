---
title: 项目架构如何从请求讲到出处
course: interview
tags: [项目架构, FastAPI, RAG]
difficulty: 中等
updated: 2026-08-18
---

## 面试问题

项目架构如何从请求讲到出处：请求从 FastAPI 路由进入检索服务，BM25 与可选向量存储分别召回，RRF 融合并按文件去重，再交给 QA 服务生成或降级为摘要。响应始终保留来源。

## 回答要点

面试讲解应沿一条真实请求链路展开：输入模型校验、课程过滤、召回、融合、回答、日志和错误降级。每层都有明确职责和测试。

## 项目结合点

M3a 保留 VectorStore 接口和 BM25 fallback，M3b 为 health、search、QA 增加可观察字段，说明架构不是只有 happy path。

## 继续追问

如果把系统扩展到多人并发，首先改哪一层？

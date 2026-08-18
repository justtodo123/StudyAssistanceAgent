---
title: 如何解释项目的可观测性设计
course: interview
tags: [可观测性, 健康检查, 结构化日志]
difficulty: 中等
updated: 2026-08-18
---

## 面试问题

如何解释项目的可观测性设计：health 返回向量引擎、知识库路径、索引大小、缓存状态和平均延迟；search/QA 输出 JSON 日志，记录 event、duration_ms、result_count、mode 和 cache_hit。

## 回答要点

指标必须说明统计口径和敏感信息边界。进程内指标适合个人项目诊断，规模化后可接 Prometheus、集中日志和 trace。

## 项目结合点

M3b 基线记录了 BM25 冷启动 23.897ms、缓存命中 0.060ms，并验证日志不包含 API key、Authorization 或问题正文。

## 继续追问

为什么平均延迟不足以代表线上体验？

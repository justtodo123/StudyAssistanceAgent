---
title: Rerank 与 top-k 选择
course: interview
tags: [Rerank, top-k, 召回]
difficulty: 进阶
updated: 2026-08-18
---

## 面试问题

Rerank 与 top-k 选择：第一阶段召回追求覆盖，第二阶段 rerank 追求精确。可以使用交叉编码器、规则特征或 LLM 对候选进行重排，但会增加延迟和成本。

## 回答要点

top-k 太小会漏掉答案，太大会增加上下文噪声。应通过 Recall@k、Precision@k、答案支持率和延迟联合选择，而不是只看单一指标。

## 项目结合点

当前项目用 BM25/向量候选加 RRF，并通过文件级去重控制结果质量；个人规模暂不引入昂贵 reranker。

## 继续追问

什么时候值得加入 reranker？

---
title: RAG 切块策略与 chunk 边界
course: interview
tags: [Chunking, 切块, 上下文]
difficulty: 中等
updated: 2026-08-18
---

## 面试问题

RAG 切块策略与 chunk 边界：切块过小会丢失上下文，过大会引入噪声并占满上下文窗口。按标题、段落和语义边界切块通常比盲目按字符数更易维护。

## 回答要点

切块应结合文档结构、查询粒度和模型窗口调优。每个 chunk 要保留文件、标题、课程和更新时间等 metadata，便于过滤与引用。

## 项目结合点

知识库索引按 Markdown 的 `##` 标题切块，跳过过短片段，并在结果中携带 file、title、course 和 content。

## 继续追问

如何用评测数据判断 chunk 太大还是太小？

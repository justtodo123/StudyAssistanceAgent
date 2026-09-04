---
title: 数组与链表的取舍
course: interview
tags: [数组, 链表, 缓存局部性]
difficulty: 入门
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/ds/array-linked-list.md
document_id: 8714ef8767e0394d34abc0ca9fd8ba46
provenance: project_authored_ai_assisted
source_type: human_markdown
format: markdown
registration_method: repository_commit
provenance_evidence: docs/reference/document-mapping.json
project_authored: true
publisher: StudyAssistanceAgent project
author: repository contributor
review_status: approved
ingest_status: approved
license_id: MIT
license_status: approved
license_verified_at: 2026-08-31
---

## 面试问题

数组与链表的取舍：数组支持 O(1) 随机访问，连续内存带来良好缓存局部性；链表插入删除在已知节点时可为 O(1)，但随机访问为 O(n) 且有指针开销。

## 回答要点

不能只按渐进复杂度选择。小规模数据和遍历密集场景中数组常更快；频繁中间插入且节点位置可直接获得时链表更合适。

## 项目结合点

检索结果使用列表排序和文件级去重，实际实现更接近连续容器；若频繁淘汰缓存条目，则 OrderedDict 能同时支持哈希定位和顺序维护。

## 继续追问

为什么很多工程代码更偏爱动态数组而不是链表？

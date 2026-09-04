---
title: 时间复杂度与空间复杂度
course: interview
tags: [复杂度, 算法分析, 大 O]
difficulty: 入门
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/ds/complexity-analysis.md
document_id: 8f64faf16ed587c1331377c2d98bc883
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

时间复杂度与空间复杂度：大 O 描述输入规模增大时资源消耗的增长上界趋势，常见有 O(1)、O(log n)、O(n)、O(n log n) 和 O(n²)。空间复杂度要说明是否包含输入本身。

## 回答要点

面试中应先给出主导项，再说明最好、平均、最坏情况和实际常数。复杂度不是运行时间的精确值，还受缓存、语言运行时和数据分布影响。

## 项目结合点

知识库检索既要看索引构建复杂度，也要看查询缓存命中后的常数级开销；基线数据用于补充复杂度无法表达的实际延迟。

## 继续追问

如何分析递归算法的时间复杂度？

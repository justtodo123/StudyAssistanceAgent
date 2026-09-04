---
title: 排序算法与稳定性
course: interview
tags: [排序, 稳定性, 快速排序]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/ds/sorting.md
document_id: b03119d3b07b2256edf22d4e0d27cc96
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

排序算法与稳定性：稳定排序保持相等元素的原始相对次序。归并排序稳定且 O(n log n) 但需要额外空间；快速排序平均 O(n log n)、原地性好但最坏可退化；堆排序最坏 O(n log n) 且通常不稳定。

## 回答要点

回答稳定性时要联系业务：按分数排序后再按原顺序保留同分结果，稳定排序能减少额外 tie-breaker。

## 项目结合点

检索结果按 RRF 分数排序，同时文件级去重要保持得分最高 chunk；稳定排序有助于让同分结果行为可预测。

## 继续追问

如何让快速排序避免最坏情况？

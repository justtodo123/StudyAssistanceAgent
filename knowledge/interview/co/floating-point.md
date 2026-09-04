---
title: IEEE 754 浮点数与舍入
course: interview
tags: [IEEE 754, 浮点数, 舍入]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/co/floating-point.md
document_id: 9ae3fe3b2f4ed34ebaae84fce543031e
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

IEEE 754 浮点数与舍入：IEEE 754 定义符号、指数、尾数以及 NaN、无穷大和非规格化数等特殊值。有限精度运算可能产生舍入误差，误差会在多次运算中积累。

## 回答要点

工程中应根据误差容忍度选比较方式：绝对误差、相对误差或十进制定点表示。序列化时也要明确单位和精度。

## 项目结合点

健康检查把平均延迟四舍五入到 3 位小数，文档同时说明这是诊断指标而非精密计量结果。

## 继续追问

NaN 为什么不等于自身？

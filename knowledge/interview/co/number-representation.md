---
title: 定点数、浮点数与补码
course: interview
tags: [补码, 浮点数, 数据表示]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/co/number-representation.md
document_id: 9fddcf05139151fae760235bcef6ce84
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

定点数、浮点数与补码：补码用最高位表达符号并让加减统一为二进制加法；浮点数用符号位、指数和尾数表示范围更大的数，但存在舍入误差和非精确表示。

## 回答要点

要说明溢出、精度和范围是不同问题。补码溢出发生在结果超出位宽，浮点误差则常来自有限尾数和舍入。

## 项目结合点

评测延迟用毫秒浮点数记录时，应明确舍入位数和测量误差，不能把显示精度当成真实精度。

## 继续追问

为什么浮点数比较不能简单使用 ==？

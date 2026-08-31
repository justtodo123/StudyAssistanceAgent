---
title: 分支预测与推测执行
course: interview
tags: [分支预测, 推测执行, CPU]
difficulty: 进阶
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/co/branch-prediction.md
document_id: 10e7d8934c4afeb79a3f6af223ef48e2
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

分支预测与推测执行：处理器预测条件分支的方向和目标，提前取指执行；预测错误时丢弃错误路径的架构结果并恢复正确路径。预测器利用历史行为和局部性提高命中率。

## 回答要点

推测执行提升吞吐，但需要严格隔离架构状态和处理侧信道风险。面试回答要区分性能正确性与安全边界。

## 项目结合点

检索系统可以预热常见课程索引，但预热属于性能优化，不能改变答案的正确性或掩盖缓存失效问题。

## 继续追问

Spectre 类问题与分支预测的关系是什么？

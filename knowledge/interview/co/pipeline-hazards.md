---
title: 流水线与数据、控制冒险
course: interview
tags: [流水线, 冒险, CPU]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/co/pipeline-hazards.md
document_id: 495d8e7437d913ef27799ec82c833ddc
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

流水线与数据、控制冒险：流水线把取指、译码、执行、访存和写回等阶段重叠，提高吞吐。数据冒险来自指令依赖，控制冒险来自分支，结构冒险来自硬件资源冲突。

## 回答要点

解决方式包括旁路、停顿、寄存器重命名、分支预测和乱序执行。流水线提高吞吐但不一定降低单条指令延迟。

## 项目结合点

FastAPI 请求流水线也可分为校验、检索、生成和序列化阶段；阶段间串行瓶颈会直接影响端到端延迟。

## 继续追问

为什么分支预测失败会清空流水线？

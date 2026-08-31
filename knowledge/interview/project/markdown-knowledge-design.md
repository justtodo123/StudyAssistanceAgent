---
title: 为什么用 Markdown 作为知识库
course: interview
tags: [Markdown, 知识库, 数据建模]
difficulty: 入门
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/project/markdown-knowledge-design.md
document_id: 7941c80d9cf99c0ab494978dd9043b85
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

为什么用 Markdown 作为知识库：Markdown 可读、可 diff、可版本化，适合个人知识资产。frontmatter 提供课程、标签、难度和更新时间，正文保持对人友好的结构。

## 回答要点

代价是查询能力和并发写入能力不如数据库，需要索引缓存和严格导航。对个人规模而言，低运维和可迁移性更重要。

## 项目结合点

知识库条目不复制外部 PDF/PPT，而是保存精炼内容与参考索引；索引服务按标题切块并生成稳定 chunk ID。

## 继续追问

什么时候应该迁移到数据库或对象存储？

---
title: 分页与分段的区别
course: interview
tags: [分页, 分段, 地址转换]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/paging-segmentation.md
document_id: be25e486d0e59a9ebbe36c83a9db0ae8
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

分页与分段的区别：分页按固定大小划分物理和虚拟空间，便于分配和消除外部碎片；分段按逻辑模块划分，便于表达代码、数据和栈的保护边界，但容易产生外部碎片。

## 回答要点

现代系统通常以分页为主，同时通过页权限和映射区域表达部分逻辑隔离。回答要从分配粒度、碎片类型、共享与保护三个角度比较。

## 项目结合点

Markdown 条目按语义标题切成 chunk，和固定大小切块类似；按标题切块则更接近按逻辑段组织内容。

## 继续追问

段页式管理如何结合两者优点？

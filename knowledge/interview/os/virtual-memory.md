---
title: 虚拟内存与页表
course: interview
tags: [虚拟内存, 页表, 缺页]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/os/virtual-memory.md
document_id: 4c680d7c3f4b1431a82cec65a1538007
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

虚拟内存与页表：虚拟内存把进程看到的虚拟地址映射到物理页框，通过页表记录映射和权限。访问不在内存中的页会触发缺页异常，由操作系统调入页面。

## 回答要点

虚拟内存提供隔离、按需分配和超卖能力，但页表遍历和缺页都会增加成本。TLB 用来缓存近期地址转换，减少重复页表访问。

## 项目结合点

知识库索引把磁盘 Markdown 转为内存对象，也体现了按需加载与缓存的取舍；索引缓存失效后才重新扫描文件。

## 继续追问

多级页表解决了什么问题？大页有什么收益和代价？

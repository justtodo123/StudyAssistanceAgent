# 知识条目模板

> 复制本模板到 `knowledge/{course}/{topic}.md`，填写 frontmatter 与正文后删除本说明注释。

```yaml
---
title: 这里写条目标题（如「分页与分段」）
course: 课程简称
tags: [核心主题, 子主题]
difficulty: 中等
updated: 2026-08-31
source_id: knowledge-pack
logical_uri: 课程简称/topic.md
document_id: 按 source_id + logical_uri 计算的稳定 ID
provenance: project_authored_ai_assisted
project_authored: true
canonical_url:  # 非项目原创时填写可核验原始 URL，并把 project_authored 改为 false
publisher: StudyAssistanceAgent project
author: repository contributor
source_type: human_markdown
format: markdown
review_status: review
ingest_status: candidate
registration_method: repository_commit
license_id: MIT
license_status: unresolved
license_verified_at:
provenance_evidence: docs/reference/document-mapping.json
---
```

## 一句话概括（TL;DR）

> 用 2-3 句话概括本条目核心内容，供快速浏览与检索。

## 核心概念

### 小节标题（概念：定义 / 特点 / 结构）

- 要点 1
- 要点 2

## 关键原理 / 算法

说明原理，配合要点列表或代码块：

```python
# 示例代码
```

## 易错点 / 高频考点

- [ ] 考点 1（简要说明）
- [ ] 考点 2

## 经典例题

### 例题 1
**题干**：…
**解答**：…

## 关联条目

- [[同课程其他条目]]
- 文档级来源登记：`docs/reference/document-mapping.json`
- 课程级原始资料索引：`docs/reference/{course}.md`

> 新条目先以 `review_status: review`、`ingest_status: candidate` 和 `license_status: unresolved`
> 登记；只有来源/原创声明、许可证和人工审核全部闭合后，才能同时改为 approved。

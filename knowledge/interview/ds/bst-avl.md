---
title: 二叉搜索树与 AVL 平衡
course: interview
tags: [二叉搜索树, AVL, 平衡树]
difficulty: 中等
updated: 2026-08-18
source_id: knowledge-pack
logical_uri: interview/ds/bst-avl.md
document_id: ae4d74c63449b254deffe0c3b233d9ab
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

二叉搜索树与 AVL 平衡：二叉搜索树要求左子树键小于根、右子树键大于根；插入顺序不佳时会退化为链表。AVL 通过旋转保持高度差不超过 1，使查找、插入、删除保持 O(log n)。

## 回答要点

面试要区分树的顺序性质和高度保证。红黑树平衡条件更弱但更新旋转较少，工程库常使用红黑树或 B 树族。

## 项目结合点

文件级检索结果需要按分数排序，若要支持动态范围查询，可考虑平衡树而不是每次完整排序。

## 继续追问

AVL 的 LL、RR、LR、RL 旋转分别如何处理？

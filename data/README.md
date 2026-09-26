# data/ — M11 数据分层边界

> 状态：**M11 v1.1 数据目录约定**。本目录说明 raw / normalized / candidate / approved 的分层与 Git 边界。
> M11 当前为 `ADMITTED / IN_PROGRESS`，A3 已允许冻结 P0 白名单的下载与入库；每次真实外部下载和正式发布仍需单独确认。
>
> 政策权威：[`docs/plans/references/m11-decision-closure-v1.md`](../docs/plans/references/m11-decision-closure-v1.md)
> 的 `M11-PRIVACY-RETENTION` 与 [`docs/plans/data-expansion-runbook.md`](../docs/plans/data-expansion-runbook.md)
> （后者为非权威参考）。

## 1. 允许出现在 Git 里的内容

- 本文件 `data/README.md`
- `data/manifests/`（Source / license 元数据、审核结果、digest；不含正文）

## 2. 禁止进入 Git 的层

`.gitignore` 已忽略：

```text
data/raw/            # 原始下载；只读
data/normalized/     # 统一编码后的文档
data/candidates/     # 待审核 Markdown
data/approved/       # 审核通过的数据（大文件）
data/rejected/       # 拒绝记录；只保存原因和身份，不复制违规正文
data/reports/        # 质量 / 许可 / 去重报告（可含计数与 digest，不含正文）
data/snapshots/      # 发布快照清单，不重复保存原始文件
```

这些目录只可由获批的 M11 可重放流水线创建和填充；真实下载前必须先完成 manifest、许可/revision 核验并取得单次确认。
2026-09-26 owner 已确认冻结 26 项真实获取；可提交 receipts 位于 `data/manifests/`，正文仍不入库，不构成 publication。

## 3. 隐私与路径

- 报告、manifest、日志不得含宿主绝对路径、凭据或私人学习状态。
- 私人会话、复习、plan、Runner ledger **不是** M11 语料。
- 外部原始课程资料仍保留在仓库外的只读资料根（治理文档只描述该根，不粘贴绝对路径）。
- `rejected/` 若将来落地，只写原因码与身份，不复制违规正文。

## 4. 本文件不做什么

- 不创建上述被忽略目录。
- 不登记任何 Source revision。
- 不把 Network candidate 或未审 dump 算进 Gate。
- 不把 `SA_SOURCE_MAX_CHUNKS_TOTAL` 提高到 v1.1 已批准的 4000 之外；默认值保持 1200。

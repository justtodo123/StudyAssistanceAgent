# M11 P0 Gate 0 metadata-only review checklist v1

> 本文件位于 `plans/references/`，不是阶段权威、Gate 记录或授权记录。
> 阶段状态以 [`docs/PLAN.md`](../../PLAN.md) 为准；正式准入政策以 `docs/standards/` 为准。

## 使用边界

本清单只复核仓库内冻结的 M11 P0 元数据、review manifest 和 normalization report。
它不执行 Gate 0，不执行正式 3K workload，也不产生新的阶段状态、批准、晋升或发布授权。

- `verified` 只表示元数据断言已被离线机械核验，不表示来源、文档、chunk 或 Gate 获得批准。
- `pending` 表示所需证据或人工复核尚未完成。
- `blocked` 表示该动作超出当前授权，或证据不足以安全执行。
- 本清单不读取或保存来源正文、凭据、私密学习状态或宿主机路径。
- 本清单准备过程不下载、不抓取、不解析、不 embedding、不建索引、不发布，也不改变
  `CANDIDATE` / `REJECTED` 状态。

## 当前摘要

| 项目 | 值 |
| --- | --- |
| 清单结果 | `REVIEW_REQUIRED` |
| 冻结范围 | `frozen M11 P0 candidate assets only` |
| asset records | 887 |
| candidate records | 884 |
| rejected records | 3 |
| approved assets/documents/chunks | 0 / 0 / 0 |
| published records | 0 |
| formal 3K run | 未执行 |
| publication | 未授权 |

## 逐项清单

| ID | 状态 | 断言 |
| --- | --- | --- |
| `stage-authority` | `verified` | M11 为 `ADMITTED / IN_PROGRESS`，开工授权仍由正式权威文件承载。 |
| `candidate-scope` | `verified` | candidate pipeline 只覆盖冻结的 P0 范围。 |
| `inventory-counts` | `verified` | review manifest 为 887 条记录，其中 884 条 candidate、3 条 rejected。 |
| `report-reconciliation` | `verified` | report 与 review manifest 的计数、拒绝原因和隐私布尔值一致。 |
| `rejected-mapping` | `verified` | 三条 rejected 记录的稳定 identity 与 rejection reason 已精确对应。 |
| `digest-evidence` | `verified` | 26 项 direct digest 与 pinned OpenDSA path metadata 可离线复核。 |
| `privacy-boundary` | `verified` | review metadata 不含正文、凭据、私密学习状态或宿主机路径。 |
| `candidate-only` | `verified` | candidate 与 rejected 状态保持不变，approved/published 计数均为零。 |
| `deterministic-review` | `verified` | 计数与 identity reconciliation 可在无网络条件下确定性复跑。 |
| `asset-license-review` | `pending` | 逐 asset license review 尚未完成，相关来源保持 `review_required`。 |
| `robots-review` | `pending` | 适用来源的 robots review 尚未全部完成。 |
| `rfc-notice-ipr-review` | `pending` | RFC notice/IPR review 尚未完成。 |
| `iana-schema-review` | `pending` | IANA schema review 尚未完成。 |
| `human-gate-review` | `pending` | reviewer、签署时间、sample 和 gold-document 等人工字段尚未完成。 |
| `formal-3k-run` | `blocked` | 当前授权不包含正式 3K Gate 执行。 |
| `candidate-promotion` | `blocked` | candidate-to-approved 晋升需要单独授权，当前不得执行。 |
| `publication` | `blocked` | publication authorization 为 false，当前不得发布。 |
| `source-expansion` | `blocked` | 冻结 P0 之外的来源扩展需要单独授权。 |
| `network-acquisition` | `blocked` | 本清单是 offline metadata-only review，不触发新的网络获取。 |

## 机器可读 contract

下面的 fenced JSON 是本清单唯一的机器可读 contract。它是非授权声明，不是第二个阶段权威来源。

```json
{
  "schema": "sa.m11.p0.metadata-only-gate0-checklist.v1",
  "checklist_kind": "METADATA_ONLY",
  "result": "REVIEW_REQUIRED",
  "scope": "frozen M11 P0 candidate assets only",
  "formal_gate0_executed": false,
  "formal_3k_executed": false,
  "candidate_approval_granted": false,
  "publication_authorized": false,
  "network_used": false,
  "source_expansion": false,
  "lifecycle_mutation": false,
  "host_paths_included": false,
  "bodies_included": false,
  "counts": {
    "asset_count": 887,
    "candidate_count": 884,
    "rejected_count": 3,
    "approved_asset_count": 0,
    "approved_document_count": 0,
    "approved_chunk_count": 0,
    "published_count": 0
  },
  "statuses": [
    {"id": "stage-authority", "status": "verified"},
    {"id": "candidate-scope", "status": "verified"},
    {"id": "inventory-counts", "status": "verified"},
    {"id": "report-reconciliation", "status": "verified"},
    {"id": "rejected-mapping", "status": "verified"},
    {"id": "digest-evidence", "status": "verified"},
    {"id": "privacy-boundary", "status": "verified"},
    {"id": "candidate-only", "status": "verified"},
    {"id": "deterministic-review", "status": "verified"},
    {"id": "asset-license-review", "status": "pending"},
    {"id": "robots-review", "status": "pending"},
    {"id": "rfc-notice-ipr-review", "status": "pending"},
    {"id": "iana-schema-review", "status": "pending"},
    {"id": "human-gate-review", "status": "pending"},
    {"id": "formal-3k-run", "status": "blocked"},
    {"id": "candidate-promotion", "status": "blocked"},
    {"id": "publication", "status": "blocked"},
    {"id": "source-expansion", "status": "blocked"},
    {"id": "network-acquisition", "status": "blocked"}
  ]
}
```

离线校验入口：`tools/validate_m11_p0_metadata_gate0.py`。通过该校验只表示本地
metadata contract 与冻结报告一致，不表示 Gate 0 已执行或通过。

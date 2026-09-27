# M11 P0 26-asset human-review batch checklist v1

> 本文件位于 `plans/references/`，不是阶段权威、Gate 记录或批准记录。
> 阶段状态以 [`docs/PLAN.md`](../../PLAN.md) 为准；正式准入政策以 `docs/standards/` 为准。
> 可执行 authority 以 [`data/manifests/m11-p0-human-review-26-authority-v1.json`](../../../data/manifests/m11-p0-human-review-26-authority-v1.json) 为准。

## 使用边界

本清单只列出 26 项 digest-captured 资产的人工核验工作单。授权批次不等于完成 review。完整 26 项
决策记录已写入且全部为 `DEFER`：RFC+IANA 6 项见
[`data/manifests/m11-p0-human-review-rfc-iana-6-v1.json`](../../../data/manifests/m11-p0-human-review-rfc-iana-6-v1.json)，
MIT OCW 20 项见
[`data/manifests/m11-p0-human-review-mit-ocw-20-v1.json`](../../../data/manifests/m11-p0-human-review-mit-ocw-20-v1.json)。
获取后再核验切片见
[`data/manifests/m11-p0-human-review-acq-defer-26-v1.json`](../../../data/manifests/m11-p0-human-review-acq-defer-26-v1.json)，
仍全部为 `DEFER` 并 `supersedes` 历史记录。
`DEFER` 不关闭 license、robots、notice/IPR、schema 或内容核验，也不执行 Formal Gate 0。
新增的 metadata-only evidence closure matrix 见
[`data/manifests/m11-p0-evidence-closure-26-v1.json`](../../../data/manifests/m11-p0-evidence-closure-26-v1.json)，
其 superseding closure slice 见
[`data/manifests/m11-p0-human-review-closure-defer-26-v1.json`](../../../data/manifests/m11-p0-human-review-closure-defer-26-v1.json)。
两者仅记录八类证据的未闭合状态，仍为 `REVIEW_REQUIRED`，不构成 Formal Gate 0 输入。

官方来源只读观察层见 [`data/manifests/m11-p0-official-source-observations-26-v1.json`](../../../data/manifests/m11-p0-official-source-observations-26-v1.json)，观察后的 successor review slice 见 [`data/manifests/m11-p0-human-review-official-observation-defer-26-v1.json`](../../../data/manifests/m11-p0-human-review-official-observation-defer-26-v1.json)。该层只记录 source-level metadata facts；MIT third-party-rights limitation 与 IANA XML 日期冲突保持未解决，不能关闭八类 evidence，也不改变 closure matrix 的全 `PENDING` 状态。

- `verified` 只表示该批次的 HUMAN_REVIEW authority 已按冻结 digest 身份绑定，不表示许可、robots 或内容已通过。
- `pending` 表示对应核验字段尚未由 owner 填写。
- `blocked` 表示该动作超出本批次授权。
- 已处于 `REJECTED` 的 MIT OCW 资产仍在本批次内，必须核验，不得因为当前 normalization 失败而从名单中删除。
- OpenDSA 861 条路径不在本批次。
- 本清单不读取或保存来源正文、凭据、私密学习状态或宿主机路径。
- 本清单不执行 Formal Gate 0、不晋升 candidate、不发布、不扩张来源、不发起新的网络获取。
- 独立 `acquisition` authority 与 ACQUIRED receipts 不改变本 HUMAN_REVIEW 清单的
  `network_used=false` / `network-acquisition=blocked`。

## 当前摘要

| 项目 | 值 |
| --- | --- |
| 清单结果 | `REVIEW_REQUIRED` |
| 冻结范围 | `digest-captured MIT OCW 20 + RFC 3 + IANA 3` |
| authority | `m11-human-review-26-20260926` |
| 资产数 | 26 |
| 含已 REJECTED 的 MIT OCW 资产 | `digital_answers`、`information_worksheet` |
| OpenDSA | 不在本批次 |
| approved assets/documents/chunks | 0 / 0 / 0 |
| Formal Gate 0 | 未授权、未执行 |
| publication | 未授权 |
| RFC+IANA 切片 | 6 项已 `DEFER` |
| MIT OCW 切片 | 20 项已 `DEFER`（含两份已 REJECTED 的 PDF） |
| 获取后再核验切片 | 26 项仍 `DEFER`，supersedes 历史切片 |
| 官方观察 successor 切片 | 26 项仍 `DEFER`，逐条 supersedes closure 切片；观察不闭合 evidence |
| 26 项决策 | 已写完，全部 `DEFER`；不通过 Formal Gate 0 |

## 核验工作单

| ID | 状态 | 断言 |
| --- | --- | --- |
| `human-review-authority` | `verified` | 26 资产 HUMAN_REVIEW authority 已绑定 digest 身份，`publication_authorized` 为 false。 |
| `scope-26-digest-assets` | `verified` | 范围恰好是 MIT OCW 20 PDF、RFC 9110/9293/1034、IANA CSV/XML/TXT。 |
| `rejected-ocw-still-in-batch` | `verified` | `digital_answers` 与 `information_worksheet` 仍在名单内。 |
| `opendsa-excluded` | `verified` | OpenDSA 不在 `source_ids` / `asset_ids`。 |
| `asset-license-review` | `pending` | 26 项 license review 尚未完成。 |
| `revision-review` | `pending` | 26 项 revision/provenance review 尚未完成。 |
| `robots-review` | `pending` | 适用来源的 robots review 尚未完成。 |
| `rfc-notice-ipr-review` | `pending` | RFC 3 项 notice/IPR review 尚未完成。 |
| `iana-schema-review` | `pending` | IANA 3 项 schema review 尚未完成。 |
| `content-quality-review` | `pending` | 26 项内容核验尚未完成。 |
| `rfc-iana-slice` | `verified` | RFC 3 + IANA 3 已写入 `DEFER` 记录；无 candidate 文档/chunks，无 ACQUIRED receipt。 |
| `mit-ocw-slice` | `verified` | MIT OCW 20 已写入 `DEFER` 记录；无 committed candidate 文档/chunks，无 ACQUIRED receipt；两份已 REJECTED 的 PDF 仍在切片内。 |
| `acq-defer-slice` | `verified` | 26 项获取后再核验仍为 `DEFER` 并 supersedes 历史记录；不关闭 pending 核验，不通过 Formal Gate 0。 |
| `official-observation-slice` | `verified` | 26 项官方观察 successor 仍为 `DEFER` 并 supersedes closure 记录；source-level observation 不关闭 evidence。 |
| `review-records` | `verified` | 完整 26 项决策记录已写完且全部为 `DEFER`；不关闭 pending 核验字段，不通过 Formal Gate 0。 |
| `formal-gate0` | `blocked` | 本批次不授权 Formal Gate 0 执行。 |
| `candidate-promotion` | `blocked` | 本批次不授权 candidate→approved 晋升。 |
| `publication` | `blocked` | 本批次不授权 publication。 |
| `source-expansion` | `blocked` | 本批次不扩张 OpenDSA、Network、Linux docs 或 SE dump。 |
| `network-acquisition` | `blocked` | 本批次不授权新的网络获取。 |

## 机器可读 contract

下面的 fenced JSON 是本清单唯一的机器可读 contract。它是非授权工作单，不能替代 execution authority，
也不能把 pending 核验升为通过。

```json
{
  "schema": "sa.m11.p0.human-review-26-checklist.v1",
  "checklist_kind": "HUMAN_REVIEW_BATCH",
  "result": "REVIEW_REQUIRED",
  "scope": "digest-captured MIT OCW 20 + RFC 3 + IANA 3",
  "authority_id": "m11-human-review-26-20260926",
  "authority_record": "data/manifests/m11-p0-human-review-26-authority-v1.json",
  "asset_count": 26,
  "source_ids": [
    "rfc-editor-index",
    "iana-registries",
    "mit-ocw-6-004-2017"
  ],
  "includes_rejected_ocw_assets": true,
  "opendsa_included": false,
  "review_records_written": true,
  "rfc_iana_slice_written": true,
  "rfc_iana_slice_asset_count": 6,
  "rfc_iana_slice_decision": "DEFER",
  "rfc_iana_slice_record": "data/manifests/m11-p0-human-review-rfc-iana-6-v1.json",
  "mit_ocw_slice_written": true,
  "mit_ocw_slice_asset_count": 20,
  "mit_ocw_slice_decision": "DEFER",
  "mit_ocw_slice_record": "data/manifests/m11-p0-human-review-mit-ocw-20-v1.json",
  "acq_defer_slice_written": true,
  "acq_defer_slice_asset_count": 26,
  "acq_defer_slice_decision": "DEFER",
  "acq_defer_slice_record": "data/manifests/m11-p0-human-review-acq-defer-26-v1.json",
  "acquisition_authority_id": "m11-acquisition-26-20260926",
  "acquisition_receipts_written": true,
  "acquisition_receipt_count": 26,
  "acquisition_receipts_record": "data/manifests/m11-p0-acquisition-26-receipts-v1.json",
  "official_observation_slice_written": true,
  "official_observation_slice_asset_count": 26,
  "official_observation_slice_decision": "DEFER",
  "official_observation_slice_record": "data/manifests/m11-p0-human-review-official-observation-defer-26-v1.json",
  "official_observation_record": "data/manifests/m11-p0-official-source-observations-26-v1.json",
  "official_observation_closes_evidence": false,
  "official_observation_unresolved_findings": [
    "SOURCE_POLICY_LIMITATION",
    "SCHEMA_METADATA_CONFLICT"
  ],
  "formal_gate0_executed": false,
  "formal_3k_executed": false,
  "candidate_approval_granted": false,
  "publication_authorized": false,
  "network_used": false,
  "source_expansion": false,
  "lifecycle_mutation": false,
  "host_paths_included": false,
  "bodies_included": false,
  "statuses": [
    {"id": "human-review-authority", "status": "verified"},
    {"id": "scope-26-digest-assets", "status": "verified"},
    {"id": "rejected-ocw-still-in-batch", "status": "verified"},
    {"id": "opendsa-excluded", "status": "verified"},
    {"id": "asset-license-review", "status": "pending"},
    {"id": "revision-review", "status": "pending"},
    {"id": "robots-review", "status": "pending"},
    {"id": "rfc-notice-ipr-review", "status": "pending"},
    {"id": "iana-schema-review", "status": "pending"},
    {"id": "content-quality-review", "status": "pending"},
    {"id": "rfc-iana-slice", "status": "verified"},
    {"id": "mit-ocw-slice", "status": "verified"},
    {"id": "acq-defer-slice", "status": "verified"},
    {"id": "official-observation-slice", "status": "verified"},
    {"id": "review-records", "status": "verified"},
    {"id": "formal-gate0", "status": "blocked"},
    {"id": "candidate-promotion", "status": "blocked"},
    {"id": "publication", "status": "blocked"},
    {"id": "source-expansion", "status": "blocked"},
    {"id": "network-acquisition", "status": "blocked"}
  ]
}
```

通过本清单只表示 26 资产人工核验批次已被授权且范围冻结。它不表示任何 asset 已通过 review，
不表示 Formal Gate 0 已执行或通过，也不表示 publication readiness。

# M11 P0 evidence-gap checklist v1

> 本文件是基于冻结 metadata 的非权威 evidence-gap 投影，不是阶段权威、Gate 记录或授权记录。
> 阶段状态以 [`docs/PLAN.md`](../../PLAN.md) 为准；正式准入政策以 `docs/standards/` 为准。

## 使用边界

本清单只读取仓库内冻结的 candidate manifest、asset review manifest 和 normalization report，按来源与证据类别
列出仍需处理的 metadata gap。它不执行 Gate 0，不执行正式 3K workload，也不产生批准、晋升、发布或来源扩展授权。

- `verified` 只表示 gap projection 与冻结 metadata 一致，不表示对应来源、资产、文档或 chunk 已通过 review。
- `pending` 表示所需证据或人工复核尚未完成；`blocked` 表示当前动作超出授权。
- `pinned`、`digest-captured`、`scope-confirmed` 和 `metadata-only` 只保留其字面事实，不能被解释为批准。
- 本清单不读取或保存来源正文、凭据、私密学习状态、宿主机路径或 runtime 输出路径。
- 本清单不下载、抓取、解析、embedding、建索引、发布，也不改变 `CANDIDATE` / `REJECTED` 状态。

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
| owner decisions | 未填写 |

## 来源限定的 gap

| 来源 | records | 主要未闭合证据 |
| --- | ---: | --- |
| MIT OCW 6-004 | 20 | license、revision、robots、provenance、content quality |
| OpenDSA | 861 | license、revision/provenance、robots/notice、content quality；861 条路径范围保持显式冻结 |
| RFC Editor | 3 | license、revision/provenance、robots、notice/IPR |
| IANA registries | 3 | license、revision/provenance、robots、schema、content quality |

IANA 已记录的 `scope-confirmed` 与 `digest-captured` 仅是局部 metadata 事实；OpenDSA 的 `pinned` 也仅是
revision 绑定事实。它们不会关闭剩余 review gap。

## Owner / Gate 待处理事项

以下事项保持未填写，不代表预先批准：asset-level license、revision/provenance、robots、RFC notice/IPR、IANA
schema，以及未来正式 Gate 0 所需 reviewer、sign-off、sample、gold-document 和 query evidence。

正式 Gate 0/3K 执行、candidate promotion、publication、source expansion 和新的 network acquisition 在当前
授权下均保持 blocked。

## 机器可读 contract

下面的 fenced JSON 是本清单唯一的机器可读 contract。它只声明冻结 metadata 的 evidence-gap 投影，不是第二个
阶段权威来源，也不是 owner decision。

```json
{
  "schema": "sa.m11.p0.evidence-gap-checklist.v1",
  "checklist_kind": "METADATA_ONLY_EVIDENCE_GAPS",
  "result": "REVIEW_REQUIRED",
  "scope": "frozen M11 P0 candidate assets only",
  "source_references": {
    "candidate_manifest": "data/manifests/sources/m11-p0-candidate-assets-v1.json",
    "review_manifest": "data/manifests/m11-p0-asset-review-v1.json",
    "normalization_report": "data/reports/m11-p0-candidate-normalization-report.json"
  },
  "formal_gate0_executed": false,
  "formal_3k_executed": false,
  "candidate_approval_granted": false,
  "publication_authorized": false,
  "network_used": false,
  "source_expansion": false,
  "lifecycle_mutation": false,
  "host_paths_included": false,
  "bodies_included": false,
  "owner_decisions_filled": false,
  "counts": {
    "asset_count": 887,
    "candidate_count": 884,
    "rejected_count": 3,
    "approved_asset_count": 0,
    "approved_document_count": 0,
    "approved_chunk_count": 0,
    "published_count": 0
  },
  "gap_categories": [
    {"id": "license", "status": "pending", "count": 887},
    {"id": "revision", "status": "pending", "count": 887},
    {"id": "robots", "status": "pending", "count": 887},
    {"id": "notice_or_ipr", "status": "pending", "count": 864},
    {"id": "schema", "status": "pending", "count": 3},
    {"id": "provenance", "status": "pending", "count": 887},
    {"id": "content_quality", "status": "pending", "count": 887}
  ],
  "source_gaps": [
    {"source_id": "iana-registries", "asset_count": 3, "gaps": {"license": 3, "revision": 3, "robots": 3, "schema": 3, "provenance": 3, "content_quality": 3}, "status": "pending"},
    {"source_id": "mit-ocw-6-004-2017", "asset_count": 20, "gaps": {"license": 20, "revision": 20, "robots": 20, "provenance": 20, "content_quality": 20}, "status": "pending"},
    {"source_id": "opendsa-main", "asset_count": 861, "gaps": {"license": 861, "revision": 861, "robots": 861, "notice_or_ipr": 861, "provenance": 861, "content_quality": 861}, "status": "pending"},
    {"source_id": "rfc-editor-index", "asset_count": 3, "gaps": {"license": 3, "revision": 3, "robots": 3, "notice_or_ipr": 3, "provenance": 3, "content_quality": 3}, "status": "pending"}
  ],
  "blocked_actions": [
    {"id": "formal-gate0", "status": "blocked"},
    {"id": "formal-3k-run", "status": "blocked"},
    {"id": "candidate-promotion", "status": "blocked"},
    {"id": "publication", "status": "blocked"},
    {"id": "source-expansion", "status": "blocked"},
    {"id": "network-acquisition", "status": "blocked"}
  ]
}
```

离线校验入口：`tools/validate_m11_p0_evidence_gaps.py`。通过校验只表示 evidence-gap 投影与冻结 metadata
一致，不表示 Gate 0 已执行或通过，不表示资产批准，也不表示 publication readiness。

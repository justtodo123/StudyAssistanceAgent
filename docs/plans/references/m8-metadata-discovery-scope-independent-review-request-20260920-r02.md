# M8 Metadata-Discovery Scope — Independent Review Request (pypdf==6.0.0)

本文件是一份**非授权**的独立审查请求指路文档。它只把已冻结的 selected-scope 六阶段 pre-review
publication 链交给一个真正隔离、身份可验证的 Reviewer；本文件本身不是独立审查、不预置结论、不产生
approval，也不授权任何 metadata discovery 或 acquisition。

- 当前状态：`READY_FOR_EXTERNAL_INDEPENDENT_REVIEW`
- `m8_status`：`BLOCKED / NOT_STARTED`
- `dependency_scope`：`["pypdf"]`（`pypdf==6.0.0`）
- cycle ID：`m8-metadata-discovery-scope-pypdf-6.0.0-20260920-r02`

## 审查根（dispatch publication）

- 完整 commit OID：`98ca8c709a3c60f0bcb9e107e1b77720c3c03393`
- 固定 path：`m8/metadata-discovery/dispatch-manifest.json`

审查者应只以该 dispatch commit 为根，沿其 content-addressed references 反向重算整条链（candidate →
self-check → request → prompt → target → dispatch），不依赖 HEAD、branch/tag、worktree 或任何调用方替换的
records。复验命令：

```bash
python tools/m8_validate_metadata_discovery_scope_review.py \
  --dispatch-commit 98ca8c709a3c60f0bcb9e107e1b77720c3c03393 \
  --repo <absolute-repository-path> \
  --output <temporary-dispatch-validation-report.json>
```

## 六阶段 content-addressed 摘要

| 阶段 | commit | git_blob_oid | byte_count | sha256 |
| --- | --- | --- | --- | --- |
| candidate_publication | `110fe8a3bfe046f06a3cb55b123808c8f398b9fe` | `acd6ad8d0aa65e4640c91af5ce82c9bae8e6e875` | 5908 | `3149102117ddaf90d7366cf4bcfbae7b88c6c6138fb3ec49e92bc4910e728a3e` |
| builder_self_check | `75ebfd3b281117de108ba91d313322743901726b` | `fc3723acf02cb9d5e55b2a6bdbaaa27f02fea6e1` | 1593 | `c05b0651c5fd5b105a06d9a5f1b72741a8cfa5b216f9b698f7fb6da214db0cba` |
| review_request | `0a66bb00ee837f2821c5408f14e4e06461268e95` | `951bf2b7b7febd6eb80598051ac2c76164b00bfe` | 2076 | `019f68ce2b13ae41de3a8f29e65e95b8d3c7317024ded8cb508d2216edf33be7` |
| review_prompt | `6fbc2cea52462c52fd113015dba538d73019c044` | `e640c2698b317313b5f17a11d723ed53c65a0954` | 2355 | `9d48375a00171bf2b4f99ea7b4c420491a34046cd11328c3b5d07ce6b38ce79a` |
| review_target | `ab34fd3df441dcfabe47df20564215e6b0eb3a74` | `45870c895ecfc69a138094698c0498beeda1385d` | 2845 | `67e6f73f25e151da88994d135c656095722148249697a2884a6d66c2eac85a62` |
| dispatch_manifest | `98ca8c709a3c60f0bcb9e107e1b77720c3c03393` | `1b6c5f842932c043c03ee712a490c9c3d0ea62e2` | 3286 | `fccf7cc60170784e07b8f396e8516c14d11aeab0fca3cd1f323503db6a15a387` |

## 冻结审查协议

- protocol ID：`m8-metadata-discovery-scope-review-protocol-v1`
- protocol SHA-256：`17303ab5e778d490b70ff2c28bca8e8e27b13e9f099e9b69e71f2ed6f8a6dec4`
- reviewer role：`INDEPENDENT_METADATA_DISCOVERY_SCOPE_REVIEWER`
- response format：`m8-metadata-discovery-scope-external-review-v1`
- required checks：`canonical_candidate`、`source_binding`、`evidence_bindings`、`scope_assertions`、
  `policy_closed`、`zero_authority`、`history_immutable`、`no_artifact_selection`、`chain_binding`、
  `reviewer_provenance`

## 审查边界

- 本请求不授权任何 metadata request、DNS、HTTP/HTTPS、PyPI 访问、下载、resolver、installer、collector
  或其他 M8 execution。
- Reviewer 不得在此请求下生成 `INDEPENDENT_REVIEW_APPROVED`、`METADATA_DISCOVERY_SCOPE_OWNER_GATE_READY`
  或 Owner approval。deterministic 复验只能返回 `READY_FOR_EXTERNAL_INDEPENDENT_REVIEW`。
- 未来的独立审查结论必须由真正隔离、身份来源可验证的 Reviewer 以独立、committed、content-addressed
  记录发布；字符串身份、Git author/committer 或 self-attestation 不能构成 verified provenance。

reviewer 指定：____（留空，待 Owner 指定真正隔离、身份可验证的 Reviewer）

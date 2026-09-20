# M8 Metadata Discovery Governance Tests

本目录验证 Metadata Discovery 的离线治理边界，不执行 metadata request、DNS、网络、下载、解析、安装、collector 或其他 M8 stage。

## 范围

- canonical JSON、严格类型、重复键、非有限数字和 surrogate 拒绝；
- committed Git object、blob、字节数和摘要绑定；
- package/tooling/API/dependency/history 证据不被误选为发行包身份；
- exact authorization token 仅作为 predicate，不能开启任何执行；
- current effective limits、execution counts 和 `m8_status` 的 failed-closed 约束；
- reviewer 只能返回 ready-for-external-review，不产生 Owner approval。
- selected-scope cycle 只冻结 Owner 已选择的 `pypdf==6.0.0`，并严格保持 `dependency_scope: ["pypdf"]`；不从 requirements 自动扩展依赖。
- `proposed_metadata_policy` 只是有限的 Builder 提案，`PROPOSED_NOT_EFFECTIVE`；它与全零 `current_effective_limits`、全零 `execution_counts` 和全 false authorization 分离。
- candidate validation 只能返回 `METADATA_DISCOVERY_SCOPE_CANDIDATE_VALIDATED_FOR_EXTERNAL_REVIEW`，不等于独立审查；当前 provenance 不可验证，完整 dispatch 校验最多返回 `READY_FOR_EXTERNAL_INDEPENDENT_REVIEW`，不产生 `INDEPENDENT_REVIEW_APPROVED`、Owner approval 或 metadata-discovery authorization。
- selected-scope chain 是六阶段、固定路径、direct-parent、forward-only 的 committed chain：`candidate_publication → builder_self_check → review_request → review_prompt → review_target → dispatch_manifest`；dispatch-rooted validator 只沿 committed content-addressed references 反向加载对象，不接受调用方替换的 records。
- Builder 与 validator 共用 bounded Git reader：full lowercase SHA-1 OID、`--no-replace-objects`、`--no-lazy-fetch`、blob 类型与声明大小预检、单对象/整链累计字节预算、Git OID 重算和 `ordinary_single_parent_commit_only`；root/merge、wrong type、oversized、truncated/extra framing 与绑定 divergence 均 fail closed 为 `MetadataGovernanceError`。

## 命令

```bash
python -m pytest tests/M8_metadata_discovery -v
```

测试使用显式当前 Git commit 的 committed objects；不会把 worktree 中的 untracked 文件作为证据。

# M8 Metadata-Discovery Governance

本文件定义 Metadata Discovery 专属的离线治理边界。它不是 M8 执行协议、网络授权、
Artifact Acquisition 方案或阶段准入记录。

## 状态机

```text
committed intent inventory
  -> Metadata-Discovery Candidate
  -> Builder Internal QA + Adversarial QA
  -> additive remediation (最多 3 轮)
  -> external isolated independent review
  -> additive remediation/re-review (最多 3 轮)
  -> Owner Gate package
  -> explicit human decision
```

每个节点均绑定调用方明确选择的完整 Git commit；禁止使用 branch head、worktree 状态、
延迟绑定、前向引用或自引用替代绑定。历史记录只读且只能追加新版本。

## 当前候选结论

当前仓库是 application/harness，而不是唯一可识别的 publishable distribution。`package.json`
是私有 Commitizen tooling metadata；FastAPI title/version 是 API presentation metadata；
requirements 文件是依赖声明；README 和历史 M8 文件是描述或治理边界。上述材料不能单独
推出 package identity、version、artifact 或 metadata URL。因此当前结果必须为：

`METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED`

Builder 不得猜测 PyPI 名称、标准 URL、wheel 文件名、host、redirect、proxy、credential 或
runtime-selected endpoint。

## 安全边界

在明确出现精确 token `METADATA_DISCOVERY_AUTHORIZATION_APPROVED` 之前，metadata discovery
request count、DNS、network、download、resolver、installer、collector 和所有 M8 execution
均为零。该 token 即使出现，也只可能开启另一个独立、有限的 metadata-discovery 授权评估，
不授权 artifact acquisition、解析、安装、collector、S1、S1-B、S2、S3 或 backend selection。

`current_effective_limits` 与未来的 `proposed_discovery_limits` 分离；当前有效限制必须继续为
零，提议值不能自动激活。所有 authorization flags 保持 false。

## 角色隔离

- **Discovery Candidate Builder**：只读取 committed Git object，生成 canonical inventory 和
  unresolved candidate。
- **Builder Internal QA / Adversarial QA**：验证 schema、canonical bytes、Git binding、零计数、
  intent non-selection 和 forbidden actions；不得声称独立审查。
- **Independent Discovery Scope Reviewer**：只能在隔离、只读环境中重算 Git object、bytes、摘要
  和角色边界；不得选包、发 token 或授权请求。
- **Owner-Gate Summary Drafter**：只汇总可验证事实和失败关闭结果；不得伪称 Owner approval。

Builder QA 最多三轮；独立审查后的 additive remediation 最多三轮。任何不收敛、证据冲突、
前置缺失或绑定失败均进入对应 `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED_*` 状态。

## 允许的 Owner Gate 结果

- `METADATA_DISCOVERY_OWNER_GATE_READY`
- `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED`
- `METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED`
- `METADATA_DISCOVERY_CANDIDATE_READY_FOR_EXTERNAL_INDEPENDENT_REVIEW`
- `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED_MISSING_PREREQUISITE`
- `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED_EVIDENCE_CONFLICT`
- `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED_QA_NOT_CONVERGED`

任何非上述值不得发布为治理结论。Owner Gate 就绪也不等于批准，只表示等待明确人工决定。

## 证据与禁止事项

证据只来自候选 commit 中的 tracked files，并记录 path、Git blob OID、byte count 与 SHA-256。
禁止使用 untracked files、local PATH、site-packages、cache、browser cache、environment host、
credentials、proxy、external source 或运行时推断值。旧 acquisition candidate、downloader、
collector、coverage receipt 和 failed-closed decision 仅作为不可变历史边界，不得重新解释为
当前 metadata intent。

当前 `m8_status` 保持 `BLOCKED / NOT_STARTED`。本轮不执行 metadata discovery、不访问网络，
不创建环境、不安装依赖、不生成 wheelhouse，也不启动任何 M8 stage。

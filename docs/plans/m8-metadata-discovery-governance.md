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

## Selected-scope cycle（pypdf==6.0.0）

Owner 已明确选择唯一 discovery scope：`pypdf==6.0.0`。这只冻结 canonical
package name 与 exact version；不构成 metadata request authorization、DNS/网络授权、PyPI
访问授权、artifact/URL/hash 选择、下载、resolver、installation、collector 或其他 M8
execution authorization。selected-scope candidate 的 `dependency_scope` 严格为
`["pypdf"]`，不会从 `platform/requirements.txt` 的其他条目扩展。

Candidate 中的 `proposed_metadata_policy` 仅是 Builder 提案，状态必须为
`PROPOSED_NOT_EFFECTIVE`；其中的 `pypi.org`、exact-version JSON metadata endpoint、GET、
TLS 与有限 timeout/size cap 不能被描述为 discovered fact 或当前 authority。`current_effective_limits`
（包含 network bytes）和 `execution_counts` 必须全为零，authorization flags 必须全为 false，
token 必须为 null；`m8_status` 继续为 `BLOCKED / NOT_STARTED`。

本 cycle 的角色与结论严格分离：deterministic candidate validation 只能返回
`METADATA_DISCOVERY_SCOPE_CANDIDATE_VALIDATED_FOR_EXTERNAL_REVIEW`；它不等于 independent
review。当前仓库没有可信 Reviewer 身份颁发、签名根或可验证的外部 provenance，因此 caller-authored
`reviewer_id`、Git author/committer 和 `independence_attested` 都不能制造 independent pass；legacy
self-attested review 路径必须 fail closed。hardening 尚未冻结时状态为
`METADATA_DISCOVERY_SCOPE_IMPLEMENTATION_HARDENING_REQUIRED`；全部实现检查通过后，dispatch-rooted
validator 的最高结论也只能是 `READY_FOR_EXTERNAL_INDEPENDENT_REVIEW`。它不能声明
`INDEPENDENT_REVIEW_APPROVED`、`METADATA_DISCOVERY_SCOPE_OWNER_GATE_READY`、Owner approval 或
metadata-discovery authorization。未来 independent review 必须由真正外部、身份可验证的 Reviewer 发布独立、
committed、content-addressed 记录；独立 review 本身仍不能授权 execution，Owner Gate readiness 也不等于
Owner approval。

Staged binding 采用单向、非自引用、非前向引用的六阶段 committed chain：
`candidate_publication → builder_self_check → review_request → review_prompt → review_target → dispatch_manifest`。
每一阶段只引用已经存在的前序 commit/path/blob/digest；dispatch-rooted validator 先加载固定 dispatch publication，再沿
content-addressed references 反向解析其余五个 stage，并重新构造完整链。每个 stage payload 都是 canonical JSON
exact schema，candidate、cycle、protocol、target 和 predecessor bindings 必须闭合一致；错误 parent、self-reference、
forward/deferred reference、任意非 JSON committed bytes 或 predecessor digest 篡改均 fail closed。本链不含
independent review publication；它只把已冻结的审查请求交给未来真正独立的 Reviewer。本 cycle 不执行 metadata request。

Builder 与 Reviewer 的 Git 读取使用同一个 bounded reader 契约：输入必须是 full lowercase 40-character SHA-1 OID，
命令禁用 replacement objects 与 lazy fetch；读取 blob 前先做 object type/declared-size preflight，再施加
`MAX_DOCUMENT_BYTES` 单对象限制和一次 traversal 的 `MAX_CHAIN_BYTES` 累计预算；读取后复算 Git blob SHA-1 与
SHA-256，并拒绝 truncation、extra output、framing mismatch、missing/wrong-type/oversized objects。source commit 与
publication commit 均限定为 `ordinary_single_parent_commit_only`，root commit 和 merge commit 失败关闭。预期的
canonical/schema/path/Git/binding/provenance 拒绝统一使用 `MetadataGovernanceError`；不依赖 HEAD、branch/tag、
worktree、后续记录或 reviewer inference。

## 当前实现边界与后续条件

当前 selected-scope 工作只做 implementation hardening，不发布 candidate、dispatch 或 independent review
artifact。实现冻结且所有回归、历史 replay 与字节不变性检查通过后，最多进入
`READY_FOR_EXTERNAL_INDEPENDENT_REVIEW`，等待真正隔离且身份来源可验证的 Reviewer。未来若定义
`independent_review_publication`，其 schema 必须 exact 绑定 dispatch、review target、candidate、request、prompt、
固定 protocol 及可验证 provenance，并且 publication commit 必须晚于 dispatch；未提交 review bytes、身份字符串不等、
自签声明或 Builder identity reuse 均只能得到 `PROVENANCE_UNVERIFIED`，不能升级状态。

通用 unresolved workflow 保持原样并继续返回
`METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED`。selected-scope hardening 不得改写历史 P1/P0、r01/r02/r03、
acquisition 或 external-gate artifacts，也不得生成 artifact、URL、filename、wheel、sdist、hash 或任何未来发现事实。

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

## 当前流程允许的治理结果

通用 unresolved workflow 允许：

- `METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED`
- `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED`
- `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED_MISSING_PREREQUISITE`
- `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED_EVIDENCE_CONFLICT`
- `METADATA_DISCOVERY_GOVERNANCE_FAILED_CLOSED_QA_NOT_CONVERGED`

selected-scope hardening/dispatch validator 允许：

- `METADATA_DISCOVERY_SCOPE_IMPLEMENTATION_HARDENING_REQUIRED`
- `METADATA_DISCOVERY_SCOPE_CANDIDATE_VALIDATED_FOR_EXTERNAL_REVIEW`
- `READY_FOR_EXTERNAL_INDEPENDENT_REVIEW`
- 上述 failed-closed 结果

本轮不得产生 `METADATA_DISCOVERY_OWNER_GATE_READY`、
`METADATA_DISCOVERY_SCOPE_REVIEW_PASSED_NO_AUTHORIZATION`、
`METADATA_DISCOVERY_SCOPE_OWNER_GATE_READY` 或任何等价的 independent-pass/Owner-Gate-ready 结论。
这些历史名称若出现在不可变旧记录中，只描述当时记录，不是当前实现可发布的状态。Owner Gate readiness
即使未来由可验证 review 支持，也仍不等于 Owner approval。

## 证据与禁止事项

证据只来自候选 commit 中的 tracked files，并记录 path、Git blob OID、byte count 与 SHA-256。
禁止使用 untracked files、local PATH、site-packages、cache、browser cache、environment host、
credentials、proxy、external source 或运行时推断值。旧 acquisition candidate、downloader、
collector、coverage receipt 和 failed-closed decision 仅作为不可变历史边界，不得重新解释为
当前 metadata intent。

当前 `m8_status` 保持 `BLOCKED / NOT_STARTED`。本轮不执行 metadata discovery、不访问网络，
不创建环境、不安装依赖、不生成 wheelhouse，也不启动任何 M8 stage。

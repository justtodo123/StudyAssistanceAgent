# 辅助与历史治理记录（plans/references/）

> 本目录不具阶段权威，不能产生新授权。
> 最终阶段状态和路线图以 [`docs/PLAN.md`](../../PLAN.md) 为准，正式准入政策以 `docs/standards/` 为准。
> 若本目录材料与上述权威冲突，以正式权威为准。

## 用途与证据边界

本目录同时存放两类材料：

1. **非正式分析与事实调查**：用于对照外部要求、讨论阶段顺序和辅助维护正式计划；不是最终支撑来源。
2. **限定范围的历史治理记录**：协议、授权、审计、处置和治理复盘可证明其明确记载的既往事实，但不具当前阶段
   权威，不得扩张、续用或组合成新的批准。

历史材料或未批准草案不能关闭 Decision、选择后端、批准阶段 admission，或授权建根、source authoring、preflight、
执行与生产实现。经负责人明确批准的范围/Decision 记录只能证明其所载政策已批准；阶段状态仍以 PLAN 和机器门禁
为准。正式任务拆解只在 PLAN 授权后写入对应 `m*-plan.md`。

## 当前文件

| 文件 | 说明 | 地位 |
| --- | --- | --- |
| [`agent-alignment-analysis.md`](agent-alignment-analysis.md) | 对照 Agent 招聘要求与仓库现状 | 辅助调查 |
| [`stage-advancement-analysis.md`](stage-advancement-analysis.md) | M6–M10 推进顺序与招聘项映射 | 辅助调查 |
| [`recruitment-driven-feasibility.md`](recruitment-driven-feasibility.md) | 以招聘要求为唯一标准的可行性分析与阶段更新建议 | 辅助调查 |
| [`m8-m12-scope-decision-v1.md`](m8-m12-scope-decision-v1.md) | M8–M12 规模化范围决策 | `APPROVED / SCOPE_FROZEN`；不等于阶段 admission |
| [`m8-decision-closure-v1.md`](m8-decision-closure-v1.md) | M8 八项 Decision 批准记录 | `APPROVED / EIGHT_DECISIONS_RESOLVED`；不选择后端或授权实现 |
| [`m8-active-execution-protocol-draft.md`](m8-active-execution-protocol-draft.md) | M8 active execution protocol `draft-0.5` | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED` |
| [`m8-active-execution-protocol-draft-0.5-authorization-20260912.md`](m8-active-execution-protocol-draft-0.5-authorization-20260912.md) | `draft-0.5` 修订授权 | 已授权并已消费的文本修订；不解除任何执行禁令 |
| [`m8-active-execution-protocol-draft-0.5-review-20260913.md`](m8-active-execution-protocol-draft-0.5-review-20260913.md) | `draft-0.5` P0 技术审查 | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；不产生执行、准入或后端权限 |
| [`m8-active-execution-protocol-draft-0.5-returned.md`](m8-active-execution-protocol-draft-0.5-returned.md) | 被审的 `draft-0.5` 原文（171830 bytes） | 历史追溯；被审字节 `ac907b83…b9fbc9`；不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.6.md`](m8-active-execution-protocol-draft-0.6.md) | `draft-0.6` 正文（174214 bytes） | **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**；未授权先修订，不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.6-authorization-20260913.md`](m8-active-execution-protocol-draft-0.6-authorization-20260913.md) | `draft-0.6` 修订**事后补正**记录 | `RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION`；**不是**授权，不赋予正当性 |
| [`m8-active-execution-protocol-draft-0.6-review-20260913.md`](m8-active-execution-protocol-draft-0.6-review-20260913.md) | `draft-0.6` P0 技术审查（AI 机械核验） | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；5 项残留阻断缺陷；`AI_ASSISTED_MECHANICAL_REVIEW`，非人类独立审查 |
| [`m8-active-execution-protocol-draft-0.7.md`](m8-active-execution-protocol-draft-0.7.md) | `draft-0.7` 正文（175826 bytes） | **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**；未授权先修订，不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.7-authorization-20260913.md`](m8-active-execution-protocol-draft-0.7-authorization-20260913.md) | `draft-0.7` 修订**事后补正**记录 | `RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION`；**不是**授权，不赋予正当性 |
| [`m8-active-execution-protocol-draft-0.7-review-20260913.md`](m8-active-execution-protocol-draft-0.7-review-20260913.md) | `draft-0.7` P0 技术审查（AI 机械核验） | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；3 项残留阻断缺陷；`AI_ASSISTED_MECHANICAL_REVIEW`，非人类独立审查 |
| [`m8-active-execution-protocol-draft-0.8.md`](m8-active-execution-protocol-draft-0.8.md) | `draft-0.8` 正文（180033 bytes） | **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**；未授权先修订，不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.8-authorization-20260913.md`](m8-active-execution-protocol-draft-0.8-authorization-20260913.md) | `draft-0.8` 修订**事后补正**记录 | `RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION`；**不是**授权，不赋予正当性 |
| [`m8-active-execution-protocol-draft-0.8-review-20260913.md`](m8-active-execution-protocol-draft-0.8-review-20260913.md) | `draft-0.8` P0 技术审查（AI 机械核验） | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；3 项残留阻断 + 2 项非阻断；`AI_ASSISTED_MECHANICAL_REVIEW` |
| [`m8-active-execution-protocol-draft-0.9.md`](m8-active-execution-protocol-draft-0.9.md) | `draft-0.9` 正文（182575 bytes） | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`；不得 binding 或执行 |
| [`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md) | `draft-0.9` 修订授权 | 已发起并消费的文本修订；不产生执行、准入或后端权限 |
| [`m8-active-execution-protocol-draft-0.9-review-20260913.md`](m8-active-execution-protocol-draft-0.9-review-20260913.md) | `draft-0.9` P0 技术审查（AI 机械核验） | `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；A/B/C/D 全闭合；`AI_ASSISTED_MECHANICAL_REVIEW`，非人类独立审查 |
| [`m8-draft09-p1-materials-20260913.md`](m8-draft09-p1-materials-20260913.md) | `draft-0.9` P0/identity/P1 材料说明 | `MATERIALS_PREPARED / P0_PENDING_INDEPENDENT_REVIEW / NOT_AUTHORIZED`；**不构成任何授权** |
| [`external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json`](external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json) | `draft-0.9` P0 门禁记录（机器可读） | **`P0_NOT_ACCEPTED`**；`independence.satisfied=false`，同一主体自查，实质独立性未成立；待人类 reviewer 复核 |
| [`external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json`](external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json) | `draft-0.9` P1 门禁记录（机器可读） | **`NOT_AUTHORIZED`**；前驱 P0 未成立，门禁边未满足；`allowed_next_action=stop` |
| [`external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json`](external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json) | `draft-0.9` experiment identity（机器可读） | 已备好但**未激活**；其存在本身不构成授权 |
| [`m8-active-execution-protocol-draft-0.4-authorization-20260912.md`](m8-active-execution-protocol-draft-0.4-authorization-20260912.md) | `draft-0.4` 修订授权 | 已消费文本修订；不解除任何执行禁令 |
| [`m8-active-execution-protocol-draft-0.4-review-20260912.md`](m8-active-execution-protocol-draft-0.4-review-20260912.md) | `draft-0.4` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`；3 项新增阻断缺陷 |
| [`m8-active-execution-protocol-draft-0.4-returned.md`](m8-active-execution-protocol-draft-0.4-returned.md) | 被退回的 `draft-0.4` 原文 | 历史追溯；不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.3-review-20260912.md`](m8-active-execution-protocol-draft-0.3-review-20260912.md) | `draft-0.3` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`m8-active-execution-protocol-draft-0.3-returned.md`](m8-active-execution-protocol-draft-0.3-returned.md) | 被退回的 `draft-0.3` 原文 | 历史追溯；不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.2-review-20260911.md`](m8-active-execution-protocol-draft-0.2-review-20260911.md) | `draft-0.2` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`m8-active-execution-protocol-draft-0.2-returned.md`](m8-active-execution-protocol-draft-0.2-returned.md) | 被退回的 `draft-0.2` 原文 | 历史追溯；不得 binding 或授权 |
| [`m8-active-execution-protocol-draft-0.1-review-20260911.md`](m8-active-execution-protocol-draft-0.1-review-20260911.md) | `draft-0.1` P0 技术审查 | `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED` |
| [`m8-active-execution-protocol-draft-0.1-returned.md`](m8-active-execution-protocol-draft-0.1-returned.md) | 被退回的 `draft-0.1` 原文 | 历史追溯；不得 binding 或授权 |
| [`m8-v7-admission-protocol.md`](m8-v7-admission-protocol.md) | V7 静态冻结协议 | 历史前置产物；执行尝试已 `INVALID` |
| [`m8-v8-admission-protocol.md`](m8-v8-admission-protocol.md) | V8 历史冻结协议 | 历史前置产物；执行根已 `INVALID` |
| [`m8-v9-admission-protocol.md`](m8-v9-admission-protocol.md) | V9 历史失败协议 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；不可复用 |
| [`m8-v10-admission-protocol.md`](m8-v10-admission-protocol.md) | V10 历史失败协议 | `PRE_SOURCE_GOVERNANCE_INVALID`；不可复用 |
| [`m8-v11-admission-protocol.md`](m8-v11-admission-protocol.md) | V11 历史失败协议 | `PRE_SOURCE_PROVENANCE_INVALID`；不可复用 |
| [`m8-v12-admission-protocol.md`](m8-v12-admission-protocol.md) | V12 历史失败协议 | `INDEPENDENT_STATIC_AUDIT_FAILED`；不可复用 |
| [`m8-v13-admission-protocol.md`](m8-v13-admission-protocol.md) | V13 历史未绑定草案 | 已停止；不得 binding、建根或执行 |
| [`m8-v13-scale-fit-assessment-20260910.md`](m8-v13-scale-fit-assessment-20260910.md) | V13 对 100K 新目标适配评估 | `NOT_FIT_AS_COMPLETE_M8_EVIDENCE_PROTOCOL` |
| [`m8-v13-disposition-20260910.md`](m8-v13-disposition-20260910.md) | V13 草案处置 | `SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED` |
| [`m8-v7-authorization-20260908.md`](m8-v7-authorization-20260908.md) | V7 仅-smoke 待签范围记录；执行尝试已 `INVALID` | 不是 M8 准入或 v8 授权 |
| [V8 authorization](m8-v8-authorization-20260908.md) | 历史授权 | 已消费并失效；执行已 `INVALID` |
| [V9 authorization](m8-v9-authorization-20260909.md) | 未授权记录 | `PRE_FREEZE_STATIC_AUDIT_FAILED`；不可复用 |
| [V10 authorization](m8-v10-authorization-20260909.md) | 未授权记录 | `PRE_SOURCE_GOVERNANCE_INVALID`；不可复用 |
| [V11 authorization](m8-v11-authorization-20260909.md) | 历史阶段 1 授权 | 已消费；`PRE_SOURCE_PROVENANCE_INVALID` |
| [V12 authorization](m8-v12-authorization-20260909.md) | 阶段 1 授权 | 已消费；V12 已因独立审计 `FAIL` 封口 |
| [V12 independent static audit (FAIL)](m8-v12-independent-static-audit-fail-20260909.md) | 现行独立静态审计报告 | 最终 `FAIL`；四项机械门禁缺陷；V12 不可复用 |
| [V12 independent static audit (historical)](m8-v12-independent-static-audit-20260909.md) | 历史审计记录 | 初判 `PASS` 已失效，仅作历史追溯 |
| [V12 disposition](m8-v12-disposition-20260909.md) | 永久处置 | `INDEPENDENT_STATIC_AUDIT_FAILED`；不可复用 |
| [V13 protocol text audit](m8-v13-protocol-text-audit-20260910.md) | V13 协议文本设计审计 | `PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED`；不构成执行或独立静态审计授权 |
| [M8 eleven-round governance review](m8-eleven-rounds-governance-review.md) | V1–V11 辅助治理复盘 | 仅供辅助判断；不是计划依据或授权 |

以上历史记录只在表中限定范围内具有事实证据效力，均不是当前 M8 准入。V8–V12 不得授权其对应身份或后继；
V12 独立静态审计最终为 `FAIL`，其授权仅覆盖已完成的阶段 1，从未覆盖独立审计 `PASS`、preflight 或执行。V13
历史协议文本审计的 `PASS_AFTER_REVISION / DRAFT_NOT_AUTHORIZED` 从未产生 repository binding、建根、source
freeze、独立静态审计 PASS 或执行授权；V13 已由处置记录永久标记为
`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`，不得恢复、修订、binding、建根、授权或执行。
后续 M8 实证只能使用全新协议身份并重新取得分阶段书面授权。
2026-09-11 active execution protocol `draft-0.1` 与 `draft-0.2` 经 P0 技术审查先后退回；2026-09-12 `draft-0.3`
也经独立 P0 技术审查退回（12 项 schema/状态/证据闭合缺陷），其精确字节已封存为
[`m8-active-execution-protocol-draft-0.3-returned.md`](m8-active-execution-protocol-draft-0.3-returned.md)，只作历史追溯。
2026-09-12 负责人主动发起 `draft-0.4` 修订，并以独立记录
[`m8-active-execution-protocol-draft-0.4-authorization-20260912.md`](m8-active-execution-protocol-draft-0.4-authorization-20260912.md)
明确授权仅进行文本修订；该版本随后于同日经独立 P0 技术审查退回（3 项新增 schema/状态/证据闭合缺陷），当前状态为
`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`。该授权只解除“不得创建
`draft-0.4`”这一针对未经发起修订的禁令，不创建 experiment/protocol
执行身份，不建立 binding，不得据此创建实验根、安装依赖、生成输入、执行 benchmark、改变 M8 registry、准入 M8
或选择 LanceDB/任何后端。`draft-0.4` 已退回；2026-09-12 负责人另行主动发起 `draft-0.5` 定点修订，仅处理该 3 项
阻断缺陷，2026-09-13 经未参与起草的 independent reviewer 完成 P0 技术审查并取得
`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`（4 项缺陷全部机械闭合，72 行映射表逐字节未变），审查记录见
[`m8-active-execution-protocol-draft-0.5-review-20260913.md`](m8-active-execution-protocol-draft-0.5-review-20260913.md)，
被审精确字节见
[`m8-active-execution-protocol-draft-0.5-returned.md`](m8-active-execution-protocol-draft-0.5-returned.md)。该 P0 接受
只表示技术文字被接受：`draft-0.5` 仍为未绑定、未授权、从未执行的 protocol blob，不产生任何执行权限，也不自动
产生 `draft-0.6`；后续修订仍须负责人另行发起。
2026-09-13 补充记载：`draft-0.6`、`draft-0.7`、`draft-0.8` 三版正文（174214 / 175826 / 180033 bytes）在形成时
**均无事先授权，也无授权、审查或 returned 字节记录落盘**，属未经负责人事先发起的自行续版，其缺陷清单只能从
修订脚本头注释推定。三版均经事后补正定为 **`UNBOUND / NEVER_AUTHORIZED / NEVER_EXECUTED`**，正文只作历史追溯，
不得 binding、授权或执行；对应补正记录为
[`draft-0.6`](m8-active-execution-protocol-draft-0.6-authorization-20260913.md) /
[`draft-0.7`](m8-active-execution-protocol-draft-0.7-authorization-20260913.md) /
[`draft-0.8`](m8-active-execution-protocol-draft-0.8-authorization-20260913.md)，均为
`RETROACTIVE_CORRECTION / NOT_A_PRIOR_AUTHORIZATION`，**不是**授权、不赋予正当性、不免除审查。三者对应的 P0 技术审查记录已由独立进程 `tools/m8_draft_reviewer.py` 机械核验并填定，结论均为
`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`（分别 5 / 3 / 3 项残留阻断缺陷）；该审查标记为
`AI_ASSISTED_MECHANICAL_REVIEW`，**非人类独立 reviewer 审查**，不构成技术认可。
2026-09-13 负责人另行主动发起 `draft-0.9` 定点修订，处理 `draft-0.8` 的三项推定阻断缺陷（A scope 固化、B `stream_scope`
标量、C `stream_query_source` 来源冲突）及两项装饰/不可达清理（D），授权记录见
[`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md)；
该版于 2026-09-13 经独立进程 `tools/m8_draft_reviewer.py` 机械核验后取得
`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`（A/B/C 三项阻断缺陷与 D 项两处清理全部闭合，整条链的保留
不变量成立，72 行表逐字节未变），审查记录见
[`m8-active-execution-protocol-draft-0.9-review-20260913.md`](m8-active-execution-protocol-draft-0.9-review-20260913.md)；
该审查标记为 `AI_ASSISTED_MECHANICAL_REVIEW`，**非人类独立 reviewer 审查**，不构成技术认可之外任何授权，
也不自动产生 `draft-0.10`。
2026-09-13 另为 `draft-0.9` 准备 P0/identity/P1 机器可读材料，说明见
[`m8-draft09-p1-materials-20260913.md`](m8-draft09-p1-materials-20260913.md)。该材料集**不包含任何已成立的门禁**：
draft-0.9 的 P0 技术文字机械核验虽可复现，但核验者与起草者为同一主体，**实质性独立性未成立**，故 P0 记录以
`P0_NOT_ACCEPTED` / `independence.satisfied=false` / `allowed_next_action=stop` 落盘，其唯一后继 P1 随之落为
`NOT_AUTHORIZED` / `stop`；identity 工件已备好但未激活。该材料集曾在首次落盘时误以
`P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY` / `satisfied=true` / P1 `AUTHORIZED` 形式记为已成立，经独立性审阅
认定属**不可验证的自我证明**，已按“待复核”语义整改（experiment identity 字节未变，仍为 `5ba25bd8…`）。P0 门禁
须由**未参与本轮起草与审查的审查者**另行建立（可另发 `-r02`），在此之前 P1 不得重新签发。该材料不产生 identity
激活、binding、建根、依赖获取、source 生成、preflight、执行、证据发布、M8 准入或后端选择中的任何一项。

招聘对照原文：[`docs/interview/StudyAssistanceAgent_requirement.md`](../../interview/StudyAssistanceAgent_requirement.md)。
该原文同样不是计划依据。

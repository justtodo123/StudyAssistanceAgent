# M8 active execution protocol `draft-0.4` 修订授权记录

- 授权对象：`docs/plans/references/m8-active-execution-protocol-draft.md` 的新修订 `draft-0.4`
- 授权日期：2026-09-12
- 负责人：`justtodo123`（用户于当前会话明确声明 `draft-0.4` 为主动发起的修订）
- 上游依据：`draft-0.3` 的 P0 技术审查退回记录
  [`m8-active-execution-protocol-draft-0.3-review-20260912.md`](m8-active-execution-protocol-draft-0.3-review-20260912.md)
- 修订后状态：授权时 **`DRAFTED / PENDING_P0_REVIEW`**；2026-09-12 经独立 P0 技术审查后为
  **`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**，审查记录见
  [`m8-active-execution-protocol-draft-0.4-review-20260912.md`](m8-active-execution-protocol-draft-0.4-review-20260912.md)

## 1. 授权内容

本授权只批准一件事：把 active execution protocol 草案推进到 `draft-0.4`，即由负责人主动发起的下一轮文本修订。该修订用于定点处理 `draft-0.3` P0 审查记录第 2 节列出的 12 项 schema/状态/证据闭合缺陷。

本授权取代 `draft-0.3` 审查记录中“不得自动创建 `draft-0.4`”的禁令，但只取代该禁令本身。该禁令的原意是禁止
**未经负责人发起**的自发修订与自动续版；2026-09-12 负责人已明确发起本次修订，故该禁令不再适用于本版本。

`draft-0.4` 是文档修订号，不是 experiment ID，也不是 executable protocol ID。本次修订不产生新身份，不取代任何
历史记录，也不改变 M8 的阶段状态。

## 2. 允许动作

1. 在 `docs/plans/references/m8-active-execution-protocol-draft.md` 上形成 `draft-0.4` 文本修订。
2. 同步登记该修订的治理与状态说明：`docs/plans/references/README.md`、`docs/plans/README.md`、
   `docs/PLAN.md`、仓库根 `README.md`、`docs/plans/m8-specialized-storage-plan.md`。
3. 形成本授权记录。本记录是唯一解除“不得创建 `draft-0.4`”禁令的文件。

`draft-0.4` 进入 `DRAFTED / PENDING_P0_REVIEW`：草案已写出，等待未参与起草的独立 reviewer 完成 P0 技术口径
审查。审查结论只能由该独立审查产生，不能由本记录或起草方预先写入。

本记录写定后，该独立 P0 审查已于 2026-09-12 完成，结论为 `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`（3 项新增
schema/状态/证据闭合缺陷）。本授权随之消费完毕：授权范围只覆盖已完成的 `draft-0.4` 文本修订，不自动产生
`draft-0.5`，也不构成对 `draft-0.4` 的任何技术接受。

## 3. 明确禁止

本授权不包含、也不得被解释为包含以下任何一项：

- 创建 experiment ID、executable protocol ID、repository binding、experiment root、nonce 或任何 S/A/G/E 根；
- 安装或获取依赖、创建 venv、获取 wheel 或任何 input digest；
- 生成 source、corpus、query 或 gold；
- 运行 preflight、smoke、full、benchmark 或任何实证执行；
- 发布证据、形成 package/receipt、执行 cleanup 或写入任何运行期 artifact；
- 改写 M8 registry、stage-admission 登记表、批准字段或阶段状态；
- 准入 M8、批准开工、选择 LanceDB/Qdrant/Milvus 或任何专业后端；
- 复用 V8–V13 的任何身份、绑定、根、source、manifest、digest 或 artifact；
- 预先写入 P0 审查结论、`PASS` 或 `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`。

被审的 `draft-0.3` 精确字节与 `draft-0.1`/`draft-0.2` 的 returned 副本仍只作历史追溯，不得 binding、授权或作为
`draft-0.4` 的等价替代。`draft-0.3` 审查记录本身是历史快照，不因本次授权而修改。

## 4. 后续前置关系

`draft-0.4` 即使取得独立 P0 `PASS`，也只表示技术口径被接受，不产生任何执行权限。其后仍须分别形成满足前置
关系的外部记录：P1–P9/P7A、全新 experiment/protocol 身份、repository binding、独立静态审阅、隔离准备授权、
执行授权、证据发布、M8 admission 与 backend selection。任何一步都不得由前一步自动推导。

## 5. 状态边界

本授权形成时与消费后，M8 均保持 `BLOCKED / NOT_STARTED`；八项 Decision 保持 `RESOLVED`（2026-09-10 已批准）；
admission approval 字段保持为空；implementation-start 保持未授权。本授权不提交、不合并、不推送；commit、merge
与 push 均须另行取得明确授权。

Agent 不得自行发起修订、自行批准准入、自行宣布 P0 结论或自行选择后端。本记录不构成对 `draft-0.4` 的技术认可，
只证明负责人已发起该修订。

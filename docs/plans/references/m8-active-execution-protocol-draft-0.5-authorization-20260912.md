# M8 active execution protocol `draft-0.5` 修订授权记录

- 授权对象：`docs/plans/references/m8-active-execution-protocol-draft.md` 的新修订 `draft-0.5`
- 授权日期：2026-09-12
- 负责人：`justtodo123`（用户于当前会话明确发起本次修订动作）
- 上游依据：`draft-0.4` 的 P0 技术审查退回记录
  [`m8-active-execution-protocol-draft-0.4-review-20260912.md`](m8-active-execution-protocol-draft-0.4-review-20260912.md)
- 修订后状态：授权时 **`DRAFTED / PENDING_P0_REVIEW`**；2026-09-13 经独立 P0 技术审查后为
  **`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`**，审查记录见
  [`m8-active-execution-protocol-draft-0.5-review-20260913.md`](m8-active-execution-protocol-draft-0.5-review-20260913.md)

## 1. 授权内容

本授权只批准一件事：把 active execution protocol 草案推进到 `draft-0.5`，即由负责人主动发起的下一轮**定点**文本
修订。该修订**仅**用于处理 `draft-0.4` P0 审查记录第 3 节所列的 3 项阻断缺陷，且只按下列已裁定的技术方案执行：

| 编号 | 缺陷 | 采用方案 | 改动要点 |
| --- | --- | --- | --- |
| B1-a | listener 检测使用未在 status map 中声明的 `RELISTENER_PREFLIGHT_LISTENER_DETECTED` / `RELISTENER_RUNTIME_LISTENER_DETECTED` | **A1** | 删除该对悬空字面量；listener 检测与出站阻断统一按实际 phase 落定到既有的 `WATCHDOG_PREFLIGHT_OUTBOUND_BLOCKED` / `WATCHDOG_RUNTIME_OUTBOUND_BLOCKED` |
| B1-b | `STATUS_MAP_ENTRY.source_domain` 声明了 `win32`，但 72 行映射表中没有任何 `win32` 行 | **B1** | 从 `source_domain` 枚举中删除悬空成员 `win32` |
| B2 | `source_domain` 枚举声明序（`ntstatus,win32,backend,watchdog,protocol`）与 72 行表的实际顺序（`backend,ntstatus,protocol,watchdog`）不一致，与 §2.3「enum 按 schema 声明顺序」比较规则冲突 | **A1** | 将枚举声明序调整为 `backend,ntstatus,protocol,watchdog`，使声明序即表序 |
| B3 | `sa.m8.cleanup-failure-record.v1.payload` 无条件必填 `pending_terminal:ABORT_TERMINAL`，但 `branch=normal` 的触发时点在所有层 PASS 之后，不存在可提供该值的层 FAIL | **A1** | 该字段改为按 branch 条件必填：`abort`/`nonpublication` 保留 `pending_terminal:ABORT_TERMINAL` 及其既有映射；`normal` 改用 `pending_disposition:"CLEANUP_INCOMPLETE"`，不虚构 abort terminal |

本授权取代 `draft-0.4` 审查记录中"不得自动创建 `draft-0.5`"的禁令，但**只取代该禁令本身**。该禁令的原意是禁止
未经负责人发起的自发修订与自动续版；2026-09-12 负责人已明确发起本次修订，故该禁令不再适用于本版本。

`draft-0.5` 是文档修订号，不是 experiment ID，也不是 executable protocol ID。本次修订不产生新身份，不取代任何
历史记录，也不改变 M8 的阶段状态。

## 2. 允许动作

1. 在 `docs/plans/references/m8-active-execution-protocol-draft.md` 上形成 `draft-0.5` 文本修订，范围**严格限于**上表
   四项，即 B1-a、B1-b、B2、B3。
2. 同步更新文档头部版本号（`draft-0.4` → `draft-0.5`）与相应日期说明。
3. 同步登记该修订的治理与状态说明：`docs/plans/references/README.md`、`docs/plans/README.md`、
   `docs/PLAN.md`、仓库根 `README.md`、`docs/README.md`、`docs/plans/m8-specialized-storage-plan.md`。
4. 形成本授权记录。

`draft-0.5` 进入 `DRAFTED / PENDING_P0_REVIEW`：草案已写出，等待未参与起草的独立 reviewer 完成 P0 技术口径
审查。审查结论只能由该独立审查产生，不能由本记录或起草方预先写入。

本记录写定后，该独立 P0 审查已于 2026-09-13 完成，结论为 `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`：
B1-a、B1-b、B2、B3 四项全部机械闭合，7 处 hunk 全部落在本授权范围内，72 行映射表逐字节未变，未引入新的阻断缺陷。
本授权随之消费完毕：授权范围只覆盖已完成的 `draft-0.5` 文本修订，不自动产生 `draft-0.6`，也不构成任何执行权限。
审查记录另记 4 项观察项（其中 3 项为本授权明确要求保留的既有状态，1 项为交叉引用 NIT），均不构成 `draft-0.5` 的
阻断缺陷，也不因此获得任何后续修订授权。

## 3. 修订边界（冻结字节不变量）

本次修订**不得**改动下列内容；如任一改动成为必需，必须停止并另行取得授权：

- `sa.m8.status-map.v1.payload` 的 **72 行映射表**：行数、每行的 `source_domain`/`phase`/`raw_status`/`stable_code`
  取值、行序、`entries:72..72` 与 `required_stable_codes:72..72` 基数均保持逐字不变。B2 只调整**枚举声明序**，
  不改表。
- 其余全部既有 schema、枚举、谓词、数量、deadline、状态机转移和 §10.1 的 26 项技术门禁。本次修订是定点文字
  修订，不是重新设计。

修订后必须重新计算并冻结 `draft-0.5` 的完整 protocol blob digest（`protocol_blob_sha256`），并在独立 P0 审查**之前**
完成 `draft-0.5-returned` 式精确字节归档，使审查记录中的 SHA-256 与被审字节一致。

## 4. 明确禁止

本授权不包含、也不得被解释为包含以下任何一项：

- 创建 experiment ID、executable protocol ID、repository binding、experiment root、nonce 或任何 S/A/G/E 根；
- 安装或获取依赖、创建 venv、获取 wheel 或任何 input digest；
- 生成 source、corpus、query 或 gold；
- 运行 preflight、smoke、full、benchmark 或任何实证执行；
- 发布证据、形成 package/receipt、执行 cleanup 或写入任何运行期 artifact；
- 改写 M8 registry、stage-admission 登记表、批准字段或阶段状态；
- 准入 M8、批准开工、选择 LanceDB/Qdrant/Milvus 或任何专业后端；
- 复用 V8–V13 的任何身份、绑定、根、source、manifest、digest 或 artifact；
- 预先写入 P0 审查结论、`PASS` 或 `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；
- 借本次修订夹带处理 `draft-0.4` 审查记录第 4 节未构成阻断的观察项，或引入任何未在上表列出的改动。

被审的 `draft-0.4` 精确字节与更早的 `draft-0.1`/`draft-0.2`/`draft-0.3` returned 副本仍只作历史追溯，不得
binding、授权或作为 `draft-0.5` 的等价替代。`draft-0.4` 审查记录本身是历史快照，不因本次授权而修改。

## 5. 后续前置关系

`draft-0.5` 即使取得独立 P0 `PASS`，也只表示技术口径被接受，不产生任何执行权限。其后仍须分别形成满足前置
关系的外部记录：P1–P9/P7A、全新 experiment/protocol 身份、repository binding、独立静态审阅、隔离准备授权、
执行授权、证据发布、M8 admission 与 backend selection。任何一步都不得由前一步自动推导。

## 6. 状态边界

本授权的形成、消费以及 `draft-0.5` 的产生与审查，均不改变以下事实：M8 保持 `BLOCKED / NOT_STARTED`；八项
Decision 保持 `RESOLVED`（2026-09-10 已批准）；admission approval 字段保持为空；implementation-start 保持未授权。
本授权不提交、不合并、不推送；commit、merge 与 push 均须另行取得明确授权。

Agent 不得自行发起修订、自行批准准入、自行宣布 P0 结论或自行选择后端。本记录不构成对 `draft-0.5` 的技术认可，
只证明负责人已发起该修订。

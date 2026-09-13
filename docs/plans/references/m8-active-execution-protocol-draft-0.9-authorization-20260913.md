# M8 active execution protocol `draft-0.9` 修订授权记录

- 授权对象：`docs/plans/references/m8-active-execution-protocol-draft.md` 的新修订 `draft-0.9`
- 授权日期：2026-09-13
- 负责人：`justtodo123`（用户于当前会话明确发起本次修订动作）
- 上游依据：`draft-0.8` 的 P0 技术审查退回所识别的机械缺陷，见修订脚本
  [`apply_draft09_revision.py`](../../../../../../D:/面试实习/apply_draft09_revision.py) 头注释与本记录 §1 清单
- 修订后状态：授权时 **`DRAFTED / PENDING_P0_REVIEW`**；2026-09-13 经独立进程机械核验后为
  **`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`**（`AI_ASSISTED_MECHANICAL_REVIEW`，非人类独立审查），
  审查记录见 [`m8-active-execution-protocol-draft-0.9-review-20260913.md`](m8-active-execution-protocol-draft-0.9-review-20260913.md)

## 0. 治理事实声明（必读）

本授权记录是在上游审查记录存在缺口的背景下形成的，特此如实声明：

- `draft-0.6`、`draft-0.7`、`draft-0.8` 三个版本均**只有正文文本**（`m8-active-execution-protocol-draft-0.6.md` /
  `m8-active-execution-protocol-draft-0.7.md` / `m8-active-execution-protocol-draft-0.8.md`），
  **没有对应的独立 P0 审查记录、authorization 记录或 returned 字节归档文件**。
- `apply_draft07_revision.py` / `apply_draft08_revision.py` / `apply_draft09_revision.py` 头注释分别声称
  0.6、0.7、0.8 经 P0 审查退回，但这些审查**未落盘为独立文件**，本仓库无法核验其审查者独立性、被审字节
  或缺陷清单，只能以修订脚本头注释作为草案身份与缺陷方向的线索。
- 因此，本授权记录所依据的 `draft-0.8` 缺陷清单**来自 `apply_draft09_revision.py` 的静态文本**，并非来自一份
  已归档的 `draft-0.8` review 记录。该缺口应在随后的治理步骤中补齐（见 §6）。

## 1. 授权内容

本授权只批准一件事：把 active execution protocol 草案推进到 `draft-0.9`，即由负责人主动发起的下一轮**定点**文本
修订。该修订**仅**用于处理修订脚本头注释所列的 `draft-0.8` 三项阻断缺陷，且只按下列已裁定的技术方案执行：

| 编号 | 缺陷 | 采用方案 | 改动要点 |
| --- | --- | --- | --- |
| A | scope 被错误地固化为 profile 常量；`parent-walk` 逐级打开 volume/device root 与普通目录，一个 profile 无法承载两种对象，一个常量无法为整次 walk 决定 scope | **A** | scope 改为 **per-open**：由该次 open 实际打开的那个对象判定，先判卷根（与 walk 冻结的卷根 `FILE_IDENTITY` 逐字段比对），再按 `leaf_kind` 判定；`NT_OPEN_PROFILE` 删除 `opens_volume_root` 字段 |
| B | `stream_scope` 为单一标量，无法表达 per-open 派生 | **B** | 以 `stream_scope_per_open:"required"` 取代单一 `stream_scope` 标量；每个 operation 的每次 open 必须独立派生自己的 scope |
| C | `stream_query_source.handle_source` 允许 `root-directory-handle`，与 §7 正文冲突 | **C** | `stream_query_source` 的 `handle_source` 仅允许 `"opened-file-handle"`，移除 `root-directory-handle` 备选 |
| D | 装饰性字段 `allowed_system_streams_closed` 与不可达的 `stream_reverify=not-applicable` 残留 | **D** | 删除这两处不可达/装饰字段；`stream_reverify` 改为逐字常量 `"required"` |

`draft-0.9` 是文档修订号，不是 experiment ID，也不是 executable protocol ID。本次修订不产生新身份，不取代任何
历史记录，也不改变 M8 的阶段状态。

本授权取代 `draft-0.5` 审查记录关于"不得自动产生 `draft-0.6`"及此后任何隐含"不得继续续版"禁令的适用；该禁令原意
是禁止**未经负责人发起**的自发修订与自动续版，2026-09-13 负责人已明确发起本次修订，故该禁令不再适用于 `draft-0.9`。
本授权**不**追溯性补认 `draft-0.6`/`draft-0.7`/`draft-0.8` 的合法性，也不使它们免于后续审查或获得任何执行权限。

## 2. 允许动作

1. 在 `docs/plans/references/m8-active-execution-protocol-draft.md` 上形成 `draft-0.9` 文本修订，范围**严格限于**
   上表四项，即 A、B、C、D。
2. 同步更新文档头部版本号（`draft-0.8` → `draft-0.9`）与相应日期、修订依据说明。
3. 在独立 P0 审查**之前**完成 `draft-0.9` 的 `-returned` 式精确字节归档，使后续审查记录中的 SHA-256 与被审字节一致。
4. 形成本授权记录。

`draft-0.9` 进入 `DRAFTED / PENDING_P0_REVIEW`：草案已写出，等待未参与起草的独立 reviewer 完成 P0 技术口径
审查。审查结论只能由该独立审查产生，不能由本记录或起草方预先写入。本授权**不**预先宣告 `PASS`，也**不**保证
审查必然通过。

本记录写定后，该机械核验已于 2026-09-13 完成，结论为 `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`：
A/B/C 三项阻断缺陷与 D 项两处清理全部机械闭合，整条链的保留不变量全部成立，72 行映射表逐字节未变。该结论由
独立进程 `tools/m8_draft_reviewer.py` 得出，标记为 `AI_ASSISTED_MECHANICAL_REVIEW`，**不是**人类独立 reviewer
的审查。本授权随之消费完毕：授权范围只覆盖已完成的 `draft-0.9` 文本修订，不自动产生 `draft-0.10`，也不构成
任何执行权限。

## 3. 修订边界（冻结字节不变量）

本次修订**不得**改动下列内容；如任一改动成为必需，必须停止并另行取得授权：

- `sa.m8.status-map.v1.payload` 的 **72 行映射表**：行数、每行的 `source_domain`/`phase`/`raw_status`/`stable_code`
  取值、行序、`entries:72..72` 与 `required_stable_codes:72..72` 基数均保持逐字不变。A/B/C/D 均不触及该表。
- `draft-0.6` 起引入且经 `draft-0.7`/`draft-0.8` 保持的系统保留流设计骨架：`SYSTEM_RESERVED_STREAM` 闭合枚举、
  `STREAM_SCOPE` 三值闭合枚举、`allowed_system_streams` allowlist 及其 `observation` 消费逻辑。本次修订只修
  scope 的判定域与查询来源，不推翻该设计。
- 其余全部既有 schema、枚举、谓词、数量、deadline、状态机转移和 §10.1 的 26 项技术门禁。本次修订是定点文字
  修订，不是重新设计。

修订后必须重新计算并冻结 `draft-0.9` 的完整 protocol blob digest（`protocol_blob_sha256`）。截至本记录形成时，
`draft-0.9` 现有文本为 **182575 bytes**，SHA-256 `162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4`；
该摘要仅记录当前草案身份，不构成 `PASS`，也不免除后续独立审查与 returned 归档要求。

## 4. 明确禁止

本授权不包含、也不得被解释为包含以下任何一项：

- 创建 experiment ID、executable protocol ID、repository binding、experiment root、nonce 或任何 S/A/G/E 根；
- 安装或获取依赖、创建 venv、获取 wheel 或任何 input digest；
- 生成 source、corpus、query 或 gold；
- 运行 preflight、smoke、full、benchmark 或任何实证执行；
- 发布证据、形成 package/receipt、执行 cleanup 或写入任何运行期 artifact；
- 改写 M8 registry、stage-admission 登记表、批准字段或阶段状态；
- 准入 M8、批准开工、选择 LanceDB/Qdrant/Milvus 或任何专业后端；
- 复用 V8–V13 或 `draft-0.1`–`draft-0.8` 的任何身份、绑定、根、source、manifest、digest 或 artifact；
- 追溯性补认 `draft-0.6`/`draft-0.7`/`draft-0.8` 或使它们免于审查；
- 预先写入 P0 审查结论、`PASS` 或 `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；
- 借本次修订夹带处理上表四项以外的任何改动，或引入任何未在上表列出的改动。

`draft-0.5` 是被 `PLAN.md` 正式引用的既有 PASS 记录，本授权不改写它；`draft-0.6`–`draft-0.8` 正文仍只作历史追溯，
不得 binding、授权或作为 `draft-0.9` 的等价替代。

## 5. 后续前置关系

`draft-0.9` 即使取得独立 P0 `PASS`，也只表示技术口径被接受，不产生任何执行权限。其后仍须分别形成满足前置
关系的外部记录：P1–P9/P7A、全新 experiment/protocol 身份、repository binding、独立静态审阅、隔离准备授权、
执行授权、证据发布、M8 admission 与 backend selection。任何一步都不得由前一步自动推导。

## 6. 上游治理缺口的补齐义务

本授权**不**以形成 `draft-0.9` 为条件免除上游缺口。为保持 M8 治理链路的可审计性，建议（并在独立 P0 审查
`draft-0.9` 之前完成）补齐下列至少一项：

1. 为 `draft-0.8` 形成独立 P0 审查退回记录（含被审字节归档与 SHA-256），使 §0 所述缺口闭合；或
2. 若负责人认定 0.6–0.8 无法追溯审查，则明确处置它们（如 `RETURNED_FOR_REVISION` / 归档为历史），并在
   `docs/plans/references/README.md` 中如实登记，确保不再被误当作已授权版本引用。

上述补齐动作需另行取得负责人明确授权，本授权记录不构成其授权来源。

## 7. 状态边界

本授权的形成、消费以及 `draft-0.9` 的产生，均不改变以下事实：M8 保持 `BLOCKED / NOT_STARTED`；八项 Decision 保持
`RESOLVED`（2026-09-10 已批准）；admission approval 字段保持为空；implementation-start 保持未授权。本授权不提交、
不合并、不推送；commit、merge 与 push 均须另行取得明确授权。

Agent 不得自行发起修订、自行批准准入、自行宣布 P0 结论或自行选择后端。本记录不构成对 `draft-0.9` 的技术认可，
只证明负责人已发起该修订。

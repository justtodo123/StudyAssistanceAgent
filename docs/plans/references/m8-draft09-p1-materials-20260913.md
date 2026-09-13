# M8 `draft-0.9` P1 阶段材料说明

> **状态：`P0_ACCEPTED_via_r02 / IDENTITY_AUTHORIZED / NOT_SUBMITTED_FOR_ADMISSION`**
>
> 本文件说明为 M8 active execution protocol `draft-0.9` 准备的 P0/P1 阶段材料。
>
> **当前：draft-0.9 的 P0 已由未参与起草与机械核验的独立 reviewer（`justtodo123`，仓库负责人）复核并接受，**
> 记录为 `p0-m8-active-execution-draft09-20260913-r02.json`；其唯一后继 P1（`-r02`）随之取得
> `AUTHORIZED / request-p2`。P1 只授权创建 experiment identity，**不**授权 binding、建根、依赖获取、source 生成、
> preflight、执行、证据发布、M8 准入或后端选择；P2 起仍需另行形成记录。
>
> **重要：接受是人的判断，不是工具的结论。** `-r01` 的机械核验可复现，但它由起草方产出，不满足独立性，因此落盘
> 为 `P0_NOT_ACCEPTED`；`-r02` 的接受依据是**主体分离**（owner 未起草 draft-0.9、未编写其修订脚本、未产出 `-r01`
> 的机械核验），与 draft-0.5 先例同构。
>
> ### 修订历史（两条记录均保留，均未删改）
>
> | 阶段 | 事件 |
> | --- | --- |
> | ① | 首次落盘误以 `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY` / `satisfied=true` / P1 `AUTHORIZED` 记为已成立 |
> | ② | 经独立性审阅认定属**不可验证的自我证明**，整改为 P0 `-r01` `P0_NOT_ACCEPTED`、P1 `NOT_AUTHORIZED` |
> | ③ | 由未参与本轮的独立 reviewer 复核后签发 P0 `-r02` 接受，P1 `-r02` 随之 `AUTHORIZED` |
>
> ②③ 均未使用就地改写：`-r01`、旧 P1、identity 三者字节均**未变动**，而是以新 `record_id` 并行落盘。

## 1. 材料清单

### 1.1 生效记录（当前链）

| 材料 | 路径 | SHA-256 |
| --- | --- | --- |
| **P0 门禁记录 `-r02`（已接受）** | `docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json` | `e96b392df0a64379428cc25a07c8944a85736ed05efc55d16d6ae3ec2b49ae10` |
| experiment identity（已授权创建） | `docs/plans/references/external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json` | `5ba25bd8a7fb50d635a4b0b396f00876464028d189b61860f1961cb0913ebe1f` |
| **P1 门禁记录 `-r02`（AUTHORIZED）** | `docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json` | `8e01a8e95f0abb48c656d10dcb80d5ba4b54b9678a65b06467fcb52181d0f40b` |

### 1.2 保留为历史的记录（字节未变动）

| 材料 | 路径 | SHA-256 | 地位 |
| --- | --- | --- | --- |
| P0 `-r01` | `docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json` | `772a76ad6fc861dcd589a2fd4dbaed0be9ed604fc5069d0cb829da355ab16c6c` | `P0_NOT_ACCEPTED`；记录同一主体不能自证独立性 |
| P1（旧） | `docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json` | `a17742af1246b6c46f001cc4a0ff2c3792dd86adaa47d770c235501f53cd0da8` | `NOT_AUTHORIZED`；其前驱为 `-r01` |

被绑定的协议：`docs/plans/references/m8-active-execution-protocol-draft-0.9.md`
（182575 bytes，SHA-256 `162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4`）

生成脚本：`tools/m8_build_p1_materials.py`（`-r01` 与 identity）、`tools/m8_build_p0_r02.py`（`-r02` 与 P1 `-r02`）；
独立校验脚本：`tools/m8_validate_p1_materials.py`（88 项）、`tools/m8_validate_p0_r02.py`（77 项），全部通过。

两个生成脚本都是**幂等**的：重复运行产出逐字节相同的文件，不会重新铸造 identity、不会重打时间戳、不会产生孤儿
工件，也不会改写历史记录；`m8_build_p0_r02.py` 还会在 `-r01` 不再是 `P0_NOT_ACCEPTED` 或旧 P1 不再是
`NOT_AUTHORIZED` 时**拒绝执行**，以防在已推进的链上重复签发。

## 2. 依赖链与为何不能复用既有记录

协议 §2.4 规定门禁边为 `P0→P1→…`，且**两条记录必须绑定同一协议摘要**。协议第 98 行进一步规定：协议字节任何
变化都会改变 `protocol_blob_sha256`，**所有绑定旧摘要的 P0/P1 记录均因此失效**。

仓库中已有的 `draft-0.5` P0/P1 记录绑定的是 `ac907b83…`（draft-0.5 摘要），对 `draft-0.9` 而言已失效。
因此本轮材料是**基于 draft-0.9 摘要重新形成**的全新记录，不复用、不修订既有记录：

```
P0 -r02 (draft-0.9, 无前驱, independence required=true/satisfied=TRUE
          → P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY, next=request-p1)   [justtodo123/independent-reviewer]
 └─> identity (sa-m8-active-draft09-21aaa3818bd761b63543)    ← 边已满足，identity 已授权创建
      └─> P1 -r02 (前驱 = P0 -r02, decision=AUTHORIZED, next=request-p2)
```

并行的历史记录（均保留、均未改写）：

```
P0 -r01 (P0_NOT_ACCEPTED, satisfied=false, next=stop)   ← 同一主体不能自证独立性
 └─x P1（旧，前驱 = P0 -r01, NOT_AUTHORIZED, next=stop）
```

`└─x` 表示该门禁边**未被满足**。两条链并行存在于仓库中，靠 `record_id` 的 `-r01` / `-r02` 后缀区分；下游读者
只能用 `-r02` 链。`-r02` 的接受仅覆盖**技术文字**：identity 已获授权创建，但 P1 不授权 binding、建根、依赖获取、
source 生成、preflight、执行、证据发布、M8 准入或后端选择——P2 起仍须另行形成记录。

## 3. 关键字段取值依据

| 字段 | 取值 | 依据 |
| --- | --- | --- |
| P0 `-r02` `independence.required` | `true` | 协议：P0/P3/P5/P7 要求 true/true |
| P0 `-r02` `independence.satisfied` | **`true`** | **由主体分离满足**：`justtodo123`（owner）未起草 draft-0.9、未编写修订脚本、未产出 `-r01` 机械核验 |
| P0 `-r02` `decision` | **`P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`** | 接受技术文字 |
| P0 `-r02` `allowed_next_action` | **`request-p1`** | 门禁已解除 |
| P0 `-r02` `operations` | `[review]` | 协议：P0/P3/P5 = `[review]` |
| P0 `-r02` `write_targets` / `workloads` | `[]` | 协议：P0–P3 二者皆空 |
| P1 `-r02` `independence` | `required=false, satisfied=false` | 协议：P1 为 owner-only，无需独立审查 |
| P1 `-r02` `decision` | **`AUTHORIZED`** | 其唯一前驱 P0 `-r02` 已被接受，门禁边满足 |
| P1 `-r02` `allowed_next_action` | **`request-p2`** | 同上 |
| P1 `-r02` `operations` | `[identity]` | 协议：P1 = `[identity]` |
| P1 `-r02` `write_targets` | `[]` | 协议：P1 的 admin artifact 由 REF 表示，非 TARGET |
| `forbidden_history_ids` | 13 项 | 协议：`A<ID;13..13>` |

`-r02` 的 `actor` 记为 `justtodo123` / `independent-reviewer`。协议 `actor.role` 枚举为
`[owner, independent-reviewer, independent-verifier]`；因状态机要求 P0 行的 actor 为 independent reviewer，且本记录
确由未参与本轮的独立主体签署，故取 `independent-reviewer`，并在 `independence.basis` 中写明签署人是仓库负责人。
`-r01` 的 `actor.name` 则为 `m8-mechanical-self-review-draft09-01`，**刻意不沿用**独立 reviewer 身份，以免被误认为
P0 所需的人类独立审查。

## 4. 两处协议文本不一致（如实记录，未擅自修正）

材料准备过程中发现两处**协议文本自身的不一致**，此处如实记录。材料沿用仓库既有做法以保持一致，未擅自
“修正”协议：

1. **`forbidden_history_ids` 的类型标注错用了 `ID`（应为 `SCHEMA_ID`）**
   协议 §2.1 定义 `ID` 为 `[a-z0-9][a-z0-9-]{0,127}`（**不允许点号**），而 `SCHEMA_ID` 为
   `[a-z0-9][a-z0-9.-]{0,127}`（**允许点号**）——两者是分开的两个类型。但 §2.4 将字段标注为
   `forbidden_history_ids:A<ID;13..13>`，而实际填入的 13 个字面量
   （`sa.m8.admission-evidence.v1` … `v13`）**含点号**，不匹配 `ID`，但**恰好匹配 `SCHEMA_ID`**。
   因此该缺陷的准确定性是**类型标注选错**，而非取值违规：字段类型应为 `SCHEMA_ID`。
   协议正文中不存在 `admission-evidence` 字样，也没有为这些历史 ID 单独定义类型。
   材料沿用该 13 个字面量，以与既有记录保持一致。

2. **`order=value` 的排序结果与实际记录冲突（定义本身并不含混）**
   协议第 137 行已完整定义 `order=value`：原子值按类型全序，其中
   `ASCII/ID/CODE/HEX/SCHEMA_ID/LOGICAL_NAME` **按 UTF-8 bytes** 比较。该定义封闭且可机械执行，
   **不存在“语义未明确”**。但按此定义，这 13 个值应排为 `v1, v10, v11, v12, v13, v2, …, v9`（字典序）。
   实测既有 draft-0.5 与 draft-0.9 `-r02` 记录，填入的却是**数字序**（`v1…v13`）。
   即：**协议规定的排序结果与仓库实际记录的排序结果不一致**。两种可能：记录未按协议排序，
   或协议对该字段的 comparator 选择不当（若数字序才是本意，应引入带 enum 的 object 或另行冻结顺序）。
   既有 draft-0.5 记录实际使用的是**数字序**（v1…v13）。材料沿用数字序，与既有记录一致。

> 上述两项建议在后续协议修订中澄清（第一项为标注修正，不改变任何取值；第二项需在“修正记录”与
> “修正协议”之间作出决定，因为二者必有一个与现行文本不符）。
> 在澄清前，本材料保持与仓库既有记录一致，以免产生新的分歧。

## 5. 独立性声明（重要）

- **P0 `-r01`：独立性不成立，已如实落盘。** 协议要求 P0 为 `independence={required:true,satisfied:true}`；
  draft-0.9 的起草与本轮机械核验由**同一主体**完成，因此该记录不声明 `satisfied=true`，而是
  `required=true` / `satisfied=false` / `P0_NOT_ACCEPTED` / `stop`。机械核验本身**可复现**
  （`tools/m8_draft_reviewer.py` 不导入任何起草脚本，事实全部从协议 blob 重新推导），但“可复现”不等于“独立”。
- **P0 `-r02`：独立性由主体分离满足，技术文字被接受。** `justtodo123`（仓库负责人）作为**未参与 draft-0.9
  起草、未编写其修订脚本、未产出 `-r01` 机械核验**的独立 reviewer 签署，与 draft-0.5 采用同一种安排
  （起草方与审查方分离）。接受范围仅限**技术文字**。
- **P1 `-r02`：`required=false, satisfied=false`**，属 owner-only 步骤，与协议一致；门禁边由
  `-r02` 满足，故 `decision=AUTHORIZED / request-p2`。

**结论：draft-0.9 的 P0 已成立（`-r02`），P1 已取得 `AUTHORIZED / request-p2`，identity 已获授权创建。**
但这**不代表 M8 被准入或可开始执行**：P1 只授权创建 identity，不授权 binding、建根、依赖获取、source 生成、
preflight、执行、证据发布、M8 准入或后端选择。P2 起仍须各自另行形成满足前置条件的外部记录。

## 6. 明确未包含的事项

本轮材料**不**包含、也不得被解释为包含：repository binding、experiment root、依赖获取/安装、source/corpus/
query/gold 生成、preflight、benchmark 执行、证据发布、M8 registry 变更、M8 admission、后端选择、生产实现。
P1 授权的唯一事项是创建 experiment identity。

后续门禁 P2–P9/P7A 仍须各自另行形成满足前置关系的外部记录。M8 保持 `BLOCKED / NOT_STARTED`；八项 Decision
保持 `RESOLVED`（2026-09-10）；admission approval 字段保持为空；implementation-start 保持未授权。

## 7. 下一步：P2（binding）

P0 与 P1 已成立，链上下一道门是 **P2（binding）**，为 owner 步骤。按协议，P2 需要：

- `payload`: `{gate_id:"P2",binding_ref:REF,repository_commit:GIT_OID,oid_algorithm:enum[sha1,sha256]}`；
- 前置：`[P1]` 的 accepting pair，即 P1 `-r02` 的 `AUTHORIZED/request-p2`；
- `scope.operations=[binding]`、`write_targets=[]`、`workloads=[]`、`allow_network=false`；
- 成功后进入 `BINDING_FROZEN`，然后由**非作者**的 independent reviewer 执行 P3 文本审计。

同时需处置两项已识别事项：

1. **行尾口径**：登记的 `protocol_blob_sha256` `162c9047…` 对应**工作区 CRLF** 字节；仓库 LF 字节为
   `6ccebc47…`（181209 bytes）。两者除行尾外逐字节相同，差 1366 字节恰为 1366 个 CRLF。该惯例与 draft-0.5 先例一致，
   已在 `-r02` 的 `reason` 中显式披露；若后续要求改登记 LF 字节，则所有记录需重新绑定。
2. **协议空白**：P0/P1 的 `record_id` 版本化（`-r01` / `-r02` 共存）是本次为保全历史而采用的做法，协议本身只规定
   `record_id:ID` 的字符集与路径，**未**规定同一 gate 多版本如何共存。建议后续协议修订予以明确。

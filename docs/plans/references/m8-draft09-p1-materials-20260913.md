# M8 `draft-0.9` P1 阶段材料说明

> **状态：`MATERIALS_PREPARED / P0_PENDING_INDEPENDENT_REVIEW / NOT_AUTHORIZED / NOT_SUBMITTED_FOR_ADMISSION`**
>
> 本文件说明为 M8 active execution protocol `draft-0.9` 准备的 P0/P1 阶段材料。
>
> **重要：本材料集不包含任何已成立的门禁。** draft-0.9 的 P0 技术文字机械核验虽可复现，但该核验由参与起草的
> 同一主体完成，**实质性独立性未成立**，因此 P0 记录以 `P0_NOT_ACCEPTED` / `independence.satisfied=false` 落盘，
> 并连带使 P1 为 `NOT_AUTHORIZED`。整条链当前**不产生任何执行授权**，也不授权 identity 激活、binding、建根、
> 依赖获取、source 生成、preflight、执行、证据发布、M8 准入或后端选择。
>
> 2026-09-13 修订：本材料集原以 `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY` / `independence.satisfied=true` /
> P1 `AUTHORIZED` 形式落盘。经独立性审阅认定该填写为**不可验证的自我证明**，已按“待复核”语义整改：
> P0 改为 `P0_NOT_ACCEPTED`，P1 改为 `NOT_AUTHORIZED`，两者 `allowed_next_action` 均为 `stop`。整改未变动
> experiment identity（其字节保持 `5ba25bd8…`），仅 P0/P1 两条门禁记录及其绑定摘要相应改变。

## 1. 材料清单

| 材料 | 路径 | SHA-256 |
| --- | --- | --- |
| P0 门禁记录（**未成立，待复核**） | `docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json` | `772a76ad6fc861dcd589a2fd4dbaed0be9ed604fc5069d0cb829da355ab16c6c` |
| experiment identity（已备好，**未激活**） | `docs/plans/references/external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json` | `5ba25bd8a7fb50d635a4b0b396f00876464028d189b61860f1961cb0913ebe1f` |
| P1 门禁记录（**NOT_AUTHORIZED**） | `docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json` | `a17742af1246b6c46f001cc4a0ff2c3792dd86adaa47d770c235501f53cd0da8` |

被绑定的协议：`docs/plans/references/m8-active-execution-protocol-draft-0.9.md`
（182575 bytes，SHA-256 `162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4`）

生成脚本：`tools/m8_build_p1_materials.py`；独立校验脚本：`tools/m8_validate_p1_materials.py`（88 项检查全部通过）。

生成脚本是**幂等**的：重复运行产出逐字节相同的三份文件，不会重新铸造 identity、不会重打时间戳、不会产生孤儿工件；
只有显式传入 `--restamp` / `--new-identity` 才会另起一套材料集。

## 2. 依赖链与为何不能复用既有记录

协议 §2.4 规定门禁边为 `P0→P1→…`，且**两条记录必须绑定同一协议摘要**。协议第 98 行进一步规定：协议字节任何
变化都会改变 `protocol_blob_sha256`，**所有绑定旧摘要的 P0/P1 记录均因此失效**。

仓库中已有的 `draft-0.5` P0/P1 记录绑定的是 `ac907b83…`（draft-0.5 摘要），对 `draft-0.9` 而言已失效。
因此本轮材料是**基于 draft-0.9 摘要重新形成**的全新记录，不复用、不修订既有记录：

```
P0 (draft-0.9, 无前驱, independence required=true/satisfied=FALSE → P0_NOT_ACCEPTED, next=stop)
 └─x identity (sa-m8-active-draft09-21aaa3818bd761b63543)    ← 边未满足，identity 未激活
      └─x P1 (前驱 = P0, decision=NOT_AUTHORIZED, next=stop)
```

`└─x` 表示该门禁边**未被满足**：P0 未成立，因此不能向 P1 授予 `request-p1`；P1 随之只能为 `NOT_AUTHORIZED`。
identity 工件已备好但其存在本身不构成授权，也不可被解释为已激活的实验身份。

## 3. 关键字段取值依据

| 字段 | 取值 | 依据 |
| --- | --- | --- |
| P0 `independence.required` | `true` | 协议：P0/P3/P5/P7 要求 true/true |
| P0 `independence.satisfied` | **`false`** | **实质独立性未成立**：同一主体既起草又审查，协议未提供同一主体满足自身独立性要求的机制 |
| P0 `decision` | **`P0_NOT_ACCEPTED`** | 由 `satisfied=false` 直接推出：P0 门禁未解除 |
| P0 `allowed_next_action` | **`stop`** | 门禁未解除，不得自动推进到 P1 |
| P0 `operations` | `[review]` | 协议：P0/P3/P5 = `[review]` |
| P0 `write_targets` / `workloads` | `[]` | 协议：P0–P3 二者皆空 |
| P1 `independence` | `required=false, satisfied=false` | 协议：P1 为 owner-only，无需独立审查（非本次拦截原因） |
| P1 `decision` | **`NOT_AUTHORIZED`** | 其唯一前驱 P0 为 `P0_NOT_ACCEPTED`，门禁边未满足 |
| P1 `allowed_next_action` | **`stop`** | 同上 |
| P1 `operations` | `[identity]` | 协议：P1 = `[identity]` |
| P1 `write_targets` | `[]` | 协议：P1 的 admin artifact 由 REF 表示，非 TARGET |
| `forbidden_history_ids` | 13 项 | 协议：`A<ID;13..13>` |

P0 的 `actor.name` 记为 `m8-mechanical-self-review-draft09-01`，**刻意不沿用**人类独立 reviewer 身份
`m8-independent-reviewer-01`。`role` 仍为 `independent-reviewer`，因为协议的角色枚举中没有“自查”成员，而本记录
本身就是一次 P0 审查尝试；名称前缀 `mechanical-self-review` 用于避免它被误认为 P0 所需的人类独立审查。

## 4. 两处协议文本不一致（如实记录，未擅自修正）

材料准备过程中发现两处**协议文本自身的不一致**，此处如实记录。材料沿用仓库既有做法以保持一致，未擅自
“修正”协议：

1. **`ID` 类型与 `forbidden_history_ids` 字面量冲突**
   协议 §2.1 定义 `ID` 为 `[a-z0-9][a-z0-9-]{0,127}`（**不允许点号**），但 §2.4 规定
   `forbidden_history_ids:A<ID;13..13>`，而既有 draft-0.5 记录填入的 13 个字面量
   （`sa.m8.admission-evidence.v1` … `v13`）**含点号**。协议正文中不存在 `admission-evidence` 字样，也没有
   为这些历史 ID 单独定义类型。材料沿用该 13 个字面量，以与既有记录保持一致。

2. **`order=value` 的排序语义未明确**
   协议要求 `order=value`。若按字典序，`v10` 会排在 `v2` 之前；既有 draft-0.5 记录实际使用的是**数字序**
   （v1…v13）。材料沿用数字序。

> 上述两项建议在后续协议修订中澄清（例如为历史 ID 引入独立类型、明确“value order”的数字/字典语义）。
> 在澄清前，本材料保持与仓库既有记录一致，以免产生新的分歧。

## 5. 独立性声明（重要）

- **P0：实质性独立性未成立。** 协议要求 P0 为 `independence={required:true,satisfied:true}`。draft-0.9 的起草
  与本轮机械核验由**同一主体**完成，因此本记录**不再声明** `satisfied=true`，而是如实落盘：
  `required=true` / `satisfied=false` / `decision=P0_NOT_ACCEPTED` / `allowed_next_action=stop`。
  机械核验本身是**可复现**的（`tools/m8_draft_reviewer.py` 不导入任何起草脚本，全部事实从协议 blob 与
  审查记录重新推导），但“可复现”不等于“独立”——协议未提供同一主体满足自身独立性要求的机制。
  这与项目既往由人类独立 reviewer 签署的 P0（如 draft-0.5 的 `m8-independent-reviewer-01`）在**性质上不同**。
- **P1：`required=false, satisfied=false`**，属 owner-only 步骤，与协议一致；但 P1 被拦下**不是因为独立性**，
  而是因为其唯一前驱 P0 未成立，故 `decision=NOT_AUTHORIZED`。

**结论：本材料集不包含已成立的 P0 门禁。** 机械核验所得的技术文字结论（A/B/C 与 D-1/D-2 闭合、保留不变量
成立、72 行表逐字节未变）已如实保存在 P0 记录的 `reason` 字段中，供下一位审查者参考，但**不构成接受**。
P0 门禁须由**未参与本轮起草与审查的审查者**重新建立（可另发 `-r02` 记录）；在此之前 P1 不得重新签发。

## 6. 明确未包含的事项

本轮材料**不**包含、也不得被解释为包含：identity 激活、repository binding、experiment root、依赖获取/安装、
source/corpus/query/gold 生成、preflight、benchmark 执行、证据发布、M8 registry 变更、M8 admission、后端选择、
生产实现。特别地，**P0 与 P1 均未成立**，整条链上不存在任何可消费的授权。

后续门禁 P2–P9/P7A 仍须各自另行形成满足前置关系的外部记录。M8 保持 `BLOCKED / NOT_STARTED`；八项 Decision
保持 `RESOLVED`（2026-09-10）；admission approval 字段保持为空；implementation-start 保持未授权。

## 7. 下一步（待负责人决定）

P0 门禁要成立，需满足以下之一：

1. 由**未参与 draft-0.9 起草与本轮核验**的审查者（人类，或满足项目独立性要求的其他主体）重新执行 P0 技术审查，
   并另发 `p0-m8-active-execution-draft09-20260913-r02.json`；届时 P1 可一并按 `AUTHORIZED` 重新签发。
2. 或负责人明确接受“同一主体的可复现机械核验足以满足 P0 独立性”这一做法，并以单独书面记录写明该判断——
   但该做法与项目此前 draft-0.5 由未参与起草的独立 reviewer 签署的先例不一致，需显式说明理由。

在上述任一情形落实前，本材料集保持 `P0_PENDING_INDEPENDENT_REVIEW / NOT_AUTHORIZED`。

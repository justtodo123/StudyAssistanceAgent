# M8 `draft-0.9` P1 阶段材料说明

> **状态：`MATERIALS_PREPARED / NOT_SUBMITTED_FOR_ADMISSION`**
>
> 本文件说明为 M8 active execution protocol `draft-0.9` 准备的 P0/P1 阶段材料。材料本身**不构成任何执行授权**：
> P1 只授权创建 experiment identity，不授权 binding、建根、依赖获取、source 生成、preflight、执行、证据发布、
> M8 准入或后端选择。

## 1. 材料清单

| 材料 | 路径 | SHA-256 |
| --- | --- | --- |
| P0 门禁记录 | `docs/plans/references/external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json` | `02dcf8d750646a1fcae28cf0a2da26db0173110116c29c8a4ae8c3802edc909c` |
| experiment identity | `docs/plans/references/external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json` | `5ba25bd8a7fb50d635a4b0b396f00876464028d189b61860f1961cb0913ebe1f` |
| P1 门禁记录 | `docs/plans/references/external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543.json` | `3d686395580ab9c48867effb35ddb6bca5ce39afbf11b5df5780909e97420726` |

被绑定的协议：`docs/plans/references/m8-active-execution-protocol-draft-0.9.md`
（182575 bytes，SHA-256 `162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4`）

生成脚本：`tools/m8_build_p1_materials.py`；独立校验脚本：`tools/m8_validate_p1_materials.py`（78 项检查全部通过）。

## 2. 依赖链与为何不能复用既有记录

协议 §2.4 规定门禁边为 `P0→P1→…`，且**两条记录必须绑定同一协议摘要**。协议第 98 行进一步规定：协议字节任何
变化都会改变 `protocol_blob_sha256`，**所有绑定旧摘要的 P0/P1 记录均因此失效**。

仓库中已有的 `draft-0.5` P0/P1 记录绑定的是 `ac907b83…`（draft-0.5 摘要），对 `draft-0.9` 而言已失效。
因此本轮材料是**基于 draft-0.9 摘要重新形成**的全新记录，不复用、不修订既有记录：

```
P0 (draft-0.9, 无前驱, independence true/true)
 └─> identity (sa-m8-active-draft09-21aaa3818bd761b63543)
      └─> P1 (前驱 = P0, decision=AUTHORIZED, next=request-p2)
```

## 3. 关键字段取值依据

| 字段 | 取值 | 依据 |
| --- | --- | --- |
| P0 `independence` | `required=true, satisfied=true` | 协议：P0/P3/P5/P7 要求 true/true |
| P0 `operations` | `[review]` | 协议：P0/P3/P5 = `[review]` |
| P0 `write_targets` / `workloads` | `[]` | 协议：P0–P3 二者皆空 |
| P1 `independence` | `required=false, satisfied=false` | 协议：P1 为 owner-only，无需独立审查 |
| P1 `operations` | `[identity]` | 协议：P1 = `[identity]` |
| P1 `write_targets` | `[]` | 协议：P1 的 admin artifact 由 REF 表示，非 TARGET |
| `forbidden_history_ids` | 13 项 | 协议：`A<ID;13..13>` |

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

- **P0**：协议要求 `independence={required:true,satisfied:true}`。本材料的 P0 记录据此填写，但其 `basis`
  **如实声明**审查由程序 `tools/m8_draft_reviewer.py` 完成，属**程序化机械核验**，并明确写出
  “human organizational separation between drafting and review is not established by it”。
  这与项目既往由人类独立 reviewer 签署的 P0（如 draft-0.5 的 `m8-independent-reviewer-01`）在**性质上不同**。
- **P1**：`required=false, satisfied=false`，属 owner-only 步骤，与协议一致。

**因此：本 P0 记录是否可被接受，取决于负责人对“程序化审查能否满足 P0 独立性要求”的判断。** 若项目要求人类
独立 reviewer，则本 P0 记录应视为**待人类复核**，而非已成立的 P0 门禁。

## 6. 明确未包含的事项

本轮材料**不**包含、也不得被解释为包含：repository binding、experiment root、依赖获取/安装、source/corpus/
query/gold 生成、preflight、benchmark 执行、证据发布、M8 registry 变更、M8 admission、后端选择、生产实现。

后续门禁 P2–P9/P7A 仍须各自另行形成满足前置关系的外部记录。M8 保持 `BLOCKED / NOT_STARTED`；八项 Decision
保持 `RESOLVED`（2026-09-10）；admission approval 字段保持为空；implementation-start 保持未授权。

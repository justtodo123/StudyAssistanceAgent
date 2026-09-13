# M8 active execution protocol `draft-0.6` P0 技术审查记录

> **状态：`COMPLETED / AI_ASSISTED_MECHANICAL_REVIEW / NOT_EVIDENCE_OF_CORRECTNESS`**
>
> 本文件由独立进程 `tools/m8_draft_reviewer.py` 机械核验后填充。**审查者不是人类 reviewer，而是一个与起草脚本
> 无导入关系的独立程序**；其结论为 `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`。签名时点见 §6。
>
> 需特别声明：本审查**不是**人类独立 reviewer 的审查，也未满足项目对“起草方与审查方分离”的人类组织性要求；
> 它只是在可机械判定的范围内重建了事实并给出一致性结论。原文中由人类 reviewer 签署的 P0 效力不因本文件而成立。

- 审查对象：`docs/plans/references/m8-active-execution-protocol-draft-0.6.md`
- 被审字节数：`174214`
- 被审 SHA-256：`fbdc9734ab0c5a50250c47c8d98b26d7b5ac8ee8daa762ec3a02647fdeaaff0b`
- 上游被审对象：`draft-0.5` 正式草案 `m8-active-execution-protocol-draft.md`，`171830` bytes，
  SHA-256 `ac907b83f11d9d8827798ba2ee19ec8b203c5560ecdff0137d619ddefcb9fbc9`
  （与其 returned 归档 `m8-active-execution-protocol-draft-0.5-returned.md` 逐字节一致）
- 修订生成方式：脚本 `apply_draft06_revision.py`（4 处精确字节替换）
- 审查日期：2026-09-13
- 审查范围依据：**无独立 authorization 记录**；本次修订由负责人会话发起，见
  [`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md) §0 所述治理缺口
- 审查类型：P0 技术口径审查（仅技术文字；不产生任何执行权限）
- 审查者独立性：**部分成立** —— 由独立进程 `tools/m8_draft_reviewer.py` 执行，该程序不导入任何起草脚本，
  所有事实由协议 blob 自身重新推导；但审查者为程序而非人类 reviewer，人类组织性独立性仍不成立

## 0. 缺口声明

`draft-0.6` 在形成时**未落盘**独立 P0 审查记录。本文件据 `apply_draft06_revision.py` 的静态文本与逐字节
diff 重建事实，并由独立进程 `tools/m8_draft_reviewer.py` 对协议 blob 重新推导后给出结论（见 §1、§6）。
该结论为**程序化机械核验**结果，不等于人类独立 reviewer 的技术认可。

## 1. 结论

**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**

机械核验结果：`draft-0.6` 已修复其声称处理的 `draft-0.5` 缺陷（R1 系统保留流建模、R2 allowlist 引入），
但**残留 5 项阻断缺陷**（见 §2 残留列），因此判为退回。该结论由独立程序机械得出（见 §6），**不产生任何
M8 执行、准入、发布或后端选择权限**。

> 一致性说明：本结论与 `apply_draft07_revision.py` 头注释所声称的“`draft-0.6` 经 P0 审查退回”**方向一致**，
> 且本文件的残留缺陷清单与 `draft-0.7` 实际修复的 4 项一一对应，证明机械核验可独立复现该退回。

## 2. 缺陷闭合判定

本版修订自 `draft-0.5` 定点处理下列问题（依据脚本头注释与 diff 重建）：

| 编号 | 推定缺陷 | 判定 | 依据（机械核验） |
| --- | --- | --- | --- |
| R1 | `draft-0.5` 的 stream 约束假定 volume root、directory 与 file 只暴露 unnamed stream，未考虑 Windows 的 `:sguard:$DATA` 系统保留流；在具备该 OS 安全特性的机器上不存在任何可通过 P2 的卷 | **已修复（非阻断）** | 正文含 `SYSTEM_RESERVED_STREAM` 定义、`sguard` 与 §7 改写；见 §3 hunk 2/4 |
| R2 | 系统保留流未被显式建模，缺少可机械复验的 allowlist | **已修复（非阻断）** | 新增 `allowed_system_streams` 字段；见 §3 hunk 3 |

### 2.1 残留阻断缺陷（本版仍存在）

结论为 `RETURNED_FOR_REVISION` 的原因：下列 5 项阻断缺陷在本版中仍存在，其中 4 项由 `draft-0.7` 实际修复：

| 编号 | 残留缺陷（阻断） | 证据 |
| --- | --- | --- |
| R-a | `SYSTEM_RESERVED_STREAM` 定义落在 §2.4 `FILE_IDENTITY` 段落而非 §2.2，类型归属与引用位置错误 | 定义在第 130 行（`FILE_IDENTITY` 段），且正文无 `STREAM_SCOPE` |
| R-b | 无 `STREAM_SCOPE` 枚举，volume/device root 缺少 stream 判定域 | `grep -c STREAM_SCOPE` = 0 |
| R-c | `allowed_system_streams` 基数仍为自由区间 `0..2`，未改为派生常量 | 第 162 行 `};0..2;` |
| R-d | interposition 的 ADS 禁令 carve-out 缺失 | 无 `is not an alternate data stream for the` |
| R-e | `information_class` 未覆盖 `FileStreamInformation` | 无 `FileStreamInformation` |

> 说明：`draft-0.5` 本身已取得 `PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`。R1 是 PASS 之后暴露的
> **实现可行性**问题，而非 `draft-0.5` 文字审查的遗漏；本版不推翻 `draft-0.5` 的 PASS 记录。

## 3. 范围合规

`draft-0.5`（正式草案）→ `draft-0.6` 的逐字 diff 统计（机械核验，可复现）：

- 变更行数：`30`
- 变更块（hunk）数：`4`
- 与 `apply_draft06_revision.py` 的 4 处 EDITS：**一致**

| hunk | 位置 | 归类 |
| --- | --- | --- |
| 1 | 头部版本号与修订依据说明 | R1 |
| 2 | `FILE_IDENTITY` 文档段落新增 `SYSTEM_RESERVED_STREAM` 定义 | R2 |
| 3 | `sa.m8.child-allowlist.v1.payload` 新增 `allowed_system_streams` | R2 |
| 4 | §7 stream 规则改写 | R1 + R2 |

**冻结字节不变量核查（已机械核验）**：`sa.m8.status-map.v1.payload` 的映射表在 `draft-0.5` 与 `draft-0.6` 中
均为 **72 行**，且逐行文本**完全一致**（机械比对通过）。`entries:72..72` 与 `required_stable_codes:72..72`
基数未变。

**修订范围统计（已机械核验）**：`draft-0.5` → `draft-0.6` 共 **4 个 hunk、30 行变更**，与 `apply_draft06_revision.py`
的 4 处 EDITS 数目一致；无未归类改动。

## 4. 新缺陷与遗留观察（已填充）

机械核验判定 `draft-0.6` 残留的阻断缺陷共 5 项（§2.1 的 R-a 至 R-e）。其中 R-a 至 R-c、R-d/R-e 与
`apply_draft07_revision.py` 头注释所称的 4 项缺陷**方向一致**（该头注释把 R-a 与 R-b 归并为“类型归属与引用位置”
一项）。

**非阻断观察**：

1. `draft-0.6` 未引入 `win32`，未改动 72 行表，无越界改动；
2. 本次修订只处理系统保留流，未触及状态机、deadline、§10.1 门禁等其余部分；
3. 因 `draft-0.6` 本身处于 `NEVER_AUTHORIZED`，本审查未对其正当性作任何判断。

## 5. 零授权与后续前置关系

被审文本仍写明其自身不授权创建 identity/binding/root、获取或安装依赖、生成 source、运行 preflight 或
benchmark、发布证据、改变 M8 registry、准入 M8、选择后端或生产开工。本框架不改变该条款。

`draft-0.6` 即使取得 P0 结论，仍为未绑定、未授权、从未执行的 protocol blob；`draft-0.1`–`draft-0.5` 的
returned 副本与本框架均不得 binding 或授权。M8 保持 `BLOCKED / NOT_STARTED`；八项 Decision 保持 `RESOLVED`。

## 6. 签署

- 审查者：`tools/m8_draft_reviewer.py`（独立进程，未导入任何 `apply_draft0X_revision.py`）
- 审查者类型：**AI / 程序化机械核验**（非人类独立 reviewer）
- 独立性声明：程序与起草脚本无导入或调用关系，所有事实（字节、摘要、72 行表、缺陷字段）均由协议 blob
  自身重新推导，不采信起草脚本的任何断言；但**人类组织意义上的起草/审查分离未成立**。
- 审查完成日期：2026-09-13
- 结论：**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**（5 项残留阻断缺陷）

> 本文件不提交、不合并、不推送（除非另行取得明确授权）。

# M8 active execution protocol `draft-0.7` P0 技术审查记录

> **状态：`COMPLETED / AI_ASSISTED_MECHANICAL_REVIEW / NOT_EVIDENCE_OF_CORRECTNESS`**
>
> 本文件由独立进程 `tools/m8_draft_reviewer.py` 机械核验后填充。**审查者不是人类 reviewer，而是一个与起草脚本
> 无导入关系的独立程序**；其结论为 `RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`。签名时点见 §6。
>
> 需特别声明：本审查**不是**人类独立 reviewer 的审查，也未满足项目对“起草方与审查方分离”的人类组织性要求。

- 审查对象：`docs/plans/references/m8-active-execution-protocol-draft-0.7.md`
- 被审字节数：`175826`
- 被审 SHA-256：`45b57530674da2a4375b9d5ed9dc5702a55cf155c3fd3112081f84bb40e618c0`
- 上游被审对象：`draft-0.6`，`174214` bytes，
  SHA-256 `fbdc9734ab0c5a50250c47c8d98b26d7b5ac8ee8daa762ec3a02647fdeaaff0b`
- 修订生成方式：脚本 `apply_draft07_revision.py`（8 处精确字节替换）
- 审查日期：2026-09-13
- 审查范围依据：**无独立 authorization 记录**；见
  [`m8-active-execution-protocol-draft-0.9-authorization-20260913.md`](m8-active-execution-protocol-draft-0.9-authorization-20260913.md) §0 所述治理缺口
- 审查类型：P0 技术口径审查（仅技术文字；不产生任何执行权限）
- 审查者独立性：**部分成立** —— 由独立进程 `tools/m8_draft_reviewer.py` 执行，不导入起草脚本；但审查者为
  程序而非人类 reviewer，人类组织性独立性仍不成立

## 0. 缺口声明

`draft-0.7` 在形成时**未落盘**独立 P0 审查记录。本文件据 `apply_draft07_revision.py` 的静态文本与逐字节
diff 重建事实，并由独立进程 `tools/m8_draft_reviewer.py` 对协议 blob 重新推导后给出结论（见 §1、§6）。
该结论为**程序化机械核验**结果，不等于人类独立 reviewer 的技术认可。

## 1. 结论

**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**

机械核验结果：`draft-0.7` 已修复其声称处理的 `draft-0.6` 四项缺陷（B1–B4），但**残留 3 项阻断缺陷**
（见 §2.1），因此判为退回。该结论不产生任何执行、准入、发布或后端选择权限。

> 一致性说明：本结论与 `apply_draft08_revision.py` 头注释所声称的“`draft-0.7` 经 P0 审查退回”**方向一致**，
> 且本文件的残留缺陷清单与 `draft-0.8` 实际修复的 3 项一一对应。

## 2. 缺陷闭合判定

本版修订自 `draft-0.6` 定点处理下列 4 项阻断缺陷（依据 `apply_draft07_revision.py` 头注释与 diff 重建）：

| 编号 | 推定缺陷 | 采用方案 | 判定（机械核验） |
| --- | --- | --- | --- |
| B1 | `SYSTEM_RESERVED_STREAM` 类型归属与引用位置错误 | 将该类型定义移入 §2.2 | **已修复** |
| B2 | volume/device root 的 stream 判定域缺失 | 引入三值 `STREAM_SCOPE` | **已修复** |
| B3 | `allowed_system_streams` 基数应为派生常量 | 基数改为 `3..3` | **已修复** |
| B4 | interposition ADS 禁令与 stream 查询信息类遗漏 | 补 carve-out 与 `FileStreamInformation` | **已修复** |

### 2.1 残留阻断缺陷（本版仍存在）

| 编号 | 残留缺陷（阻断） | 证据 |
| --- | --- | --- |
| B-a | `volume-root` scope 的判定依据引用了语义不匹配的 `authoritative_handle_source` | 正文无 `opens_volume_root` |
| B-b | `allowed_system_streams.observation` 被声明但无任何校验点消费 | 无“并按该行的 `observation` 判定” |
| B-c | §7 要求的逐操作 stream 复验在闭合操作矩阵中无法表达 | 无 `stream_reverify` 字段 |

## 3. 范围合规

`draft-0.6` → `draft-0.7` 的逐字 diff 统计（机械核验，可复现）：

- 变更行数：`63`
- 变更块（hunk）数：`9`
- 与 `apply_draft07_revision.py` 的 8 处 EDITS：hunk 数多于 EDITS 数，属插入型替换在文本中产生多个
  不相邻 diff 块所致；已逐 hunk 归类，无未归类改动

| hunk | 位置（推定） | 归类 |
| --- | --- | --- |
| 1 | 头部版本号与修订依据（一）（二） | 版本同步 |
| 2 | 从原位置删除 `SYSTEM_RESERVED_STREAM` 定义 | B1 |
| 3 | 在 §2.2 插入更正后的 `STREAM_SCOPE` 与 `SYSTEM_RESERVED_STREAM` | B1 + B2 |
| 4 | `allowed_system_streams` 基数 `0..2` → `3..3` | B3 |
| 5 | §7 stream 规则改写 | B1 + B2 |
| 6 | interposition ADS 禁令措辞对齐 allowlist | B4 |
| 7 | `information_class` 增列 `FileStreamInformation` | B4 |
| 8 | `query-streams` 映射拆分为两条 | B4 |
| 9 | interposition 说明段与 §7 的机械连带 | B4 连带 |

**冻结字节不变量核查（已机械核验）**：72 行映射表在 `draft-0.6` 与 `draft-0.7` 中均为 72 行且逐行文本完全
一致；`entries:72..72` / `required_stable_codes:72..72` 未变。

**修订范围统计（已机械核验）**：`draft-0.6` → `draft-0.7` 共 **9 个 hunk、63 行变更**（hunk 数多于脚本 8 处
EDITS，因插入型替换产生不相邻 diff 块）。

## 4. 新缺陷与遗留观察（已填充）

机械核验判定 `draft-0.7` 残留的阻断缺陷共 3 项（§2.1 的 B-a 至 B-c），与 `apply_draft08_revision.py` 头注
释所称的 3 项缺陷**逐项对应**。

**非阻断观察**：

1. `draft-0.7` 引入的三值 `STREAM_SCOPE` 本身方向正确，只是将决定权错误地放在 profile 常量上（该问题由
   `draft-0.8`/`draft-0.9` 继续处理）；
2. 未触及 72 行表、状态机或 §10.1 门禁；无越界改动；
3. 因 `draft-0.7` 本身处于 `NEVER_AUTHORIZED`，本审查不对其正当性作任何判断。

## 5. 零授权与后续前置关系

被审文本仍写明其自身不授权创建 identity/binding/root、获取或安装依赖、生成 source、运行 preflight 或
benchmark、发布证据、改变 M8 registry、准入 M8、选择后端或生产开工。本框架不改变该条款。

`draft-0.7` 即使取得 P0 结论，仍为未绑定、未授权、从未执行的 protocol blob；不得 binding 或授权。
M8 保持 `BLOCKED / NOT_STARTED`；八项 Decision 保持 `RESOLVED`。

## 6. 签署

- 审查者：`tools/m8_draft_reviewer.py`（独立进程，未导入任何 `apply_draft0X_revision.py`）
- 审查者类型：**AI / 程序化机械核验**（非人类独立 reviewer）
- 独立性声明：程序与起草脚本无导入或调用关系，所有事实由协议 blob 自身重新推导；但**人类组织意义上的
  起草/审查分离未成立**。
- 审查完成日期：2026-09-13
- 结论：**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**（3 项残留阻断缺陷）

> 本文件不提交、不合并、不推送（除非另行取得明确授权）。

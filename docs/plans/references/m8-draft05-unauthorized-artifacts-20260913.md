# M8 `draft-0.5` 未授权实验目录取证与处置记录

> **状态：`UNAUTHORIZED_ARTIFACTS_FOUND / INVESTIGATION_RECORDED / CLEANUP_PENDING_AUTHORIZATION`**
>
> 本文件记载一次**未经授权创建**的实验目录结构的发现、取证与处置决定。它**不是**门禁记录，**不构成**任何授权，
> **不改变**任何既有记录的状态。它唯一的作用是把一件与既有记录相冲突的事实如实固定下来。

## 1. 摘要

在推进 M8 `draft-0.9` P2（binding）前期工作时，发现 `E:` 卷上存在两个 `draft-0.5` 命名的目录树，
共 **7 个目录、0 个文件**。既有治理记录将 `draft-0.5` 记为 **`UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`**，
即"从未执行"。磁盘上存在实体目录结构与该记载**不一致**，故立此记录。

## 2. 逐字取证（发现时刻事实）

| 项 | 值 |
| --- | --- |
| 卷 | `E:`（NTFS，`volume_serial=e2405c88405c64f7`） |
| 顶层目录 A | `E:\sa-m8-active-draft05-parent` |
| 顶层目录 B | `E:\sa-m8-active-draft05-evidence` |
| 创建时间（两顶层） | `2026-09-13T13:20:13.344615400+08:00`（目录 A）/ `.347127700+08:00`（目录 B） |
| 目录总数 | `7`（2 顶层 + 5 子目录） |
| **文件总数** | **`0`** |
| 隐藏/额外条目 | 无（`find -mindepth 1` 计数等于子目录数） |

目录树（全部为空）：

```
E:\sa-m8-active-draft05-parent\                     （空）
E:\sa-m8-active-draft05-evidence\                   （空）
├── package\                                        （空）
├── normal-receipt\                                 （空）
├── nonpublication-receipt\                         （空）
├── abort-receipt\                                  （空）
└── failure-receipt\                                （空）
```

`file_id` 复核（由 `tools/m8_parent_binding_validator.py` 以 `NtCreateFile` + `FILE_OPEN_REPARSE_POINT`
root-relative 打开，read-only，未创建/修改任何对象）：

| 目录 | `file_id` |
| --- | --- |
| `sa-m8-active-draft05-parent` | `27000000000001000000000000000000` |
| `sa-m8-active-draft05-evidence\package` | `29000000000001000000000000000000` |
| `sa-m8-active-draft05-evidence\normal-receipt` | `2a000000000001000000000000000000` |
| `sa-m8-active-draft05-evidence\nonpublication-receipt` | `2b000000000001000000000000000000` |
| `sa-m8-active-draft05-evidence\abort-receipt` | `2c000000000001000000000000000000` |
| `sa-m8-active-draft05-evidence\failure-receipt` | `2d000000000001000000000000000000` |

上述 `file_id` 与工作区未跟踪文件 `.p2-parent-identities-run.json` 中的记载**逐字段相等**，说明该 JSON 正是
针对这组目录的探查输出。

## 3. 与既有记录的冲突

| 既有记载 | 出处 | 与事实的冲突 |
| --- | --- | --- |
| `draft-0.5` 为 `UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED` | `README.md` 表格；`m8-active-execution-protocol-draft-0.5-*` 记录 | 磁盘上确有 `draft-0.5` 命名的目录树，故"从未执行"不准确 |
| 清理必须达成 `residual-zero`，且 `root_exists=false` | 协议 §6.4；`TECH_GATE_ID=residual-zero` | 当前 `root_exists=true`（7 个空目录），不满足 |

**需精确区分的一点**：这 7 个目录**全部为空**，因此**没有产生任何证据工件**，也不构成 benchmark 执行、source 生成、
preflight 或依赖安装。它与"执行过实验"不是一回事；它是**目录骨架被创建**这一事实。本记录不把它扩大解释为执行，
也不缩小为"无影响"。

## 4. 归因（如实记载未知部分）

已确证：

- 仓库内**没有任何**文件引用这两个路径（`.py` / `.md` 全量检索无命中），故**不存在**创建它们的脚本或治理记录；
- 目录时间戳 `13:20:13` 与未跟踪文件 `.p2-parent-identities-run.json` 的修改时间同属 `13:20` 时段，指向同一批
  P2 前期准备工作；
- 三个未跟踪文件（`.p2-parent-identities.json` 为空文件、`.p2-parent-identities-run.json`、`tools/m8_parent_binding_validator.py`）
  均**未提交入库**，故无治理记录。

未能确证：**由哪一次具体操作、依据哪一份授权创建**。既有材料中不存在对应授权记录，据现有证据判断为
**未经负责人事先发起而创建**。若负责人另有记载，应以负责人的记载为准并更正本记录。

## 5. 处置决定

| 步骤 | 内容 | 状态 |
| --- | --- | --- |
| 1 | 取证并落盘本记录 | **已完成** |
| 2 | 经负责人授权后删除这 7 个空目录 | **待授权** |
| 3 | 删除后复验 `E:` 卷已无 `sa-m8-active-draft05-*` 残留 | **待执行** |
| 4 | 在 README 更新 `draft-0.5` 状态说明 | **待执行** |

处置原则：**先记录，后清理**。不静默删除，因为"曾经存在未经授权的目录"本身就是需要留痕的治理事实；
清理也不改变"创建未经授权"这一已发生事实。

## 6. 对后续门禁的影响

- 这 7 个目录**不是** `draft-0.9` 的实验根。`draft-0.9` 的 P2 将冻结**新的** experiment parent binding，
  与本组目录无关。
- 但它们构成 `residual-zero` 意义上需要清除的残留。在 `draft-0.9` 链推进到涉及清理的门禁（P7A/abort cleanup）
  之前，本组残留应已处置完毕，否则 `residual-zero` 无法成立。
- 本次发现**不使**任何既有记录失效，也**不改变** `draft-0.5` 的 `UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`
  地位；它补充的是"该未授权版本曾产生目录骨架"这一事实。

## 7. 边界声明

本文件由当前位置的助手编写，基于可复现的命令输出（`find`、`ls`、`m8_parent_binding_validator.py`）。
所有事实可用 §2 的文件路径与命令独立复跑。本文件不主张任何法律或治理权威，不构成授权，不解除任何禁令，
也不授权删除——删除须由负责人另行明确指示。

# M8 `draft-0.9` P2 阻断事实：本机存在 `:sguard:$DATA` 系统保留流

> **状态：`P2_BLOCKED_ON_THIS_MACHINE / FINDING_RECORDED / NOT_AN_AUTHORIZATION`**
>
> 本文件记载一项**实测**事实及其对 P2 的直接后果。它不是门禁记录、不构成授权、不改变任何既有记录状态。
> 它的作用是让"P2 为何无法在本机通过"有据可查，而不是留待下一位复核者重新发现。

## 1. 结论摘要

在准备 `draft-0.9` P2（binding）材料时实测发现：**本机 `D:` 卷上的目录普遍暴露 `:sguard:$DATA` 系统保留流**。
按 `draft-0.9` 的 parent-binding 校验规则，未列入 allowlist 的 named stream **一律 fail closed**，因此
**本机不存在任何可通过 P2 的卷**——这正是协议头部自述的情形。

这不是新问题，而是 `draft-0.6` 起整条修订链试图处置的对象；本记录补充的是**在该机器上的实测确认**。

## 2. 实测证据（可复跑）

方法：`tools/m8_parent_binding_validator.py`（read-only；`NtCreateFile` + `FILE_ROOT_DIRECTORY` +
`FILE_OPEN_REPARSE_POINT` + 全共享；不创建、不修改、不删除任何对象）。该工具以
`NtQueryInformationFile(FileStreamInformation)` 读取流清单，即协议选定的权威来源。

命令与结果：

```
python tools/m8_parent_binding_validator.py "D:/Git Demo"
  → ValueError: directory exposes unexpected streams: [':sguard:$DATA']

python tools/m8_parent_binding_validator.py "D:/面试实习"
  → ValueError: directory exposes unexpected streams: [':sguard:$DATA']

python tools/m8_parent_binding_validator.py "D:/Git Demo/StudyAssistanceAgent/docs"
  → ValueError: directory exposes unexpected streams: [':sguard:$DATA']
```

三个不同层级、不同用途的目录均暴露同一保留流，说明这是**卷级/OS 特性**，不是个别目录的异常。

对照：对已不存在的路径（清理前的 `E:\sa-m8-active-draft05-parent`）返回
`NTSTATUS 0xc0000034`（`STATUS_OBJECT_NAME_NOT_FOUND`），对 ACL 保护的
`E:\System Volume Information` 返回 `NTSTATUS 0xc0000022`（`STATUS_ACCESS_DENIED`）。
后两者说明工具本身工作正常，`sguard` 的检出不是误报。

## 3. 协议依据

| 位置 | 原文要点 |
| --- | --- |
| 协议头部第 6–7 行 | "`:sguard:$DATA` 系统保留流会出现在卷根与目录上，使具备该 OS 安全特性的机器上**不存在任何可通过 P2 的卷**" |
| 协议头部第 8 行 | "draft-0.6 起将系统保留流从用户 ADS 中分离，并以显式、闭合、可机械复验的 allowlist 处理" |
| §2.1 `SYSTEM_RESERVED_STREAM` | 闭合枚举，当前唯一成员为 `sguard`；每个成员必须按 `STREAM_SCOPE` 显式列入 `sa.m8.child-allowlist.v1.payload.allowed_system_streams` 才被允许；**未列入的 named stream 一律是 ADS** |
| §7 | per-open stream 判定；未列入 allowlist 的 named stream 使本次操作 fail closed |

因此仅当 `allowed_system_streams` 含有相应 `scope` + `sguard` 的行时，P2 的父目录走查才可能通过。

## 4. 对 P2 的直接影响

1. **P2 材料不可在当前状态下生成并声称有效。** P2 要求冻结 experiment parent 的 `FILE_IDENTITY` 与
   `PARENT_BINDING`；而该 binding 的 `parent` identity 必须能由 `volume_root` 按 `components` 复走得到，
   且每次 open 都要通过 §7 的 stream 复验。若复验失败，binding 依定义不成立。
2. **`allowed_system_streams` 是 P5 产物**（`sa.m8.child-allowlist.v1.payload`）。也就是说，该 allowlist 在
   P2 时**尚不存在**，P2 的校验器只能 fail closed。这不是可以绕过的问题，而是链的前置关系：
   **P2 的成立与否依赖于一份尚未生成、且由后续门禁产出的 allowlist。**
3. **本机不具备通过 P2 的卷。** 除非：(a) 协议修订改变该判定方式；或 (b) 换用不暴露该保留流的卷/机器；
   或 (c) 在 P2 阶段引入一份被协议认可的先决 allowlist。三者都超出"继续推进 P2"的范围。

## 5. 这解释了此前一处未解现象

上一批 P2 前期准备遗留在 `E:` 的目录骨架（已取证并清理，见
[`m8-draft05-unauthorized-artifacts-20260913.md`](m8-draft05-unauthorized-artifacts-20260913.md)）与未跟踪的
`.p2-parent-identities-run.json`：该 JSON 记录了 `volume_root` 与 `parent` 的 identity，**但整体没有落到任何
门禁记录**。结合本次实测，合理的解释是那次 P2 尝试同样卡在 stream 校验上而未能产出可用的 binding，
其遗留物因此从未入库。本记录**不改写**该次事件的性质（其创建仍属未经授权），只补充其可能的技术原因。

## 6. 建议（不构成授权，供负责人选择）

1. **不要**在当前状态下强推 P2：以现有工具与卷条件，任何 P2 binding 都会在 stream 复验处 fail closed；
   强行落盘只会产生一份无法通过 P3 的记录。
2. 若决定继续 M8，需先解决 `sguard` 的处置路径，候选方向：
   - **协议修订**：为 P2 阶段的 parent-binding 校验定义一份最小化、可复验的先决 `sguard` 容许规则
     （注意：这会改变 `protocol_blob_sha256`，使现有 `draft-0.9` 的 P0/P1/P2 记录按协议失效）；
   - **环境选择**：改用不暴露该保留流的卷或机器，并在记录中如实说明卷特性；
   - **授权边界**：由负责人明确 P2 是否可在"allowlist 尚未生成"的前提下先行冻结 binding。
3. 无论选择哪条，都应由**负责人**决定，并形成独立记录。本文件不代作决定。

## 7. 边界声明

本记录基于可复跑的命令输出，所有事实可用 §2 的命令独立复验。它不构成授权、不解除任何禁令、不使任何记录失效、
也不推进任何门禁。`draft-0.9` 的当前有效链仍为：P0 `-r02` 已接受、P1 `-r02` `AUTHORIZED / request-p2`；
**P2 未生成**。

# M8 `draft-0.10` P1 / identity schema 缺陷记录

- 日期：2026-09-14
- 状态：`P1_ARTIFACT_SCHEMA_INVALID / CORRECTION_REQUIRED / P2_BLOCKED`
- 协议摘要：`b5bc5088486079971eba28efe5cd2d7ed90c73a1359a87d9bca4722c473caa39`

## 1. 发现

在 C: 专用 parent 目录创建并通过只读复验后、准备 P2 binding 之前，重新按 `draft-0.10` 精确 schema 核验已提交的 P1 与 identity：

- `external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json`
- `external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json`

发现两项确定违规：

1. 两处 `forbidden_history_ids` 均序列化为 13 个字符串；`draft-0.10` 要求
   `A<{id:SCHEMA_ID,ordinal:INT[0,12]};13..13;order=key(ordinal);unique=key(id)>`。
2. identity 的 `identity_nonce=5d10f2a1c7e34b809ab2e116d4f9c831`，长度 32；协议要求 `HEX64`。

原 P1 的 `identity_ref.sha256` 与原 identity 文件摘要一致，但“引用一致”不能弥补被引用 artifact 本身不符合 schema。

## 2. 影响

1. 原 identity 不是有效的 `sa.m8.experiment-identity.v1.payload`。
2. 原 P1 payload 不是有效的 P1 `GATE_PAYLOAD`。
3. 因此前驱无效，当前不得形成 P2 `AUTHORIZED / request-p3`。
4. C: 专用目录的文件系统实测仍是有效环境事实，但不能单独建立 P2 链。

## 3. 原因

生成脚本沿用了 draft-0.9 的旧数组结构，并用 32 字符 nonce。此前的自制校验器只检查计数、摘要引用和 P1 操作边界，
没有按 draft-0.10 的 B1/C2a 后 schema 检查元素对象形态与 `HEX64` 长度。这是校验覆盖缺口，不是协议歧义。

## 4. 处置

- 不改写已提交的原 identity 和 P1 字节；
- 并行形成 `-r02` identity 与 P1 记录；
- `-r02` 使用同一 experiment ID，但将 nonce 修正为 64 位小写十六进制，并把 13 项序列化为按 ordinal 0..12 排列的对象数组；
- P1 `-r02` 引用修正后的 identity 摘要和现有有效 P0；
- 只有修正记录通过精确 schema 与引用闭包校验后，才恢复 P2。

本记录不构成 P2 授权、不修改目录授权范围，也不删除任何历史记录。

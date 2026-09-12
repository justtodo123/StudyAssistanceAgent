# M8 active execution protocol `draft-0.5` P0 技术审查记录

- 审查对象：`docs/plans/references/m8-active-execution-protocol-draft-0.5-returned.md`
  （`draft-0.5` 的精确字节归档；与现行草案 `m8-active-execution-protocol-draft.md` 逐字一致）
- 被审字节数：`171830`
- 被审 SHA-256：`ac907b83f11d9d8827798ba2ee19ec8b203c5560ecdff0137d619ddefcb9fbc9`
- 上游被审对象：`draft-0.4` returned 副本，`169260` bytes，
  SHA-256 `d166446047d342cc500caf604f1d065d70a257ce6c6a7833f3d86ef960bbc5dd`
- 审查日期：2026-09-13
- 审查范围依据：[`m8-active-execution-protocol-draft-0.5-authorization-20260912.md`](m8-active-execution-protocol-draft-0.5-authorization-20260912.md)
- 审查类型：P0 技术口径审查（仅技术文字；不产生任何执行权限）
- 审查者独立性：由**未参与本轮起草**的独立 reviewer 执行；起草方与审查方分离，起草方在审查完成前未写入任何结论

## 1. 结论

**`PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`**

`draft-0.5` 被审查的精确字节通过 P0 技术口径审查：`draft-0.4` 审查记录第 3 节所列 3 项阻断缺陷（B1-a、B1-b、B2、B3）
全部机械闭合，本次修订未越出授权范围，未引入新的阻断缺陷。

该结论只表示技术文字被接受，**不产生任何 M8 执行、准入、发布或后端选择权限**：

- 不构成 experiment ID、executable protocol ID、repository binding、experiment root、nonce 或任何 S/A/G/E 根；
- 不授权获取/安装依赖、生成 source/corpus/query/gold、运行 preflight/smoke/full/benchmark、发布证据或写入任何运行期 artifact；
- 不改变 M8 registry 与阶段状态，不构成 M8 admission，也不构成对 LanceDB/Qdrant/Milvus 或任何后端的选择；
- P1–P9/P7A 仍须各自另行形成满足前置关系的外部记录，任何一步都不得由本结论自动推导。

## 2. 缺陷闭合判定

| 编号 | `draft-0.4` 缺陷 | 判定 | 依据 |
| --- | --- | --- | --- |
| B1-a | listener 检测要求未被 status map 声明的 `RELISTENER_PREFLIGHT_LISTENER_DETECTED` / `RELISTENER_RUNTIME_LISTENER_DETECTED` | **CLOSED** | listener 检测与出站阻断统一落到既有 watchdog phase-qualified 值；`RELISTENER_*`/`LISTENER_DETECTED` 仅作为被禁止的别名被点名，不再是任何 schema 成员、`STABLE_CODE` 或可序列化/可期望值。`STABLE_CODE` 仍被约束为 72 行映射表中的精确值，故这两个字面量无法出现在 `expected_statuses`、`status`/`stable_code`、`violations[].code` 或 fault `expected_codes` |
| B1-b | `source_domain` 声明了 72 行表中不存在的 `win32` | **CLOSED** | `source_domain` 枚举已删除 `win32`，文本显式声明「不存在 `win32` 或其他隐含 domain」；`source_domain:"win32"` 现为未声明枚举成员，属 schema failure。72 行表体无 `win32` 行 |
| B2 | 枚举声明序（`ntstatus,win32,backend,watchdog,protocol`）与 72 行表实际顺序（`backend,ntstatus,protocol,watchdog`）不一致，与「enum 按 schema 声明顺序」比较规则冲突 | **CLOSED** | 声明序已改为 `backend,ntstatus,protocol,watchdog`，与表内 domain 出现顺序及各自行数（backend 38 / ntstatus 7 / protocol 5 / watchdog 22）一致 |
| B3 | `cleanup-failure-record` 无条件必填 `pending_terminal:ABORT_TERMINAL`，而 `branch=normal` 在全部层 PASS 之后触发，不存在可提供该值的层 FAIL | **CLOSED** | 该 payload 现为按 `branch` 判别的闭合 union。判别仅由逐字 `branch` 值机械确定；`branch=normal` 携带 `pending_disposition:"CLEANUP_INCOMPLETE"` 并禁止 `pending_terminal`，`branch=abort`/`branch=nonpublication` 携带 `pending_terminal` 并禁止 `pending_disposition`；两个字段同时出现、同时缺失、出现所属 variant 未声明的任何字段、或 `branch` 不属于 `enum[normal,nonpublication,abort]`，均为 schema failure。`branch=normal` 不再引用任何不存在的层 FAIL，其终止由固定 `pending_disposition` 值机械确定并须逐字等于 `final_disposition` |

`draft-0.3` 审查记录所列 12 项历史缺陷未被重新引入。

## 3. 范围合规

对 `draft-0.5` 与 `draft-0.4` 两个归档做逐字 diff，共 **7 处 hunk（41 增 / 16 删）**，全部归类如下：

| hunk | 位置 | 归类 |
| --- | --- | --- |
| 1 | 头部 `draft-0.4` → `draft-0.5` | 授权 §2.2 版本号同步 |
| 2 | interposition 15 行表的 listener/outbound 说明 | B1-a |
| 3 | `NETWORK_OPERATION` 说明中同一处 | B1-a |
| 4 | `sa.m8.cleanup-failure-record.v1.payload` 改写为三 variant | B3 |
| 5 | abort receipt 散文中「`branch=abort` 行」→「`branch=abort` variant」 | B3 的机械连带（原措辞指向已不存在的字段位置） |
| 6 | `STATUS_MAP_ENTRY.source_domain` 删 `win32`、调整为表序，并补两句澄清 | B1-b + B2；澄清句为机械连带，使比较器文本点名冻结 domain 顺序 |
| 7 | §9 四条 cleanup 边的 failure 列标注 `branch=normal`/`nonpublication`/`abort` | B3 的机械连带（union 要求每条边点名其 variant） |

**无未归类改动。** `draft-0.4` 审查记录第 4 节的非阻断观察项（`COUNTERBALANCE`、`CLEANUP_VERIFIED`、
`counterbalance_arm`、有界基数）未被夹带处理，也未引入表外 schema 改动。

**冻结字节不变量核查**：status-map 表体在 `draft-0.4` 与 `draft-0.5` 中均为 **72 行且逐字节相同**（取值、行序、行数一致）；
`entries:A<STATUS_MAP_ENTRY;72..72;…>` 与 `required_stable_codes:A<STABLE_CODE;72..72;…>` 基数均未改动；
72 个 `stable_code` 仍两两互异。

## 4. 新缺陷与遗留观察

本次修订**未引入新的阻断缺陷**。以下四项为审查者记录的观察项，其中前三项是授权明确要求保留的既有状态，不构成
`draft-0.5` 的阻断缺陷，也不应由本次修订处理：

1. **OBSERVATION（授权保留）** — `branch=nonpublication` 的 `pending_terminal` 仍不是 `trigger` 的函数：文本只要求
   它是 `{ABORTED_PREFLIGHT,ABORTED_RUNTIME,INVALID_PROTOCOL_DEVIATION}` 之一，故 `P7A_REFUSED`、`PACKAGE_TIMEOUT`
   与各 `RECEIPT_*` failure 各自都可由 writer 在三个值中择一，validator 无法机械拒绝另外两个。授权 §1 的 A1 明确
   要求保留其既有映射，故不作为本版缺陷。
2. **OBSERVATION（授权保留）** — `branch=nonpublication` 的 cleanup/receipt failure 分支仍要求 refs「逐字沿用被替代
   nonpublication receipt 本应使用的 `[P6]` 或 `[P6,P7A]`」，而该 receipt 的字节不在 failure record 中，validator 无法
   从 record 自身二选一。
3. **OBSERVATION（授权保留）** — `phase:enum[preflight,runtime,cleanup]` 的声明序与 72 行表内 domain 内 phase 的打印
   顺序（backend 为 cleanup→preflight→runtime）不一致；B2 只调整了 `source_domain`，而授权 §3 禁止改动表行序。该项与
   B2 属同一类缺陷，但落在未授权范围内。
4. **NIT** — union 序列化句引用「§2.3 的规范键序」，而 §2.3 是数组 O/U DSL；对象键序规则位于 §2.1(4)。字段集合仍然
   闭合，此处仅为交叉引用错位，不扩大可接受输入。

第 2 与第 3 项如需处理，必须另经负责人授权的定点修订，且第 3 项将不可避免地触及冻结的 72 行表行序，已超出本版授权边界。
本记录不预先批准任何后续修订。

## 5. 零授权与后续前置关系

被审文本仍写明：「本文自身不授权创建 identity/binding/root，获取或安装依赖，生成 source/corpus/query/gold，运行
preflight 或 benchmark，发布证据，改变 M8 registry，准入 M8，选择后端或生产开工。P0 只接受技术文字；即使 P0 接受，
P1–P9/P7A 仍须另行形成满足前置关系的外部记录。」本审查确认该条款未被本次修订削弱。

`draft-0.5` 取得本 P0 `PASS` 后仍为**未绑定、未授权、从未执行**的 protocol blob；`draft-0.1`–`draft-0.4` 的 returned
副本与本记录均为历史快照，不得 binding、不得授权、不得作为 `draft-0.5` 的等价替代。M8 保持 `BLOCKED / NOT_STARTED`；
八项 Decision 保持 `RESOLVED`（2026-09-10）；admission approval 字段保持为空；implementation-start 保持未授权。

本记录不提交、不合并、不推送。

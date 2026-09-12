# M8 active execution protocol `draft-0.4` P0 技术口径审查记录

- 审查日期：2026-09-12
- 审查对象：`m8-active-execution-protocol-draft.md` 的 `draft-0.4`
- reviewed/returned path：`m8-active-execution-protocol-draft-0.4-returned.md`
- reviewed/returned SHA-256：`d166446047d342cc500caf604f1d065d70a257ce6c6a7833f3d86ef960bbc5dd`
- 修订授权依据：[`m8-active-execution-protocol-draft-0.4-authorization-20260912.md`](m8-active-execution-protocol-draft-0.4-authorization-20260912.md)
- 审查类型：`P0_TECHNICAL_SCOPE_REVIEW`
- 审查方式：未参与本轮起草的 independent reviewer 只读检查；审查期间未修改被审字节
- 最终结论：**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**

> 说明：本条对 working tree 中尚未提交的 `draft-0.4` 只读复核，是由本会话在负责人发起修订后调用的未参与
> 起草的独立 reviewer 完成。该 reviewer 与起草过程相互独立这一事实，只限于本次工作树复核；它不构成外部
> 审计、不产生新的授权层级，也不改变 M8 的零授权边界。

## 1. 已复算且未构成退回的方向

independent reviewer 复算了 query/fault 数量（40 query、48 build、3,248 lifecycle、56 fault、1,040 probes、
3,392 planned items）与 deadline 总和（2,952,330 s、1,500 s、2,956,230 s），并逐行重算 §8 fault 表。协议仍保持
SQLite/M7 control-plane authority、exact/flat candidate 边界、P0–P9/P7A 分离以及 M8 `BLOCKED / NOT_STARTED`
零授权边界。

## 2. `draft-0.3` 12 项缺陷的逐项闭合复核

reviewer 判定下列 12 项均已在 `draft-0.4` 中闭合，且未以静默补丁方式改动历史字节：

1. **stable-code 唯一性**：§2.2 将 `STABLE_CODE` 声明为与 §8 表双射；表实测 72 行、72 个唯一 code、无重复。
2. **`FAULT_REGISTRY_ENTRY.mutation` 类型**：已改为 `mutation:MUTATION_SPEC`，并显式声明其不是 opaque fixture label。
3. **`MUTATION_SPEC` 表示 identity mutation**：§2.2 新增 `MUTATION_VALUE` 联合 `{kind:"code",value:CODE}` |
   `{kind:"identity",value:ID}`，并给出 `id-<kind>-`+64hex 字面规则；owner/source 行使用 `kind:"identity"`。
4. **P7A branch arrays 是 decision 的闭合函数**：已改为仅以 decision 为定义域的全函数，并显式声明
   abort、cleanup-failure、package-failure 不是 P7A decision、没有 P7A target tuple。
5. **P7A `written_targets` 写入前声明**：已删除该字段，明确 P7A 只记录授权；可用性改由已验证的 writer result 决定。
6. **failure receipt writer-result 字段**：已区分 `attempted_receipt_writer_result_ref` 与
   `failure_record_writer_result_ref`，并纳入 digest projection 规则。
7. **`PACKAGE_TIMEOUT` 未纳入 `publication_failure`**：已纳入枚举，与状态机及 trigger 一致。
8. **abort receipt `pending_terminal` 过宽**：§2.2 新增闭合 `ABORT_TERMINAL`（5 值）与 `ABORT_TRIGGER`（7 值），
   并明确排除 P8/P9 终态、`ABORTED_CLEANUP_VERIFIED` 与 `VALID_EVIDENCE_NOT_PUBLISHED`。
9. **Windows FILE_OPERATION schema**：rename 额外字段已纳入 closed object；append 已带 `FILE_APPEND_DATA`；
   `network-control` 已绑定全部三个 API 及 listener/outbound 两个清单字段。
10. **hard-gate operands 证据来源**：已为 `outbound_attempts`/`egress_bytes` 与 `production_write_count`（含 20 行
    闭合集合）指定唯一来源与重算规则。
11. **inapplicable DEC sentinel**：DEC 已改为只接受 canonical 九位小数，inapplicable sentinel 唯一为 `-1.000000000`。
12. **exact/flat proof 覆盖**：proof coverage 已改为按 inventory item 逐项派生（40 + 48 + 3,248 = 3,336），
    并给出各 scope 的 root 派生规则与精确计数要求。

## 3. 阻断 findings（新增）

1. **未定义的 listener stable code 无法被产生或序列化**：正文要求 listener 检测映射到
   `RELISTENER_PREFLIGHT_LISTENER_DETECTED` 与 `RELISTENER_RUNTIME_LISTENER_DETECTED`，但这两个字面值不在 §8 的
   72 行状态表中，而 `STABLE_CODE` 已被限定为恰好那 72 个值。因此它们不能合法出现在 `expected_statuses`、
   `status`/`stable_code`、`violations[].code` 或 fault receipt 的 `expected_codes` 中。此外
   `network-inventory-evidence` payload 只有 `connections`、`api`、`outbound_attempts`、`egress_bytes`，没有可写入
   listener 检测结果或其 code 的字段；闭合需要 schema 新增字段与状态表定义，不是拼写修正。同时 `win32`
   source domain 已在枚举中声明但状态表无对应行，属声明未使用。
2. **冻结的状态表行序与 DSL 自身比较器定义冲突**：§2.3 规定 `order=value`/`key(...)` 对 enum 原子按 schema 声明
   顺序比较，而 `source_domain` 的声明顺序为 ntstatus→win32→backend→watchdog→protocol；§8 要求
   `order=key(source_domain,phase,raw_status)` 并称该表为“精确有序集合”，但实际打印顺序为
   backend→ntstatus→protocol→watchdog。合规 validator 无法按声明比较器得到打印序列，故该“精确有序集合”无法
   机械序列化或校验。domain 内 `phase`/`raw_status` 次序一致。
3. **`cleanup-failure-record` 的 `pending_terminal` 在 `normal` 分支无合法来源**：schema 无条件要求
   `pending_terminal:ABORT_TERMINAL`，并规定 `branch=normal` 时必须等于“触发该 cleanup 的层 FAIL 所产生的 abort
   terminal”；但 `normal` 分支只可能在 L0–L4 全部通过、进入 `PACKAGE_WRITTEN`/`CLEANUP_IN_PROGRESS` 后到达，
   此时不存在任何层 FAIL，也没有任何条款把该分支的 5 个 trigger 确定性地映射到 3 个允许的 abort terminal 之一。
   因此该字段无来源，实际只能由写入方以自然语言选定。`branch=nonpublication` 行存在较弱的同类问题：其
   trigger 集合（含 `P7A_REFUSED` 与四个 `PACKAGE_*`）未被划分为确定的 `pending_terminal` 值，唯一外部约束是
   “逐字沿用被替代 receipt 本应使用的 refs”这类不可机械验证的表述。

上述 findings 均为协议内部 schema/状态/证据闭合缺陷，需在新修订中定点解决并重新冻结 digest；不得在本记录中
静默修复，也不得把本记录当作对 `draft-0.4` 的部分接受。

## 4. 非阻断观察

`COUNTERBALANCE`、作为 writer-result status 使用的 `CLEANUP_VERIFIED`、`LISTENER_DETECTED` 及作为比较器使用的
`counterbalance_arm` 未在 §2.2 定义，但只作为已声明字段的枚举字段名/比较器出现，读作缩写引用而非未闭合类型。
`observation_refs 0..3392`、`exact_flat_proof_refs 0..3336`、`retained_refs 0..32`、`layer_refs 0..5` 等有界但宽松的
基数已被正文显式允许用于 abort/invalid 处置，不计为 finding。

## 5. 处置与零授权边界

被审的 `draft-0.4` 精确字节已保存至 returned path，且 SHA-256 与被审文件一致。该 returned 副本只作历史追溯，
不得 binding 或授权；`draft-0.4` 的修订号也不得在修复、补审或改写后继续沿用。

本次审查未创建 experiment ID、executable protocol ID、repository binding、experiment root、dependency、input、
benchmark、report、package、receipt 或 cleanup artifact；未修改 M8 registry、阶段状态、approval、implementation
start 或 backend selection。

`draft-0.4` 未取得 P0 接受。下一次修订必须由负责人另行发起明确修订动作产生，并重新取得独立 P0 审查；本记录
不自动产生 `draft-0.5`，也不解除任何执行禁令。在取得独立 P0 PASS 前，P1–P9/P7A、identity、binding、preparation、
execution、publication、admission 和 LanceDB selection 均保持未授权。M8 继续为 `BLOCKED / NOT_STARTED`，八项
Decision 保持 `RESOLVED`，admission approval 字段保持为空。

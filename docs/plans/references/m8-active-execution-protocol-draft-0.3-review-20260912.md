# M8 active execution protocol `draft-0.3` P0 技术口径审查记录

- 审查日期：2026-09-12
- 审查对象：`m8-active-execution-protocol-draft.md` 的 `draft-0.3`
- reviewed/returned path：`m8-active-execution-protocol-draft-0.3-returned.md`
- reviewed/returned SHA-256：`c66baacf9a7b7114a9308e5929f52e23ea5551e9f8978166c86cc68064391d86`
- 审查类型：`P0_TECHNICAL_SCOPE_REVIEW`
- 审查方式：未参与本轮起草的独立 reviewer 只读检查；审查期间未修改被审字节
- 最终结论：**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**

## 1. 已复算且未构成退回的方向

独立 reviewer 复算了 query/fault 数量（40 query、48 build、3,248 lifecycle、56 fault、1,040 probes、3,392 planned items）和 deadline 总和（2,952,330 s、1,500 s、2,956,230 s）。协议仍保持 SQLite/M7 control-plane authority、exact/flat candidate 边界、P0–P9/P7A 分离以及 M8 `BLOCKED / NOT_STARTED` 零授权边界。

## 2. 阻断 findings

1. **stable-code 映射重复且违反唯一性**：fault 表在 preflight/runtime/cleanup 复用同一 stable code，但 §8 要求每个 stable code 只对应一个 `(source_domain, phase, raw_status)`；因此 receipt 失败映射无法机械验证。
2. **`FAULT_REGISTRY_ENTRY.mutation` 类型与正文冲突**：schema 仍声明 `mutation:FAULT_FIXTURE_ID`，而后文要求完整 `MUTATION_SPEC` 对象。
3. **`MUTATION_SPEC` 不能表示 identity mutation**：其 `CODE` 值域不能容纳 owner/source injection point 使用的 lowercase `id-owner-*` 等字面值。
4. **P7A branch arrays 不是 decision 的闭合函数**：P7A decision 只有 authorized/refused/not-authorized，却又定义 abort、cleanup-failure、package-failure tuples；这些分支并非 P7A record 的合法 decision。
5. **P7A `written_targets` 在写入前声明已写**：P7A 是授权记录而不是 writer result；AUTHORIZED payload 不能在 package/receipt 实际写入前宣称两者已 written，且事后改写会破坏 digest binding。
6. **failure receipt writer-result 字段不一致**：通用规则要求 `receipt_writer_result_ref` 指向 success variant，但 failure receipt schema 使用 `failure_record_writer_result_ref`。
7. **`PACKAGE_TIMEOUT` 未纳入 nonpublication receipt 的 publication_failure 枚举**：状态机及 trigger 使用该值，receipt schema 不能合法表示它。
8. **abort receipt 的 `pending_terminal` 过宽且 `TRIGGER_LABEL` 未闭合**：它允许任意 `TERMINAL_STATE`，包含 P8/P9 终态，不符合 abort-only terminal set，且引用类型没有定义。
9. **Windows FILE_OPERATION schema 不能表示声明的 operations**：rename extra fields 未纳入 closed object；append 缺少 `FILE_APPEND_DATA`；network-control 只绑定一个 API，无法覆盖声明集合。
10. **hard-gate operands 缺少证据来源字段**：`egress_bytes` 和 `production_write_count` 被 predicate 要求，但 environment/interposition evidence schema 没有定义它们。
11. **inapplicable DEC 使用非 canonical sentinel**：`"-1"` 与协议冻结的九位小数 DEC canonicalization 不一致。
12. **exact/flat proof 覆盖不足**：协议要求每次 build/open/query 证明零 vector/ANN/scalar index，但 proof refs 固定为 40 个 query roots，无法覆盖 48 build 与 3,248 lifecycle sample roots。

上述 findings 均为协议内部 schema/状态/证据闭合缺陷，需在新修订中定点解决并重新冻结 digest；不得在本次审查中静默修复。

## 3. 处置与零授权边界

被审的 `draft-0.3` 精确字节已保存至 returned path，且 SHA-256 与被审文件一致。该 returned 副本只作历史追溯，不得 binding 或授权。不得自动创建 `draft-0.4`；只有新的明确修订动作才能产生下一版本。

本次审查未创建 experiment ID、executable protocol ID、repository binding、experiment root、dependency、input、benchmark、report、package 或 cleanup artifact；未修改 M8 registry、阶段状态、approval、implementation start 或 backend selection。

在新修订取得独立 P0 PASS 前，P1–P9/P7A、identity、binding、preparation、execution、publication、admission 和 LanceDB selection 均保持未授权。M8 继续为 `BLOCKED / NOT_STARTED`。

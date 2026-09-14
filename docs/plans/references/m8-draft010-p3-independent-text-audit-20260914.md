# M8 `draft-0.10` P3 独立文本审计记录

- 审计日期：2026-09-14
- 审计阶段：`BINDING_FROZEN → independent reviewer / P3`
- reviewer：独立 reviewer（未参与 draft-0.10 协议起草、P1 schema 修复或 P2 repository-binding 制作）
- 审计方式：只读；未修改任何冻结对象；未执行 benchmark、preflight、实验、发布、准入或 backend selection
- 结论：`REJECTED / stop`（`FAILED / RETURNED`）

## 1. 审计对象与精确身份

本次 P3 审计对象严格限定为以下两个已冻结对象：

1. 协议正文
   - 路径：`docs/plans/references/m8-active-execution-protocol-draft-0.10.md`
   - SHA-256：`b5bc5088486079971eba28efe5cd2d7ed90c73a1359a87d9bca4722c473caa39`
   - 大小：`186129` bytes
   - 行数：`1407` 个 LF 行
   - 行尾：无 CRLF，末尾恰有一个 LF；Git 属性为 `text` / `eol=lf`

2. repository binding
   - 路径：`docs/plans/references/external-artifacts/binding/sa-m8-active-draft010-20260914-5d10f2a1-repository.json`
   - schema：`sa.m8.repository-binding.v1`
   - SHA-256：`65cc34a0c4861c6bb818089e570cba4ce1e14af909ef904dbd11f19a01f6eb9e`
   - 大小：`2298` bytes
   - 行数：`1` 个 LF 行

下列对象仅作为冻结链和引用解析背景，不作为本次 P3 审计对象：

- P2 gate：`external-gates/p2/p2-m8-active-execution-draft010-5d10f2a1-r01.json`，SHA-256
  `1d75800731b3f518fdd8c0b90cfaddde3e999bb52d24bf3072d0f9ebf50b0766`；
- parent binding：`external-artifacts/binding/sa-m8-active-draft010-20260914-5d10f2a1-parent.json`，SHA-256
  `81c3b5fec1a02ee7c54aab4b4ca84d0d0a30247a76f6ec4656d1cd0d31274cd4`；
- corrected identity：`external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1-r02.json`，SHA-256
  `714b95707fe468a98d90981e02bfd2e8f8c9e9e096caebe862f51538388a2dcc`；
- corrected P1：`external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1-r02.json`，SHA-256
  `519d78374e9060b0d495c61edabb6b6c05cd3b708fbbbb708f2d99243a16ecb0`。

旧 draft、旧 identity/P1、mutable working copy、P2 parent-environment authorization、P2 parent-validation
材料及未绑定附件均未被当作审计对象。

## 2. 前置冻结链与机械核验

- Git 工作区在审计开始时为 clean；repository binding 的 `repository_dirty` 为 `false`。
- binding 固定的 repository commit 为
  `9e7e9f795f99ca5bce85b09f80495b0d1db031a9`，`oid_algorithm` 为 `sha1`。
- binding 的 `reviewed_protocol_path` 和 `reviewed_protocol_sha256` 与协议正文的实际路径和摘要逐字一致。
- repository binding 的 `identity_ref` 指向 corrected identity `-r02`，不是已记录 schema defect 的旧对象。
- `experiment_parent_binding` 与五个 publication purpose（`package`、`normal-receipt`、
  `nonpublication-receipt`、`abort-receipt`、`failure-receipt`）均逐字指向同一已冻结 parent binding，purpose 集合和顺序完整。
- P2 gate 为 `AUTHORIZED / request-p3`，前驱为 corrected P1 `-r02`，scope operations 仅为 `[binding]`，
  `allow_network=false`、`allow_production_write=false`、`write_targets=[]`。
- 已运行仓库提供的 P2/binding validator；parent binding、repository binding、P2 gate canonical、closed-field、引用、
  commit、protocol digest、purpose coverage 和授权边界检查全部报告 `PASS`。
- 协议正文与 binding 所固定 commit 中的版本无 diff。
- 对冻结 JSON 使用标准库解析、canonical 重序列化近似检查和摘要核对均通过；该近似检查不替代协议规定的完整
  `sa-json-c14n-v1` validator。

## 3. 检查方法与逐项结果

### 3.1 通过项

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| 对象身份、路径、bytes、LF 行数、摘要和 binding 一致性 | PASS | §1；repository binding payload；上述机械核验 |
| canonical envelope、closed object、字段必填、数组排序/唯一性 DSL | PASS | 协议 §2.1–§2.4（尤其 §2.1 第 64–77 行、§2.2 第 159–177 行） |
| P2/P5 stream allowlist 的阶段选择 | PASS | §2.2 `BINDING_STREAM_ALLOWLIST`；§7 第 989–998 行；禁止交叉、合并和并集替代 |
| gate 前驱和唯一主链 | PASS | §3 第 388–392 行；唯一边为 `P0→P1→P2→P3→P4→P5→P6→P7→P7A→P8→P9` |
| P3 operation/TARGET | PASS（但见缺陷 A/C） | §3 第 394–397、406–417 行；`[review]` 和空 TARGET 不补足 audit schema |
| P4 targets、预算、网络和依赖获取边界 | PASS（但见角色缺陷） | §3 第 399–404 行；P4 仅 `[acquire,prepare]`，网络仅用于 ordered lock hosts |
| 禁止隐含 identity/binding/root/依赖/执行/发布/准入/backend 授权 | PASS（但见 admission_scope 缺陷） | §1 第 42–58 行；§11 第 1397–1408 行 |
| backend 值域与选择 | PASS | §2.2 `BACKEND`；§3 第 419–424 行；§10 的排除规则 |
| abort、拒绝、cleanup 和 terminal 分支闭合 | PASS | §9 第 1202–1222、1250–1270 行 |

### 3.2 缺陷 A：gate、actor role 与独立性未机械绑定（高优先级）

**状态：FAIL。该缺陷足以拒绝本次 P3。**

协议 §3 第 357–369 行的共用 `sa.m8.external-gate-record.v1.payload` schema 只声明：

```text
actor:{name:ASCII[1,128],role:enum[owner,independent-reviewer,independent-verifier]}
independence:{required:BOOL,satisfied:BOOL,basis:UTF8[1,1024]}
```

而 §3 第 394–397 行只按 gate 声明 `independence.required/satisfied` 和 operation 集合，没有把
`gate_id` 与合法 `actor.role` 作为 closed schema 约束。§9 第 1224–1248 行虽然在状态转移表中以 prose
写出 P0/P3/P5 为 independent reviewer、P7 为 independent verifier、P4 等为 owner，但该角色要求没有
回写为可由 external gate record validator 判定的约束。

因此，满足现有字段类型检查但违反治理边界的记录仍可能被接受，例如：

- P0/P3/P5 使用 `actor.role="independent-verifier"`；
- P7 使用 `actor.role="independent-reviewer"`；
- P4 使用非 owner 角色，尽管 P4 拥有 acquire/prepare 及唯一的网络授权能力；
- 同一实际主体以不同 `actor.name` 形成多个 gate record；
- reviewer 与协议作者、owner、coordinator 或 report-writer 实际为同一主体，而仅以自由文本
  `independence.basis` 自我声明独立。

协议没有提供可机械验证的 gate-specific role discriminator，也没有提供与作者、上游 actor、coordinator
或 report-writer 的不重合关系约束。这样，角色独立性这一关键 fail-closed 条件退化为叙述性断言。

**要求的修订方向：** 将 gate-specific role 固定进 closed/discriminated schema（P0/P3/P5 为
`independent-reviewer`，P7 为 `independent-verifier`，P1/P2/P4/P6/P7A/P8/P9 为 `owner`），并为
需要独立性的 gate 提供可验证的不重合关系；`independence.basis` 只能作为说明性证据，不能作为唯一满足条件。

### 3.3 缺陷 B：P8 `admission_scope` 为开放自由文本（中优先级）

**状态：FAIL。该缺陷使 M8 admission 边界无法完全机械闭合。**

协议 §3 第 385 行将 P8 payload 的字段定义为：

```text
admission_scope:UTF8[1,1024]
```

该字段不是闭合 enum、固定 literal、受控 schema ID 或带有可验证授权链的 `REF`。P8 的 operation 在
§3 第 394–396 行为 `[admit]`，且 §9 第 1247 行允许 owner/P8 从 `CLEANUP_VERIFIED` 进入
`P8_DECIDED`。与此同时，§1 第 52–54 行和 §11 第 1406–1408 行明确协议不得授权 M8 admission、
registry change 或 backend selection。

任意 1–1024 字符的 `admission_scope` 可承载未定义或扩大的准入范围；validator 无法仅凭 schema
拒绝该语义扩张。虽然零授权 prose 限制了协议本身的权力，但开放字段仍使技术 P8 记录与外部 M8
registry/stage admission 权威之间存在不可机械判定的边界张力。

**要求的修订方向：** 将 `admission_scope` 改为闭合 enum/fixed literal，或改为指向独立、版本化、
可验证且另行授权的 scope record 的 `REF`，并明确 P8 不得生成、变更、替代或暗示任何 M8
registry/stage/implementation admission。

### 3.4 缺陷 C：`text_audit_ref` 无封闭 artifact schema（高优先级）

**状态：FAIL。该缺陷使合法 P3 gate 无法构造，足以独立阻断 P3。**

协议 §2.3 第 185–186 行将 `REF` 定义为
`{schema_id:SCHEMA_ID,logical_name:LOGICAL_NAME,sha256:HEX64}`，并规定它只能引用带 §2.4 envelope 的
canonical JSON artifact；reader 必须验证被引用 artifact 的 envelope `schema_id`、logical-name binding 和完整
摘要。协议 §3 第 344–348 行另行定义了所有 external gate record 的统一 envelope schema
`sa.m8.external-gate-record.v1` 及 canonical logical name，而 §3 第 379 行将 P3 payload 固定为：

```text
{gate_id:"P3",binding_ref:REF,text_audit_ref:REF}
```

但协议全文只在该 P3 payload 中出现 `text_audit_ref`，没有定义其目标 text-audit artifact 的 schema ID、
closed payload、canonical logical name、结果值域、审计对象绑定或 envelope 规则。因而 reviewer 无法按冻结协议
构造一个既满足 `REF` 定义、又能由 validator 机械验证的引用目标；自行发明 schema 或字段会违反 closed-schema
和 fail-closed 规则。

“text audit + P3 record”在该结构下需要区分两个对象：一个是供 `text_audit_ref` 引用的 canonical
text-audit artifact，另一个是 logical name 为 `external-gates/p3/<record_id>.json` 的 canonical P3 external
gate record。本 Markdown 记录仅为人类可读的独立文本审计记录，不是协议定义的 canonical text-audit
artifact，不能替代该引用目标，也不能替代 machine P3 gate。由于 P3 payload 中 `text_audit_ref` 是必填 `REF`
且没有合法目标，本次不创建或臆造任何 `external-gates/p3` machine gate。

**要求的修订方向：** 为 text-audit artifact 定义独立、版本化、closed 且可 canonicalize 的 schema，固定其
logical-name binding、审计对象身份、verdict 和必要证据字段，并明确 P3 gate 对该 artifact 的引用与验证规则；
随后重新取得与修订协议一致的新 P0/P1/P2 冻结链，再请求独立 P3。

## 4. 最终 verdict

本次审计没有发现对象身份、冻结 commit、protocol digest、P2 predecessor、parent binding、P2 scope、
P2/P5 allowlist 时序、P4 目标集合、backend 值域或主状态链方面的缺陷；但发现上述三项协议规范性缺陷。

因此不能生成 `VERIFIED / request-p4`，也不能把本记录解释为 P4 授权、execution authorization、backend
selection 或 M8 admission。依据协议 §9 的 P3 行，最终 verdict 为：

```text
P3: REJECTED / stop
Overall: FAILED / RETURNED
Next action: stop; revise protocol text and obtain a new P0/P1/P2 chain before requesting P3 again
```

本记录仅是独立 P3 文本审计记录；未创建或臆造 `external-gates/p3` machine gate，未修改协议正文、
repository binding、任何 P1/P2 对象、PLAN 或 README，且未提交 Git commit。

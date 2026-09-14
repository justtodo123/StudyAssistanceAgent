# M8 active execution protocol `draft-0.11` 修订提案（三项 P3 阻断）

> **状态：`PROPOSAL_ONLY / NOT_AN_AUTHORIZATION / NOT_A_REVISION`**
>
> 本文件是一份**提案**，不是授权记录，不是审查记录，也不修改协议正文。它记录 `draft-0.10`
> 独立 P3 文本审计发现的三项阻断，并提出未来 successor protocol 的闭合修法与验收条件。
> 在负责人明确批准并另行形成授权记录之前，不得据以写入协议字节、创建协议身份或推进任何门禁。
>
> 本提案由 AI 起草，未经独立审查，不构成独立性证据，也不代作负责人裁定。

- 提案日期：2026-09-14
- 负责人：`justtodo123`
- 目标 successor：未来的 `draft-0.11`；本文件**不创建**该协议正文
- 直接依据：[`draft-0.10` 独立 P3 文本审计](m8-draft010-p3-independent-text-audit-20260914.md)
- 历史提案先例：[`m8-protocol-revision-proposal-20260913.md`](m8-protocol-revision-proposal-20260913.md)

## 0. 权限边界与当前结论

`docs/PLAN.md` 仍是阶段状态与路线图的最终权威，`docs/standards/` 中的正式门禁政策仍然有效，
`docs/plans/references/` 不能单独或组合产生新授权。本提案不改变任何权威状态：

- M8 仍为 `BLOCKED / NOT_STARTED`。
- M8 八项 Decision 仍为 `RESOLVED`，但这不等于 M8 admission、实现授权、执行授权或后端选择。
- `draft-0.10` 仍为 `REJECTED / stop`（`FAILED / RETURNED`）和 `NEVER_EXECUTED`。
- 不存在 machine P3 gate；现有链不得 `request-p4`。
- 任何 experiment root、依赖获取、source/input 准备、preflight、benchmark、执行、发布、后端选择及 M8 admission
  均未获本提案授权。
- 本提案不是 `draft-0.11` 协议 blob、owner authorization、P0/P1/P2/P3 record 或 P4/P5 record。

建议的治理顺序只有：

```text
本提案 → 负责人另行授权 → 新协议正文 → 新 P0 → 新 P1 → 新 P2 → 新独立 P3
```

在该顺序中，任何上一步缺失都不能由本提案、历史记录或技术验证替代。

## 1. 冻结基线与失败事实

下列对象已经冻结，只能作为本提案的读取基线，不能就地修改、重写或替换：

- `draft-0.10` protocol：
  [`m8-active-execution-protocol-draft-0.10.md`](m8-active-execution-protocol-draft-0.10.md)
  - SHA-256：`b5bc5088486079971eba28efe5cd2d7ed90c73a1359a87d9bca4722c473caa39`
  - 186129 bytes；1407 LF。
- repository binding：
  [JSON binding record](external-artifacts/binding/sa-m8-active-draft010-20260914-5d10f2a1-repository.json)
  - SHA-256：`65cc34a0c4861c6bb818089e570cba4ce1e14af909ef904dbd11f19a01f6eb9e`
  - 绑定 commit：`9e7e9f795f99ca5bce85b09f80495b0d1db031a9`。
- corrected P1：
  [P1 record](external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1-r02.json)
  - SHA-256：`519d78374e9060b0d495c61edabb6b6c05cd3b708fbbbb708f2d99243a16ecb0`。
- P2：
  [P2 record](external-gates/p2/p2-m8-active-execution-draft010-5d10f2a1-r01.json)
  - SHA-256：`1d75800731b3f518fdd8c0b90cfaddde3e999bb52d24bf3072d0f9ebf50b0766`。

独立 P3 审计确认了三项尚未闭合的阻断：

1. gate-specific actor role、独立性标志与操作集合没有形成 closed mechanical mapping；
2. P8 的 `admission_scope:UTF8[1,1024]` 仍允许越过协议内部决定边界的任意自由文本；
3. P3 的 `text_audit_ref` 没有对应的 closed canonical text-audit artifact schema。

因此当前 P3 结论保持 `REJECTED / stop`；不能通过补写一个 Markdown 报告、修改 P2 或换用历史对象来消除这些缺陷。

## 2. 修订 A：闭合 gate role、独立性与主体不重合

### 2.1 推荐的 closed gate mapping

未来 successor protocol 应把 gate、actor role、independence flags 和 operations 绑定为 closed discriminated
schema。推荐映射如下：

| Gate | `actor.role` | `independence.required` | `independence.satisfied` | operations |
| --- | --- | --- | --- | --- |
| P0、P3、P5 | `independent-reviewer` | `true` | `true` | `[review]` |
| P7 | `independent-verifier` | `true` | `true` | `[verify]` |
| P1、P2、P4、P6、P7A、P8、P9 | `owner` | `false` | `false` | 各 gate 已定义的精确集合 |

未来 schema 和 validator 必须 fail closed：

- gate、role、任一 independence flag 或 operations 与映射不一致时拒绝；
- `independence.basis` 只能说明依据，不能单独证明独立性；
- P0/P3/P5 使用 `independent-verifier` 必须拒绝；
- P7 使用 `independent-reviewer` 必须拒绝；
- owner gate 使用非 `owner` role 必须拒绝；
- owner role 与 `required=true` 或 `satisfied=true` 的组合必须拒绝；
- independence-required gate 使用 `satisfied=false` 必须拒绝。

### 2.2 主体不重合

对每个要求独立性的 gate，`actor.name` 必须不同于同一 `protocol_blob_sha256` chain 中已经绑定的所有
owner actor。该比较必须是可机械执行的链内规则，而不是对自由文本 `basis` 的信任。

由于 P0 没有 owner predecessor，建议未来 P0 closed payload 增加：

```text
drafting_party_name:ASCII[1,128]
```

并强制：

- P0 reviewer 的 `actor.name` 必须不同于 `drafting_party_name`；
- P0 reviewer 也必须满足其自身的 `independent-reviewer` mapping；
- 后续 independence-required actor 必须不同于同一链上的全部 owner actor；
- 不引入没有独立 closed schema 和绑定来源的 `principal_id`；
- 不能通过变更 `basis`、别名或显示名称绕过主体不重合规则。

### 2.3 A 的验收边界

正向验收至少应证明每个 gate 的 role、flags 和 operations 精确匹配上表，且 P0 reviewer 与 drafting party、后续
reviewer/verifier 与 owner actors 均不重合。负向验收至少覆盖错误 role、flag mismatch、错误 operations、仅凭
`basis` 自证独立以及 actor name 重合；全部必须 fail closed。

## 3. 修订 B：关闭 P8 admission scope

将未来 protocol 中的开放字段：

```text
admission_scope:UTF8[1,1024]
```

改为唯一允许的 literal：

```text
admission_scope:"protocol-p8-decision-only"
```

机械语义必须固定如下：

- 除 `protocol-p8-decision-only` 外的任何值均拒绝；
- P8 `operations` 仍精确为 `[admit]`；
- P8 `write_targets` 必须为空；
- P8 只能记录该 protocol 内部的 P8 decision；
- P8 不得创建、改变、替换或暗示 M8 registry admission、M8 stage admission、implementation authorization 或
  backend selection；
- P9 保持独立 gate，并继续单独承载协议内部的 backend-selection decision；
- P8 不能替代 `docs/PLAN.md`、stage-admission registry、正式准入政策或负责人批准。

正向验收应只接受该 literal；负向验收应拒绝其他字符串、非空 write target 以及试图把项目级 admission 写入 P8
payload 的结构。该修订不改变正式 M8 状态，也不选择任何后端。

## 4. 修订 C：canonical text-audit artifact 与 P3 一致性

### 4.1 新的 closed artifact schema

未来 successor protocol 应定义：

```text
schema_id:sa.m8.text-audit.v1
canonical logical name:external-artifacts/text-audits/<record_id>.json
```

artifact envelope 和 payload 必须是 closed object（`additionalProperties=false`）。payload 至少精确定义为：

```text
{
  audited_protocol_path:REPO_PATH,
  audited_protocol_sha256:HEX64,
  binding_ref:REF,
  verdict:enum[VERIFIED,REJECTED],
  finding_ids:A<ID;0..64;order=value;unique=value>,
  object_bindings:A<{
    object_role:enum[protocol,repository-binding],
    logical_name:LOGICAL_NAME,
    sha256:HEX64
  };2..2;order=key(object_role);unique=key(object_role)>
}
```

进一步的机械规则为：

- `object_bindings` 必须恰好两个元素，且只能各有一个 `protocol` 与 `repository-binding`；
- 缺项、重复、第三个 object role 或 object role 顺序错误均拒绝；
- `binding_ref.schema_id` 必须为 `sa.m8.repository-binding.v1`；
- `audited_protocol_path` 和 `audited_protocol_sha256` 必须与 binding 选中的 protocol 完全一致；
- `VERIFIED` 必须对应 `finding_ids=[]`；`REJECTED` 必须对应非空 `finding_ids`；
- `logical_name` 和 digest 必须由 canonical envelope、REF resolution 与 SHA-256 机械核验；
- 人类可读的 Markdown 审计报告仍是非 canonical 记录，不能作为 `text_audit_ref` 的目标。

### 4.2 P3 的 closed resolution

未来 P3 payload 的 `text_audit_ref` 必须精确解析为上述 schema、logical name 和 digest。还必须满足：

- P3 `binding_ref`、text-audit artifact 的 `binding_ref` 与 P2 repository-binding reference 逐字节一致；
- text-audit artifact 的 protocol identity 与当前 successor binding 选择的 protocol 一致；
- P3 `read_refs` 恰好包含 inspected P2 gate、repository binding 和 canonical text-audit artifact；
- P3 `write_targets=[]`；
- `verdict=VERIFIED` 只能得到 `P3: VERIFIED / request-p4`；
- `verdict=REJECTED` 只能得到 `P3: REJECTED / stop`；
- verdict、decision、next action 或 reference resolution 任一不一致均为 `INVALID_PROTOCOL_DEVIATION`。

text-audit artifact 与 P3 gate 都是行政记录，不是 protocol write target。本提案不创建任一记录。

### 4.3 durable package 成员

未来 durable package 应新增独立标量：

```text
text_audit_member:PACKAGE_MEMBER_REF
```

它必须在 schema ID、logical name 和 digest 三方面精确等于 P3 `text_audit_ref`，并满足：

- `gate_members` 仍为恰好 9 个成员；
- `input_members` 仍为恰好 19 个成员；
- `text_audit_member` 不计入、也不插入上述任一数组；
- 缺失、重复、放错数组或引用不同 artifact 均拒绝。

正向验收应覆盖合法 artifact、两对象 binding、两种 verdict 映射和正确 package cardinality。负向验收应覆盖 schema、
logical name、digest、binding、object count、findings、refs、decision/next-action 和 package member 的每一种不一致。

## 5. 失效面与全新重启要求

任何协议字节变化都会形成新的 protocol blob identity。未来若负责人授权并实际产生 `draft-0.11`，必须：

1. 生成新的 successor protocol bytes 和新的 SHA-256；
2. 不得就地修改 `draft-0.10`、其 repository binding、P1、P2、identity 或其他 frozen-chain object；
3. 在新 digest 上形成全新的 P0；
4. 由新 P0 形成全新的 P1；
5. 由新 P1 形成全新的 P2；
6. 只有新 P0/P1/P2 chain 闭合后，才能请求新的 independent P3；
7. 任何历史 P0/P1/P2、identity、binding 或本提案都不能替代这些步骤。

当前仓库中预计有 **7 条** JSON record 的 `payload.reviewed_protocol_sha256` 精确绑定 `draft-0.10` protocol：

- P0 记录 1 条；
- 原始与 corrected P1 记录 2 条；
- P2 记录 1 条；
- 原始与 corrected identity 记录 2 条；
- repository-binding 记录 1 条。

该“7”是应由后续工具机械复核的仓库事实，不是本提案执行了失效操作的声明。parent-binding 不含
`payload.reviewed_protocol_sha256`，因此不计入该 digest invalidation surface。旧记录不得因本提案被删除或改写。

## 6. 未来 validator 验收矩阵

本节只规定未来实现应验证的行为，不修改现有 validator、builder 或测试。

### 6.1 正向案例

- 所有 gate 使用精确 role、independence flags 和 operations；
- P0 reviewer 与 drafting party 及 owner actors 均不同；
- P8 使用唯一 literal `protocol-p8-decision-only`，且 write targets 为空；
- canonical text-audit artifact 通过 schema、logical name、digest、binding、两对象 binding 和 verdict 约束；
- `VERIFIED` 与 `REJECTED` 分别解析为唯一允许的 P3 decision/next-action；
- durable package 保持 9 个 gate members、19 个 input members，并使用独立且匹配的 `text_audit_member`。

### 6.2 负向与 fail-closed 案例

- gate 使用错误 role，或 role 与 required/satisfied 不匹配；
- operations 缺项、多项或属于另一 gate；
- 仅凭 `independence.basis` 声明独立；
- independent actor 与 drafting party 或任一 owner actor 重合；
- P0 缺少 drafting party 或 reviewer 与 drafting party 重合；
- P8 使用其他 scope、非空 write target 或项目级 admission 内容；
- text-audit schema、logical name、digest、binding 或 object count 错误；
- 用 Markdown 报告冒充 canonical text-audit artifact；
- `finding_ids` 与 verdict 不一致，或 verdict、P3 decision、next action 不一致；
- P3 read_refs 缺项、多项或指向错误对象；
- package 缺少 `text_audit_member`，或把它计入 9/19 cardinality；
- successor 试图复用 `draft-0.10` 的任一 P0/P1/P2 或其他 frozen-chain object。

所有上述案例都应拒绝，不得依靠人工解释继续向下一 gate 推进。

## 7. 明确不执行的事项

本提案不授权、也不执行以下任何动作：

- 创建或修改 `m8-active-execution-protocol-draft-0.11.md`；
- 创建 draft-0.11 authorization、identity、repository binding、P0、P1、P2、P3、P4 或 P5 artifact；
- 创建 canonical text-audit JSON artifact；
- 修改 draft-0.10、repository binding、P1、P2、parent-binding 或 P3 审计报告；
- `request-p4` 或创建任何 P4/P5 record；
- experiment root 创建、依赖获取、source/input 准备、preflight、benchmark、experiment、receipt 或证据发布；
- backend selection、registry mutation、implementation authorization 或 M8 admission；
- 修改 `docs/PLAN.md`、根 `README.md`、stage-admission policy/registry、validator、builder 或测试；
- 以本提案代替负责人授权、独立审查或新的 P0/P1/P2 chain；
- Git commit、push 或其他外部发布。

负责人若批准该方向，仍须另行书面授权具体 protocol bytes 变更；授权本身也不能预置 P0/P1/P2/P3 结果。

## 8. 本提案的结论

推荐把 A、B、C 三项修订作为一次 successor protocol revision 的闭合范围，以避免在不同 schema 口径之间重复
重建 P0/P1/P2。但“是否采用、采用哪些具体文字、何时授权”仍属于负责人裁定。

在负责人另行批准前，本文件只是一份可审阅的 `draft-0.11` 修订提案：不产生协议正文，不产生授权，不推进门禁，
不解除 `draft-0.10` 的 `REJECTED / stop`，也不改变 M8 的 `BLOCKED / NOT_STARTED`。

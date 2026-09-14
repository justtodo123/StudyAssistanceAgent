# M8 active execution protocol `draft-0.11` 修订授权记录

- 授权日期：2026-09-14
- 授权人：`justtodo123`（owner）
- 授权对象：以 `draft-0.10` 为只读基线形成未来的 successor protocol `draft-0.11`
- 上游依据：[`draft-0.11` 修订提案](m8-draft011-revision-proposal-20260914.md)
- 直接阻断依据：[`draft-0.10` 独立 P3 文本审计](m8-draft010-p3-independent-text-audit-20260914.md)
- 授权状态：`AUTHORIZED_FOR_PROTOCOL_REVISION / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`
- 预期修订后状态：`DRAFTED / PENDING_INDEPENDENT_P0_REVIEW`

## 0. Owner 决议

负责人明确批准：

> 批准 A+B+C 作为一次 draft-0.11 协议修订，并按上述六项边界起草独立授权记录。

本记录把该决定收敛为一次定点 successor protocol 修订。A、B、C 必须在同一 `draft-0.11` protocol blob 中全部完成，
不得拆成多个 protocol 版本，也不得只修其中一项后请求 P0、P1、P2 或 P3。

本记录是**授权记录**，不是协议正文、审查记录或门禁记录。它不创建 `draft-0.11` 字节，不预置任何门禁结论，
不解除 `draft-0.10` 的 `P3 REJECTED / stop`，也不改变 M8 的 `BLOCKED / NOT_STARTED` 状态。

## 1. 授权修订 A：闭合 gate、角色、独立性与操作集合

### 1.1 Gate closed mapping

`draft-0.11` 必须把 gate、`actor.role`、`independence.required`、`independence.satisfied` 与 `scope.operations`
绑定为 closed discriminated mapping：

| Gate | 唯一允许的 `actor.role` | `required` | `satisfied` | 唯一允许的 operations |
| --- | --- | --- | --- | --- |
| P0 | `independent-reviewer` | `true` | `true` | `[review]` |
| P1 | `owner` | `false` | `false` | `[identity]` |
| P2 | `owner` | `false` | `false` | `[binding]` |
| P3 | `independent-reviewer` | `true` | `true` | `[review]` |
| P4 | `owner` | `false` | `false` | `[acquire,prepare]` |
| P5 | `independent-reviewer` | `true` | `true` | `[review]` |
| P6 | `owner` | `false` | `false` | `[execute]` |
| P7 | `independent-verifier` | `true` | `true` | `[verify]` |
| P7A | `owner` | `false` | `false` | `[cleanup,publish]` |
| P8 | `owner` | `false` | `false` | `[admit]` |
| P9 | `owner` | `false` | `false` | `[select]` |

任一 gate 使用错误 role、任一 flag 不匹配、operations 缺项/多项/错序或属于另一 gate，必须 fail closed。
`independence.basis` 只能说明依据，不能替代 closed mapping，也不能单独证明独立性。

### 1.2 主体不重合

对所有要求独立性的 gate，必须形成可机械执行的主体不重合规则：

1. P0 payload 增加 `drafting_party_name:ASCII[1,128]`；
2. P0 `actor.name` 必须不同于 `drafting_party_name`；
3. P3/P5/P7 `actor.name` 必须不同于同一 successor protocol chain 中已经绑定的全部 owner actor names；
4. 不能通过修改自由文本 `basis`、别名或显示名称绕过比较；
5. 不新增没有独立 closed schema 和绑定来源的 `principal_id`。

修订正文必须说明主体不重合所读取的 chain records、比较规范和 fail-closed 结果，不能只写原则性文字。

## 2. 授权修订 B：关闭 P8 admission scope

将 P8 payload 中开放字段：

```text
admission_scope:UTF8[1,1024]
```

改为唯一允许的 literal：

```text
admission_scope:"protocol-p8-decision-only"
```

并闭合以下机械语义：

- 其他任何值均拒绝；
- P8 operations 仍精确为 `[admit]`；
- P8 `write_targets=[]`；
- P8 只能记录当前 protocol 内部的 P8 decision；
- P8 不得创建、改变、替换或暗示 M8 registry admission、stage admission、implementation authorization 或 backend selection；
- P9 保持独立门禁，单独承载 protocol 内部 backend-selection decision；
- P8 不能替代 `docs/PLAN.md`、正式准入政策、stage-admission registry 或负责人批准。

本项不授权改变 M8 正式阶段状态，不授权任何 backend 选择。

## 3. 授权修订 C：canonical text-audit artifact 与 P3 闭环

### 3.1 新增 closed artifact schema

`draft-0.11` 必须定义：

```text
schema_id:sa.m8.text-audit.v1
canonical logical name:external-artifacts/text-audits/<record_id>.json
```

其 envelope 与 payload 均为 closed object。payload 至少精确定义：

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

机械规则必须包括：

- `object_bindings` 恰有 `protocol` 与 `repository-binding` 各一项；
- 缺项、重复、第三角色或顺序错误均拒绝；
- `binding_ref.schema_id=sa.m8.repository-binding.v1`；
- audited protocol path/digest 与 binding 所选 protocol 完全一致；
- `VERIFIED` 当且仅当 `finding_ids=[]`；`REJECTED` 必须对应非空 findings；
- schema ID、logical name、canonical digest 与 REF resolution 全部机械核验；
- Markdown 审计报告不能作为 `text_audit_ref` 的目标。

### 3.2 P3 closed resolution

未来 P3 payload 的 `text_audit_ref` 必须精确解析为 `sa.m8.text-audit.v1`。还须强制：

- P3 `binding_ref`、text-audit artifact 的 `binding_ref`、P2 repository-binding reference 三者一致；
- artifact protocol identity 与 successor binding 所选 protocol 一致；
- P3 `read_refs` 恰含 inspected P2、repository binding 与 canonical text-audit artifact；
- P3 `write_targets=[]`；
- `VERIFIED` 唯一映射为 `P3: VERIFIED / request-p4`；
- `REJECTED` 唯一映射为 `P3: REJECTED / stop`；
- verdict、decision、next action 或 reference resolution 任一不一致均为 `INVALID_PROTOCOL_DEVIATION`。

### 3.3 Durable package member

新增独立标量：

```text
text_audit_member:PACKAGE_MEMBER_REF
```

该 member 必须在 schema ID、logical name、digest 三方面精确等于 P3 `text_audit_ref`。原有 cardinality 保持：

- `gate_members` 恰为 9；
- `input_members` 恰为 19；
- `text_audit_member` 不计入、也不插入上述任一数组；
- 缺失、重复、放错数组或引用不同 artifact 均拒绝。

## 4. 六项授权边界

### 边界一：只允许 A/B/C

修订范围严格限于 §1、§2、§3。不得夹带任何第四类功能、格式重构、术语迁移、状态机重设计或历史补认。

### 边界二：冻结无关内容

除实现 A/B/C 所必需的交叉引用、schema 字段和机械规则外，不得修改：

- P2 `BINDING_STREAM_ALLOWLIST`、stream observation 与 per-open 判定；
- `sa.m8.status-map.v1.payload` 的 72 行映射、行序与两项 `72..72`；
- `TECH_GATE_ID` 的 26 个成员及两处 `26..26`；
- `ID`、`SCHEMA_ID`、`CODE`、`REF`、`PACKAGE_MEMBER_REF` 等既有基础类型定义；
- `order=value` 与 `order=key(...)` 的比较器定义；
- P0→P1→P2→P3→P4→P5→P6→P7→P7A→P8→P9 的门禁顺序；
- P0/P1/P2/P3 以外因 A/B/C 不需要变化的 payload；
- 既有 deadline、receipt、status-map、binding、input 与 execution 语义；
- draft-0.10 及其 P0/P1/P2、identity、parent-binding、repository-binding、P3 审计记录。

如闭合 A/B/C 必然要求修改上述冻结内容，必须停止并另行取得授权。

### 边界三：不创建 gate 或 artifact

本授权只允许协议文本修订及其必要的文档导航、事实校验器和字节核验。不得创建 draft-0.11 的
identity、text-audit artifact、binding、P0/P1/P2/P3/P4/P5 或任何运行期 artifact。

### 边界四：修订后只能等待独立 P0

协议正文完成后的唯一允许状态是：

```text
DRAFTED / PENDING_INDEPENDENT_P0_REVIEW / UNBOUND / NOT_EXECUTION_AUTHORIZED
```

不得在协议文件、授权记录、README 或校验器中预告 `PASS`、`P0_ACCEPTED`、`request-p1` 或任何后续结果。

### 边界五：起草方不得担任独立 reviewer

参与本授权记录、draft-0.11 协议文字、修订脚本或验收脚本起草的一方，不得担任 draft-0.11 的 P0 或 P3 reviewer。
P0、P3 的结论必须由未参与起草的独立主体另行产生。

### 边界六：M8 持续阻断

在 draft-0.11 依次完成新的独立 P0、owner P1、新 P2 和独立 P3 之前：

- M8 保持 `BLOCKED / NOT_STARTED`；
- 不得请求或创建 P4；
- 不得创建 experiment root；
- 不得获取依赖、准备 source/input、运行 preflight/benchmark/experiment；
- 不得发布证据、执行 admission 或选择 backend；
- 不得把 draft-0.10 的任何 gate/artifact 当作 successor chain 的替代品。

## 5. 允许动作

1. 从 `draft-0.10` 的精确字节复制形成一个**新文件** `m8-active-execution-protocol-draft-0.11.md`；不得就地改写 `draft-0.10`。
2. 只在新文件中执行 A/B/C 一次性修订，并更新版本头部与修订依据。
3. 为新协议文件增加逐文件 LF 规则；不得用范围过宽的通配规则改写历史版本。
4. 编写只读事实校验器，覆盖提案 §6 的正向与负向验收矩阵。
5. 同步更新导航文件，使其状态保持 `DRAFTED / PENDING_INDEPENDENT_P0_REVIEW`。
6. 形成修订实施说明和精确字节归档，包括字节数、LF 行数、SHA-256、与 draft-0.10 的差异范围。
7. 提交协议文本修订及其直接配套材料；不得在同一提交中夹带任何 gate/artifact。

## 6. 失效范围与全新重启

任何 `draft-0.11` 字节都会形成新的 protocol blob identity。当前机械事实是，7 条 JSON 记录的
`payload.reviewed_protocol_sha256` 精确绑定 `draft-0.10`：P0 1 条、P1 2 条、P2 1 条、identity 2 条、
repository-binding 1 条。parent-binding 不含该字段，不计入此数。

本授权不删除、不改写、不重算上述 7 条记录。它们继续作为 `draft-0.10` 已失败冻结链的历史证据，不能用于
`draft-0.11`。successor 必须重新形成：

```text
new protocol bytes → independent P0 → owner P1 + new identity → owner P2 + new bindings → independent P3
```

历史 P0/P1/P2、identity、binding、提案、Markdown P3 审计报告均不能替代任一步。

## 7. 验收矩阵

修订配套校验器必须至少证明：

### 正向

- 11 个 gate 全部匹配唯一 role/flags/operations mapping；
- P0 reviewer 与 drafting party 不重合，P3/P5/P7 与链上 owner actors 不重合；
- P8 只接受 `protocol-p8-decision-only` 且 write targets 为空；
- canonical text-audit schema、两项 object binding、binding 闭包与两种 verdict 映射成立；
- durable package 仍为 9 个 gate members、19 个 input members，并有独立 `text_audit_member`。

### 负向（均须 fail closed）

- 错误 gate role、flag mismatch、错误 operations；
- 仅凭 `basis` 自证独立，或独立 actor 与 drafting party/owner actor 重合；
- P8 使用其他字符串、非空 write target 或项目级 admission 内容；
- text-audit schema、logical name、digest、binding、object count、finding/verdict、read refs 或 decision/next action 不一致；
- Markdown 报告冒充 canonical artifact；
- package 缺少 `text_audit_member`、将其塞入 9/19 数组或引用不同 artifact；
- successor 复用 draft-0.10 的 gate/artifact。

## 8. 明确禁止

本授权不允许：

- 修改、删除、重算或替换 draft-0.10 frozen chain 的任何字节；
- 创建或补写 draft-0.10 machine P3 gate；
- 把 `draft-0.10` 的 P3 拒绝改写为通过；
- 在 draft-0.11 文本修订提交中创建任何 gate/artifact；
- 运行 P0/P1/P2/P3/P4/P5 或其他门禁；
- 创建 experiment root、依赖环境、source/input、benchmark、receipt、package 或 publication；
- 修改 `docs/PLAN.md`、根 `README.md`、正式 M8 policy/registry 或 stage-admission 状态；
- 准入 M8、批准实现、选择 LanceDB/Qdrant/Milvus 或其他 backend；
- 推送远端或对外发布。

## 9. 授权后的状态

本授权生效后，只允许起草方开始执行 `draft-0.11` 协议文本修订。当前状态仍为：

```text
draft-0.10: P3 REJECTED / stop / FAILED / RETURNED
draft-0.11: AUTHORIZED_FOR_PROTOCOL_REVISION / PROTOCOL_BYTES_NOT_YET_CREATED
M8: BLOCKED / NOT_STARTED
```

本记录不宣告 `draft-0.11` 会通过独立 P0 或 P3。修订完成后必须停止在
`DRAFTED / PENDING_INDEPENDENT_P0_REVIEW`，由未参与起草的一方另行审查。

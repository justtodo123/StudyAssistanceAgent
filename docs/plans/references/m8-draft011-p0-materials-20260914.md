# M8 `draft-0.11` P0 独立审查材料

- 日期：2026-09-14
- 被审对象：`m8-active-execution-protocol-draft-0.11.md`
- 被指定 reviewer：`justtodo123` / `independent-reviewer`
- drafting party：`ai-assistant`
- 状态：`MATERIALS_PREPARED / P0_PENDING_REVIEW / NOT_A_GATE`

## 0. 边界

本材料由 draft-0.11 起草方编写，不是独立审查结论，也不构成 P0 记录。下列事实均须 reviewer 自行复验；
起草方的校验脚本不能证明协议正确或独立性成立。

## 1. 精确被审字节

| 项 | 值 |
| --- | --- |
| 路径 | `docs/plans/references/m8-active-execution-protocol-draft-0.11.md` |
| 字节数 | 191290 |
| LF 行数 | 1457 |
| SHA-256 | `92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d` |
| 行尾 | 纯 LF，受逐文件 `.gitattributes` 规则保护 |

## 2. 独立性待核验事实

1. `drafting_party_name` 应在未来 P0 payload 中写为 `ai-assistant`；
2. reviewer `actor.name=justtodo123`，与 drafting party 逐字不同；
3. `actor.role` 必须是 `independent-reviewer`；
4. `independence.required=true`、`satisfied=true`；
5. `scope.operations=[review]`；
6. reviewer 未编写 draft-0.11 正文、修订脚本或验收脚本；owner 批准修订方向不等于参与协议文字起草。

以上第 6 项属于 reviewer 自我声明；起草方不能替 reviewer 证明。

## 3. A 的待审事实

- 11 个 gate 是否均有唯一 role/required/satisfied/operations 组合；
- 错误 role、flags、operations 是否明确 fail closed；
- P0 payload 是否要求 `drafting_party_name`；
- P0 是否机械比较 reviewer 与 drafting party；
- P3/P5/P7 是否沿唯一 predecessor chain 收集所有 owner actors；
- missing/spliced chain、主体重合、仅凭 `basis` 或 alias 自证是否均拒绝；
- 是否避免引入无 closed schema/binding 来源的 `principal_id`。

## 4. B 的待审事实

- P8 schema 是否只允许 `admission_scope:"protocol-p8-decision-only"`；
- 旧 `admission_scope:UTF8[1,1024]` 是否已不存在；
- P8 operations 是否仍为 `[admit]`、write targets 是否为空；
- P8 是否明确不能替代 M8 registry/stage admission、implementation authorization 或 backend selection；
- P9 是否保持独立 backend-selection gate。

## 5. C 的待审事实

- 是否定义 closed `sa.m8.text-audit.v1.payload`；
- `audit_id` 是否能唯一派生 `external-artifacts/text-audits/<audit_id>.json`；
- object bindings 是否恰为 protocol 与 repository-binding 两项并有唯一顺序；
- audit binding/protocol identity 是否与 repository binding 一致；
- VERIFIED/finding_ids=[] 与 REJECTED/non-empty findings 是否形成 iff；
- P3 read refs 是否恰为 P2、repository binding、canonical audit 三项；
- P3 binding/ref/verdict/decision/next action 是否闭合；
- Markdown 是否明确不能冒充 canonical audit artifact；
- durable package 是否有独立 `text_audit_member`，同时保持 gate/input member 9/19 基数。

## 6. 冻结边界

reviewer 应确认 A/B/C 之外未修改：基础类型、comparators、P2 stream allowlist、status-map 72 行、TECH_GATE_ID 26 项、
gate 顺序、deadline、receipt、binding、input 与 execution 语义，以及 draft-0.10 frozen chain。

## 7. 允许的 P0 结果

reviewer 只能自行选择：

- `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / request-p1`；或
- `P0_NOT_ACCEPTED / stop`。

本材料不推荐其中任一结果。P0 即使接受，也不产生 identity、binding、执行或 M8 admission 权限。

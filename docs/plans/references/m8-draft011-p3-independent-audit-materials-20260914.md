# M8 `draft-0.11` P3 独立文本审计材料

- 日期：2026-09-14
- 状态：`P3_MATERIALS_READY / INDEPENDENT_REVIEWER_REQUIRED / NOT_A_GATE`
- drafting party：`ai-assistant`
- owner actors in predecessor chain：`justtodo123`
- reviewer：待指定，且必须与上述两个名字逐字节不同
- protocol：`docs/plans/references/m8-active-execution-protocol-draft-0.11.md`
- protocol SHA-256：`92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d`
- P2：`external-gates/p2/p2-m8-active-execution-draft011-940ecec4-r01.json`
- P2 SHA-256：`7b5efd98b844559d93f67203ee94906555a60e2cb9296d5ac7e5d8a9e73c66a8`
- repository binding：`external-artifacts/binding/sa-m8-active-draft011-20260914-940ecec4-repository.json`
- binding SHA-256：`91af7708a8d73ffe99e185d1cfec8efba8f09ad04768408f2e3bbfc7785bc602`

## 1. 审计目标

P3 reviewer 独立检查被 binding 冻结的 protocol 与 repository binding 是否形成完整、无歧义、可机械执行的文本合同。
本材料由起草方准备，不给出 `VERIFIED` 或 `REJECTED` 建议，不替 reviewer 生成 finding、text-audit artifact 或 P3 gate。

## 2. 必查闭包

1. P2 canonical、logical-name、摘要、actor mapping、前驱 P1、`AUTHORIZED / request-p3` 是否精确有效。
2. Repository binding 是否精确绑定 clean commit `9e80d7e1275a835cdee9fcf5d927f094e2b7d128`、identity、protocol、
   experiment parent 和五种 publication purpose。
3. Protocol 的十一 gate closed mapping、独立主体不重合规则、P8 唯一 admission scope、P3 text-audit schema 是否闭合。
4. `sa.m8.text-audit.v1.payload` 的七个字段、logical name 派生、两个 object binding 顺序、verdict/finding 双向映射是否完整。
5. P3 payload 是否只含 `gate_id`、`binding_ref`、`text_audit_ref`；scope `read_refs` 是否恰为 P2、repository binding、
   text-audit 三项；三处 binding REF 是否逐字节相同。
6. 是否存在任何会错误授权 P4、建根、依赖、输入、执行、发布、backend selection 或 M8 admission 的文本漏洞。

## 3. Reviewer 必须自行作出的产物

Reviewer 应先独立形成审计 findings 和 verdict，再落盘 canonical text-audit artifact：

```text
external-artifacts/text-audits/<audit_id>.json
```

- `VERIFIED` 当且仅当 `finding_ids=[]`；
- `REJECTED` 当且仅当 `finding_ids` 非空；
- object bindings 按 `protocol`、`repository-binding` 顺序恰有两项；
- audit binding REF 必须与 P2 repository binding REF 完全相同。

随后才能形成 P3 gate：

- actor role：`independent-reviewer`；
- independence：`required=true / satisfied=true`；
- operations：`["review"]`；
- predecessor：唯一 P2；
- 接受映射：`VERIFIED / request-p4`；
- 拒绝映射：`REJECTED / stop`。

## 4. 禁止事项

在独立 reviewer 完成审计并签署前，不得由 `ai-assistant` 或 `justtodo123` 代签 P3，不得预置空 findings，不得创建
P4、experiment root、依赖、输入或执行产物。P3 即使 `VERIFIED` 也只允许 `request-p4`，不直接授权准备或执行。

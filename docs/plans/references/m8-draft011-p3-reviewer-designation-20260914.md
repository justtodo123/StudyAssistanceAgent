# M8 `draft-0.11` P3 independent reviewer 指定记录

- 日期：2026-09-14
- 指定人：`justtodo123`（owner）
- reviewer：`external-reviewer-01`
- 状态：`P3_REVIEWER_DESIGNATED / AUDIT_PENDING / NOT_A_GATE`
- protocol：`docs/plans/references/m8-active-execution-protocol-draft-0.11.md`
- P2：`external-gates/p2/p2-m8-active-execution-draft011-940ecec4-r01.json`
- P2 SHA-256：`7b5efd98b844559d93f67203ee94906555a60e2cb9296d5ac7e5d8a9e73c66a8`

## 1. 指定决定

Owner `justtodo123` 指定 `external-reviewer-01` 作为 `draft-0.11` P3 独立文本审计 reviewer。

该名字与 drafting party `ai-assistant`、P1/P2 owner `justtodo123` 逐字节不同。指定只确定审计主体，不代表主体已经
检查材料，不证明独立性事实已经满足，也不预置 `VERIFIED`、`REJECTED`、findings 或下一动作。

## 2. Reviewer 范围

`external-reviewer-01` 应独立读取并核验：

- `m8-draft011-p3-independent-audit-materials-20260914.md`；
- `m8-draft011-p3-reviewer-worksheet-20260914.md`；
- protocol、P0/P1/P2、identity、parent-binding 与 repository-binding 的实际 bytes；
- draft-0.11 的 gate mapping、主体不重合、P8 admission scope 与 canonical text-audit schema；
- P3 三项 read REF、binding REF 一致性及 verdict/finding 双向映射。

Reviewer 必须自行复算摘要、形成 findings 和 verdict，并以自己的判断填写工作单或另行形成独立审计记录。

## 3. 允许与禁止

允许 reviewer 执行只读检查、机械负向测试、摘要复算和审计记录起草。若作出最终裁定，才可按协议生成对应的 canonical
text-audit artifact 与 P3 gate。

在 reviewer 最终签署前：

- `ai-assistant` 不得代替 reviewer 选择 verdict、finding IDs 或独立性 basis；
- `justtodo123` 不得作为 P3 reviewer；
- 不得创建 P4、experiment root、依赖、输入、preflight、benchmark 或执行产物；
- 不得发布证据、选择后端或准入 M8。

## 4. 来源

Owner 在 P3 reviewer 选择中明确选择：

> external-reviewer-01

本记录忠实落盘该主体指定，不扩张为 P3 技术裁定。

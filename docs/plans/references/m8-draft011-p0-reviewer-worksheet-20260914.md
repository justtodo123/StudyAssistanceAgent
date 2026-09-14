# M8 `draft-0.11` P0 reviewer 工作单

- reviewer：`justtodo123`
- role：`independent-reviewer`
- drafting party：`ai-assistant`
- 性质：`REVIEW_WORKSHEET / NOT_A_GATE / VERDICT_BLANK`

## 1. 字节与授权

- [ ] 实测 191290 bytes / 1457 LF / SHA-256 `92e28958…d40d`；
- [ ] 工作区与仓库字节一致，纯 LF；
- [ ] owner 授权只覆盖 A+B+C，正文 diff 不含第四类修改；
- [ ] 未创建 draft-0.11 gate、identity、binding 或 text-audit artifact。

## 2. 独立性

- [ ] `actor.name=justtodo123` 与 `drafting_party_name=ai-assistant` 不同；
- [ ] reviewer 未参与正文、修订脚本或验收脚本起草；
- [ ] role/flags/operations 应为 `independent-reviewer / true / true / [review]`；
- [ ] `basis` 不作为主体独立性的唯一证明。

## 3. A：closed mapping

- [ ] 11 个 gate 的映射唯一且完整；
- [ ] wrong role、flag mismatch、wrong operations 均 fail closed；
- [ ] P0 drafting-party 比较机械可执行；
- [ ] P3/P5/P7 owner actor 收集与比较机械可执行；
- [ ] predecessor 缺失、拼接或无法解析时拒绝。

## 4. B：P8 scope

- [ ] 唯一 literal 为 `protocol-p8-decision-only`；
- [ ] P8 `[admit]`、write targets 为空；
- [ ] 不表示项目级 admission、实现授权或 backend selection；
- [ ] P9 独立保持。

## 5. C：text audit/P3/package

- [ ] `sa.m8.text-audit.v1` closed schema 完整；
- [ ] logical name 从 `audit_id` 派生；
- [ ] 两个 object bindings 恰好且顺序唯一；
- [ ] verdict/findings iff；
- [ ] P3 三个 read refs、binding 和 protocol identity 闭合；
- [ ] verdict 唯一映射 decision/next action；
- [ ] Markdown 不能作为 canonical ref；
- [ ] package 独立 `text_audit_member`，9/19 不变。

## 6. 冻结与负向验收

- [ ] `tools/m8_validate_draft011_revision.py` 的正向/负向项目全部通过；
- [ ] 冻结基础类型、comparators、stream allowlist、status map、gate order 均未变；
- [ ] draft-0.10 frozen chain 摘要不变；
- [ ] 无授权外内容。

## 7. Reviewer 裁定（必须由 reviewer 填写）

| 项 | 裁定 | 依据 |
| --- | --- | --- |
| 独立性成立 | | |
| A 可接受 | | |
| B 可接受 | | |
| C 可接受 | | |
| 冻结边界保持 | | |
| P0 最终决定 | | |

最终决定只能是：

- `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / request-p1`
- `P0_NOT_ACCEPTED / stop`

# M8 最小 1K 协议 S0 reviewer worksheet

- 状态：`REVIEW_WORKSHEET / VERDICT_BLANK / NOT_A_DECISION`
- drafting party：`ai-assistant`
- owner：`justtodo123`
- reviewer：`________________________________`

Reviewer 必须与 drafting party 名称逐字节不同，并只读审查冻结 commit `306f8267fd0bebb517a2a5d7f921c761d0d1180d`。

| 检查项 | PASS / FAIL | finding ID | 证据 |
| --- | --- | --- | --- |
| protocol/schema/validator 摘要复算一致 |  |  |  |
| 范围仅限 SQLite/LanceDB 1K synthetic |  |  |  |
| 与 draft-0.11 冻结链分离且无 P4 |  |  |  |
| S0–S3 权限、失败和停止点闭合 |  |  |  |
| S1 执行前冻结字段充分 |  |  |  |
| 同一 input digest 和 correctness oracle 明确 |  |  |  |
| hard failure 覆盖安全与生命周期 |  |  |  |
| artifact 集合最小且能记录真实产物 |  |  |  |
| 1K 不自动授权 10K/选择/admission |  |  |  |
| 正负例 validator 通过 |  |  |  |
| 无其他不可满足矛盾 |  |  |  |

## Findings

```text
finding_ids（按 byte value 排序；接受时必须为空）：

```

## 最终裁定

| 字段 | Reviewer 填写 |
| --- | --- |
| reviewer name |  |
| independence basis |  |
| decision |  |
| allowed_next_action |  |
| finding_ids |  |
| timestamp |  |

封闭映射：空 findings → `PROTOCOL_ACCEPTED / request-s1`；非空 findings → `PROTOCOL_REJECTED / stop`。
本工作单不构成 S0 裁定。

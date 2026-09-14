# M8 `draft-0.11` P3 independent reviewer worksheet

- 状态：`REVIEW_WORKSHEET / NOT_A_GATE / VERDICT_BLANK`
- drafting party：`ai-assistant`
- predecessor owner：`justtodo123`
- reviewer：`________________________________`

Reviewer 名字必须与 `ai-assistant` 和 `justtodo123` 逐字节不同。

## 1. 对象摘要复算

| 对象 | 期望 SHA-256 | Reviewer 复算值 | 结果 |
| --- | --- | --- | --- |
| protocol | `92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d` |  |  |
| repository binding | `91af7708a8d73ffe99e185d1cfec8efba8f09ad04768408f2e3bbfc7785bc602` |  |  |
| P2 gate | `7b5efd98b844559d93f67203ee94906555a60e2cb9296d5ac7e5d8a9e73c66a8` |  |  |

## 2. 独立检查表

| 检查项 | PASS / FAIL | finding ID（若失败） | Reviewer 证据 |
| --- | --- | --- | --- |
| P0→P1→P2 唯一前驱链与 actor 映射闭合 |  |  |  |
| P2 clean commit、identity、protocol 与 parent REF 闭合 |  |  |  |
| 五种 publication purpose 完整且顺序正确 |  |  |  |
| 十一 gate role/independence/operations closed mapping 完整 |  |  |  |
| P3/P5/P7 reviewer 与 drafting party/所有 owner 不重合 |  |  |  |
| P8 admission scope 仅为 `protocol-p8-decision-only` |  |  |  |
| text-audit schema、logical name 和 verdict 映射闭合 |  |  |  |
| P3 三项 read REF 与三处 binding REF 关系闭合 |  |  |  |
| P4–P9 未被 P2 或 P3 提前授权 |  |  |  |
| 未发现其他阻断性文本/schema 缺陷 |  |  |  |

## 3. Findings

```text
finding_ids（按 ID byte value 排序；接受时必须为空）：

```

## 4. 最终裁定

| 字段 | Reviewer 填写 |
| --- | --- |
| Reviewer name |  |
| 独立性 basis |  |
| text-audit `audit_id` |  |
| text-audit verdict |  |
| finding_ids |  |
| P3 decision |  |
| allowed_next_action |  |
| timestamp |  |

封闭映射：text-audit `VERIFIED` + 空 findings → P3 `VERIFIED / request-p4`；text-audit `REJECTED` + 非空 findings →
P3 `REJECTED / stop`。本工作单保持空白，不构成裁定。

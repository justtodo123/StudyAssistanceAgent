# M8 最小 1K v3 独立 S0 Reviewer 工作单

- 状态：`VERDICT_BLANK / NOT_A_DECISION / NOT_EXECUTION_AUTHORIZED`
- reviewed object commit：`50bea24df515f8d2956f619b2b92844f5f6eb194`
- review materials：`m8-minimal-1k-v3-s0-review-materials-20260914.md`

> 本工作单由起草方提供结构，不预置 reviewer、finding 或 verdict。Reviewer 应在独立环境核对冻结摘要、运行允许的 fixture harness，并自行形成结论。

## A. Reviewer 与独立性披露

- reviewer name：
- 是否参与 v3 protocol/schema/validator/generator/test 起草：
- 与 drafting party `ai-assistant` 的分离依据：
- 无法证明的独立性边界：
- 审查环境与 Python 版本：

## B. 冻结对象核验

| 对象 | 摘要/字节是否匹配 | 备注 |
| --- | --- | --- |
| protocol v3 |  |  |
| artifact schema v3 |  |  |
| graph validator v3 |  |  |
| fixture generator v3 |  |  |
| test harness v3 |  |  |
| fixture-tree-v1 |  |  |
| reviewed object commit |  |  |

## C. 职责分层与安全边界

| 检查项 | PASS/FAIL | finding ID / 说明 |
| --- | --- | --- |
| JSON Schema 仅承担局部结构约束 |  |  |
| graph validator 承担跨文件 bytes/REF/聚合约束 |  |  |
| SQLite oracle 与 LanceDB candidate 边界正确 |  |  |
| 仅限 synthetic 1K，排除 Qdrant/ANN/10K/真实资料 |  |  |
| S0 前禁止真实 identity、环境、依赖、输入和运行 |  |  |
| S3 接受不自动产生后续权限 |  |  |

## D. Graph validator 审查

| 检查项 | PASS/FAIL | finding ID / 说明 |
| --- | --- | --- |
| 读取真实持久 artifact directory |  |  |
| 固定九 artifact role 集合且拒绝未知/缺失对象 |  |  |
| canonical JSON 与 experiment ID 一致性 |  |  |
| typed REF 解析实际 role/schema/logical name/bytes |  |  |
| manifest digest/byte/JSONL count 复算 |  |  |
| protocol digest 与冻结 protocol bytes 绑定 |  |  |
| observer event、sequence、kind、lifecycle 和摘要复算 |  |  |
| S0 无前驱；S1 必须依赖 accepted S0 |  |  |
| S2 必须依赖 authorized S1 + PASS validation + CLEANED cleanup |  |  |
| S3 不得接受 failed S2 |  |  |
| 合法失败图与 invalid graph 明确区分 |  |  |
| path escape、断链与篡改 fail-closed |  |  |

## E. Fixture 与负例重放

- generator exit/output：
- test harness exit/output：
- success graph：
- failure-cleanup graph：
- failure-observer graph：
- failure-runtime graph：
- failure-validation graph：
- 18 个 mutation 是否逐项被拒绝：
- 是否发现 harness 未覆盖的关键 fail-open：

## F. 对 v2 findings 的处置判断

逐项填写 `CLOSED / PARTIALLY_CLOSED / OPEN / REFRAMED_BY_RESPONSIBILITY_SPLIT`，并给出依据：

- `m8-v2-s0-001`：
- `m8-v2-s0-002`：
- `m8-v2-s0-003`：
- `m8-v2-s0-004`：
- `m8-v2-s0-005`：
- `m8-v2-s0-006`：
- `m8-v2-s0-007`：
- `m8-v2-s0-008`：
- `m8-v2-s0-009`：
- `m8-v2-s0-010`：
- `m8-v2-s0-011`：
- `m8-v2-s0-012`：
- `m8-v2-s0-013`：

注意：v3 明确把真实 S1 环境、完整 1K generator implementation 和 observer OS 配置留作 S1 前置冻结。Reviewer 应判断这种职责边界是否足以接受“协议/validator harness 的 S0”，不得把尚未签发的 S1 配置虚构为已存在。

## G. Findings

按 finding ID byte value 排序；每项说明阻断对象、可复现方式和为何不能由现有 fail-closed 路径处理。

- finding IDs：
- finding 详情：

## H. 最终裁定

- decision：`PROTOCOL_ACCEPTED` / `PROTOCOL_REJECTED`
- allowed_next_action：接受时仅可为 `request-s1`；拒绝时仅可为 `stop`
- reason：
- timestamp：

无论结论如何，本工作单本身都不签发 S1，不创建 experiment identity，也不授权真实 1K dry-run。

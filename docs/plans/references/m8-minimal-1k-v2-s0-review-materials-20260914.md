# M8 最小 1K 协议 v2 独立 S0 审查材料

- 状态：`S0_V2_MATERIALS_READY / VERDICT_BLANK / NOT_EXECUTION_AUTHORIZED`
- drafting party：`ai-assistant`
- owner：`justtodo123`
- reviewed object commit：`1f1d147deb9fd9b28338851f00f9cbbbc5c26614`
- review package commit：待本材料独立提交后填写；reviewer 应使用实际包含本文件的 commit，并验证其为 object commit 后代
- protocol SHA-256 / bytes / LF：`1a6be348b8d0396ecf44943b582e94bee2a80dcbe0277a16fcd86141adc9aeda / 6379 / 102`
- schema SHA-256 / bytes：`d29d368083c2a62b1f9687aa8fd870a1c8f22df655ffc185a17095c4da3af14e / 17214`
- validator SHA-256 / bytes / LF：`879b7b3b74d50bb6807269af2a03be541636a9575c8ae3f595bcf053a0245077 / 6383 / 25`

## v1 findings 闭合声明

| Finding | v2 闭合点 |
| --- | --- |
| m8-s0-001 | 双 commit 语义；后代与对象字节相同检查 |
| m8-s0-002 | 六类 payload 按 schema ID `oneOf`，object 全部拒绝额外字段 |
| m8-s0-003 | `jsonschema` Draft 2020-12 实际验证六类正例与 13 个关键负例 |
| m8-s0-004 | 固定 query counts、agreement、版本、40-hex commit、clean digest、observer config |
| m8-s0-005 | PCG64、chunk/query/gold ID、perturbation 与 4 个负向 fixture 均冻结 |
| m8-s0-006 | acquisition/measured boundary、进程树、network/write/redaction observer 与 fail closed |
| m8-s0-007 | logical-name grammar、typed REF、actor role、timestamp/digest/count/resource format |
| m8-s0-008 | 根外 evidence directory；cleanup receipt 先于 final validation/S2；失败强制 FAIL/stop |

## Reviewer 必查

1. 复算三个摘要并验证 object commit 与 package commit 的关系和对象字节；
2. 运行 `python tools/m8_validate_minimal_1k_protocol_v2.py`，并独立审阅/扩展负例；
3. 验证六类 schema 确实 closed，不能以 `oneOf` 重叠或 nested object 开放绕过；
4. 验证完整 identity→manifest→run→cleanup→validation→S2 正例可实例化且 REF 一致；
5. 验证 gate decision/actor/action 的跨字段映射是否仍有遗漏；
6. 验证 cleanup 失败、observer 失败、unexpected error、backend/input 不一致不能与 PASS/EVIDENCE_READY 并存；
7. 检查 deterministic workload 是否无歧义且足以产生 104 query/gold；
8. 检查 Windows observer 设计是否可实现，或是否仍只是不可验证的自然语言；
9. 检查 v2 是否越出八项 finding，或隐含 10K/backend selection/M8 admission；
10. 检查是否存在其他组合不可满足问题。

允许裁定仅为 `PROTOCOL_ACCEPTED/request-s1` 或 `PROTOCOL_REJECTED/stop`。本材料不预置 reviewer、verdict 或 finding，
不授权 S1、环境创建、依赖安装、输入生成或 dry-run。

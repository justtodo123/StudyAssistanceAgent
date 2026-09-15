# M8 最小 1K v3 独立 S0 复审材料 r02

- 状态：`INDEPENDENT_REVIEW_REQUIRED / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`
- predecessor audit：`m8-minimal-1k-v3-s0-rereview-audit-20260915-r01.md`
- reviewed object commit：`df78c1110a782b8c95edfda175840e6454835a94`
- 本轮只修复 `m8-v3-r01-s0-001`：observer ledger 必须非空且以 LF 结尾；旧记录全部保持不变。

## 修订内容

- observer ledger 校验在逐行解析前强制 `data` 非空且 `data.endswith(b"\n")`；
- 增加 `missing-final-lf` 和 `empty-observer` 两个 fail-closed mutation；
- 当前测试矩阵：5 个持久 graph + 22 个 fail-closed mutation；
- 未创建真实 identity、实验根或 venv；未安装 LanceDB；未生成真实 1K 输入；未运行 SQLite/LanceDB dry-run。

## reviewed object 核验摘要

| 对象 | SHA-256 | bytes | LF |
| --- | --- | ---: | ---: |
| protocol | `fec455349091afe91f7033651d8b93f6dbb67d989d7926a6f1bef92273414875` | 10063 | 150 |
| schema | `2dae3b8929a5e8d3b0c39fb4837de256b9e8b8cc694e48015e1d724cc1e41e13` | 2134 | 1 |
| graph validator | `e6a8ee5e8934a522e735715fb8c92b858a6425c7fea5e26c1d65c3867149e22d` | 16646 | 287 |
| fixture generator | `fb1344b2aa2e359b0896b85d72c8761b68735b359bf434805a4cd4eb41cc1cad` | 9228 | 213 |
| test harness | `a3d8563f9f68cdb43e3dc4417393338d39424b9a512b59b` | 5926 | 100 |

> 上表中的 test harness 摘要只作为历史材料中的字面值；Reviewer 必须从 reviewed object 独立重算，并以实际完整 SHA 为准。该对象在 r02 中仅更新 validator/test harness；protocol/schema/generator bytes 未改变。

Fixture tree：按 `fixture-tree-v1` 规则独立复算，预期 `e09c1e45eab38f72e9cc92e128f50d5e3ec4440d0d7d29f113c7617a57cd250a`，90 files / 41519 bytes。

## 必须复审

1. 独立核对 reviewed object commit、工作区状态和所有实际摘要；
2. 双路径复算 fixture tree：工作区 bytes 与 Git object bytes；
3. 重放五个持久 graph；
4. 在临时副本中删除 observer ledger 最终 LF，并同步 summary 与全部 REF，确认 exit 非 0；
5. 在临时副本中清空 observer ledger，并同步 summary 与全部 REF，确认 exit 非 0；
6. 确认拒绝原因是终止/非空约束，而非 stale digest/ref；
7. 重放 noncanonical event/input、invalid JSON，确认既有行为未退化；
8. 检查合法 success/failure graph 仍可通过；
9. 独立裁定 `m8-v3-r01-s0-001` 为 CLOSED/PARTIALLY_CLOSED/OPEN，并报告新的 findings。

## 允许命令

```bash
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/success
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/failure-cleanup
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/failure-observer
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/failure-runtime
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/failure-validation
```

Generator/test harness 会重写冻结 fixture，若运行须在仓库副本中执行；不得修改本仓库。

## 最终裁定格式

接受：`decision: PROTOCOL_ACCEPTED`、`allowed_next_action: request-s1`

拒绝：`decision: PROTOCOL_REJECTED`、`allowed_next_action: stop`

接受只表示可向 Owner 请求 S1，不自动授权 S1、真实环境或 1K dry-run。

# M8 最小 1K v3 独立 S0 复审材料 r01

- 状态：`INDEPENDENT_REVIEW_REQUIRED / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`
- drafting party：`ai-assistant`
- predecessor S0：`PROTOCOL_REJECTED / stop`
- predecessor audit：`m8-minimal-1k-v3-s0-independent-audit-20260915.md`
- correction record：`m8-minimal-1k-v3-fixture-tree-correction-20260915-r01.md`
- reviewed object commit：`1ccefe1640307fbae82ef09ab11700efaf951f9c`

旧审查材料和拒绝记录保持原字节不动。本材料只请求对修订对象重新执行独立 S0，不把旧拒绝改写成接受。

## 1. 修订范围

只处理 v3 S0 的两个 finding：

1. `m8-v3-s0-001`：以独立复算记录澄清旧材料摘要错误，并冻结修订对象的实际 fixture-tree 摘要；
2. `m8-v3-s0-002`：graph validator 对 input 与 observer JSONL 每行强制 `sa-json-c14n-v1` bytes，并新增两个 fail-closed mutation。

未签发 S1，未创建真实实验环境，未安装 LanceDB，未执行 SQLite/LanceDB 1K dry-run。

## 2. 修订对象摘要

| 对象 | SHA-256 | bytes | LF |
| --- | --- | ---: | ---: |
| `m8-minimal-1k-dry-run-protocol-v3.md` | `fec455349091afe91f7033651d8b93f6dbb67d989d7926a6f1bef92273414875` | 10063 | 150 |
| `schemas/m8-minimal-1k-artifacts-v3.schema.json` | `2dae3b8929a5e8d3b0c39fb4837de256b9e8b8cc694e48015e1d724cc1e41e13` | 2134 | 1 |
| `tools/m8_validate_minimal_1k_graph_v3.py` | `e6a8ee5e8934a522e735715fb8c92b858a6425c7fea5e26c1d65c3867149e22d` | 16646 | 287 |
| `tools/m8_generate_minimal_1k_v3_fixtures.py` | `fb1344b2aa2e359b0896b85d72c8761b68735b359bf434805a4cd4eb41cc1cad` | 9228 | 213 |
| `tools/m8_test_minimal_1k_graph_v3.py` | `a3d8563f9f68cdb15ab4009fc7a31fcd43e3dc4417393338d39424b9a512b59b` | 5926 | 100 |

Fixture tree 使用旧材料已声明的 `fixture-tree-v1` 算法：

```text
SHA-256: e09c1e45eab38f72e9cc92e128f50d5e3ec4440d0d7d29f113c7617a57cd250a
files: 90
bytes: 41519
```

## 3. 修复实现

- `jsonl_count()` 现在要求非空、LF 结尾、每行可解析，且 `line + LF == canonical(parsed_object)`；
- observer ledger 逐行执行相同 canonical bytes 比较；
- fixture generator 使用 canonical serializer 生成 chunks、queries、gold JSONL；
- harness 新增：
  - `noncanonical-event`
  - `noncanonical-input`
- 当前矩阵：5 个持久图 + 20 个 fail-closed mutation。

## 4. 可重放命令

只读审查可直接逐目录运行 validator。若要运行会重写 fixture 的 generator/harness，应先复制仓库到独立临时目录。

```bash
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/success
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/failure-cleanup
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/failure-observer
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/failure-runtime
python tools/m8_validate_minimal_1k_graph_v3.py docs/plans/references/fixtures/m8-minimal-1k-v3/failure-validation
python tools/m8_test_minimal_1k_graph_v3.py
```

起草阶段结果为：

```text
ALL PASS: 5 persistent graphs + 20 fail-closed mutations
```

该结果不是独立 S0 裁定。

## 5. Reviewer 必须独立核验

1. 从 reviewed object commit bytes 独立复算 fixture-tree；
2. 确认旧摘要不匹配属于材料记录错误，而不是 reviewer 使用另一份 tree；
3. 在临时副本中分别制造 non-canonical input 与 event JSONL，同时同步相关摘要，确认 validator 仍拒绝；
4. 确认 canonical 检查不会把合法失败图误判为 invalid graph；
5. 检查异常 JSONL 是否 fail-closed，而非产生未处理 traceback；
6. 检查修复是否引入新的组合不可满足或路径依赖；
7. 对两个 finding 分别裁定 `CLOSED / PARTIALLY_CLOSED / OPEN`；
8. 自行形成 verdict，不沿用起草方结论。

## 6. 复审边界

本轮复审只决定 v3 protocol/validator harness 是否可进入 `request-s1`。即使接受，也必须由 owner 另行签发 S1；不自动授权真实 identity、实验根、venv、依赖安装、1K/10K、后端选择、生产改动或 M8 admission。

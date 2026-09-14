# M8 最小 1K v3 独立 S0 审查材料

- 状态：`INDEPENDENT_REVIEW_REQUIRED / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`
- drafting party：`ai-assistant`
- owner authorization：`m8-minimal-1k-v3-implementation-validation-authorization-20260914.md`
- reviewed object commit：`50bea24df515f8d2956f619b2b92844f5f6eb194`
- 基线：v2 S0 `PROTOCOL_REJECTED / stop`；13 项 finding 保持冻结

## 1. 被审对象

| 对象 | SHA-256 | bytes | LF |
| --- | --- | ---: | ---: |
| `m8-minimal-1k-dry-run-protocol-v3.md` | `ed339a0ff6ed52413acb8c14262f92b3c88eb261169c49ccce94c58454bf2124` | 9993 | 150 |
| `schemas/m8-minimal-1k-artifacts-v3.schema.json` | `2dae3b8929a5e8d3b0c39fb4837de256b9e8b8cc694e48015e1d724cc1e41e13` | 2134 | 1 |
| `tools/m8_validate_minimal_1k_graph_v3.py` | `edd4f125f93f60a2f1885cdf93cb7c13087eb8b373b65c56d4b3f17e81ea04b4` | 16165 | 277 |
| `tools/m8_generate_minimal_1k_v3_fixtures.py` | `538a0050239db2e3856329b6e5d28d002b94ec688b23d37ffad37bf69f2f74d6` | 9174 | 213 |
| `tools/m8_test_minimal_1k_graph_v3.py` | `06d8864bae4b1705b23e8309fa156791a408caa61adb8bd88abe9e0130eaf3df` | 5383 | 98 |

Fixture tree 摘要采用 `fixture-tree-v1`：按相对 POSIX 路径 byte value 排序，对每个文件依次输入
`4-byte big-endian path length || path bytes || 8-byte big-endian content length || content bytes`。
冻结结果：`51d7723caf5a77f90d64baf6210d49e948fa8420be3daab03a5cc58dc39963e2`，90 files，41519 bytes。

## 2. 审查职责

Reviewer 应独立判断，不接受起草方预置 verdict。至少检查：

1. v3 是否明确把单文件结构与跨 artifact graph 验证分层，且没有把 JSON Schema 能力夸大为可解析引用 bytes；
2. graph validator 是否实际读取调用方指定目录，并拒绝缺失/未知 artifact、路径逃逸、非 canonical bytes、错 experiment ID；
3. typed REF 是否绑定实际 role、schema ID、logical name、SHA-256 和 byte count；
4. manifest 是否复算成员 bytes、digest 与 JSONL record count；
5. S0→S3 actor、decision、action、前驱和 authority 是否机械闭合；
6. S2 success 是否必须同时依赖已授权 S1、PASS validation 和 CLEANED cleanup；
7. observer ledger 的事件结构、sequence、kind、生命周期、摘要与聚合是否 fail-closed；
8. cleanup、observer、runtime、validation 四类失败是否能形成合法失败图，而不能伪装为成功；
9. 五个持久 fixture 与 18 个 mutation 是否覆盖 v2 十三项 finding 的关键 fail-open 类别；
10. 是否仍存在组合不可满足、测试仅自证自身、或协议声称已闭合但 validator 未实现的约束。

## 3. 可重放命令

```bash
python tools/m8_generate_minimal_1k_v3_fixtures.py
python tools/m8_test_minimal_1k_graph_v3.py
python tools/m8_validate_minimal_1k_graph_v3.py \
  docs/plans/references/fixtures/m8-minimal-1k-v3/success
```

期望测试摘要为：

```text
ALL PASS: 5 persistent graphs + 18 fail-closed mutations
```

该输出只说明当前 harness 按其实现通过，不预先证明 S0 应接受。Reviewer 必须审阅代码和冻结 fixture，不得只采信摘要。

## 4. 已验证但不构成 S0 裁定的事实

起草阶段已运行：

- 三个 v3 Python 文件 `py_compile`；
- 五个持久图逐目录验证；
- 18 个临时副本 mutation 均被拒绝；
- `m8_validate_p1_materials.py`：88/88；
- `m8_validate_p0_r02.py`：77/77；
- `git diff --check`。

这些是材料准备事实，不是独立 reviewer 的技术接受，也不授权 S1。

## 5. 明确边界

本材料、worksheet、fixture 与 validator 均不是 dry-run evidence。独立 S0 接受前不得创建真实 experiment identity、实验根或 venv，不得安装 LanceDB、生成真实 1K 输入或运行 SQLite/LanceDB。即使 S0 接受，也只允许 owner 另行决定是否签发 S1；不会自动授权 1K、10K、后端选择、生产修改或 M8 admission。

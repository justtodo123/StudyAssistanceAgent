# M8 最小 1K v3 独立 S0 审查记录

- reviewer：`s0-independent-reviewer-20260914`
- reviewed object commit：`50bea24df515f8d2956f619b2b92844f5f6eb194`
- review package commit：`1b9fe314c12096f77b26ed8018dbae2ef7518d05`
- decision：`PROTOCOL_REJECTED`
- allowed_next_action：`stop`
- timestamp：`2026-09-14T21:52:27+08:00`

## 独立性披露

Reviewer 声明未参与 v3 protocol、schema、graph validator、fixture generator 或 test harness 的起草。审查基于只读静态代码审查、冻结文件摘要重算、持久 fixture 逐目录 validator 重放，以及 v2 审查记录对照。

独立性依据仅为 reviewer 身份名称、审查会话和代码路径上的会话分离。当前仓库状态无法密码学证明 reviewer 从未参与历史讨论、历史起草或其他会话；名称和会话分离不等于完整人员独立性证明。

审查期间未安装依赖、未创建 venv、未安装 LanceDB、未生成真实 1K 输入、未创建真实实验根，未运行 SQLite/LanceDB dry-run。

## 冻结摘要核验

protocol、schema、graph validator、fixture generator、test harness 以及 reviewed object commit 均与审查材料声明匹配。

fixture-tree 文件数和总字节数匹配：`90 files / 41519 bytes`；但按 `fixture-tree-v1` 规则重算得到：

```text
6d4a2d16ba97b90331ec796daf6869356737a7256935130381653ce6c9fb1b8a
```

审查材料声明的冻结摘要为：

```text
51d7723caf5a77f90d64baf6210d49e948fa8420be3daab03a5cc58dc39963e2
```

因此 fixture-tree 摘要核验失败。

## 重放结果

- success graph：`VALID_GRAPH verdict=PASS`
- failure-cleanup graph：合法失败图，`VALID_GRAPH verdict=FAIL`
- failure-runtime graph：合法失败图，`VALID_GRAPH verdict=FAIL`
- failure-validation graph：合法失败图，`VALID_GRAPH verdict=FAIL`
- failure-observer：并行重放被执行环境安全分类器超时拦截；代码和冻结 fixture 静态检查显示结构一致
- 未运行 generator 和 test harness，因为其会重写仓库内冻结 fixture

## v2 finding 处置摘要

- `m8-v2-s0-001`：`REFRAMED_BY_RESPONSIBILITY_SPLIT`
- `m8-v2-s0-002`：`CLOSED`
- `m8-v2-s0-003`：`CLOSED`
- `m8-v2-s0-004`：`CLOSED`
- `m8-v2-s0-005`：`CLOSED`
- `m8-v2-s0-006`：`CLOSED`
- `m8-v2-s0-007`：`CLOSED`
- `m8-v2-s0-008`：`PARTIALLY_CLOSED`
- `m8-v2-s0-009`：`PARTIALLY_CLOSED`
- `m8-v2-s0-010`：`PARTIALLY_CLOSED`
- `m8-v2-s0-011`：`CLOSED`
- `m8-v2-s0-012`：`CLOSED`
- `m8-v2-s0-013`：`REFRAMED_BY_RESPONSIBILITY_SPLIT`

Reviewer 认为 v2 的主体跨文件 graph、typed REF、gate authority、合法失败图和 S2 authority 问题已大体关闭或按职责边界重新划分；但 v3 仍存在以下阻断。

## Findings

### m8-v3-s0-001 — 冻结 fixture-tree 摘要不匹配

复现：读取 `docs/plans/references/fixtures/m8-minimal-1k-v3/`，按相对 POSIX 路径 UTF-8 byte value 排序，对每个文件依次输入路径长度、路径 bytes、内容长度、内容 bytes 后计算 SHA-256，得到 `6d4a2d16...f9fb1b8a`，而材料声明为 `51d7723c...9963e2`。

阻断理由：路径集合和总字节数一致不能证明内容逐字节一致；validator 不校验 fixture-tree manifest，因此无法处理该冻结材料摘要不一致。在解释或更新摘要前，不能证明重放对象就是材料声明的冻结 fixture tree。

### m8-v3-s0-002 — JSONL canonicalization 未被 graph validator 强制

复现：复制 success fixture 到临时目录，将 `events/network.jsonl` 的一行改为语义等价但非 canonical 的 JSON（增加空格或调整键顺序），同步修改 `run-report.json` 中对应 summary 的 SHA-256 和 byte_count，并运行：

```bash
python tools/m8_validate_minimal_1k_graph_v3.py <temporary-copy>
```

静态依据：validator 对 observer ledger 和 input JSONL 执行 JSON parse、字段、sequence、kind、生命周期、summary、digest、bytes、count 检查，但未比较每一行是否等于 canonical JSON 序列化结果。摘要 digest 只能证明 summary 指向修改后的 bytes，不能证明 bytes 满足 canonicalization 规则。

阻断理由：协议冻结了 JSONL canonicalization，但当前 validator 未机械实现；非 canonical ledger 或 input line 在同步摘要后可能被接受，且现有 mutation 未覆盖该 fail-open。

## 最终裁定

```text
decision: PROTOCOL_REJECTED
allowed_next_action: stop
```

理由：fixture-tree 冻结摘要与实际内容不匹配，且 graph validator 对协议声明的 JSONL canonicalization 未机械实现。当前不得签发 S1，不得创建 experiment identity，不得生成真实 1K 输入，不得安装 LanceDB，不得运行 SQLite/LanceDB dry-run，也不改变 v2 历史拒绝结论。

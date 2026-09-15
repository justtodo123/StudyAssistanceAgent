# M8 最小 1K v3 独立 S0 复审记录 r01

- reviewer：`s0-independent-reviewer-20260915-r01`
- reviewed object commit：`1ccefe1640307fbae82ef09ab11700efaf951f9c`
- review package commit：`0514ddad91620e7d691afc9754afd528fcf2faa1`
- decision：`PROTOCOL_REJECTED`
- allowed_next_action：`stop`
- timestamp：`2026-09-15T09:50:36+08:00`

## 独立性与边界

Reviewer 声明未参与 v3 原对象或本轮修订起草，使用独立身份和审查会话，独立读取冻结对象、Git object bytes 和 fixture，并执行双路径摘要复算、五个持久 graph 重放及临时副本负例。仓库无法密码学证明 reviewer 未参与历史讨论或其他会话；名称和会话分离不等于完整人员独立性证明。

审查期间未修改仓库，未创建真实 identity、实验根或 venv，未安装依赖或 LanceDB，未生成真实 1K 输入，未运行 SQLite/LanceDB dry-run，未读取 `D:\111_Others_Subjects`，未签发 S1。开始和结束时工作区均干净。

## 提交与摘要核验

- HEAD：`0514ddad91620e7d691afc9754afd528fcf2faa1`
- reviewed object 是 review package 的祖先：是
- protocol、schema、graph validator、fixture generator、test harness：均与 r01 材料冻结值匹配

Reviewer 正文表格中的 schema/test harness 摘要存在省略或抄写错误，但随后明确给出 schema 实际完整摘要为材料值，整体裁定不依赖这些截短字面量。本记录不把截短值登记为冻结摘要。

Fixture tree 双路径复算结果：

```text
SHA-256: e09c1e45eab38f72e9cc92e128f50d5e3ec4440d0d7d29f113c7617a57cd250a
files: 90
bytes: 41519
path sets equal: yes
byte-different files: 0
```

当前工作区 bytes 与 reviewed object Git bytes 一致，并与 r01 冻结值匹配。旧材料的 `51d7723c...` 属于摘要记录错误或未提交版本；没有证据表明前次 reviewer 审查了另一份 tree。

## 持久 graph 重放

- success：`VALID_GRAPH verdict=PASS`，exit 0
- failure-cleanup：`VALID_GRAPH verdict=FAIL`，exit 0
- failure-observer：`VALID_GRAPH verdict=FAIL`，exit 0
- failure-runtime：`VALID_GRAPH verdict=FAIL`，exit 0
- failure-validation：`VALID_GRAPH verdict=FAIL`，exit 0

四个 failure graph 的 exit 0 只表示其失败语义内部合法。

## Canonicalization 负例

Reviewer 在临时目录同步全部受影响摘要和 REF 后独立验证：

- noncanonical event：exit 1，因 `observer network: non-canonical JSONL line` 拒绝；
- noncanonical input：exit 1，因 `JSONL line is not canonical JSON` 拒绝；
- invalid observer JSON：exit 1，受控拒绝，无 traceback；
- test harness：`ALL PASS: 5 persistent graphs + 20 fail-closed mutations`。

但删除 observer ledger 最终 LF、同步 summary 和所有相关 REF 后，validator 返回：

```text
exit=0
VALID_GRAPH verdict=PASS
```

## 历史 finding disposition

- `m8-v3-s0-001`：`CLOSED`
- `m8-v3-s0-002`：`PARTIALLY_CLOSED`

`m8-v3-s0-002` 已关闭语义等价非 canonical event/input 和 invalid JSON 的路径，但 observer ledger 尚未机械要求非空和最终 LF。

## 新 Finding

### `m8-v3-r01-s0-001` — observer ledger missing-final-LF accepted

复现：复制 success fixture，删除 `events/network.jsonl` 最终 LF，同步 `run-report.json` observer summary 以及所有直接和间接 REF 后运行 graph validator。实际得到 exit 0 与 `VALID_GRAPH verdict=PASS`。

代码依据：observer ledger 路径直接对 `data.splitlines()` 逐行解析，没有复用会检查 `data.endswith(b"\n")` 的 `jsonl_count()`，因此非空、逐行 canonical 但缺少最终 LF 的 ledger 可被接受。

阻断理由：协议要求 observer ledger 使用 canonical JSON + LF；当前实现允许违反该约束的 observer evidence 进入有效 S2/S3 graph，构成 fail-open。

## 最终裁定

```text
decision: PROTOCOL_REJECTED
allowed_next_action: stop
```

历史 fixture-tree finding 已关闭，JSONL 主要修复有效，但 observer ledger 最终 LF 约束仍未闭合。不得进入 `request-s1`，不得创建真实实验环境或开始 1K dry-run。

# M8 最小 1K v3 独立 S0 复审记录 r02

- reviewer：`s0-independent-reviewer-20260915-r02`
- reviewed object commit：`df78c1110a782b8c95edfda175840e6454835a94`
- review package commit：`d2a76520c04aa94cb0d0ac06fa15d71845ca5613`
- decision：`PROTOCOL_REJECTED`
- allowed_next_action：`stop`
- timestamp：`2026-09-15`

## 独立性与审查边界

Reviewer 声明未参与 r02 修订起草，通过独立会话、Git object 与工作区 bytes 双路径读取和独立同步负例形成结论。仓库不能密码学证明 reviewer 未参与其他历史会话；名称与会话分离不等于完整人员独立性证明。

审查期间未修改仓库，未创建真实 identity、实验根或 venv，未安装依赖或 LanceDB，未生成真实 1K 输入，未执行 SQLite/LanceDB dry-run，未读取 `D:\111_Others_Subjects`，未签发 S1。开始和结束时工作区均干净。

## 提交和对象核验

- HEAD：`d2a76520c04aa94cb0d0ac06fa15d71845ca5613`
- reviewed object 是 review package 的祖先：是
- protocol、schema、fixture generator：摘要与材料一致
- fixture tree 双路径结果一致：

```text
SHA-256: e09c1e45eab38f72e9cc92e128f50d5e3ec4440d0d7d29f113c7617a57cd250a
files: 90
bytes: 41519
path sets equal: yes
byte-different files: 0
```

但 r02 材料没有准确记录修订对象中的 validator 与 harness bytes：

```text
graph validator actual:
4636caa05302c2ec13360f51b70e8dcdbf4482fe11465337c5623d3a6dee36cc
16773 bytes / 288 LF

test harness actual:
c915a551551609ac0f970fc05cb60f05921620582f295667fc2db25afc728f1e
6165 bytes / 102 LF
```

材料仍将 graph validator 写为修订前的 `e6a8ee5e...7149e22d / 16646 / 287`，且 test harness 使用截短旧值。

## 持久 graph 重放

- success：exit 0，`VALID_GRAPH verdict=PASS`
- failure-cleanup：exit 0，`VALID_GRAPH verdict=FAIL`
- failure-observer：exit 0，`VALID_GRAPH verdict=FAIL`
- failure-runtime：exit 0，`VALID_GRAPH verdict=FAIL`
- failure-validation：exit 0，`VALID_GRAPH verdict=FAIL`

## r01 finding 回归

Reviewer 在临时目录同步 observer summary、run-report canonical bytes、validation-report REF、S2 REF、S3 REF 及其他受影响链后验证：

- missing-final-LF：exit 1，明确报 `JSONL must be non-empty and LF terminated`，无 stale digest/REF 错误，无 traceback；
- empty observer：exit 1，明确报非空/LF 约束，并伴随 lifecycle 失败，无 stale digest/REF 错误，无 traceback；
- noncanonical event/input、invalid observer/input JSON：均受控拒绝，无 traceback。

因此：

```text
m8-v3-r01-s0-001: CLOSED
```

## Findings

### `m8-v3-r02-s0-001` — r02 graph validator 冻结摘要错误

材料记录的 validator 摘要、bytes 和 LF 属于修订前对象，与 reviewed object 中包含本轮关键 LF/nonempty 检查的实际 bytes 不一致。Review package 未准确冻结其声称送审的 validator，属于阻断性材料缺陷。

### `m8-v3-r02-s0-002` — 新增 harness mutation 仅由 stale summary 拒绝

Harness 的 `missing-final-lf` 和 `empty-observer` 只修改 ledger bytes，没有同步 run-report observer summary、run-report canonical bytes和后续 validation/S2/S3 REF；harness 又只检查 `returncode != 0`，不检查具体拒绝原因。因此即使移除 LF/nonempty 检查，这两个 mutation 仍可能因陈旧 digest、byte count、event count 或 REF 而显示 `PASS negative`。

Reviewer 独立构造的完整同步负例证明当前 validator 实现本身正确，但不能弥补冻结 harness 的机械覆盖缺口。

## 历史完整性

首次 v3 与 r01 历史拒绝记录未被就地改写。r01 审查记录的 Git blob 在相关提交间保持一致。

## 最终裁定

```text
decision: PROTOCOL_REJECTED
allowed_next_action: stop
```

r01 observer ledger 缺陷本身已经关闭，但 r02 材料未准确冻结修订后的 validator bytes，新增 harness mutation 也未真正针对本轮约束。不得签发 S1，不得创建真实 experiment identity 或实验环境，不得授权或执行真实 1K dry-run。

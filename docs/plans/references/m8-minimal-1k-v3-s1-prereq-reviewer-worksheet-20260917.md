# M8 最小 1K v3 S1 prerequisite 独立复核工作单

- 状态：`VERDICT_BLANK / NOT_A_DECISION / NOT_EXECUTION_AUTHORIZED`
- reviewed candidate commit：`50300667983f631dbb13bc17c8e659e1c4230d48`
- review package identity：本文件所在的 handoff-only commit；Reviewer 必须从 Git 解析并记录完整 40-hex
- review materials：`m8-minimal-1k-v3-s1-prereq-review-materials-20260917.md`

> 本工作单必须保持 blank，直到未参与 candidate 或 package 修改的独立 Reviewer 在只读环境中自行填写。
> 它不是 gate，不预置接受，不授权执行。

## 1. Reviewer 身份与独立性

- reviewer name / identity：
- review timestamp：
- 是否参与 candidate `8e006b3d1e7630a650718a515e50644c67940e37` 修改：
- 是否参与 candidate `50300667983f631dbb13bc17c8e659e1c4230d48` 修改：
- 是否参与 freeze、Builder record、materials 或 worksheet 起草：
- 是否修改任何 candidate/package object：
- 主体分离与独立性依据：
- 无法密码学证明的独立性限制：
- OS / Python / Git：
- review clone absolute path：

若 Reviewer 修改 candidate 或 package，停止填写；该 Reviewer 已转为 fixer，须由另一位未参与者重新终审。

## 2. Commit、clone 与 ancestry

- package checkout 初始 `git status --porcelain=v1`：
- package HEAD（完整 40-hex）：
- candidate commit（完整 40-hex）：
- `git cat-file -t <candidate>`：
- `git cat-file -t <package>`：
- `git merge-base --is-ancestor <candidate> <package>` return code：
- candidate 是否为 package 祖先：
- review clone 是否 full/non-shallow：
- object alternates 是否 absent：
- detached candidate checkout HEAD：
- detached checkout 初始 status：

## 3. Package-only path boundary

`git diff-tree --no-commit-id --name-status -r <candidate> <package>` actual output：

```text

```

- package path count（预期 4）：
- freeze artifact：
- Builder self-check record：
- review materials：
- blank worksheet：
- 是否存在任何额外 path：
- `docs/plans/references/README.md` candidate/package blob 是否相同：
- `tools/README.md` candidate/package blob 是否相同：

从 freeze artifact 读取全部 119 个 candidate path 并逐一比较：

- compared path count：
- unchanged object count：
- changed candidate path count：
- changed candidate paths（预期空）：
- boundary result：`PASS / FAIL`

## 4. Package freeze artifact

- artifact path：
- SHA-256：
- byte count：
- LF count：
- UTF-8 / no BOM：
- no CR：
- exactly one final LF：
- compact sorted canonical JSON：
- `format`：
- `purpose`：
- `canonicalization_id`：
- `source_commit`：
- `aggregate.file_count`：
- `aggregate.total_byte_count`：
- `worktree_comparison.status`：
- `divergent_paths`：
- artifact 是否与 candidate Git objects 独立复算一致：

## 5. 29 个 non-fixture frozen objects

| path | Git blob | SHA-256 | bytes | LF | match |
| --- | --- | --- | ---: | ---: | --- |
| `.gitattributes` |  |  |  |  |  |
| references README |  |  |  |  |  |
| protocol v3 |  |  |  |  |  |
| generator spec |  |  |  |  |  |
| observer spec |  |  |  |  |  |
| artifacts schema |  |  |  |  |  |
| observer-config schema |  |  |  |  |  |
| redaction-registry schema |  |  |  |  |  |
| S1 config schema |  |  |  |  |  |
| S1 gate schema |  |  |  |  |  |
| observer-config template |  |  |  |  |  |
| redaction-registry template |  |  |  |  |  |
| S1 config template |  |  |  |  |  |
| S1 gate template |  |  |  |  |  |
| `tools/README.md` |  |  |  |  |  |
| prerequisite freeze tool |  |  |  |  |  |
| formal generator |  |  |  |  |  |
| fixture generator |  |  |  |  |  |
| synthetic observer |  |  |  |  |  |
| environment probe |  |  |  |  |  |
| mock-only runner |  |  |  |  |  |
| prerequisite freeze tests |  |  |  |  |  |
| generator tests |  |  |  |  |  |
| graph harness |  |  |  |  |  |
| observer tests |  |  |  |  |  |
| S1 controls tests |  |  |  |  |  |
| aggregate suite |  |  |  |  |  |
| graph validator |  |  |  |  |  |
| S1 preflight validator |  |  |  |  |  |

- fixture graph count / member count / total paths：
- 90 fixture objects all match：
- total 119 objects all match：

## 6. Strict clean-clone freeze

- strict freeze run 1 path：
- run 1 SHA-256 / bytes / LF：
- strict freeze run 2 path：
- run 2 SHA-256 / bytes / LF：
- run 1 与 run 2 byte-identical：
- `worktree_comparison.status`：
- `divergent_paths`：
- package freeze 与 strict freeze object facts 一致：
- whole-file difference 是否仅为 `NOT_REQUESTED` vs `MATCH`：

## 7. Portability remediation

- 首个 candidate fresh-clone failure 是否复现/由记录充分证明：
- failure 是否为 4 components × 2 const mismatches：
- 主 checkout observer physical bytes / SHA：
- candidate observer Git-object bytes / SHA：
- CRLF count/delta 是否解释精确：
- controls test 是否只规范化 CRLF pair：
- residual CR 是否 fail closed：
- schema const 是否绑定 LF Git-object bytes：
- replay clone 中是否未 repair：
- final candidate portability disposition：`PASS / FAIL`

## 8. Syntax 与 aggregate

- 13 个 candidate Python tools compile result：
- aggregate command / return code：
- aggregate final marker：
- 16 项是否全部 PASS：
- aggregate result：`PASS / FAIL`

## 9. Graph harness

- command / return code：
- five generated fixtures：
- five committed fixtures：
- containment directory-junction：
- fixture-generator output junction：
- injected `lstat()` failure：
- backend `per_query` negative cases：
- process phase missing/duplicate/reordered：
- measured outbound / listener failures：
- canonical/nonempty/final-LF mutations：
- causal mutation checks：
- sensitivity proofs：
- final marker（预期 5 / 45 / 2）：
- harness result：`PASS / FAIL`

> 五个 persistent graph 都应 process exit 0；semantic verdict 区分 PASS/FAIL。

## 10. Focused suites 与 historical regressions

| check | command / actual result | expected | match |
| --- | --- | --- | --- |
| deterministic generator |  | 27/27 |  |
| synthetic observer |  | 20/20 |  |
| S1 controls |  | 13/13 |  |
| S1 prerequisite freeze self-test |  | dedicated PASS marker |  |
| existing review freeze |  | hermetic PASS marker |  |
| historical P1 materials |  | 88/88 |  |
| historical P0/P1 r02 |  | 77/77 |  |

## 11. Repository integrity与结束状态

- `git diff --check`：
- strict no-reflog fsck command / return code：
- unexpected fsck output：
- candidate clone final `git status --porcelain=v1`：
- package checkout final status：
- `.claude/tmp/`、logs 或 test outputs 是否进入 package：

## 12. Safety与权限检查

- 创建真实 experiment identity/root：
- 创建正式 evidence root：
- 创建真实执行 venv：
- 安装/升级依赖：
- 生成正式 1K input：
- 运行 SQLite/LanceDB：
- 签发 S1/S2/S3：
- 修改 production：
- 访问 `D:\111_Others_Subjects`：
- push origin：
- backend selection / M8 admission：

以上各项预期均为 `NO`。

## 13. Findings

| ID | severity | path:line | failure scenario | evidence | required remediation |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

- blocking finding count：
- non-blocking finding count：

## 14. Final verdict（必须由独立 Reviewer 填写）

- verdict：`S1_PREREQUISITES_ACCEPTED / S1_PREREQUISITES_REJECTED`
- allowed next action：`request-owner-s1-decision / stop`
- rationale：
- reviewer signature / identity：
- signed timestamp：

> 即使选择 `S1_PREREQUISITES_ACCEPTED`，本工作单也不签发 S1，不等于 `DRY_RUN_AUTHORIZED`，不授权创建真实 identity、
> root、venv、安装依赖、生成正式输入、运行后端、S2、S3 或 M8 admission。

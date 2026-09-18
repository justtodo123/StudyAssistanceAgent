# M8 最小 1K v3 S1 prerequisite 独立 Reviewer worksheet

- 状态：`VERDICT_BLANK / NOT_A_DECISION / NOT_EXECUTION_AUTHORIZED`
- reviewed candidate commit：`6f9cf4617e79462130737eaf78cdb392b02b6664`
- review package identity：本文件所在 handoff-only commit；从 Git 解析完整 40-hex：
- review materials：`m8-minimal-1k-v3-s1-prereq-rereview-materials-20260918-r01.md`

> 本工作单必须保持 blank，直到未参与 candidate 或 package 修改的独立 Reviewer 在只读环境中自行填写。
> 不预置接受、拒绝、Builder verdict 或 S1 gate，不授权执行。

## 1. Reviewer 身份与独立性

- reviewer name / identity：
- review timestamp：
- 是否参与 replacement candidate `6f9cf4617e79462130737eaf78cdb392b02b6664` 修改：
- 是否参与 rejected candidate/package 修改：
- 是否参与 freeze、remediation、materials 或 worksheet 起草：
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
- package direct parent（完整 40-hex）：
- `git merge-base --is-ancestor <candidate> <package>` return code：
- candidate 是否为 package 祖先：
- review clone 是否 full/non-shallow：
- object alternates 是否 absent：
- replacement refs 是否 absent：
- detached candidate checkout HEAD：
- detached checkout 初始 status：

## 3. Package-only path boundary

`git diff-tree --no-commit-id --name-status -r <candidate> <package>` actual output：

```text

```

- package path count（预期 4）：
- freeze artifact path：
- Builder remediation path：
- rereview materials path：
- blank worksheet path：
- 是否存在任何额外 path：
- candidate/package closure path 是否均未变化：

从 freeze artifact 读取全部 123 个 candidate path 并逐一比较：

- compared path count：
- unchanged object count：
- changed candidate path count：
- changed candidate paths（预期空）：
- mode/OID/SHA-256/bytes/LF facts 是否全部一致：
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
- `closure_version`：
- `source_commit`：
- manifest blob/OID facts：
- `aggregate.file_count`：
- `aggregate.total_byte_count`：
- closure digest：
- `worktree_comparison.status`：
- `divergent_paths`：
- artifact 是否与 candidate Git objects 独立复算一致：

## 5. Manifest closure and 123 frozen objects

- manifest target-commit binding：
- bootstrap authority chain：
- five graph names：
- generated fixture member count：
- expanded fixture object count（预期 90）：
- total frozen object count（预期 123）：
- all paths normalized/unique/relative/non-symlink：
- forbidden ambient path classes rejected：
- undeclared read/subprocess fail-closed checks：
- all 123 object facts match candidate Git objects：
- changed object paths（预期空）：

| path | Git blob OID | SHA-256 | bytes | LF | mode | package match |
| --- | --- | --- | ---: | ---: | --- | --- |
|  |  |  |  |  |  |  |

## 6. Strict clean-clone freezes

- strict clone path：
- strict freeze run 1 path：
- run 1 SHA-256 / bytes / LF：
- strict freeze run 2 path：
- run 2 SHA-256 / bytes / LF：
- run 1 与 run 2 byte-identical：
- `worktree_comparison.status`：
- `divergent_paths`：
- package 与 strict freeze object facts 一致：
- whole-file difference 是否仅为 `NOT_REQUESTED` vs `MATCH`：

## 7. Portability remediation

- historical CRLF failure 是否复现/由记录充分证明：
- 主 checkout observer physical bytes / SHA：
- candidate observer Git-object bytes / SHA：
- CRLF pair normalization 是否限定且明确：
- residual CR 是否 fail closed：
- schema constants 是否绑定 LF Git-object bytes：
- replay clone 中是否未 repair：
- final portability disposition：`PASS / FAIL`

## 8. Syntax 与 closed aggregate

- candidate Python tools compile result：
- aggregate default command / return code：
- aggregate explicit `--gating-only` command / return code：
- 两种 gating output 是否等价：
- aggregate first marker：
- aggregate final marker：
- manifest contract PASS：
- closure-bound syntax PASS：
- execution policy and fail-closed regressions PASS：
- declared read/subprocess enforcement PASS：
- subprocess output oracle PASS：
- external closure materialization PASS：
- per-child runtime isolation PASS：
- manifest dispatch exact-once PASS：
- closed child suites PASS：
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
- final marker：
- harness result：`PASS / FAIL`

> 五个 persistent graph 都应 process exit 0；semantic verdict 区分 PASS/FAIL，不得把合法 failure graph 的语义结果误判为进程失败。

## 10. Focused suites

| check | command / actual result | expected | match |
| --- | --- | --- | --- |
| deterministic generator |  | 27/27 |  |
| synthetic observer |  | 20/20 |  |
| S1 controls |  | 14/14；canonical declared templates |  |
| S1 prerequisite freeze self-test |  | dedicated PASS marker |  |
| existing hermetic S0 freeze regression |  | hermetic PASS marker |  |
| canonical S1 config template |  | 6008 bytes / expected SHA-256 |  |
| fresh clone `.pyc` / `__pycache__` check |  | zero side effects |  |

## 11. Historical replay（non-gating）

- explicit historical command：
- helper self-test command / return code：
- exact eight-object materialization verified：
- source historical validators unchanged：
- unique structural `REPO = Path(<literal>)` rewrite verified：
- unrelated cwd：
- sanitized environment：
- bounded output / timeout / cleanup：
- P1 expected / observed：88/88：
- P0/P1 r02 expected / observed：77/77：
- exact success marker：
- `HISTORICAL_REGRESSION_FAILED` absent on success：
- historical evidence marked non-gating：

## 12. Git integrity与结束状态

- `git diff --check` command / return code：
- `git fsck --full --strict --no-reflogs` command / return code：
- unexpected fsck output：
- candidate clone final `git status --porcelain=v1`：
- candidate clone final ignored-inclusive status：
- package checkout final status：
- `.claude/tmp/` preserved and not packaged：
- logs/test outputs/bytecode absent from package：

## 13. Safety与权限检查

| action | actual result (expected NO) | evidence |
| --- | --- | --- |
| create real experiment identity/root |  |  |
| create formal evidence root |  |  |
| create real execution venv |  |  |
| install/upgrade/uninstall dependencies |  |  |
| generate formal 1K input |  |  |
| run SQLite/LanceDB |  |  |
| issue S1/S2/S3 |  |  |
| modify production |  |  |
| access `D:\111_Others_Subjects` |  |  |
| push origin |  |  |
| select backend / advance M8 admission |  |  |

## 14. Findings

| ID | severity | path:line | failure scenario | evidence | required remediation |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

- blocking finding count：
- non-blocking finding count：
- unresolved finding disposition：

## 15. Final verdict（必须由独立 Reviewer 填写）

- decision：
- allowed next action：
- rationale：
- reviewer signature / identity：
- signed timestamp：

> 只能由独立 Reviewer 选择 `S1_PREREQUISITES_ACCEPTED / request-owner-s1-decision` 或
> `S1_PREREQUISITES_REJECTED / stop`。即使选择 ACCEPTED，本工作单也不签发 S1，不等于
> `DRY_RUN_AUTHORIZED`，不授权创建 identity、root、venv、安装依赖、生成正式输入、运行 backend、S2、S3 或 M8 admission。

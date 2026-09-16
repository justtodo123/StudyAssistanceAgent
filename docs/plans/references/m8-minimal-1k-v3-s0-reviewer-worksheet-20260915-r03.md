# M8 最小 1K v3 Reviewer B 独立 S0 终审工作单 r03

- 状态：`VERDICT_BLANK / NOT_A_DECISION / NOT_EXECUTION_AUTHORIZED`
- reviewed object commit：`8c7f598dd6da72b0f87be63ffdda853071eb77c0`
- review package identity：本文件所在的 handoff-only commit；Reviewer B 必须从 Git 解析并记录完整 40-hex
- review materials：`m8-minimal-1k-v3-s0-review-materials-20260915-r03.md`
- predecessor audit：`m8-minimal-1k-v3-s0-rereview-audit-20260915-r02.md`

> 本工作单必须保持 blank，直到未参与 candidate 修改的 Reviewer B 在只读环境中自行填写。它不是 gate，不预置接受。

## 1. Reviewer 身份与独立性

- reviewer name：
- reviewer identity/organization（如适用）：
- review timestamp：
- 是否参与 Candidate Commit A `c784079f810e82b57b56455633f47c022bff22ec`：
- 是否参与 Candidate Commit B `8c7f598dd6da72b0f87be63ffdda853071eb77c0`：
- 是否参与 freeze artifact/remediation/materials/worksheet 起草：
- 是否修改任何 candidate object：
- 主体分离与独立性依据：
- 无法密码学证明的独立性限制：
- OS / Python / Git：
- review clone absolute path：

若 Reviewer B 修改 candidate object，停止填写；Reviewer B 已转为 fixer，须由未参与修改的 Reviewer C 终审。

## 2. 初始状态、commit 与 ancestry

- package checkout 初始 `git status --porcelain=v1`：
- package HEAD（完整 40-hex）：
- package commit 是否等于本工作单登记值：
- candidate commit（完整 40-hex）：
- `git cat-file -t <candidate>`：
- `git cat-file -t <package>`：
- `git merge-base --is-ancestor <candidate> <package>` return code：
- candidate 是否为 package 祖先：
- review clone 是否 full/non-shallow：
- object alternates 是否 absent：
- detached candidate checkout HEAD：

## 3. Candidate/package path boundary

`git diff-tree --no-commit-id --name-status -r <candidate> <package>` actual output：

```text

```

- package 变化是否严格限于 5 个 handoff material：
- freeze artifact：
- remediation log：
- r03 review materials：
- r03 worksheet：
- references README：
- 是否存在任何额外 path：

Candidate path inventory 从 freeze artifact 读取。对全部 99 path 执行 candidate/package object 比较：

- compared path count：
- changed candidate path count：
- changed candidate paths（预期空）：
- candidate/package boundary：`PASS / FAIL`

## 4. Canonical freeze artifact

- artifact path：
- SHA-256：
- byte count：
- LF count：
- UTF-8 / no BOM：
- exactly one final LF：
- sorted keys / no spaces：
- `format`：
- `canonicalization_id`：
- `source_commit`：
- candidate file count / total bytes：
- fixture file count / total bytes：
- fixture-tree-v1 SHA-256：
- package artifact `worktree_comparison.status`：
- artifact 是否与 candidate Git objects 独立复算一致：

九个非 fixture frozen object 独立结果：

| path | Git blob | SHA-256 | bytes | LF | match |
| --- | --- | --- | ---: | ---: | --- |
| `.gitattributes` |  |  |  |  |  |
| protocol v3 |  |  |  |  |  |
| schema v3 |  |  |  |  |  |
| `tools/README.md` |  |  |  |  |  |
| freeze tool |  |  |  |  |  |
| fixture generator |  |  |  |  |  |
| freeze self-test |  |  |  |  |  |
| graph harness |  |  |  |  |  |
| graph validator |  |  |  |  |  |

## 5. Strict clean-clone freeze

- strict freeze run 1 path：
- strict freeze run 1 SHA-256 / bytes / LF：
- strict freeze run 2 path：
- strict freeze run 2 SHA-256 / bytes / LF：
- run 1 与 run 2 byte-identical：
- `worktree_comparison.status`：
- `divergent_paths`：
- object-only package freeze 与 strict freeze 的 object facts 一致：
- whole-file SHA 差异是否只由 `NOT_REQUESTED` vs `MATCH` 字段引起：
- freeze self-test output：

## 6. 五个 persistent graph

> 正确 oracle：五个 valid graph 的 process exit 均为 0；semantic verdict 区分 PASS/FAIL。

| graph | actual exit | actual output | expected match |
| --- | ---: | --- | --- |
| success |  |  |  |
| failure-cleanup |  |  |  |
| failure-observer |  |  |  |
| failure-runtime |  |  |  |
| failure-validation |  |  |  |

- 是否把 valid failure graph 错当作 nonzero：
- 五图总评：`PASS / FAIL`

## 7. 22 个 fail-closed mutation

逐项填 actual result 与目标错误，不得只写总数：

| mutation | actual | target/observed error | stale digest/REF only? |
| --- | --- | --- | --- |
| target-bytes |  |  |  |
| ref-role |  |  |  |
| ref-schema |  |  |  |
| logical-name |  |  |  |
| ref-digest |  |  |  |
| member-count |  |  |  |
| protocol-digest |  |  |  |
| gate-actor |  |  |  |
| s0-read-ref |  |  |  |
| s1-with-rejected-s0 |  |  |  |
| gate-decision-action |  |  |  |
| s2-missing-authority |  |  |  |
| observer-summary |  |  |  |
| event-sequence |  |  |  |
| noncanonical-event |  |  |  |
| missing-final-lf |  |  |  |
| empty-observer |  |  |  |
| noncanonical-input |  |  |  |
| failure-as-success |  |  |  |
| missing-artifact |  |  |  |
| unknown-artifact |  |  |  |
| path-escape |  |  |  |

- harness summary line：
- 22/22 是否全部 PASS：

## 8. Causal mutation 与 sensitivity proofs

| proof | actual result | exact target error / absence of forbidden error |
| --- | --- | --- |
| causal empty-observer |  |  |
| causal missing-final-lf |  |  |
| causal noncanonical-event |  |  |
| causal noncanonical-input |  |  |
| sensitivity final-lf-disabled |  |  |
| sensitivity nonempty-disabled |  |  |

- observer summary 是否重密封：
- run-report 是否 canonical 重写：
- validation-report REF 是否更新：
- S2 全部受影响 REF 是否更新：
- S3 S2 REF 是否更新：
- missing-final-lf 是否因 target final-LF/nonempty 约束拒绝：
- empty-observer 是否因 target nonempty 约束拒绝：
- stale digest/byte count/event count/REF 是否被 forbidden oracle 排除：
- 两项 sensitivity proof 是否证明 target check 可辨识：

## 9. Generator determinism 与 committed fixture equality

- generator run 1 output root：
- generator run 2 output root：
- run 1 file count / bytes / tree digest：
- run 2 file count / bytes / tree digest：
- run 1 与 run 2 path set equal：
- run 1 与 run 2 byte differences：
- run 1 与 committed fixture path set equal：
- run 1 与 committed fixture byte differences：
- 是否使用 `--replace-tracked` 修改 review checkout（必须否）：

## 10. Syntax、historical regression、Git 与结束状态

- Python syntax compilation：
- P1 materials：passed / total / failed：
- P0-r02 materials：passed / total / failed：
- candidate `git diff --check`：
- Git connectivity check：
- clone final `git status --porcelain=v1`：
- package checkout final `git status --porcelain=v1`：
- 审查期间是否修改仓库：

## 11. r02 findings disposition

### `m8-v3-r02-s0-001` — r02 freeze facts inaccurate

- disposition：`CLOSED / PARTIALLY_CLOSED / OPEN`
- Git-object-only freeze 是否从显式 full commit 生成：
- artifact 与独立复算是否一致：
- hostile PATH/replacement refs/alternates/symlink/gitlink 等 self-test：
- reason/evidence：

### `m8-v3-r02-s0-002` — causal mutations not fully resealed

- disposition：`CLOSED / PARTIALLY_CLOSED / OPEN`
- missing-final-lf：
- empty-observer：
- causal checks：
- sensitivity proofs：
- stale digest/REF exclusion：
- reason/evidence：

## 12. 新 findings

| finding ID | severity | summary | evidence | required disposition |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

- blocking finding count：
- non-blocking/deferred finding count：

## 13. 安全与授权边界复核

- 未创建真实 experiment identity：
- 未创建 experiment/evidence root：
- 未创建 venv：
- 未安装 LanceDB：
- 未生成真实 1K input：
- 未运行 SQLite/LanceDB dry-run：
- 未访问/复制 `D:\111_Others_Subjects`：
- 未选择 backend / 未修改 production / 未推进 M8 admission：
- 历史审查、授权、拒绝与更正记录保持不变：

## 14. 最终裁定（Reviewer B 留空）

- decision：
- allowed_next_action：
- reason：
- reviewer signature/identity：
- timestamp：
- independent audit record path/commit：

允许值仅为：

- 接受：`PROTOCOL_ACCEPTED` / `request-s1`
- 拒绝：`PROTOCOL_REJECTED` / `stop`

即使接受，也只允许向 Owner 请求 S1；本工作单不签发 S1、不授权真实环境、identity、输入生成或 1K dry-run，不授权 10K、
backend selection、生产修改或 M8 admission。

# M8 最小 1K v3 Reviewer-Fixer 修复记录

- reviewer-fixer：`reviewer-a-20260915`
- 角色：`reviewer-fixer / remediation author`
- 修复起点分支：`master`
- 修复起点 commit：`e397d4d1e897399ffbd0ae2c615c92c3d0c4cbdf`
- 前轮 reviewed object：`df78c1110a782b8c95edfda175840e6454835a94`
- 前轮 review package：`d2a76520c04aa94cb0d0ac06fa15d71845ca5613`
- 最终候选 commit：`8c7f598dd6da72b0f87be63ffdda853071eb77c0`
- review package identity：本文件所在的 handoff-only commit；完整 40-hex 必须由 Reviewer B 从 Git 解析并记录，不能自引用写入
- 状态：`REMEDIATION_COMPLETE / SELF_CHECK_PASS / NOT_AN_INDEPENDENT_S0_DECISION / NOT_EXECUTION_AUTHORIZED`

> 本记录由参与候选对象修改的 Reviewer A 编写，只记录修复、自查与交接事实。它不是独立 S0 裁定，不能签署
> `PROTOCOL_ACCEPTED`。r02 的 `PROTOCOL_REJECTED / stop` 在 Reviewer B 独立只读终审前持续有效。

## 1. 中断恢复与初始现场

本轮从已中断的脏工作区继续，不丢弃、不覆盖、不回退继承修改。接管时观察到 37 个已修改 tracked path、2 个 untracked
path，约 2991 insertions / 288 deletions；观察到的修改均位于本轮 M8 v3 remediation 范围。为保留恢复现场，在仓库外持续保留：

| 恢复证据 | bytes | SHA-256 |
| --- | ---: | --- |
| `D:\Git Demo\reviewer-a-interrupted-worktree-start.patch` | 230120 | `79d96ef3ca51c5834503d6d93fae67862e612c295796f02beac34928d7abb941` |
| `D:\Git Demo\reviewer-a-interrupted-index-start.patch` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

第二个 patch 为 0 bytes，表示接管时 index 没有 staged diff。两份恢复文件均未删除。修复期间没有执行 `git reset`、
`git clean`、`git checkout -- <path>`、`git restore` 或 `git stash`，没有删除未跟踪文件，没有回退到 HEAD 重新实现，也没有
修改或删除任何历史审查、授权、拒绝或更正记录。

## 2. 必须闭合的 r02 findings

### 2.1 `m8-v3-r02-s0-001` — 冻结摘要不准确

修复：新增 Git-object-only review freeze 工具与 hermetic 自测，从显式完整 40-hex candidate commit 读取 Git blob，不以工作区
bytes 或手抄摘要作为冻结事实。工具冻结每个候选文件的 Git blob OID、SHA-256、byte count 与 LF count，并按
`fixture-tree-v1` 复算 fixture tree。canonical freeze 使用 `sa-json-c14n-v1`：UTF-8、排序键、无空格、恰一个最终 LF。

Disposition（Reviewer A self-check）：`CLOSED_FOR_REVIEWER_B_VERIFICATION`。

### 2.2 `m8-v3-r02-s0-002` — mutation 由 stale summary/REF 拒绝

修复：harness 对 `missing-final-lf`、`empty-observer`、`noncanonical-event`、`noncanonical-input` 执行完整因果 mutation：

1. 修改目标 ledger/input bytes；
2. 重密封 observer summary 的 SHA-256、byte count、event count 与 status；
3. 重写 canonical run-report bytes；
4. 更新 validation-report REF；
5. 更新 S2 受影响 REF 与 canonical bytes；
6. 更新 S3 的 S2 REF 与 canonical bytes；
7. 以精确 failure oracle 断言目标错误，并禁止 stale digest、byte count、event count 或 REF 冒充通过；
8. 构造关闭 final-LF 或 nonempty 目标检查的 validator variant，证明 mutation 不会再被无关 stale 链拒绝。

`empty-observer` 允许同时命中预定义且独立的 summary minimum 与 lifecycle 错误；这不替代 nonempty 目标错误。正式矩阵为 5 个
persistent graph、22 个 fail-closed mutation、4 个 causal mutation check 与 2 个 observer-boundary sensitivity proof。

Disposition（Reviewer A self-check）：`CLOSED_FOR_REVIEWER_B_VERIFICATION`。

## 3. 继承修改与最终候选

### 3.1 Candidate Commit A

- commit：`c784079f810e82b57b56455633f47c022bff22ec`
- subject：`fix(m8): complete reviewer-fixer graph remediation`
- 结果：37 files changed，2991 insertions，288 deletions。
- 范围：`.gitattributes`、协议、schema、5 个 fixture graph、fixture generator、graph validator、graph harness、
  `tools/README.md`。

### 3.2 Candidate Commit B

- commit：`8c7f598dd6da72b0f87be63ffdda853071eb77c0`
- subject：`feat(m8): add deterministic git-object review freeze`
- 结果：2 files created，2234 insertions。
- 范围：review freeze 工具及其 hermetic self-test。

Commit B 是最终候选 commit。候选提交后未再修改任何 candidate object path；后续只创建 handoff materials。

## 4. Git for Windows discovery 修复

初始错误为 `trusted Git executable cannot be located`。实际环境为 Windows 11 / Git Bash：

```text
Git: git version 2.49.0.windows.1
exec path: D:/Git/mingw64/libexec/git-core
Python shutil.which("git"): D:\Git\mingw64\bin\git.EXE
```

根因是原实现只根据 Python executable 所在 drive 推导固定安装布局，未覆盖本机 `D:\Git`。第一次把 `shutil.which` 放在固定
布局之前后，hostile PATH shim 测试能够劫持选择，self-test 报告 `PATH shim affected trusted Git selection` / `PATH Git shim was
invoked`。

最终实现按顺序尝试已知 Git for Windows 固定布局，再把 `shutil.which("git")` 和 `shutil.which("git.exe")` 作为 fallback；每个
candidate 必须通过 absolute path、regular-file、symlink/reparse、executable identity、SHA-256、version 与 capability 检查，使用前后
复验 identity。Git subprocess 固定使用 `--no-replace-objects`、`--no-lazy-fetch`、`--literal-pathspecs`，禁用 global/system config，
并限制 timeout 与 output。结果：

```text
ALL PASS: hermetic Git-object freeze and CLI checks
```

## 5. Candidate freeze

仓库内 canonical handoff artifact：

`docs/plans/references/external-artifacts/m8-minimal-1k-v3-review-freeze-20260915.json`

| 项目 | 值 |
| --- | --- |
| source commit | `8c7f598dd6da72b0f87be63ffdda853071eb77c0` |
| artifact SHA-256 | `e704b44231d19eaba75276426f741127ba77aa4e526f5260aa85aa3b143ccc5d` |
| artifact bytes / LF | 55183 / 1 |
| canonicalization | `sa-json-c14n-v1` verified |
| candidate files / bytes | 99 / 276649 |
| fixture-tree-v1 SHA-256 | `0d6dd48dfc2dbaa5e0dbd482170ab1bd27949e0b6dd1c4e4bb669f691e8952f9` |
| fixture files / bytes | 90 / 42574 |
| worktree comparison | `NOT_REQUESTED` |

仓库外两个 object-only freeze 保持 byte-identical：

- `D:\Git Demo\m8-v3-freeze-first-kbc05G.json`
- `D:\Git Demo\m8-v3-freeze-second-vbrYw9.json`
- SHA-256：`e704b44231d19eaba75276426f741127ba77aa4e526f5260aa85aa3b143ccc5d`

九个非 fixture frozen object：

| path | Git blob | SHA-256 | bytes | LF |
| --- | --- | --- | ---: | ---: |
| `.gitattributes` | `5416299a4e928bee4b9f3923b79a6f10e594ef0a` | `bd95d8d2ae6d9bdfed24612650d00bcb6856389e94dbec582cfedb985639b305` | 2274 | 34 |
| `docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md` | `1d1cbe409e1f309d152d529716eebd3a8d6fdc1b` | `6efdb7b40a6382843f8ed26d3695880d9df3e155bffbbb088072d32713d95a49` | 11123 | 158 |
| `docs/plans/references/schemas/m8-minimal-1k-artifacts-v3.schema.json` | `de5db465b2beb6fd799f5878605bb3f134d6c7fc` | `660777316bea20852d3d31535f54c6766349fd4b53827091599e6f3f3935c3e2` | 19721 | 366 |
| `tools/README.md` | `811b12640ed19c9bc69ab94572215ad85b58b1d0` | `6f1bef38839e43dc874c904e629e1c2cf280af8981328b889d51650b0162dc6d` | 16899 | 295 |
| `tools/m8_freeze_minimal_1k_v3_review.py` | `69bcc89e4d5654d15b8c7cfd8f03a88050f725de` | `271da6bebf0a5996f7021d92dffbf19926e1956470542a50a3a5b4296a5961ca` | 45325 | 1302 |
| `tools/m8_generate_minimal_1k_v3_fixtures.py` | `f7e18b3798823055ee4fc4a4e5566ab75bbe3cf7` | `adb4f57020231b4dfa9366efc5eccc1de93b48bf4835527881138d77c23f55ae` | 14121 | 374 |
| `tools/m8_test_freeze_minimal_1k_v3_review.py` | `0f6ab60aa9b580f4e5bc5396a2125d48a609d2f6` | `2931e5ec2a37b3a07932b21cf24ed7596cab395a52d44c3ce15b7e97281c0d0c` | 33257 | 932 |
| `tools/m8_test_minimal_1k_graph_v3.py` | `22b9613d860cf62ee6359fefdeb2c19ef8199eab` | `9b1538f484349cba72682d98bfac12803680316f66265d214df727703d4146e1` | 42722 | 1179 |
| `tools/m8_validate_minimal_1k_graph_v3.py` | `ce7c237a6279343ba24efb9f4567e3be918fd233` | `f60b6498462a01e37db6dc01e41430b820b021f22283f16db65ad8d76acf01ec` | 48633 | 1336 |

独立 fixture-tree 复算最初误把 relative-path length 编码为 8-byte big-endian，得到不适用的
`bd312d64616c783d72952770d9527517f0d5ece31cc7960e907a095f695de108`。按冻结算法改为 4-byte big-endian 后得到与 artifact 一致的
`0d6dd48d...e8952f9`。该误算只发生在 ad hoc 验证，不改变候选或 artifact。

## 6. 主工作区行尾 caveat 与 `.gitattributes`

`.gitattributes` 为候选/evidence 文本声明 `eol=lf`，并把 fixture 二进制保持为 binary。仓库 local config 为
`core.autocrlf=false`、`core.eol=lf`。但两个在配置变更前已 materialize 的 freeze scripts 在主工作区仍为 physical CRLF；Git
index normalization 因此报告 clean，主工作区的 `--compare-worktree` 仍返回 exit 3 / `DIVERGENT`：

| path | 工作区 | candidate object | 证明 |
| --- | --- | --- | --- |
| `tools/m8_freeze_minimal_1k_v3_review.py` | 46627 bytes；1302 CRLF；SHA `eda792b8...7289ef` | 45325 bytes；1302 LF；SHA `271da6be...5961ca` | CRLF→LF 后逐 byte 等于 candidate |
| `tools/m8_test_freeze_minimal_1k_v3_review.py` | 34189 bytes；932 CRLF；SHA `4cc6360c...75aed` | 33257 bytes；932 LF；SHA `2931e5ec...c0d0c` | CRLF→LF 后逐 byte 等于 candidate |

为遵守“candidate commit 后不得修改 candidate path”，没有重写这两个文件。Git object bytes 是 package freeze 的权威事实；
clean full clone 的严格比较另行证明所有 99 个 materialized path 与 candidate object 完全相同。此主工作区物理行尾差异为透明记录
的非阻断本地 checkout caveat，不是 candidate object divergence。

## 7. Full-clone replay

使用非 shallow、无 object alternates 的完整 clone：`D:\Git Demo\m8-v3-full-clone-VpJXwC`，detached checkout 到最终候选。

第一次背景组合命令完成 clone、候选 checkout、freeze self-test、完整 graph harness 和五个 graph 输出后，以 code 3 结束。该次输出
真实记录为：self-test PASS、harness 全 PASS、五个 graph 均输出正确 semantic verdict；命令没有显示后续 strict freeze/generator
阶段完成。没有把该 exit 3 擦除或误报为全流程成功。

随后在同一个 clean clone 中分阶段完成余下 replay：

- `git rev-parse --is-shallow-repository`：`false`；
- object alternates：absent；
- detached HEAD：`8c7f598dd6da72b0f87be63ffdda853071eb77c0`；
- Python syntax compilation：PASS；
- freeze self-test：`ALL PASS: hermetic Git-object freeze and CLI checks`；
- graph harness：`ALL PASS: 5 persistent graphs + 22 fail-closed mutations + 2 sensitivity proofs`；
- 两次 strict freeze byte-identical；
- 两次 generator output byte-identical；
- generator run 1 与 committed 90-file fixture tree byte-identical；
- replay 后 clone status clean；
- Git connectivity fsck PASS。

两个 strict clone freeze：

- `D:\Git Demo\m8-v3-clone-freeze-first-gq1ktk.json`
- `D:\Git Demo\m8-v3-clone-freeze-second-jNoeTs.json`
- SHA-256：`edbb220c16845ed3490d1f0efae7f9078a1e9871be876b1c71c6151fc05880b0`
- 55175 bytes / 1 LF；`worktree_comparison.status=MATCH`；`divergent_paths=[]`。

它们与仓库 package artifact 的 whole-file SHA 不相同是预期行为：前者字段为 `MATCH`，后者为 `NOT_REQUESTED`；两者的
candidate-object facts 均来自同一 source commit，不构成 freeze inconsistency。

两次 generator output：

- `D:\Git Demo\m8-v3-gen-first-1Vnn0f`
- `D:\Git Demo\m8-v3-gen-second-Rps5kY`

## 8. Graph、mutation 与回归结果

五个 persistent graph 均为结构有效图，因此 process exit code 均为 0；成功/失败由 semantic verdict 表达：

| graph | exit | output |
| --- | ---: | --- |
| success | 0 | `VALID_GRAPH verdict=PASS` |
| failure-cleanup | 0 | `VALID_GRAPH verdict=FAIL` |
| failure-observer | 0 | `VALID_GRAPH verdict=FAIL` |
| failure-runtime | 0 | `VALID_GRAPH verdict=FAIL` |
| failure-validation | 0 | `VALID_GRAPH verdict=FAIL` |

一次 ad hoc follow-up oracle 曾错误要求四个合法 failure graph exit 3，因 `failure-cleanup` 实际 exit 0 而失败。该 expectation 错误，
不是候选缺陷；随后独立捕获每个 return code 并确认上表。invalid/mutated graph 才应 nonzero。

完整 harness 结果：

```text
PASS fixture success / failure-cleanup / failure-observer / failure-runtime / failure-validation
PASS committed fixture success / failure-cleanup / failure-observer / failure-runtime / failure-validation
PASS containment directory-junction
PASS valid ready-s2-s3-reject
PASS negative target-bytes / ref-role / ref-schema / logical-name / ref-digest / member-count
PASS negative protocol-digest / gate-actor / s0-read-ref / s1-with-rejected-s0 / gate-decision-action
PASS negative s2-missing-authority / observer-summary / event-sequence / noncanonical-event
PASS negative missing-final-lf / empty-observer / noncanonical-input / failure-as-success
PASS negative missing-artifact / unknown-artifact / path-escape
PASS causal empty-observer / missing-final-lf / noncanonical-event / noncanonical-input
PASS sensitivity final-lf-disabled / nonempty-disabled
ALL PASS: 5 persistent graphs + 22 fail-closed mutations + 2 sensitivity proofs
```

历史 regression：

- `tools/m8_validate_p1_materials.py`：88 checks / 88 passed / 0 failed；
- `tools/m8_validate_p0_r02.py`：77 checks / 77 passed / 0 failed。

历史脚本同时重复其已记录的 D1a/pre-pin CRLF digest 说明；本轮没有修改任何历史 bytes。

## 9. 其他故障与处置

- 对 raw repository 执行 `shutil.copytree` 的 ad hoc determinism 实验因 ignored/runtime transient path 的 WinError 5 与路径消失而失败；
  此方法被弃用，改用 clean full Git clone。不是 generator failure。
- 对固定外部 freeze path 的输出因可能覆盖已有文件而被拒；改为 `mktemp` 新路径，两份输出均保留。
- 一个 read-only Explore agent 因 HTTP 503 / model channel unavailable 失败，并遗留
  `.claude/worktrees/agent-a87966e9cd5b31c49`；没有违反禁令强删该 worktree。
- 一次手误把 candidate SHA 拼错，`cat-file` fail closed；随后使用精确完整 SHA。
- 尝试用被禁止的方式物理规范化主工作区 CRLF 被拒；没有绕过拒绝、没有改动 candidate path。
- 当前 checkout 的额外 `git fsck --full --strict --no-reflogs` exit 0，并报告两个 dangling blob 与一个 dangling commit；这些是
  可达性之外的本地 Git 垃圾对象，不影响 candidate/package ancestry 或 clone connectivity，未清理。

## 10. 新发现、延期项与边界

### 已处置的新发现

1. Git discovery 对非系统盘 Git for Windows 漏检：已修复并由 hostile PATH shim self-test 覆盖。
2. 工作区 clean 不等于 physical bytes 等于 blob：freeze 以 Git object 为权威，严格 MATCH 在 clean clone 中证明，主 checkout caveat
   明示。
3. 合法 failure graph process semantics 易被误读：材料和 worksheet 明确规定 rc=0 + `verdict=FAIL`。

### 延期到未来 S1 的非阻断配置

协议第 6～8 节所列 machine identity、精确 Python/NumPy/LanceDB/PyArrow/psutil 版本、wheel inventory、repository 外绝对路径、
真实 1K generator implementation、observer API/Windows race/reparse handling 与 redaction registry 均必须由未来 Owner 在独立 S0
接受后另行冻结。它们不属于本轮 S0 micro-fixture candidate，也不得在本轮创建或执行。

本轮未访问或复制 `D:\111_Others_Subjects`，未创建真实 experiment identity、仓库外 experiment/evidence root 或 venv，未安装
LanceDB，未生成真实 1K input，未运行 SQLite/LanceDB dry-run，未选择后端，未推进 M8 admission。

## 11. Reviewer A self-check 与交接

Reviewer A 的自查结论仅为 remediation readiness，不是独立 S0 decision：

```text
m8-v3-r02-s0-001: CLOSED_FOR_REVIEWER_B_VERIFICATION
m8-v3-r02-s0-002: CLOSED_FOR_REVIEWER_B_VERIFICATION
known fail-open blockers: none found in Reviewer A self-check
required next reviewer: independent read-only Reviewer B
```

Reviewer B 必须未参与候选对象修改，从 candidate commit 的 Git objects 独立复算 freeze、核对 package-only boundary，并自行裁定
两个 r02 findings 及任何新 finding。即使 Reviewer B 接受，也只能 `request-s1`；不能签发 S1 或授权真实 1K dry-run。

最终 review package identity 采用“本文件所在的 handoff-only commit”的非自引用定义；Reviewer B 须直接从 Git 解析完整
40-hex，并核对 candidate/package diff、ancestry 与结束 worktree state。本记录不在自身内容中预填不可自洽的 commit ID。

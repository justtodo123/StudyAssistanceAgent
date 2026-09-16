# M8 最小 1K v3 Reviewer B 独立 S0 终审材料 r03

- 状态：`INDEPENDENT_REVIEW_REQUIRED / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`
- reviewed object commit：`8c7f598dd6da72b0f87be63ffdda853071eb77c0`
- review package identity：本文件所在的 handoff-only commit；Reviewer B 必须从 Git 解析并记录完整 40-hex
- predecessor audit：`m8-minimal-1k-v3-s0-rereview-audit-20260915-r02.md`
- governance：`m8-reviewer-fixer-two-stage-decision-20260915.md`
- remediation log：`m8-minimal-1k-v3-reviewer-fixer-remediation-20260915.md`
- canonical freeze：`external-artifacts/m8-minimal-1k-v3-review-freeze-20260915.json`
- Reviewer A：`reviewer-a-20260915`，角色为 `reviewer-fixer / remediation author`，已参与 candidate 修改，不具终审独立性。

> 本材料由 Reviewer A 编写，只供 Reviewer B 只读独立复核，不预置 `PROTOCOL_ACCEPTED`。r02 的
> `PROTOCOL_REJECTED / stop` 在 Reviewer B 签署新裁定前保持有效。

## 1. Reviewer B 独立性与权限边界

Reviewer B 必须满足：

1. 未参与 `c784079f810e82b57b56455633f47c022bff22ec`、`8c7f598dd6da72b0f87be63ffdda853071eb77c0`
   的代码、fixture、test、freeze 工具或 handoff material 修改；
2. 对 reviewed object 和 package 执行只读审查；若 Reviewer B 修改 candidate object，其身份立即转为 fixer，必须交 Reviewer C
   或其他未参与修改者终审；
3. 不信任本材料中的 copied prose 或摘要，必须从显式完整 commit 的 Git object bytes 独立复算；
4. 记录 reviewer identity、主体分离依据、环境、开始/结束 status，以及无法证明的独立性限制。

Reviewer B 不得创建真实 experiment identity、实验根、evidence root 或 venv，不得安装 LanceDB，不得生成真实 1K input，不得运行
SQLite/LanceDB dry-run，不得访问或复制 `D:\111_Others_Subjects`。本审查不选择后端、不批准生产修改或 M8 admission。

## 2. Package 与 candidate 边界

最终 package commit 必须满足：

- reviewed object 是 package commit 的祖先；
- `8c7f598...<package>` 之间不修改 99 个 candidate object path；
- package commit 仅新增/修改以下 handoff materials：
  - `docs/plans/references/external-artifacts/m8-minimal-1k-v3-review-freeze-20260915.json`
  - `docs/plans/references/m8-minimal-1k-v3-reviewer-fixer-remediation-20260915.md`
  - `docs/plans/references/m8-minimal-1k-v3-s0-review-materials-20260915-r03.md`
  - `docs/plans/references/m8-minimal-1k-v3-s0-reviewer-worksheet-20260915-r03.md`
  - `docs/plans/references/README.md`

若 reviewed object、freeze artifact 或 candidate path 在 package 中变化，当前材料自动失效。

## 3. Canonical Git-object freeze

仓库内 freeze artifact 应为 canonical `sa-json-c14n-v1`：UTF-8、排序键、无空格、恰一个最终 LF。

| 项目 | 预期值 |
| --- | --- |
| artifact SHA-256 | `e704b44231d19eaba75276426f741127ba77aa4e526f5260aa85aa3b143ccc5d` |
| artifact bytes / LF | 55183 / 1 |
| source commit | `8c7f598dd6da72b0f87be63ffdda853071eb77c0` |
| candidate files / bytes | 99 / 276649 |
| fixture-tree-v1 SHA-256 | `0d6dd48dfc2dbaa5e0dbd482170ab1bd27949e0b6dd1c4e4bb669f691e8952f9` |
| fixture files / bytes | 90 / 42574 |
| package artifact comparison | `NOT_REQUESTED` |

九个非 fixture object 的预期摘要：

| path | SHA-256 | bytes | LF | Git blob |
| --- | --- | ---: | ---: | --- |
| `.gitattributes` | `bd95d8d2ae6d9bdfed24612650d00bcb6856389e94dbec582cfedb985639b305` | 2274 | 34 | `5416299a4e928bee4b9f3923b79a6f10e594ef0a` |
| protocol v3 | `6efdb7b40a6382843f8ed26d3695880d9df3e155bffbbb088072d32713d95a49` | 11123 | 158 | `1d1cbe409e1f309d152d529716eebd3a8d6fdc1b` |
| schema v3 | `660777316bea20852d3d31535f54c6766349fd4b53827091599e6f3f3935c3e2` | 19721 | 366 | `de5db465b2beb6fd799f5878605bb3f134d6c7fc` |
| `tools/README.md` | `6f1bef38839e43dc874c904e629e1c2cf280af8981328b889d51650b0162dc6d` | 16899 | 295 | `811b12640ed19c9bc69ab94572215ad85b58b1d0` |
| freeze tool | `271da6bebf0a5996f7021d92dffbf19926e1956470542a50a3a5b4296a5961ca` | 45325 | 1302 | `69bcc89e4d5654d15b8c7cfd8f03a88050f725de` |
| fixture generator | `adb4f57020231b4dfa9366efc5eccc1de93b48bf4835527881138d77c23f55ae` | 14121 | 374 | `f7e18b3798823055ee4fc4a4e5566ab75bbe3cf7` |
| freeze self-test | `2931e5ec2a37b3a07932b21cf24ed7596cab395a52d44c3ce15b7e97281c0d0c` | 33257 | 932 | `0f6ab60aa9b580f4e5bc5396a2125d48a609d2f6` |
| graph harness | `9b1538f484349cba72682d98bfac12803680316f66265d214df727703d4146e1` | 42722 | 1179 | `22b9613d860cf62ee6359fefdeb2c19ef8199eab` |
| graph validator | `f60b6498462a01e37db6dc01e41430b820b021f22283f16db65ad8d76acf01ec` | 48633 | 1336 | `ce7c237a6279343ba24efb9f4567e3be918fd233` |

不要把 main checkout 的 Git-clean status 当成 physical byte equality。Reviewer A 的旧 checkout 中两个新 freeze scripts 在
materialize 时为 CRLF；candidate Git objects 为 LF，且 CRLF→LF 后相等。Reviewer B 应使用 fresh full clone，并运行
`--compare-worktree` 得到 `MATCH`。

Reviewer A 的 strict clone freeze SHA 为 `edbb220c16845ed3490d1f0efae7f9078a1e9871be876b1c71c6151fc05880b0`
（55175 bytes）。它与 package artifact 的 whole-file SHA 不同是预期的唯一 framing 差异：strict clone 写
`worktree_comparison=MATCH`，package artifact 写 `NOT_REQUESTED`。Reviewer B 应比较全部 candidate object facts，而不是要求两个
JSON 文件的 whole-file digest 相同。

## 4. 必须独立裁定的 r02 findings

### `m8-v3-r02-s0-001`

问题：r02 materials 没有准确冻结 actual validator/harness bytes。

Reviewer A 声称的修复：Git-object freeze 工具从显式 commit 自动读取并验证 99 个 candidate blob，发布 canonical freeze artifact，
并在 hermetic repository 中覆盖 deterministic output、replacement refs、alternates、symlink/gitlink、linked worktree、full clone、
hostile PATH、timeout/output bounds 与 publication failures。

Reviewer B 必须独立裁定：`CLOSED / PARTIALLY_CLOSED / OPEN`。

### `m8-v3-r02-s0-002`

问题：r02 的 `missing-final-lf`、`empty-observer` 只改 ledger，没有同步 summary 与下游 REF；仅以 nonzero return code 判 PASS。

Reviewer A 声称的修复：完整 reseal observer summary → run-report → validation-report REF → S2 → S3，精确检查目标错误，禁止 stale
摘要/REF 错误；另以关闭目标检查的 validator variant 形成 `final-lf-disabled` 与 `nonempty-disabled` 两项 sensitivity proof。

Reviewer B 必须检查：

- `missing-final-lf` 精确命中 final-LF/nonempty 错误；
- `empty-observer` 精确命中 nonempty，并允许同时命中预定义 summary minimum/lifecycle 错误；
- 两者均不以 stale digest、byte count、event count 或 REF 代替目标失败；
- disabling target check 后，sensitivity proof 能检测 mutation 不再由无关 stale 链阻断；
- causal `noncanonical-event` 与 `noncanonical-input` 仍成立。

Reviewer B 必须独立裁定：`CLOSED / PARTIALLY_CLOSED / OPEN`。

## 5. Replay 行为与 exact oracle

### 5.1 五个 persistent graph

这些都是结构有效 graph，因此 process exit code **全部为 0**。合法失败图以 semantic verdict `FAIL` 表达，不得错误期待 exit 3：

| graph | expected exit | expected output |
| --- | ---: | --- |
| success | 0 | `VALID_GRAPH verdict=PASS` |
| failure-cleanup | 0 | `VALID_GRAPH verdict=FAIL` |
| failure-observer | 0 | `VALID_GRAPH verdict=FAIL` |
| failure-runtime | 0 | `VALID_GRAPH verdict=FAIL` |
| failure-validation | 0 | `VALID_GRAPH verdict=FAIL` |

invalid/mutated graph 才应 nonzero，并应由 harness 核对目标错误类别。

### 5.2 Harness expected result

```text
ALL PASS: 5 persistent graphs + 22 fail-closed mutations + 2 sensitivity proofs
```

Reviewer B 不应只接受总数，必须核对 22 个 fail-closed mutation 的逐项 PASS、四项 causal output 和两项 sensitivity output，重点
排除 stale digest/REF 冒充目标检查。

### 5.3 Freeze self-test expected result

```text
ALL PASS: hermetic Git-object freeze and CLI checks
```

## 6. 推荐只读复核流程

在 Reviewer B 自己创建的临时 full clone 中执行，不在 package checkout 重写 fixture：

```bash
CANDIDATE=8c7f598dd6da72b0f87be63ffdda853071eb77c0
PACKAGE=<review-package-full-commit>

# 先验证 ancestry 与 package-only boundary
git merge-base --is-ancestor "$CANDIDATE" "$PACKAGE"
git diff-tree --no-commit-id --name-status -r "$CANDIDATE" "$PACKAGE"

# detached candidate checkout 后，验证 syntax、freeze 与 harness
python -m py_compile \
  tools/m8_validate_minimal_1k_graph_v3.py \
  tools/m8_generate_minimal_1k_v3_fixtures.py \
  tools/m8_test_minimal_1k_graph_v3.py \
  tools/m8_freeze_minimal_1k_v3_review.py \
  tools/m8_test_freeze_minimal_1k_v3_review.py
python tools/m8_test_freeze_minimal_1k_v3_review.py
python tools/m8_test_minimal_1k_graph_v3.py

python tools/m8_validate_minimal_1k_graph_v3.py \
  docs/plans/references/fixtures/m8-minimal-1k-v3/success
python tools/m8_validate_minimal_1k_graph_v3.py \
  docs/plans/references/fixtures/m8-minimal-1k-v3/failure-cleanup
python tools/m8_validate_minimal_1k_graph_v3.py \
  docs/plans/references/fixtures/m8-minimal-1k-v3/failure-observer
python tools/m8_validate_minimal_1k_graph_v3.py \
  docs/plans/references/fixtures/m8-minimal-1k-v3/failure-runtime
python tools/m8_validate_minimal_1k_graph_v3.py \
  docs/plans/references/fixtures/m8-minimal-1k-v3/failure-validation

# 使用两个不同的新输出路径生成两次；应 byte-identical 且 status=MATCH
python tools/m8_freeze_minimal_1k_v3_review.py \
  --commit "$CANDIDATE" --repo "<absolute-clone-path>" --compare-worktree --output "<new-output-1>"
python tools/m8_freeze_minimal_1k_v3_review.py \
  --commit "$CANDIDATE" --repo "<absolute-clone-path>" --compare-worktree --output "<new-output-2>"

# generator 必须在两个新 output root 中运行；不得在 review checkout 使用 --replace-tracked
python tools/m8_generate_minimal_1k_v3_fixtures.py --output-root "<new-fixture-root-1>"
python tools/m8_generate_minimal_1k_v3_fixtures.py --output-root "<new-fixture-root-2>"

# 历史 regression
python tools/m8_validate_p1_materials.py
python tools/m8_validate_p0_r02.py
```

Reviewer B 还应独立：

- 确认 clone 非 shallow、无 alternates、HEAD 为显式 candidate；
- 复算 canonical package artifact SHA/bytes/LF；
- 从 candidate Git objects 独立复算每个 frozen file 和 fixture-tree-v1；
- 比较两次 strict freeze；
- 比较两次 generator tree，并与 committed fixture tree 逐 path/byte 相等；
- 结束时确认 clone clean；
- 执行 Git connectivity check；
- 核对 historical 88/88 与 77/77 regression；
- 在 worksheet 中记录所有实际命令、return code 和输出，不得只抄本材料预期值。

## 7. Reviewer A replay disclosure

Reviewer A 的第一次背景 full-clone 组合命令在完成 self-test、harness 与五图输出后以 code 3 结束；没有把它记为全流程 PASS。
Reviewer A 随后在同一 clean clone 分阶段完成 strict freeze、generator 比较、final clean status 与 fsck，均通过。Reviewer B 必须自行
重放，不能把 Reviewer A 后续结果替代独立验证。

Reviewer A 还曾用错误 oracle 期待合法 failure graph exit 3；该 ad hoc oracle 被实际 rc=0 拒绝。候选 validator 的正确 contract 是
“valid graph rc=0；semantic verdict 表示 PASS/FAIL”，Reviewer B 应按本材料第 5.1 节核验。

## 8. 最终裁定格式

Reviewer B 只能在完整只读核验后自行填写 blank worksheet 并另行落盘最终独立审查记录。

接受：

```text
decision: PROTOCOL_ACCEPTED
allowed_next_action: request-s1
```

拒绝：

```text
decision: PROTOCOL_REJECTED
allowed_next_action: stop
```

接受只允许向 Owner 请求 S1；不签发 S1，不授权 identity/environment/input generation，不授权 SQLite/LanceDB 真实 1K dry-run，
不授权 10K、backend selection、生产修改或 M8 admission。

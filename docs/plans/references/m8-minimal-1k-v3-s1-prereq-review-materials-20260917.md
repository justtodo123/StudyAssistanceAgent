# M8 最小 1K v3 S1 prerequisite 独立复核材料

- 状态：`INDEPENDENT_REVIEW_REQUIRED / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`
- reviewed candidate commit：`50300667983f631dbb13bc17c8e659e1c4230d48`
- review package identity：本文件所在的 handoff-only commit；独立 Reviewer 必须从 Git 解析并记录完整 40-hex
- canonical freeze：`external-artifacts/m8-minimal-1k-v3-s1-prereq-freeze-20260917.json`
- Builder record：`m8-minimal-1k-v3-s1-prereq-builder-self-check-20260917.md`
- blank worksheet：`m8-minimal-1k-v3-s1-prereq-reviewer-worksheet-20260917.md`

> 本材料由参与 candidate 修改的 Builder 编写，只供未参与修改的 Reviewer 只读独立复核。它不预置接受或拒绝，
> 不签发 S1，不授权任何真实 dry-run。

## 1. 独立性与权限边界

Reviewer 必须满足：

1. 未参与 `8e006b3d1e7630a650718a515e50644c67940e37`、`50300667983f631dbb13bc17c8e659e1c4230d48`
   或本 handoff package 的修改；
2. 使用 Reviewer 自己创建的 full、non-shallow、无 alternates clone，只读审查精确 candidate Git objects；
3. 不信任本文复制的摘要，独立复算 freeze、path inventory、测试输出与 candidate/package boundary；
4. 若 Reviewer 修改 candidate 或 package，立即失去本轮终审独立性，须由另一位未参与者重新复核。

本复核不得创建真实 experiment identity/root、正式 evidence root 或 venv，不得安装/升级依赖，不得生成正式 1K input，
不得运行 SQLite/LanceDB，不得访问 `D:\111_Others_Subjects`，不得修改 production、选择后端、签发 S1/S2/S3 或推进 M8 admission。

## 2. Package 与 candidate boundary

Candidate 必须是 package commit 的祖先。`candidate..<package>` 之间只允许新增：

1. `docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-prereq-freeze-20260917.json`
2. `docs/plans/references/m8-minimal-1k-v3-s1-prereq-builder-self-check-20260917.md`
3. `docs/plans/references/m8-minimal-1k-v3-s1-prereq-review-materials-20260917.md`
4. `docs/plans/references/m8-minimal-1k-v3-s1-prereq-reviewer-worksheet-20260917.md`

`docs/plans/references/README.md` 和 `tools/README.md` 都属于 frozen candidate inventory，package 必须保持其 blob 不变。
Reviewer 应从 freeze 的 `frozen_files` 读取全部 119 个 path，并逐 path 比较 candidate/package Git object identity；任何变化都使当前
package 无效。

## 3. Canonical prerequisite freeze

Package artifact 的预期整体事实：

| field | expected |
| --- | --- |
| SHA-256 | `efd95cf45d1749b323a008f5559f4839f0ef1cb0acfa674720c185e455ac806a` |
| bytes | 32688 |
| format | `m8-s1-prerequisites-v3-freeze-v1` |
| purpose | `S1_PREREQUISITE_RECORD_ONLY_NOT_AUTHORIZATION` |
| canonicalization | `sa-json-c14n-v1` |
| source commit | `50300667983f631dbb13bc17c8e659e1c4230d48` |
| frozen paths / bytes | 119 / 808180 |
| package comparison status | `NOT_REQUESTED` |
| divergent paths | empty |

Artifact 必须为 UTF-8、无 BOM、无 CR、compact sorted JSON、恰一个 final LF。S1 freeze 的 119 个 entries 全部位于
`frozen_files`；它没有 S0 review freeze 的 `fixture_tree` 字段。Reviewer 不得把旧 99-path S0 freeze 当作本轮 inventory。

29 个 non-fixture candidate path 为：

- `.gitattributes`
- `docs/plans/references/README.md`
- `docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md`
- `docs/plans/references/m8-minimal-1k-v3-generator-spec.md`
- `docs/plans/references/m8-minimal-1k-v3-observer-spec.md`
- `docs/plans/references/schemas/m8-minimal-1k-artifacts-v3.schema.json`
- `docs/plans/references/schemas/m8-minimal-1k-observer-config-v3.schema.json`
- `docs/plans/references/schemas/m8-minimal-1k-redaction-registry-v3.schema.json`
- `docs/plans/references/schemas/m8-minimal-1k-s1-config-v3.schema.json`
- `docs/plans/references/schemas/m8-minimal-1k-s1-gate-v3.schema.json`
- `docs/plans/references/templates/m8-minimal-1k-observer-config-v3.json`
- `docs/plans/references/templates/m8-minimal-1k-redaction-registry-v3.json`
- `docs/plans/references/templates/m8-minimal-1k-s1-config-v3.json`
- `docs/plans/references/templates/m8-minimal-1k-s1-gate-v3.json`
- `tools/README.md`
- `tools/m8_freeze_s1_prerequisites_v3.py`
- `tools/m8_generate_minimal_1k_input_v3.py`
- `tools/m8_generate_minimal_1k_v3_fixtures.py`
- `tools/m8_observe_minimal_1k_v3.py`
- `tools/m8_probe_s1_environment_v3.py`
- `tools/m8_run_minimal_1k_v3.py`
- `tools/m8_test_freeze_s1_prerequisites_v3.py`
- `tools/m8_test_generate_minimal_1k_input_v3.py`
- `tools/m8_test_minimal_1k_graph_v3.py`
- `tools/m8_test_observe_minimal_1k_v3.py`
- `tools/m8_test_s1_controls_v3.py`
- `tools/m8_test_s1_prerequisites_v3.py`
- `tools/m8_validate_minimal_1k_graph_v3.py`
- `tools/m8_validate_s1_preflight_v3.py`

其余 90 个为五个 fixture graph 各 18 members。Reviewer 必须以 artifact 内容与 Git objects 为准，不信任手抄列表。

## 4. 必须复核的 portability remediation

首个 candidate `8e006b3…` 在 fresh clone 中失败，因为 observer schema reference 绑定了主 checkout CRLF physical bytes，
而 Git object/fresh clone 为 LF。Replacement candidate `5030066…` 修改：

- `tools/m8_test_s1_controls_v3.py`：CRLF pair → LF，残留 CR fail closed；
- observer-config schema：const 更新为 18520 bytes / SHA-256
  `f8fb842955f5a6164e61c6d62f9e25de0fe738391e98cd925a82c39c3d4fbf95`。

Reviewer 必须证明最终 candidate 在新 clone 中通过；不得在 replay clone 内 repair。

## 5. 推荐只读复核流程

```bash
CANDIDATE=50300667983f631dbb13bc17c8e659e1c4230d48
PACKAGE=<commit-containing-these-materials>

git cat-file -e "$CANDIDATE^{commit}"
git cat-file -e "$PACKAGE^{commit}"
git merge-base --is-ancestor "$CANDIDATE" "$PACKAGE"
git diff-tree --no-commit-id --name-status -r "$CANDIDATE" "$PACKAGE"
```

在 Reviewer 自己创建的 full clone 中 detached checkout candidate，确认 non-shallow、无 alternates、clean status，然后执行：

```bash
python -m py_compile \
  tools/m8_freeze_s1_prerequisites_v3.py \
  tools/m8_generate_minimal_1k_input_v3.py \
  tools/m8_generate_minimal_1k_v3_fixtures.py \
  tools/m8_observe_minimal_1k_v3.py \
  tools/m8_probe_s1_environment_v3.py \
  tools/m8_run_minimal_1k_v3.py \
  tools/m8_test_freeze_s1_prerequisites_v3.py \
  tools/m8_test_generate_minimal_1k_input_v3.py \
  tools/m8_test_minimal_1k_graph_v3.py \
  tools/m8_test_observe_minimal_1k_v3.py \
  tools/m8_test_s1_controls_v3.py \
  tools/m8_test_s1_prerequisites_v3.py \
  tools/m8_validate_minimal_1k_graph_v3.py \
  tools/m8_validate_s1_preflight_v3.py

python tools/m8_test_s1_prerequisites_v3.py
python tools/m8_test_minimal_1k_graph_v3.py
python tools/m8_test_generate_minimal_1k_input_v3.py
python tools/m8_test_observe_minimal_1k_v3.py
python tools/m8_test_s1_controls_v3.py
python tools/m8_test_freeze_s1_prerequisites_v3.py
python tools/m8_test_freeze_minimal_1k_v3_review.py
python tools/m8_validate_p1_materials.py
python tools/m8_validate_p0_r02.py
```

使用两个新的仓库外 output path 独立生成两次 strict freeze：

```bash
python tools/m8_freeze_s1_prerequisites_v3.py \
  --commit "$CANDIDATE" --repo "<absolute-clone-path>" \
  --compare-worktree --output "<new-output-1>"
python tools/m8_freeze_s1_prerequisites_v3.py \
  --commit "$CANDIDATE" --repo "<absolute-clone-path>" \
  --compare-worktree --output "<new-output-2>"
```

两次 strict freeze 必须 byte-identical 且 `worktree_comparison.status=MATCH`。它们与 package artifact 的 whole-file SHA
可以不同，但差异必须只来自 `MATCH` 与 `NOT_REQUESTED` 的 comparison 字段；所有 object facts 必须一致。

最后执行 `git diff --check`、strict no-reflog fsck，并确认 clone status clean。所有 actual commands、return codes 和输出应记录在
blank worksheet；不得只复制本文预期值。

## 6. 预期 replay oracles

- aggregate：`ALL PASS: M8 v3 S1 prerequisite suite`
- graph harness：`ALL PASS: 5 persistent graphs + 45 fail-closed mutations + 2 sensitivity proofs`
- generator：27/27
- observer：20/20
- S1 controls：13/13
- S1 prerequisite freeze self-test：`ALL PASS: M8 v3 S1 prerequisite freeze self-test`
- existing review freeze：`ALL PASS: hermetic Git-object freeze and CLI checks`
- historical regressions：88/88 与 77/77

五个 persistent graph 都是结构有效 graph，process exit 均应为 0；成功/失败由 semantic verdict 表达。Reviewer 不得把合法
failure graph 错误要求为 nonzero。

## 7. 裁定边界

Reviewer 必须自行决定：

- `S1_PREREQUISITES_ACCEPTED / request-owner-s1-decision`；或
- `S1_PREREQUISITES_REJECTED / stop`。

这里的 `S1_PREREQUISITES_ACCEPTED` 只是独立 prerequisite-review verdict，不是仓库 schema 所定义的 Owner S1 gate
`DRY_RUN_AUTHORIZED / run-s2`。接受只允许把 candidate 交给 Owner 作独立 S1 决策；它不签发 S1，不授权创建 identity、root、
venv、安装依赖、生成正式输入或运行任一 backend。任何新 finding 均须记录 severity、path/line、failure scenario、证据与
required remediation。

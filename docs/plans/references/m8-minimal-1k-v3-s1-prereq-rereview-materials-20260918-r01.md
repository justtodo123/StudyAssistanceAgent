# M8 最小 1K v3 S1 prerequisite 独立重审材料

- 状态：`INDEPENDENT_REREVIEW_REQUIRED / NOT_A_GATE / NOT_EXECUTION_AUTHORIZED`
- reviewed candidate：`6f9cf4617e79462130737eaf78cdb392b02b6664`
- review package：本文件所在的 direct-child handoff-only commit；Reviewer 必须从 Git 解析完整 40-hex
- canonical package freeze：`external-artifacts/m8-minimal-1k-v3-s1-prereq-freeze-20260918-r01.json`
- Builder remediation：`m8-minimal-1k-v3-s1-prereq-remediation-20260918-r01.md`
- blank worksheet：`m8-minimal-1k-v3-s1-prereq-reviewer-worksheet-20260918-r01.md`

> 本材料由参与 candidate 修改的 Builder 编写，只供独立 Reviewer 只读复核。摘要与预期值均须独立复算；本材料
> 不预置 verdict，不签发 S1，不授权真实 dry-run。

## 1. 独立性和安全边界

Reviewer 必须未参与 replacement candidate、handoff package、freeze、remediation、materials 或 worksheet 的修改，
并使用自己新建的 full、non-shallow、无 alternates clone。若 Reviewer 修改任何 candidate/package object，则立即转为
fixer，本轮不得作最终 Reviewer。

复核不得创建真实 experiment identity/root/evidence root/venv，不得安装或改变依赖，不得生成正式 1K input，不得运行
SQLite/LanceDB，不得访问 `D:\111_Others_Subjects`，不得修改 production、选择 backend、签发 S1/S2/S3、推进
M8 admission 或 push origin。

历史 rejected candidate `50300667983f631dbb13bc17c8e659e1c4230d48`、rejected package
`b71c1a1ebaf269f387422b4984cd4ace3e1b31b3`，以及外部 audit
`D:\面试实习\m8-minimal-1k-v3-s1-prereq-independent-audit-20260917.md`（SHA-256
`2dffb86de3cdd989cda74f867b9383675c65801fc5101de7628469a7470912cd`）均为历史不可变记录。

## 2. Commit ancestry 与 exact package boundary

Reviewer 应验证：

1. candidate 与 package 均为 commit object；
2. package 的直接 parent **等于** candidate；
3. candidate 是 package ancestor；
4. candidate 到 package 的 diff 恰为四个 additions：
   - `docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-prereq-freeze-20260918-r01.json`
   - `docs/plans/references/m8-minimal-1k-v3-s1-prereq-remediation-20260918-r01.md`
   - `docs/plans/references/m8-minimal-1k-v3-s1-prereq-rereview-materials-20260918-r01.md`
   - `docs/plans/references/m8-minimal-1k-v3-s1-prereq-reviewer-worksheet-20260918-r01.md`
5. 无其他 add/modify/delete/rename；
6. 从 package freeze 读取全部 123 个 `frozen_files`，逐项确认 candidate 与 package 的 Git mode/OID 相同。

示例只读命令：

```bash
CANDIDATE=6f9cf4617e79462130737eaf78cdb392b02b6664
PACKAGE=<commit-containing-these-materials>

git cat-file -e "$CANDIDATE^{commit}"
git cat-file -e "$PACKAGE^{commit}"
git rev-parse "$PACKAGE^"
git merge-base --is-ancestor "$CANDIDATE" "$PACKAGE"
git diff-tree --no-commit-id --name-status -r "$CANDIDATE" "$PACKAGE"
```

## 3. Package freeze 的独立复算

Package artifact 的 expected framing：

| field | expected |
| --- | --- |
| SHA-256 | `6f1315591915a80ae9d463ec85aafa92925d57514ea691180318dc212817a517` |
| bytes / LF / CR | 38095 / 1 / 0 |
| format | `m8-s1-prerequisites-v3-freeze-v2` |
| purpose | `S1_PREREQUISITE_RECORD_ONLY_NOT_AUTHORIZATION` |
| canonicalization | `sa-json-c14n-v1` |
| source commit | `6f9cf4617e79462130737eaf78cdb392b02b6664` |
| closure version | `m8-s1-prerequisite-closure-v2` |
| frozen files / total bytes | 123 / 1019137 |
| closure digest | `b3063aa32b07ecfb1b6349210e4ec6a20c86922d1f6f6155828d180d654dd011` |
| package comparison | `NOT_REQUESTED` / empty divergent paths |

Reviewer 必须自行验证 UTF-8、无 BOM、无 CR、递归 key-sorted compact JSON 和恰一个 final LF；然后从 candidate
Git objects 重读 target-commit manifest、展开 fixture closure、验证 object type/mode/OID/SHA-256/bytes/LF，独立重算
aggregate 和 closure digest。不得从当前 worktree、Builder 摘要或 mutable path 推断事实。

Manifest 声明五个 fixture graphs × 18 members = 90 fixture objects；其余 33 个对象由 manifest bootstrap、static
reads、support modules、allowed subprocesses、gating entrypoint 和四个 declared templates 的去重 union 决定。
最终权威 inventory 是 artifact 中按 path 排序的 123 entries，而不是手抄路径列表。

## 4. Fresh full-clone 和 strict freeze

在 Reviewer 自建 clone 中 detached checkout candidate，并验证：

- full / non-shallow；
- 无 object alternates；
- 无 replacement refs；
- 初始 ordinary 与 ignored-inclusive status clean；
- candidate HEAD 精确匹配；
- 不在 clone 内 repair 或修改文件。

从 unrelated cwd 使用两个全新的 repository-external output path 生成两次 strict freeze：

```bash
python -I -B tools/m8_freeze_s1_prerequisites_v3.py \
  --commit "$CANDIDATE" --repo "<absolute-clone-path>" \
  --compare-worktree --output "<external-output-1>"
python -I -B tools/m8_freeze_s1_prerequisites_v3.py \
  --commit "$CANDIDATE" --repo "<absolute-clone-path>" \
  --compare-worktree --output "<external-output-2>"
```

两份 strict freeze 必须 byte-identical，expected whole-file SHA-256 为
`af17d1e50a3ca0ba4cb9f018fc3928a47ea7ac100f7794ecb1f5a3eed3417578`，并且
`worktree_comparison.status = MATCH`、`divergent_paths = []`。将 strict object 与 package object 结构化比较；
唯一允许差异是 package `NOT_REQUESTED` 对 strict clone `MATCH` 的 comparison framing。

## 5. Closed gating replay

Default command 与 explicit `--gating-only` 必须等价；它们只运行 manifest-derived closed gating closure，开头为
`GATING_SUITE_ONLY`，成功结尾必须为：

```text
GATING PASS: M8 v3 S1 prerequisite closed oracle
```

必须核对中间十个 PASS markers，包括 manifest contract、closure-bound syntax、execution policy、fail-closed regressions、
declared reads/subprocesses、bounded output oracle、external closure materialization、per-child isolation、exact-once dispatch 和
manifest-declared child suites。任何未声明读取、subprocess、ambient primary checkout 使用、timeout、truncation、cleanup failure
或 child failure 均必须 fail closed；`PermissionError` 不能被当作 PASS。

建议在 unrelated cwd、清理 `PYTHONPATH/PYTHONHOME`、设置 repository-external pycache/runtime roots 后执行：

```bash
python -I -B tools/m8_test_s1_prerequisites_v3.py
python -I -B tools/m8_test_s1_prerequisites_v3.py --gating-only
```

## 6. Focused suites、portability 和 runtime isolation

独立复核至少覆盖：

| check | expected oracle |
| --- | --- |
| graph harness | `ALL PASS: 5 persistent graphs + 45 fail-closed mutations + 2 sensitivity proofs` |
| deterministic generator | 27/27 |
| synthetic observer | 20/20 |
| S1 controls | 14/14；`ALL PASS: canonical declared templates` |
| prerequisite freeze self-test | `ALL PASS: M8 v3 S1 prerequisite freeze self-test` |
| existing S0 freeze regression | `ALL PASS: hermetic Git-object freeze and CLI checks` |

四个 manifest-declared templates 必须由同一 strict parser 与 canonical serializer 证明 canonical、blank、non-authorizing；
S1 config template 必须为 6008 bytes，SHA-256
`8938077a1ce9f846cd5c7049aa6b5a29915f2d0ae4ad8b0aafc9fc68f231fcf1`。placeholder instantiation 必须为
structured replacement，不得 raw text replace。

Portability 复核应确认 observer schema 绑定 candidate Git-object LF bytes（18520 bytes，SHA-256
`f8fb842955f5a6164e61c6d62f9e25de0fe738391e98cd925a82c39c3d4fbf95`）；只规范化 CRLF pair，孤立 CR
fail closed，fresh clone 内不 repair。

Runtime isolation 复核应确认 child 使用 `python -I -B`、`PYTHONDONTWRITEBYTECODE=1`、清空
`PYTHONPATH/PYTHONHOME`，每个 child 有独立外部 cwd/runtime/pycache root，Windows process tree 被完整约束，clone
最终没有 `.pyc` 或 `__pycache__` side effects。

## 7. Historical replay 必须单独运行且 non-gating

Historical evidence 不属于 gating verdict。必须以另一条显式命令调用，绑定 absolute repo 与完整 candidate commit：

```bash
python -I -B tools/m8_test_s1_prerequisites_v3.py \
  --historical-regressions \
  --repo "<absolute-clone-path>" \
  --commit "$CANDIDATE"
```

也可直接审查 helper self-test 与 helper machine-readable output。应确认恰好八个 historical objects 从 candidate Git objects
materialize，原始 validator 未改；临时 copied validator 仅改写唯一合法 module-level `REPO = Path(<literal>)`，从第三方 cwd
在 sanitized/bounded 环境运行。成功 marker 必须为：

```text
HISTORICAL NON-GATING PASS: 88/88 and 77/77 via isolated replay
```

任何 mismatch 必须打印 `HISTORICAL_REGRESSION_FAILED` 并 nonzero，且不得产生 gating PASS。historical PASS 也不能
弥补 gating failure，不能升级 authorization。

## 8. Git integrity、结束状态与 worksheet

完成所有验证后执行：

```bash
git diff --check
git fsck --full --strict --no-reflogs
git status --porcelain=v1
git status --porcelain=v1 --ignored
```

记录 return code、unexpected output、ordinary/ignored-inclusive status，以及是否存在 bytecode/log/test-output side effects。
Reviewer 必须将 actual values 填入同 package 的 blank worksheet，而不是复制本材料的 expected values。

## 9. 独立裁定 schema

独立 Reviewer 只能选择：

```text
decision: S1_PREREQUISITES_ACCEPTED
allowed_next_action: request-owner-s1-decision
```

或：

```text
decision: S1_PREREQUISITES_REJECTED
allowed_next_action: stop
```

`S1_PREREQUISITES_ACCEPTED` 仅表示独立 prerequisite rereview 通过；它不是 Owner S1 gate，不等于
`DRY_RUN_AUTHORIZED` 或 `run-s2`，也不授权 identity/root/venv/input/backend、S2、S3 或 M8 admission。

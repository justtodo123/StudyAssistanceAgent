# M8 最小 1K v3 S1 prerequisite remediation / Builder self-check

- 状态：`S1_PREREQUISITES_READY / SELF_CHECK_PASS`
- 本记录性质：Builder remediation 与 handoff 自检；不是独立复核，不是 S1 gate
- immutable replacement candidate：`6f9cf4617e79462130737eaf78cdb392b02b6664`
- direct-child handoff package：本记录所在 commit；Reviewer 必须从 Git 解析完整 40-hex
- allowed next action：`request-independent-s1-prerequisite-rereview`

## 1. 独立性、历史边界与当前状态

本记录由参与 replacement candidate 修改的 Builder 编写，不能作为独立 Reviewer 的结论。
`SELF_CHECK_PASS is not S1_PREREQUISITES_ACCEPTED`。独立 Reviewer 必须使用自己的 full clone、
自行复算 Git objects、freeze、边界和测试结果，并填写同 package 内的 blank worksheet。

历史上被拒绝的对象保持不变：

- rejected candidate：`50300667983f631dbb13bc17c8e659e1c4230d48`
- rejected package：`b71c1a1ebaf269f387422b4984cd4ace3e1b31b3`
- rejected candidate parent：`8e006b3d1e7630a650718a515e50644c67940e37`
- immutable external audit：`D:\面试实习\m8-minimal-1k-v3-s1-prereq-independent-audit-20260917.md`
- external audit SHA-256：`2dffb86de3cdd989cda74f867b9383675c65801fc5101de7628469a7470912cd`

外部 audit 的三项阻断 findings（`001`、`002`、`003`）及其拒绝决定均未被修改、覆盖或关闭。

权威状态仍为：M8 `BLOCKED / NOT_STARTED`；S1 prerequisite 独立复核 `REQUIRED`；S1 gate
`NOT_AUTHORIZED`；S2/S3 `NOT_AUTHORIZED`。

## 2. Findings 与最小修复

### M8-V3-S1-PREREQ-001：gating closure 不闭合

旧 package 仅冻结 119 个路径，aggregate verdict 仍可能依赖未登记 governance、registry、动态 evidence
和 historical 输入。

Replacement 修复为 target-commit-bound、manifest-derived 的 closed oracle：

- manifest：`docs/plans/references/m8-minimal-1k-v3-s1-prereq-oracle-manifest.json`
- closure version：`m8-s1-prerequisite-closure-v2`
- default mode：`gating-only`
- gating entrypoint：`tools/m8_test_s1_prerequisites_v3.py`
- 关闭的 candidate Git-object closure：123 objects（90 fixture objects 加 manifest 声明的源码、schema、template、spec 与工具）
- 读取与 subprocess dispatch 均绑定到 manifest-expanded closure；未声明 read/subprocess fail closed
- historical replay 从 default gating 中移出，独立且明确标记 non-gating

Gating aggregate output 已确认：

```text
GATING_SUITE_ONLY
PASS: manifest-derived repository contract
PASS: closure-bound Python syntax
PASS: manifest-aware execution policy
PASS: execution-policy fail-closed regressions
PASS: declared read and subprocess enforcement
PASS: subprocess output-oracle regressions
PASS: external closure materialization regressions
PASS: per-child runtime isolation regressions
PASS: manifest dispatch exact-once regressions
PASS: manifest-declared closed child suites
GATING PASS: M8 v3 S1 prerequisite closed oracle
```

### M8-V3-S1-PREREQ-002：historical validator 逃逸 detached clone

旧 validator 将 `REPO` 硬编码为 primary checkout，因而不能证明 detached clone。

Replacement 不修改历史 validator 或历史输入，而是从 candidate commit 精确 materialize 八个声明 Git objects，
验证 mode、blob OID、SHA-256、byte count 与 LF count；对临时复制的 validator 仅结构化改写唯一的
module-level `REPO = Path(<string literal>)`，随后在第三方 cwd、sanitized environment、bounded subprocess、
外部 pycache/runtime 根中运行。historical replay 只允许显式 `--repo` 与完整 lowercase 40-hex `--commit`，
并且是 non-gating evidence。

两次 independent full-clone replay 均得到：

```text
HISTORICAL NON-GATING PASS: 88/88 and 77/77 via isolated replay
```

### M8-V3-S1-PREREQ-003：S1 config template 非 canonical

旧 template 声明 `sa-json-c14n-v1` 但未递归排序。Replacement 使用与 preflight 相同的严格解析和 canonical
serialization，且四个 manifest-declared templates 均通过相同 canonicality 检查。S1 config template 的
candidate Git-object facts 为：6008 bytes、无 CR、恰一个 final LF，SHA-256
`8938077a1ce9f846cd5c7049aa6b5a29915f2d0ae4ad8b0aafc9fc68f231fcf1`。
模板 instantiation 只允许 parse → structured placeholder replacement → canonical serialization → strict preflight。

## 3. Candidate、freeze 与 two-clone facts

Candidate `6f9cf4617e79462130737eaf78cdb392b02b6664` 为本次唯一 immutable replacement candidate；本 handoff
不修改其任何 closure object。package freeze 使用 `m8-s1-prerequisites-v3-freeze-v2`，purpose 为
`S1_PREREQUISITE_RECORD_ONLY_NOT_AUTHORIZATION`，canonicalization 为 `sa-json-c14n-v1`，并保持
`worktree_comparison.status = NOT_REQUESTED`。

Package freeze facts：

- SHA-256：`6f1315591915a80ae9d463ec85aafa92925d57514ea691180318dc212817a517`
- bytes：38095；LF：1；CR：0；UTF-8；无 BOM；恰一个 final LF
- source commit：`6f9cf4617e79462130737eaf78cdb392b02b6664`
- aggregate：123 files / 1019137 bytes
- closure digest：`b3063aa32b07ecfb1b6349210e4ec6a20c86922d1f6f6155828d180d654dd011`
- `divergent_paths: []`

从 candidate Git objects 生成的两份 package freeze byte-identical。两份 fresh full clone 的 strict freeze
也 byte-identical，均为 123 files / 1019137 bytes、同一 closure digest，`worktree_comparison.status = MATCH`
且 `divergent_paths = []`。package 与 strict freeze 的所有 object facts 一致，唯一允许差异是
`NOT_REQUESTED` 与 `MATCH` comparison framing。

两个 clone 均为 full、non-shallow、无 alternates、无 replacement refs，并通过：

```text
git fsck --full --strict --no-reflogs
```

## 4. Test and control results

- deterministic generator：27/27
- synthetic observer：20/20
- graph marker：`ALL PASS: 5 persistent graphs + 45 fail-closed mutations + 2 sensitivity proofs`
- S1 controls：14/14；四个 declared templates canonical 且 blank/non-authorizing
- S1 prerequisite freeze self-test：PASS
- existing hermetic S0 freeze regression：PASS
- aggregate closed gating oracle：PASS
- historical replay：88/88 与 77/77，明确为 non-gating
- child isolation：每个 child 拥有独立 repository-external cwd/runtime/pycache root；使用 `python -I -B`、
  `PYTHONDONTWRITEBYTECODE=1`，并清除 `PYTHONPATH` 与 `PYTHONHOME`
- fresh clone replay 未产生 `.pyc` 或 `__pycache__` side effects
- CRLF portability：observer schema 使用 Git-object LF bytes；残留孤立 CR fail closed；clone 内未 repair

## 5. 权限限制与 recovery patch

The requested external recovery patch was not created because the permission classifier rejected the export operation.

No bypass or stash was used.

No patch SHA-256 or path inventory is claimed.

The final replacement candidate was validated from the immutable candidate commit and two fresh full clones.

此外，未创建真实 experiment identity/root/evidence root/执行 venv，未安装、升级或卸载依赖，未生成正式 1K
input，未运行 SQLite/LanceDB，未选择 backend，未修改 production，未访问 `D:\111_Others_Subjects`，
未 push origin，未签发 S1/S2/S3，未推进 M8 admission；`.claude/tmp/` 保持原有未跟踪状态。

## 6. 结论与后续动作

本 Builder self-check 仅证明 handoff package 已按 candidate Git objects 准备并完成自检。它不签署 S1，也不
授权 `DRY_RUN_AUTHORIZED`、`run-s2`、`EVIDENCE_READY`、`ACCEPT_1K_EVIDENCE`、后端选择或任何实验执行。

```text
S1_PREREQUISITES_READY
SELF_CHECK_PASS
allowed_next_action: request-independent-s1-prerequisite-rereview
```

下一步只能由未参与 candidate/package 修改的独立 Reviewer 进行 prerequisite rereview。Reviewer 必须在 blank
worksheet 中选择：

```text
decision: S1_PREREQUISITES_ACCEPTED
allowed_next_action: request-owner-s1-decision
```

或：

```text
decision: S1_PREREQUISITES_REJECTED
allowed_next_action: stop
```

即使独立 Reviewer 接受，也只允许请求 Owner 作独立 S1 decision；不会自动授权 S1、S2、S3 或 M8。

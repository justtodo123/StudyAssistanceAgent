# M8 最小 1K v3 S1 prerequisite Builder 修复与自查记录

- 角色：`S1 Builder / preparation author / remediation author`
- 原 candidate commit：`8e006b3d1e7630a650718a515e50644c67940e37`
- 最终 candidate commit：`50300667983f631dbb13bc17c8e659e1c4230d48`
- handoff package identity：本文件所在的 handoff-only commit；独立 Reviewer 必须从 Git 解析完整 40-hex
- 状态：`REMEDIATION_COMPLETE / SELF_CHECK_PASS / NOT_AN_INDEPENDENT_S1_PREREQUISITE_DECISION / NOT_EXECUTION_AUTHORIZED`

> 本记录只陈述 Builder 的修复、自查和交接事实。作者参与了 candidate 修改，不具独立审查资格；本文不签发 S1、
> 不预置 `S1_PREREQUISITES_ACCEPTED`，也不授权任何真实 dry-run。

## 1. 授权与不变量

本轮只准备 S1 prerequisite candidate 与独立复核材料。外部 S0 事实仅为
`PROTOCOL_ACCEPTED / allowed_next_action: request-s1`；它不授权真实 experiment identity/root、正式 evidence root、
真实执行 venv、依赖安装或升级、正式 1K input、SQLite/LanceDB、S1/S2/S3 gate、production 修改、后端选择或 M8 admission。

本轮没有访问 `D:\111_Others_Subjects`，没有 push origin，也没有执行 `git reset`、`git clean`、
`git restore` 或 `git checkout -- <path>`。M8 仍为 `BLOCKED / PREPARING_S1`。

## 2. 首个 candidate 与 fresh-clone failure

首个不可变 candidate 为：

- commit：`8e006b3d1e7630a650718a515e50644c67940e37`
- subject：`feat(m8): prepare v3 s1 prerequisite candidate`

在全新、完整、非 shared clone 中重放时，aggregate suite 的
`S1 contracts and authorization controls` 失败。具体失败来自四个 observer component 的八个 schema const mismatch：
每个 component 的 `implementation_ref.byte_count` 与 `implementation_ref.sha256` 都不匹配。

失败 clone 中没有修复任何文件。后续修复返回 Builder 主 checkout，并以新 commit 取代旧 candidate。

## 3. 根因与修复

根因是主 Windows checkout 的 `tools/m8_observe_minimal_1k_v3.py` 仍物理 materialize 为 CRLF，而 candidate Git object 与
fresh clone 根据 `.gitattributes` 为 LF。旧测试从当前 worktree bytes 动态计算 synthetic reference，schema const 则绑定主
checkout 的 CRLF bytes，导致主 checkout 通过而 fresh clone 失败。

| representation | bytes | carriage returns | SHA-256 |
| --- | ---: | ---: | --- |
| 主 checkout physical bytes | 19044 | 524 | `20a0b4a6f581364ba95d6132a5a4e88c1ec871bf9cb0fe2461673b45dd29873f` |
| candidate Git-object LF bytes | 18520 | 0 | `f8fb842955f5a6164e61c6d62f9e25de0fe738391e98cd925a82c39c3d4fbf95` |

修复仅涉及两个既有 candidate path：

1. `tools/m8_test_s1_controls_v3.py`：synthetic fact 只把 CRLF pair 规范化为 LF；若规范化后仍含孤立 CR，则 fail closed。
2. `docs/plans/references/schemas/m8-minimal-1k-observer-config-v3.schema.json`：将 observer implementation const 更新为
   Git-object LF bytes（18520 / `f8fb8429…fbf95`）。

最终 replacement candidate：

- commit：`50300667983f631dbb13bc17c8e659e1c4230d48`
- subject：`fix(m8): bind observer schema to git bytes`
- delta：2 files changed，4 insertions，2 deletions

修复后的 focused S1 controls 为 13/13 PASS。语言服务器未报告诊断。

## 4. Fresh full-clone replay

Builder 随后创建了另一个全新 full clone，并 detached checkout 到精确 final candidate。该 replay 满足：

- `git rev-parse --is-shallow-repository` 为 `false`；
- `.git/objects/info/alternates` 不存在；
- detached HEAD 为 `50300667983f631dbb13bc17c8e659e1c4230d48`；
- strict no-reflog fsck 通过；
- 初始与最终 status 均 clean；
- 14 个 candidate Python tools 编译通过；
- `git diff --check` 通过。

完整 aggregate 通过全部 16 项，并以以下标记结束：

```text
ALL PASS: M8 v3 S1 prerequisite suite
```

附加 replay 结果：

- graph harness：`ALL PASS: 5 persistent graphs + 45 fail-closed mutations + 2 sensitivity proofs`；
- deterministic generator suite：27/27；
- synthetic observer suite：20/20；
- S1 controls：13/13；
- S1 prerequisite freeze self-test：PASS；
- existing hermetic review-freeze regression：PASS；
- historical P1 materials：88/88；
- historical P0/P1 r02：77/77。

这些是 Builder verification，不是独立 S1 prerequisite review。

## 5. Deterministic Git-object prerequisite freeze

只从 final candidate 的 Git-object bytes 生成两份不同临时输出。两份文件逐字节相同：

| field | value |
| --- | --- |
| source commit | `50300667983f631dbb13bc17c8e659e1c4230d48` |
| format | `m8-s1-prerequisites-v3-freeze-v1` |
| purpose | `S1_PREREQUISITE_RECORD_ONLY_NOT_AUTHORIZATION` |
| canonicalization | `sa-json-c14n-v1` |
| artifact SHA-256 | `efd95cf45d1749b323a008f5559f4839f0ef1cb0acfa674720c185e455ac806a` |
| artifact bytes | 32688 |
| candidate file count | 119 |
| candidate total bytes | 808180 |
| worktree comparison | `NOT_REQUESTED`；`divergent_paths=[]` |

两份均为 UTF-8、无 BOM、无 CR、compact sorted canonical JSON，并恰有一个 final LF。仓库内 handoff artifact 是这组已比较
bytes 的原样副本，不以 package checkout 或可变 worktree 重新生成。

## 6. Handoff-only package boundary

当前 handoff package 只新增以下四个非 candidate path：

1. `docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-prereq-freeze-20260917.json`
2. `docs/plans/references/m8-minimal-1k-v3-s1-prereq-builder-self-check-20260917.md`
3. `docs/plans/references/m8-minimal-1k-v3-s1-prereq-review-materials-20260917.md`
4. `docs/plans/references/m8-minimal-1k-v3-s1-prereq-reviewer-worksheet-20260917.md`

`docs/plans/references/README.md` 是 119-path frozen candidate closure 的成员，故 package 明确不修改它。包内 review materials
自身列出完整四文件 inventory，避免以索引便利性破坏 candidate/package byte boundary。`tools/README.md` 同样保持不变。

`.claude/tmp/`、临时 freeze、replay logs 和测试输出均不属于 package，不得提交。

## 7. Builder self-check 与交接

Builder self-check 的含义仅为 prerequisite package 已准备完毕，并不构成独立裁定：

```text
candidate: 50300667983f631dbb13bc17c8e659e1c4230d48
builder replay: PASS
builder double-freeze comparison: PASS
candidate-path preservation requirement: 119/119 unchanged
independent review performed: no
S1 gate issued: no
execution authorized: no
```

允许的下一步只有请求一个未参与 candidate 或本 package 修改的独立 Reviewer，在只读 full clone 中复算 freeze、重放要求并自行填写
blank worksheet。即使 prerequisite review 将来接受，也不自动产生 `DRY_RUN_AUTHORIZED`，更不授权 S2 或 S3。

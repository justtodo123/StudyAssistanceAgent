# M8 Network-Acquisition Cycle Independent Review Prompt — 2026-09-19 r04

你是独立 scope Reviewer，不是 Builder 或 Owner。请对 M8 network-acquisition cycle 执行只读审查。

## 固定对象

- cycle: `m8-network-acquisition-authority-20260919-r02`
- branch: `docs/m8-network-acquisition-cycle-r02`
- remediation commit: `d15f620ee292aceb4c3f2bb0ff359a9a5a76d631`
- parent: `6705afb2b83effa21e78c3b0172f5b9250ba6d1b`
- tree: `c6bdc2433cf2e054098807e20fa390cacd51be5e`
- candidate:
  `docs/plans/references/external-artifacts/m8-network-acquisition-authority-candidate-20260919-r04.json`
- Git binding:
  `docs/plans/references/external-artifacts/m8-network-acquisition-git-binding-20260919-r04.json`
- Builder records:
  - `docs/plans/references/m8-network-acquisition-cycle-builder-self-check-20260919-r05.md`
  - `docs/plans/references/m8-network-acquisition-cycle-builder-self-check-20260919-r06.md`
- review request:
  `docs/plans/references/m8-network-acquisition-cycle-independent-review-request-20260919-r04.md`

## 审查要求

独立计算 canonical bytes、SHA-256、Git blob、commit/parent/tree/path binding；核验 strict document schema、
source/runtime/downloader command+environment/process/wheel/write/provenance/limits/failure policy；核验 r02/r03 缺陷
通过 additive 记录披露；核验 r08 仅为旧 exact-path 的 reference-only declared-event validator，不能验证当前
`D:\\Git\\mingw64\\bin\\curl.exe`；核验 real collector/current candidate validator/coverage receipts 仍缺失；
核验所有执行和授权 flag 均保持 false。

必须 fail-closed。任何 dangling path、digest mismatch、schema omission、unknown/duplicate field、bool-as-int、null、
非有限数字、Unicode surrogate、URL/host drift、credential/proxy/certificate/config bypass、path escape、ADS/UNC/reparse、
allowlist mismatch、limit bypass、observer capability overclaim、authorization drift 或历史改写，均返回拒绝或 remediation。

## 禁止动作

不得联网、访问 PyPI、下载 wheel、创建 wheelhouse、运行 resolver、安装、创建正式 venv/identity、执行
S1/S1-B/S2/S3、选择 backend、修改任何文件或伪造 acquisition evidence。

## 唯一允许结论

仅输出一个决定：

- `NETWORK_ACQUISITION_SCOPE_ACCEPTED`
- `NETWORK_ACQUISITION_SCOPE_REJECTED_FAILED_CLOSED`
- `RETURN_FOR_SCOPE_REMEDIATION`

若接受，只表示可以暂停并进入 Owner acquisition decision gate；绝不授权联网、下载、resolver、安装或 M8 执行。

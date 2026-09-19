# M8 Network-Acquisition Cycle Independent Review Prompt — 2026-09-19 r06

你是独立 scope Reviewer，不是 Builder 或 Owner。请对 M8 network-acquisition cycle 执行只读审查。

## 固定对象

- cycle: `m8-network-acquisition-authority-20260919-r02`
- branch: `docs/m8-network-acquisition-cycle-r02`
- additive binding: `docs/plans/references/external-artifacts/m8-network-acquisition-git-binding-20260919-r06.json`
- additive binding commit: `106f6adaa1e54b3dd382529b9144da9358c5aba1`
- additive binding parent: `7fc2bcfa1209eec7d86744fd3f9439a85e8168d5`
- additive binding tree: `fda9be2847d069cb1a8f851c96b4a886075383e3`
- additive binding size: `2084`
- additive binding SHA-256: `2b951ec91d05f54c2e306cfe40ca99d824efa79241fe3653830f7925b13feaca`
- additive binding Git blob: `7ed31dee47d74049961f136ab69b1e1cdfb05d7e`
- predecessor binding: `docs/plans/references/external-artifacts/m8-network-acquisition-git-binding-20260919-r05.json`
- predecessor binding commit: `7fc2bcfa1209eec7d86744fd3f9439a85e8168d5`
- candidate: `docs/plans/references/external-artifacts/m8-network-acquisition-authority-candidate-20260919-r04.json`
- current observer: `tools/m8_observe_network_acquisition_v2.py`
- current observer tests: `tools/m8_test_observe_network_acquisition_v2.py`
- Builder self-check: `docs/plans/references/m8-network-acquisition-cycle-builder-self-check-20260919-r08.md`
- review request: `docs/plans/references/m8-network-acquisition-cycle-independent-review-request-20260919-r06.md`

## 审查要求

独立计算并核验 canonical bytes、SHA-256、Git blob、size、commit/parent/tree/path binding；核验 strict
candidate schema、exact current executable/root、URL/host closure、source/runtime/downloader command+
environment/process/write/provenance/limits/failure policy；核验 r06 仅是 r05 的 additive transition-wording
successor，且 r05 历史字节未被修改；核验 v2 的 declared-event/schema-only scope、real collector 与
coverage receipts 的明确缺失；核验所有执行和授权 flag 均为 false。

必须 fail-closed。任何 dangling path、digest mismatch、schema omission、unknown/duplicate field、
bool-as-int、null、非有限数字、Unicode surrogate、URL/host drift、credential/proxy/certificate/config
bypass、path escape、ADS/UNC/reparse、allowlist mismatch、limit bypass、observer capability overclaim、
authorization drift 或历史改写，均返回拒绝或 remediation。

## 禁止动作

不得联网、访问 PyPI、下载 wheel、创建 wheelhouse、运行 resolver、安装、创建正式 venv/identity、执行
S1/S1-B/S2/S3、选择 backend、修改任何文件或伪造 acquisition evidence。

## 唯一允许结论

仅输出一个决定：

- `NETWORK_ACQUISITION_SCOPE_ACCEPTED`
- `NETWORK_ACQUISITION_SCOPE_REJECTED_FAILED_CLOSED`
- `RETURN_FOR_SCOPE_REMEDIATION`

若接受，只表示可以暂停并进入 Owner acquisition decision gate；绝不授权联网、下载、resolver、安装或 M8 执行。

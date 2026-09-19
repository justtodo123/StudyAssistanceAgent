# M8 Network-Acquisition Cycle Builder Adversarial Self-Check — 2026-09-19 r07

- record_type: `M8_NETWORK_ACQUISITION_CYCLE_BUILDER_ADVERSARIAL_SELF_CHECK`
- builder_role: `builder`
- cycle_id: `m8-network-acquisition-authority-20260919-r02`
- cycle_type: `NETWORK_ACQUISITION_CYCLE`
- branch: `docs/m8-network-acquisition-cycle-r02`
- review_package_commit: `a621159`
- result: `BUILDER_RETURN_FOR_SCOPE_REMEDIATION`
- acquisition_status: `NOT_AUTHORIZED`
- m8_status: `BLOCKED / NOT_STARTED`

> 本记录取代 r06 的 Builder readiness 结论，但不修改 r06 历史字节。它不是独立 Reviewer 或 Owner 决定。

## 后置对抗审计结论

r04 binding 和 r04 review request 已在 `a621159` 中 additive 提交，因此先前关于“binding/request 不存在”的观察已由
该提交关闭；binding 正确冻结 `d15f620...` 中的 r04/r05 字节。然而，observer source/test 独立静态审计确认
r06 仍过度陈述 implementation conformance，必须 fail-closed：

| check_id | result | evidence |
| --- | --- | --- |
| exact-downloader-validation | BLOCKED | bound r08 validator 只接受 `C:\\Program Files\\Git\\mingw64\\bin\\curl.exe`，r04 candidate 是 `D:\\Git\\mingw64\\bin\\curl.exe`。 |
| exact-root-validation | BLOCKED | bound validator root 是 `...20260918-r01`，r04 candidate root 是 `...20260919-r02`。 |
| current-candidate-validator | NOT_IMPLEMENTED | r04 已披露，但 r06 仍把 source/write/process policy 写成足以进入 scope review 的完整矩阵。 |
| canonical-url-closure | BLOCKED | validator 接受显式 `:443` 和大小写漂移；r04 未冻结 no-explicit-port / strict-canonical-URL policy。 |
| candidate-schema-enforcement | BLOCKED | r04 strict document policy 仅为声明，未绑定执行该 schema 的 validator 与负例测试。 |
| test-coverage | BLOCKED | 当前 tests 未覆盖 candidate path/root、files.pythonhosted.org initial-host deny、部分 bool-as-int、Infinity 和 undecodable binary redaction。 |
| collector-coverage | BLOCKED | real collector、coverage receipts、rename/PID/argv/cwd/lifecycle evidence 仍不存在。 |

## 处置

r04/r05、binding 和 r04 request/prompt 均保留为不可变 Builder 历史，但不得发送给独立 Reviewer，也不得把
`a621159` 解释为 scope-review readiness。下一步必须 additive 实现与当前 candidate 对齐的 hermetic schema/
declared-event validator 及负例测试，或进一步把 scope 明确缩小为不含 implementation conformance；无论何种路径，
都必须重新冻结 Git objects 并生成新的 Builder/review package。

- independent_scope_review_status: `NOT_STARTED`
- owner_acquisition_decision_status: `NOT_REACHED`
- acquisition_authorized: `false`
- network_access_authorized: `false`
- wheel_download_authorized: `false`
- wheelhouse_creation_authorized: `false`
- resolver_authorized: `false`
- installation_authorized: `false`
- formal_venv_authorized: `false`
- formal_identity_authorized: `false`
- real_collector_authorized: `false`
- s1_retry_authorized: `false`
- s1_b_authorized: `false`
- s2_authorized: `false`
- s3_authorized: `false`
- backend_selection_authorized: `false`
- allowed_next_action: `additive-current-candidate-validator-remediation`

`BUILDER_RETURN_FOR_SCOPE_REMEDIATION`

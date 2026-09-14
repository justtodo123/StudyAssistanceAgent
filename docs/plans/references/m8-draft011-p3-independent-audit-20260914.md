# M8 `draft-0.11` P3 独立文本审计记录

- reviewer：`external-reviewer-01`
- audit_id：`p3-audit-20260914-external-reviewer-01`
- text-audit verdict：`REJECTED`
- P3 decision：`REJECTED / stop`
- timestamp：`2026-09-14T09:52:57Z`

## 独立性 basis

Reviewer 名称与 drafting party `ai-assistant`、P0/P1/P2 predecessor-chain owner `justtodo123` 均逐字节不同。审计结论依据冻结的 draft-0.11 协议、P0→P1→P2 canonical records、identity、parent-binding、repository-binding 及其 schema 规则形成，未采用预置的 verdict、finding_ids 或下一动作。现有材料无法独立密码学证明 reviewer 未参与协议、授权记录、修订脚本或验收脚本起草，因此该事项不被虚构为已证明事实。

## Findings

- **c-01**：BINDING_STREAM_ALLOWLIST 使用 order=key(scope)，但 STREAM_SCOPE 的声明顺序为 file,directory,volume-root，冻结字面量却为 volume-root,directory,file；任一实例都无法同时满足冻结字面量和 comparator。
- **c-02**：P7A 的 scope.operations 使用 order=value，操作枚举中 publish 排在 cleanup 之前，但 closed mapping 要求 [cleanup,publish]；[publish,cleanup] 虽满足排序却违反 exact mapping，因此不存在合法 P7A operations 数组。
- **c-03**：query-observation 未运行后缀要求 stable_code=NOT_RUN_GATE_STOP，但该字段类型为 RESULT_CODE，允许的是 phase-qualified STABLE_CODE 或 NONE；NOT_RUN_GATE_STOP 不是合法值。
- **c-04**：fault-fixture receipt 的 closed schema 仅提供 mutation_sha256，而后续验证规则要求 receipt 重复完整五字段 MUTATION_SPEC；增加字段违反 closed object，省略字段又无法满足验证要求。
- **c-05**：多个 hard/resource predicate 将原始 INVALID_PROTOCOL_DEVIATION 指定为 false code，但对应字段要求 phase-qualified STABLE_CODE；使用合规的 PROTOCOL_RUNTIME_INVALID_PROTOCOL_DEVIATION 又不再等于 registry 中冻结的 raw code。
- **c-06**：catalog、index、query-plan artifacts 被要求进入完整 evidence REF closure，但闭合 evidence selector 只能选择 proof/digest 路径，不能选择这些 artifact 的 REF；digest-only proof 无法满足完整 envelope REF 要求。
- **c-07**：durable package 只约束 gate_members 数量为九个，未枚举九个 gate record 的 logical names、gate IDs 或 external-gate schema；因此非 gate member 集合也可满足同一 cardinality 约束。
- **c-08**：forbidden_history_ids 按 key(ordinal) 排序，却只要求 ordinal 在 0..12 且未要求 ordinal 唯一；不同 ID 可共享 ordinal，导致 canonical order 不确定。
- **c-09**：query-streams 的 stream_query_source 一方面因其 API 已是 NtQueryInformationFile/FileStreamInformation 而必须为 "not-applicable"，另一方面又因 file operation 规则必须为 object；该字段无法实例化。
- **c-10**：child-allowlist 的 control evidence 每个 API family 只冻结一个 scalar api，但 environment/watchdog/process evidence 又要求分别包含多个唯一 api_values；两个 closed schema 要求无法同时满足。
- **c-11**：deny-code 表冻结单一 STABLE_CODE，同时覆盖 preflight 与 runtime outbound 场景；后续规则要求按 phase 使用不同的 phase-qualified code，不能与冻结表的单值要求同时成立。
- **c-12**：exact_flat_proof_refs 的 schema comparator 要求按 key(logical_name,schema_id,sha256) 排序，但后续文字要求按 key(scope,workload,backend,sample_id) 排序；REF comparator 又不能读取 pointee 字段，故同一数组无法机械满足两种排序。
- **c-13**：lifecycle 要求 P7、verification report、package、normal receipt 与 P8 disposition byte-identical，但 P8 payload 没有 disposition 字段；该 equality 约束无法被 P8 记录完整表达或验证。
- **l-02**：abort cleanup 因 root 或 descendants 已存在而启动，但成功 receipt 同时要求 cleanup 前后 inventory 均为零且 root_exists=false；需要 cleanup 的分支无法产生满足该成功条件的证据。

上述 findings 均为文本/schema 层面的阻断性缺陷。未将 disputed 的 `.payload` schema-ID 命名模式、P8/P9 状态标签、P3 drafting-party 比较解释或 coordinator/report-writer 身份问题列入 findings。

按协议闭合映射，`text-audit=REJECTED` 且 findings 非空只能产生 `P3 REJECTED / stop`。不得 `request-p4`，不得创建 P4、experiment root、获取依赖、准备输入、执行 benchmark、发布证据、选择 backend 或准入 M8。M8 继续 `BLOCKED / NOT_STARTED`。

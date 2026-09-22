# M11 真实数据规模化准入准备计划

> 当前状态：设计准备；`BLOCKED / NOT_STARTED`，未获准开工
> 拟议前置：M8、M9、M10 退出证据；M7 source lifecycle 权威保持有效
> 范围决策：[`references/m8-m12-scope-decision-v1.md`](references/m8-m12-scope-decision-v1.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. 目标、范围与非目标

M11 的唯一正式退出目标是：

> 发布并验证 10,000 个许可清晰、来源可追溯、质量可验证的真实 approved chunks，形成可供学习、检索、规划与
> Runner 使用的数据产品，而不是容量 fixture。

规模统一按可检索 chunks 计量。M11 采用“当前基线 → 3K → 10K”逐级 Gate；30K/100K 只作为后续扩展 Gate，
不阻塞 M11 完成。M8 的 100K synthetic/半合成 capacity evidence 不能替代 M11 的真实语料质量证据。

本阶段不部署云服务器、不引入多租户、不批准 Qdrant server、不追求百万级数据，也不得通过重复切块、低质量抓取、
未授权题库或未审 Stack Exchange 全量 dump 补量。

## 2. 不可削弱的不变量

- M7 SQLite Registry 继续是 Source、owner、revision、generation、lifecycle、删除和 provenance 的唯一权威；
- raw、normalized、candidate、approved、rejected、report、snapshot 分层保持清晰，原始数据和大型索引不进入 Git；
- 每个 approved document 必须有 canonical URL、来源、许可、revision、抓取/导入时间和内容 digest；
- 每个 chunk 必须可追溯到 document、Source revision、chunk policy、embedding generation 与发布 snapshot；
- parser 失败不得静默丢弃；未批准、许可不明、第三方或隐私内容不得进入 published view；
- Source 删除、撤销许可或 revision 替换必须传播到 BM25、vector、cache、provenance 和计划 grounding；
- 默认本地离线 profile 可运行；数据扩展不能强制云端或外部 AI。

拟议阶段前置继续保持未满足，不因本计划存在而自动闭合：

| Prerequisite ID | 状态 | 闭合条件 |
| --- | --- | --- |
| `M11-M8-EXIT` | `OPEN` | M8 取得独立完成批准并提供可引用退出证据 |
| `M11-M9-EXIT` | `OPEN` | M9 取得独立完成批准并提供可引用退出证据 |
| `M11-M10-EXIT` | `OPEN` | M10 取得独立完成批准并提供可引用退出证据 |

## 3. 强制 Decision（准入前全部保持 `OPEN`）

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M11-SCALE-GATES` | `OPEN` | 当前基线、3K、10K 的精确 chunk/document/source 计量、停止条件与限额 |
| `M11-SOURCE-ALLOWLIST` | `OPEN` | 来源白名单、领域分布、许可策略、revision 和排除规则 |
| `M11-PARSER-QUALITY` | `OPEN` | 支持格式、parser 版本、失败/乱码/结构丢失门槛和人工复核 |
| `M11-CHUNK-POLICY` | `OPEN` | chunk 大小、overlap、标题/代码/表格/公式边界、版本和去重 |
| `M11-LICENSE-PROVENANCE` | `OPEN` | 许可、署名、canonical URL、派生关系、撤销与审计保留 |
| `M11-QUALITY-EVALUATION` | `OPEN` | 事实准确率、重复率、领域平衡、人工抽样和发布阈值 |
| `M11-RETRIEVAL-EVALUATION` | `OPEN` | 真实 query/gold、Recall@3/5、MRR、no-hit、hard-negative、跨语言和 filter |
| `M11-PUBLICATION` | `OPEN` | candidate → approved → generation publication、last-good、rollback 和 receipt |
| `M11-INCREMENTAL-SYNC` | `OPEN` | fingerprint、增量 upsert/delete、失败重试、幂等和禁止常规 `replace_all()` |
| `M11-PRIVACY-RETENTION` | `OPEN` | 用户数据、私人资料、日志/报告、保留、导出和删除边界 |

所有 Decision 必须包含唯一政策值、证据、责任人、日期、复核/撤销条件和独立批准。候选来源列表、目标数量或
“后续人工处理”不能替代闭合政策。

## 4. 数据源优先级与领域平衡

初始参考白名单沿用 [`data-expansion-runbook.md`](data-expansion-runbook.md)，但每个来源必须重新完成许可与 revision
核验：

- P0：项目人工知识包、项目原创评测集、许可明确的 MIT OCW 子集、OpenDSA 经确认的教材内容；
- P0/P1：RFC Editor approved subset、IANA registries、Linux Kernel Documentation 的明确许可内容；
- P1：数据库、编译原理、分布式系统、软件工程和安全的许可明确开放课程/官方文档；
- P2：Stack Exchange 审核子集，仅在署名生成、许可版本、删除和派生链闭合后启用。

不得让 Linux/RFC 大量内容机械淹没数据结构、组成原理、数据库等教学领域。每个 Gate 在执行前必须冻结领域配额与
最大占比；权威规范层、教学解释层和评测层分开统计。

## 5. 分级 Gate

### 5.1 Baseline Gate

- 当前默认知识包约 682 chunks 的 identity、provenance、Recall 和删除语义保持稳定；
- 固定默认三课回归和 Network 显式扩展边界；
- 冻结 parser/chunk/embedding profile 和报告 schema。

### 5.2 3K Gate

3K 是首个真实扩展 Gate，不是 M11 完成：

- 3,000 个真实 approved chunks，禁止用纯 synthetic fixture 计数；
- 100% document 有来源/许可/revision/canonical URL；
- 100% chunk 可追溯；parser failure 无静默丢失；
- 精确重复率、乱码率、事实准确率和领域分布达到预冻结阈值；
- 真实 query/gold 与检索指标通过；
- incremental publish、rollback 和删除传播通过。

### 5.3 10K Exit Gate

10K 是 M11 正式退出目标：

- 10,000 个真实 approved chunks；
- 以增量 upsert/delete 和 generation publication 为常规同步方式，禁止全库 `replace_all()`；
- 在 M8 获批数据面与 SQLite fallback 上验证 quality、filter、reopen、delete 和资源预算；
- M9 Planner 在 10K 下仍只消费有界摘要/目录输入；
- M10 ingestion/embedding/reindex job 在取消、崩溃和恢复下无半发布 generation；
- 负责人独立批准 10K 数据产品发布和 M11 完成。

### 5.4 30K/100K 后续 Gate

30K 与 100K 只记录触发条件、资源和质量预算，不属于 M11 完成前置。达到 10K 后，只有真实需求、来源质量和维护能力
证明有价值时，才逐级提出新批准；不得从 10K 直接跳到 100K。

## 6. 质量与检索验收类别

数值必须在运行前冻结，至少覆盖：

- 100% approved document 来源、许可、revision 和 canonical URL 完整；
- 100% chunk provenance 完整；未授权第三方内容和凭据为零；
- parser 失败、乱码、结构缺失、精确/近重复率和人工抽样事实准确率；
- 领域与来源分布，防止单一来源垄断 top-k；
- Recall@3、Recall@5、MRR、no-hit、hard-negative、跨语言、缩写/全称和代码/协议编号；
- owner/source/generation/snapshot filter 正确率；删除 Source 零召回；
- build/incremental/reopen/delete 的延迟、RSS 和磁盘；
- citation/provenance 与答案 grounding 的人工抽查。

100K synthetic benchmark 只能复用工程资源门槛，不得直接复用为真实质量阈值或 PASS。

## 7. 获准后的拟实施顺序

1. 关闭十项 Decision 并冻结 Baseline/3K 协议；
2. 完成 P0 来源的许可/revision/asset inventory；
3. 建立 raw → normalized → candidate → approved 的可重放 pipeline；
4. 生成并双人/独立抽查 3K candidate，达到 Gate 后原子发布；
5. 扩展来源和领域，使用增量 pipeline 推进 10K；
6. 冻结并执行 10K quality/retrieval/lifecycle/Planner/Runner 联合验收；
7. 独立批准数据产品和 M11 完成；30K/100K 另行立项。

## 8. 准入检查与批准记录

- [ ] M8/M9/M10 真实退出证据有效；**2026-09-22 就地标注**：M8 已由 owner 以「维持现状结论」分支结掉
  （`references/m8-owner-policy-only-scope-decision-20260919.md`：`POLICY_ONLY_SCOPE_ACCEPTED` /
  `record-policy-only-scope-and-stop`，所有真实动作 `NOT_AUTHORIZED / NOT_PERFORMED`），**不会**产生
  「真实退出证据」。因此本项在 M11 准入前必须**重新澄清**——要么接受 M8 侧的维持现状结论（与 M9 的
  `M9-M8-EXIT`、M10 的 `M10-M8-EXIT` 同一分支），要么明确 M11 另有 10K 真实数据需求而**另行**为 M8 立项。
  不得把本项读成「M8 迟早会给出真实退出证据」而无限期挂起；
- [ ] 十项强制 Decision 全部 `RESOLVED`；
- [ ] Baseline/3K workload、来源、许可、parser、chunk、质量和检索阈值冻结；
- [ ] 数据目录、manifest、报告和隐私边界可验证；
- [ ] `docs/PLAN.md`、本计划和机器门禁一致；
- [ ] 负责人完成阶段 admission 和生产开工的分离批准。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准为空，M11 必须保持 `BLOCKED / NOT_STARTED`。本文不授权下载、抓取、导入、解析、embedding、索引构建、数据发布、
云部署、commit、merge 或 push。

## 9. 撤销与后续边界

来源许可、parser/chunk/embedding profile、质量/检索 workload、控制面权威或删除语义实质变化时，阶段 admission 必须
`REVOKED` 并重新批准。M12 只能消费经过批准的 M11 published snapshot，不能用云端容量掩盖本地数据质量问题。

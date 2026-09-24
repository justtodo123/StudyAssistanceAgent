# M11 真实数据规模化准入准备计划

> 当前状态：`ADMITTED / IN_PROGRESS`（2026-09-23 获准入并授权开工，范围 `m11-data-scaling-v1`，
> plan_revision v1.1 纳入 A1/A2/A3：`tests/M11/`、chunk 硬顶 4000、P0 白名单下载入库）
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

三项前置自 2026-09-23 起均已 `SATISFIED`。十项 Decision 同日全部 `RESOLVED`（闭合记录
[`references/m11-decision-closure-v1.md`](references/m11-decision-closure-v1.md)）。2026-09-23 owner 批准准入
（见 §8.1）：`admission_status=ADMITTED`，`delivery_status=IN_PROGRESS`，`implementation_start=AUTHORIZED`。
plan_revision v1.1（见 §8.2）把 A1/A2/A3 从 `excluded` 移入 `included`。

| Prerequisite ID | 状态 | 闭合条件 |
| --- | --- | --- |
| `M11-M8-EXIT` | `SATISFIED` | 2026-09-23 owner 批准的**维持现状结论**（见 §2.1）：M11 数据面维持当前 SQLite registry + linear cosine + 默认 BM25，100K 专业化存储容量验证保持待命参考；**不是** M8 容量证据或 M8 COMPLETE |
| `M11-M9-EXIT` | `SATISFIED` | M9 独立完成批准与退出证据；见 `docs/PLAN.md` 与 [`m9-goal-driven-planning-plan.md`](m9-goal-driven-planning-plan.md) §4.5 |
| `M11-M10-EXIT` | `SATISFIED` | M10 独立完成批准与退出证据；见 `docs/PLAN.md`、[`m10-autonomous-runner-plan.md`](m10-autonomous-runner-plan.md) §5.3 与 [`references/m10-completion-evidence-v1.md`](references/m10-completion-evidence-v1.md) |

### 2.1 `M11-M8-EXIT` 维持现状结论（2026-09-23 owner 裁定）

`M11-M8-EXIT` 的准入检查表已要求本项在准入前**重新澄清**，不得把 M8 维持现状读成「迟早会给出真实退出证据」。
本节兑现与 M9/M10 相同的维持现状分支。

| 裁定字段 | 值 |
| --- | --- |
| decided_by | justtodo123 |
| decided_at | 2026-09-23 |
| decision_reference | User instruction: 「走维持现状结论（推荐）」——回应「`M11-M8-EXIT` 走哪条。推荐选『维持现状结论』」。读作：M11 数据面维持当前 SQLite/BM25，不重启 M8 协议链，100K 专业化存储保持待命参考 |
| data_plane | 维持当前 SQLite registry（唯一控制面）+ SQLite linear cosine + 默认 BM25 |
| deferred | 100K 专业化存储容量验证（LanceDB / Qdrant）保持**待命参考**，不阻塞 M11 准入准备 |

**结论的依据**（三条，均可追溯）：

1. **M11 的正式退出目标是 10K 真实 approved chunks，不是专业向量后端。** 许可、来源、parser、chunk、质量与检索评测都不依赖 LanceDB/Qdrant。
2. **M8 侧已由 owner 亲手封存**：`references/m8-owner-policy-only-scope-decision-20260919.md` 记
   `POLICY_ONLY_SCOPE_ACCEPTED`、`allowed_next_action: record-policy-only-scope-and-stop`；其后
   `draft-0.10` / `draft-0.11` 独立 P3 均 `REJECTED / stop`。
3. **M9 与 M10 已走同一分支**：`M9-M8-EXIT` 与 `M10-M8-EXIT` 均以维持现状结论兑现。再开一轮 M8 的期望产出是再下探一层约束，不是 M11 所需的真实语料质量证据。

**本裁定做什么**：把 `M11-M8-EXIT` 由 `OPEN` 改为 `SATISFIED`，并在登记表写入上述证据路径。

**本裁定不做什么**（逐条，防止被后读高估）：

- **不构成当时的 M11 准入批准**：在本裁定作出时，`admission_status` 仍为 `BLOCKED`、`approval` 五个字段仍为空；当时仍需 §3 全部十项强制决策 `RESOLVED` 与 owner 的独立准入批准。十项 Decision 随后于 2026-09-23 同日闭合，准入批准及开工授权也已分别记录于 §8.1/§8.2；当前状态以文档顶部和登记表为准。
- **不批准 M8 的任何执行**：不选择后端、不建 `tests/M8/`、不做 100K 实证；M8 保持 `BLOCKED / NOT_STARTED`。
- **不产生任何容量证据**：这是维持现状，不是「容量已验证」。
- **不授权下载、抓取、导入、解析、embedding、索引或数据发布**：这些是本裁定作出时的边界；后续已获授权的范围与当前未授权事项见 §8.2–§8.4。
- **不触发 §4 撤销、不写 `admission_history`**：在本裁定作出时 M11 尚未准入，本次是 `BLOCKED → BLOCKED`；随后批准记录按 §8.1/§8.2 留存。

## 3. 强制 Decision（十项已 `RESOLVED`；当前 M11 为 `ADMITTED / IN_PROGRESS`）

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M11-SCALE-GATES` | `RESOLVED` | 当前基线、3K、10K 的精确 chunk/document/source 计量、停止条件与限额（2026-09-23 批次 ①，`value` 见登记表与 [`references/m11-decision-closure-v1.md`](references/m11-decision-closure-v1.md) §1.1） |
| `M11-SOURCE-ALLOWLIST` | `RESOLVED` | 来源白名单、领域分布、许可策略、revision 和排除规则（2026-09-23 批次 ①，见闭合记录 §1.2） |
| `M11-PARSER-QUALITY` | `RESOLVED` | 支持格式、parser 版本、失败/乱码/结构丢失门槛和人工复核（2026-09-23 批次 ②，见闭合记录 §3.1） |
| `M11-CHUNK-POLICY` | `RESOLVED` | chunk 大小、overlap、标题/代码/表格/公式边界、版本和去重（2026-09-23 批次 ②，见闭合记录 §3.2） |
| `M11-LICENSE-PROVENANCE` | `RESOLVED` | 许可、署名、canonical URL、派生关系、撤销与审计保留（2026-09-23 批次 ①，见闭合记录 §1.3） |
| `M11-QUALITY-EVALUATION` | `RESOLVED` | 事实准确率、重复率、领域平衡、人工抽样和发布阈值（2026-09-23 批次 ③，见闭合记录 §5.1） |
| `M11-RETRIEVAL-EVALUATION` | `RESOLVED` | 真实 query/gold、Recall@3/5、MRR、no-hit、hard-negative、跨语言和 filter（2026-09-23 批次 ③，见闭合记录 §5.2） |
| `M11-PUBLICATION` | `RESOLVED` | candidate → approved → generation publication、last-good、rollback 和 receipt（2026-09-23 批次 ②，见闭合记录 §3.3） |
| `M11-INCREMENTAL-SYNC` | `RESOLVED` | fingerprint、增量 upsert/delete、失败重试、幂等和禁止常规 `replace_all()`（2026-09-23 批次 ②，见闭合记录 §3.4） |
| `M11-PRIVACY-RETENTION` | `RESOLVED` | 用户数据、私人资料、日志/报告、保留、导出和删除边界（2026-09-23 批次 ①，见闭合记录 §1.4） |

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

1. 关闭十项 Decision 并冻结 Baseline/3K 协议（决策已闭合；冻结物见
   [`references/m11-baseline-3k-freeze-v1.md`](references/m11-baseline-3k-freeze-v1.md)，测试方案见
   [`references/m11-test-plan-v1.md`](references/m11-test-plan-v1.md)——二者**不**批准准入）；
2. 完成 P0 来源的许可/revision/asset inventory；
3. 建立 raw → normalized → candidate → approved 的可重放 pipeline；
4. 生成并双人/独立抽查 3K candidate，达到 Gate 后原子发布；
5. 扩展来源和领域，使用增量 pipeline 推进 10K；
6. 冻结并执行 10K quality/retrieval/lifecycle/Planner/Runner 联合验收；
7. 独立批准数据产品和 M11 完成；30K/100K 另行立项。

## 8. 准入检查与批准记录

- [x] M8/M9/M10 退出前置已澄清并登记为 `SATISFIED`（`M11-M8-EXIT` 以 §2.1 的维持现状结论兑现，**不是**容量证据；`M11-M9-EXIT` / `M11-M10-EXIT` 只登记 M9/M10 COMPLETE 事实）；
- [x] 十项强制 Decision 全部 `RESOLVED`（2026-09-23 批次 ①②③，见 [`references/m11-decision-closure-v1.md`](references/m11-decision-closure-v1.md)）；
- [x] Baseline/3K workload、来源、许可、parser、chunk、质量和检索阈值冻结（见 [`references/m11-baseline-3k-freeze-v1.md`](references/m11-baseline-3k-freeze-v1.md)；3K/10K 的 Recall 绝对值与事实准确率百分数仍须在每个 Gate **开跑前**写入该 Gate 报告，本冻结物只钉住必须有独立真实 query/gold 与必须有阈值）；
- [x] 数据目录、manifest、报告和隐私边界可验证（仓库根 `data/README.md` + `.gitignore`：Git 只收 `data/README.md` 与未来 `data/manifests/` 小文件；raw/normalized/candidates/approved 大文件不入库）；
- [x] [`docs/PLAN.md`](../PLAN.md)、本计划和机器门禁一致（十项 Decision `RESOLVED`、三项前置 `SATISFIED`、准入 `ADMITTED`、交付 `IN_PROGRESS`；准备物已索引）；
- [x] 负责人完成阶段 admission（2026-09-23，见 §8.1）与生产开工（同日「允许执行」，见 §8.2）；v1.1 纳入 A1/A2/A3。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-23 |
| approval_reference | User instruction: 「允许进入下一个阶段」（原文与解读见 §8.1）；v1.1 见 §8.2 |
| plan_revision | v1.1 |
| decision_set_version | m11-decision-set-v1 |

### 8.1 准入批准（2026-09-23）

| 批准字段 | 值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-23 |
| approval_reference | User instruction: 「允许进入下一个阶段」——回应「准备物已经够用来单独考虑准入…若要准入，需要你显式批准，并分开写：1. admission 2. implementation_start」。按本仓既有惯例逐字引用原话并说明解读：批准 M11 **准入**（治理范围 `m11-data-scaling-v1`），**不**批准生产开工 |
| plan_revision | v1.0 |
| decision_set_version | m11-decision-set-v1 |
| approval_scope | `m11-data-scaling-v1` |
| implementation_start | 当时 `NOT_AUTHORIZED`；同日稍后「允许执行」改为 `AUTHORIZED`（见 §8.2） |

**当时批准范围 `m11-data-scaling-v1`（v1.0）**：十项决策对应的 `included`；`excluded` 含下载、提额、`tests/M11/`、
M8 后端、M12、Network 晋升、SE dump。v1.1 把 A1/A2/A3 移入 `included`，见 §8.2。

**本批准做什么**：把 `admission_status` 改为 `ADMITTED`。当时 `delivery_status` 保持 `NOT_STARTED`。

**本批准当时不做什么**：不授权开工、不下载、不提额、不创建 `tests/M11/`、不批准被排除项、不产生
`completion_approval`、不写 `admission_history`（`BLOCKED → ADMITTED` 由批准字段承担）。

### 8.2 开工授权与 v1.1 范围扩张（2026-09-23）

| 字段 | 值 |
| --- | --- |
| implementation_start | `AUTHORIZED` |
| authorized_by | justtodo123 |
| authorized_at | 2026-09-23 |
| authorization_reference | User instruction: 「允许执行」——回应「要真正开工，需要单独一句开工授权」 |
| plan_revision | v1.1 |
| scope_expansion | User instruction: 「A1 A2 A3 全部批准」——创建 `tests/M11/`、chunk 硬顶 4000、P0 白名单下载入库 |

**v1.1 `included`**（13 项）：原十项决策 + `m11.create-tests-m11` + `m11.raise-chunk-limits` +
`m11.download-or-ingest-corpus`。

**v1.1 `excluded`**（6 项）：`m8.backend-selection`、`m12.cloud-deployment`、`network.document-promotion`、
`m11.stackexchange-dump`、`m11.raise-limits-beyond-3k`、`m11.linux-kernel-docs-at-3k`。

**本扩张做什么**：允许创建 `tests/M11/`；允许把 `SA_SOURCE_MAX_CHUNKS_TOTAL` 硬顶从 2000 收到 **4000**
（默认仍 1200，3K 通过环境变量显式提额，不得超过 4000；该变更已在 A2 落地并由 `tests/M11/test_scale_limits.py` 保护）；允许对冻结白名单的 P0 来源做官方入口下载与入库
（MIT OCW 6.004、OpenDSA 固定 commit、RFC 批准清单、IANA registries、项目默认包与原创评测）。

**本扩张不做什么**：不把硬顶拉到 10K；不把 Linux docs 算进 3K；不晋升 Network；不导入 SE dump；不选 M8 后端；
不部署 M12；不产生 `completion_approval`。v1.1 是范围扩张、决策值未改，不触发 §4 撤销。

### 8.3 3K Gate 阈值批准（2026-09-24）

owner 选择「保守门槛（推荐）」，批准 `data/manifests/m11-3k-gate-protocol-v1.json` 的 3K 绝对阈值：

- 人工抽样事实准确率 ≥ 0.95；
- Recall@3 ≥ 0.85，Recall@5 ≥ 0.90，MRR ≥ 0.75；
- no-hit 错误数 ≤ 3，hard-negative 错误数 ≤ 3。

该批准只冻结阈值，不指定人工抽样数量或 reviewer，不填充尚为空的 gold document IDs，不授权正式 3K Gate 运行，
也不授权 publication。协议因此由 `AWAITING_OWNER_THRESHOLD_APPROVAL` 转为
`THRESHOLDS_APPROVED_REVIEW_PENDING`，`formal_run_authorized` 与 `publication_authorized` 继续为 `false`。

同日完成 P0 官方来源初审：MIT OCW 仅允许逐 asset 核验后的 MIT-hosted PDF/static resources，排除视频、播客、
外链与 all-rights-reserved 内容；OpenDSA 固定 commit 的根 MIT notice 不自动覆盖 tree 中的 third-party 目录；RFC 仅允许
显式 allowlist，按 TLP 5 保留 notices 且不修改 RFC 正文；IANA 2021 联合声明将 `iana.org/protocols` 或
`ietf.org/assignments` 直接链接的 Protocol Registry 数据按 CC0 1.0 开放，但明确排除链接的 RFC 和其他页面内容。
全部外部来源仍为 `review_required`：许可范围明确不等于 asset 已批准，仍须逐 asset 完成 revision、robots 与内容核验。

### 8.4 Candidate pipeline 批准（2026-09-24）

owner 明确指令「批准以下范围进入 candidate pipeline」，范围仅限已冻结清单：MIT OCW 20 个 PDF、RFC
9110/9293/1034、IANA Service Name and Transport Protocol Port Number Registry 的 CSV/XML/TXT，以及 OpenDSA pinned
commit 下 `RST/en/` 的 861 个路径。该批准允许 candidate metadata / normalized candidate / license-provenance review，
不把任何 asset 晋升为 approved，不授权正式 3K Gate 运行或 publication，也不扩张 Network、Linux docs、SE dump、
M8 后端或 10K 限额。机器记录见 `data/manifests/sources/m11-p0-candidate-assets-v1.json` 与
`data/manifests/sources/m11-opendsa-rst-paths-v1.json`；26 项 digest 汇总见
`data/manifests/m11-p0-digest-evidence-v1.json`。

编排实现见 `platform/app/m11_candidate_pipeline.py`。它复用 M7 `parse_document` / `normalize_document`，只写
candidate/rejected 证据；公开入口仅接受冻结 evidence。MIT OCW、RFC、IANA 用 26 项 SHA-256 manifest，OpenDSA 用 pinned
path manifest 的 Git blob SHA-1 验证本地 bytes，再以 SHA-256 形成 normalized content fingerprint；无 evidence 绑定的
规范化仅保留为私有 hermetic helper。source/asset identifier 在任何 artifact 写入前校验，非法值仅以短哈希进入 rejected。
已知限制（不阻塞 candidate 授权，但阻塞 TXT 正文规范化）：当前 Python 3.13.3 上 TXT
parser 按精确 `cpython-textio==3.11.9` 合同为 `SOURCE_PARSER_UNAVAILABLE`。因此 RFC TXT、IANA CSV/XML/TXT 与
OpenDSA RST 在本机 fail-closed；Markdown 仍可规范化。M11 **不**为凑数放宽该合同。PDF 分支跟随 `pypdf` 是否按
M7 pin 可用。candidate 结果只返回相对 artifact 名，不含宿主绝对路径。

## 9. 撤销与后续边界

来源许可、parser/chunk/embedding profile、质量/检索 workload、控制面权威或删除语义实质变化时，阶段 admission 必须
`REVOKED` 并重新批准。M12 只能消费经过批准的 M11 published snapshot，不能用云端容量掩盖本地数据质量问题。

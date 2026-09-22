# M7 用户 Source 生命周期与千级检索准备计划

> 当前状态：仅基础设施范围 `ADMITTED / COMPLETE`；独立生产开工门禁为 `AUTHORIZED`；Search/QA overlay 与 generation-bound vector 已落地；M7-1/M7-2/M7-3/M7-4/M7-5/M7-6 的实现、冻结证据和 correctness 收口均已复验；justtodo123 于 2026-09-06 另行明确批准 `M7 COMPLETE`
> 暂停边界：`data-expansion-runbook.md` 仅为未来参考，不构成生产开工、语料批准或下游阶段批准
> 前置：`M7-M6A-SOURCE-CONTRACT` 与 `M7-PROTECTED-BASELINE` 均为 `SATISFIED`；准入、开工与独立完成批准记录见 §4
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)
> 本文件冻结强制决策与批准范围；当前已实现并冻结 M7-1 Source Registry、文件级 manifest、五格式 parser matrix、normalized document、source-local FULL/INCREMENTAL/delete/isolation 合同，并已落地 source-local FTS5/vector/offline fail-closed 与 Search/QA overlay。冻结 1k/3k BGE 门槛已通过；M7-6 已完成真实五格式 parser/normalized-document 及 provenance/recovery/delete E2E 技术验收。技术证据本身不等于 human M7 COMPLETE 批准；本阶段完成状态来自 2026-09-06 的独立人工批准，且不扩展原 `m7-infrastructure-only-v1` scope。Agent 不得自行批准准入、阶段退出或 M8 开工。

## 1. 范围与非目标

M7 在 M6a 稳定 Source identity 和静态快照边界后，规划用户源持久化注册、同步、删除、多源隔离以及
1k–3k chunk 可复现检索。它不迁移到 LanceDB/Qdrant，不实现目标规划或自主 Runner，也不把外部原始
PDF/PPT 复制进仓库。

本计划已取得仅限基础设施的阶段准入，且独立生产开工门禁已授权。当前已实现 Source Registry、manifest/parser、normalized document、source-local FULL 与受限 incremental sync 局部合同：独立
SQLite 控制面、版本化 lifecycle schema、用户源身份、CAS 状态机、五类 lifecycle record 持久化、owner-only 读取、
schema fail-closed 与定量并发/回滚/重启/privacy workload；并已形成文件级 manifest、五格式冻结 parser matrix、normalized document
和 source-local FULL candidate/原子发布的局部合同。该 lifecycle repository 是新的控制面边界，不是 M6a 已冻结的 published
 descriptor `SourceRegistryRepository`。FULL/INCREMENTAL/delete/isolation/FTS5/offline 已接入 Search/QA 的受信任内部 principal overlay；M6b preview 与正式学习会话仍不含用户源。完整 provenance 晋升链或独立 Source API 尚未创建。只读盘点
`tools/source_inventory.py` 仍是 collect-only 调查，不能替代下列强制决策、语料批准或 M7 退出。

## 2. 前置证据与继承不变量

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M7-M6A-SOURCE-CONTRACT` | `SATISFIED` | M6a identity、额外源校验、generation 切换、缓存失效和路径隐私的退出证据；映射见 §2.1 |
| `M7-PROTECTED-BASELINE` | `SATISFIED` | `m7-admission-20260829-02` disposable reference、继承保护回归和默认 90 题复验；详见 §3.5.1 与 [`docs/baselines.md`](../baselines.md) |

M7 完整继承统一准入政策中的 M0–M5 不变量：正式状态转换继续由 `StudySessionService` 掌握；旧 SQLite
session 可恢复；默认 OS/DS/CO 90 题和 Network 显式扩展边界不变；默认离线路径不依赖外部模型或新服务；
对外结果、日志和 trace 不泄露宿主机绝对路径。

`M7-M6A-SOURCE-CONTRACT=SATISFIED` 只表示 M6a 退出证据已登记；本阶段的 `ADMITTED` 另由 §4 的人工批准产生，
且不等于完整 M7 退出；生产实施另需独立开工授权。

### 2.1 M6a Source 契约映射

下列 M6a 已 `RESOLVED` 的契约是 M7 的继承约束，不是 M7 专属决策的选定值。M7 不得重新定义 identity
公式、公开出处形态或路径隐私；也不得把 M6a 静态 extra 配置宣称为用户源注册。

| M6a Decision | M7 必须继承的约束 | 退出证据 |
| --- | --- | --- |
| `M6A-IDENTITY` | `source_id + logical_uri` 派生 `document_id`；`logical_uri` 为 NFC POSIX 相对路径；`fingerprint` / `revision` / `generation` 职责分离；禁止宿主绝对路径 | [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md) §0.4、`tests/M6a/test_protocols.py`、`tests/M6a/test_default_pack_adapter.py` |
| `M6A-SOURCE-POLICY` | 默认可检索仅 `human_markdown` / `web_reviewed` 且 `ingest_status=approved`；`web_candidate` 与 `ai_draft` 永不检索；缺字段兼容只适用于可信默认 pack | [`runtime-contracts.md`](../standards/runtime-contracts.md) §1、`tests/M6_crawler/test_ingest_gate.py`、`tests/regression/test_runtime_contracts.py` |
| `M6A-EXTRA-SOURCES` | M6a extra 仅启动期静态配置；公开出处为 `extra://{source_id}/{logical_uri}`；`user-` 前缀保留给未来用户源，不得被 extra 占用 | [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md) §0.4、`tests/M6a/test_extra_sources_config.py` |
| `M6A-CACHE-KEYS` | 构建缓存键含 identity/chunk schema 与 **parser version**，不含 generation；结果缓存按已发布 generation 与 scope 隔离 | [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md) §0.4、`tests/M6a/test_cache_lifecycle.py` |
| `M6A-SNAPSHOT-SWITCH` | staging → 校验 → 原子发布；读 last-good；M6a 只做完整快照，不做增量 tombstone（留给 `M7-DELETE-SEMANTICS`） | [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md) §0.4、`tests/M6a/test_snapshot_publication.py` |
| 路径隐私 | API、模型/工具结果、日志、trace、manifest 不回显宿主绝对路径 | `tests/regression/test_path_privacy.py`、`tests/M6a/test_default_pack_adapter.py` |

M6a 的 `M6A-SOURCE-LIMITS` 与默认 90 题保护基线**不能**替代 `M7-PROTECTED-BASELINE` 或 `M7-SCALE-LIMITS`。

## 3. 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M7-LIFECYCLE-SCHEMA` | `RESOLVED` | `sa.source.lifecycle.v1`；五类版本化记录、CAS 状态转换、单一权威写入者及 fail-closed 升级政策，见 §3.1 |
| `M7-SYNC-SEMANTICS` | `RESOLVED` | `sa.source.sync.v1`；完整候选快照、受限增量、单 active run、确定性重试/取消/恢复及原子 generation 发布，见 §3.2 |
| `M7-DELETE-SEMANTICS` | `RESOLVED` | `sa.source.delete.v1`；不可逆逻辑删除、读时 tombstone、全检索面清除、30 天最小审计保留及可验证 hard-delete receipt，见 §3.3 |
| `M7-ISOLATION` | `RESOLVED` | `sa.source.isolation.v1`；服务端 principal、owner-only 用户源、强制查询前过滤、授权集缓存隔离及无存在性泄露拒绝，见 §3.4 |
| `M7-FTS5-TOKENIZER` | `RESOLVED` | `sa.source.fts5-tokenizer.v1`；jieba `0.42.1` search-mode 预分词、NFC/空白规范化、版本化 token stream、不可用时 M7 fail-closed，见 §3.7 |
| `M7-SCALE-LIMITS` | `RESOLVED` | `sa.source.scale-limits.v1`；单源 100 documents/1,000 chunks/256 MiB、单 principal 与单进程 3,000 chunks 聚合硬上限、预检拒绝与 last-good 保留，见 §3.8 |
| `M7-BENCHMARK` | `RESOLVED` | 固定 1k/3k chunk fixture、中文查询与标注、Recall@1/3/5、冷/暖 p50/p95、索引大小、同步/重建时间、硬件、样本数和门槛，见 §3.5 |
| `M7-OFFLINE-FALLBACK` | `RESOLVED` | `sa.source.offline-fallback.v1`；无可选 tokenizer/vector fallback；依赖、索引或用户源不可验证时 M7 用户源 fail-closed，不启动查询、不发布候选，见 §3.12 |
| `M7-SOURCE-MANIFEST` | `RESOLVED` | `sa.source.manifest.v1`；文件级 canonical manifest、来源类型/格式分离、完整内容 fingerprint、Source revision 聚合与 fail-closed 校验，见 §3.6 |
| `M7-PARSER-MATRIX` | `RESOLVED` | `sa.source.parser-matrix.v1`；`md`/`txt`/`pdf`/`pptx`/`docx` 唯一解析器与精确版本、格式级上限、整 revision 失败及离线 fail-closed，见 §3.9 |
| `M7-NORMALIZED-DOCUMENT` | `RESOLVED` | `sa.source.normalized-document.v1`；统一 unit 字段、稳定 `chunk_key`、受管 normalized-document 缓存、fingerprint/parser/chunk-schema 失效与 staging 清理已冻结，删除完成条件遵循 §3.3，见 §3.10 |
| `M7-PROVENANCE` | `RESOLVED` | `sa.source.provenance.v1`；公开出处、QA 可见字段、内容晋升及更新/删除传播规则，见 §3.11 |

每项只有按统一政策记录明确选定值、默认与覆盖、校验/失败行为、兼容/隐私影响、适用阈值、证据、责任人和
日期后才能标为 `RESOLVED`。候选项、`TBD`、无 workload 的数字或“实施时决定”都保持 `OPEN`。
`M7-LIFECYCLE-SCHEMA`、`M7-SYNC-SEMANTICS`、`M7-DELETE-SEMANTICS`、`M7-ISOLATION`、
`M7-FTS5-TOKENIZER`、`M7-SCALE-LIMITS`、`M7-BENCHMARK`、`M7-OFFLINE-FALLBACK`、`M7-SOURCE-MANIFEST`、
`M7-PARSER-MATRIX`、`M7-NORMALIZED-DOCUMENT` 与 `M7-PROVENANCE` 已依次闭合；M7 专属保护基线也已登记为
`SATISFIED`。§4 的准入与完成批准都只覆盖基础设施；阶段当前为 `ADMITTED / COMPLETE`，独立生产开工门禁为 `AUTHORIZED`。完成状态来自独立人工批准，不是由测试或 benchmark 自动产生；当前实现包括 Source Registry、manifest/parser、normalized document、source-local FULL/INCREMENTAL/delete/isolation 与 FTS5/vector/offline fail-closed 合同。

### 3.1 `M7-LIFECYCLE-SCHEMA`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-LIFECYCLE-SCHEMA`，schema family 固定为 `sa.source.lifecycle.v1`。
- 控制面使用五类版本化记录：`SourceRecord`、`SourceRevision`、`SyncRun`、`LifecycleError`、`AuditEvent`；
  每条记录都含 `schema_version=1`、UTC 时间戳和不可变主键。
- 新用户源的 `source_id` 固定为 `user-` 加 canonical lowercase UUIDv7；创建后不可修改或复用。M6a 已存在的
  `knowledge-pack` 与静态 extra source ID 不迁移、不重命名，也不写入 M7 用户源控制面。
- `SourceRecord` 的生命周期状态固定为 `REGISTERED`、`SYNCING`、`READY`、`DEGRADED`、`DISABLED`、
  `DELETE_PENDING`、`DELETED`。允许转换固定为：`REGISTERED -> SYNCING|DISABLED|DELETE_PENDING`，
  `SYNCING -> READY|DEGRADED|DISABLED|DELETE_PENDING`，`READY|DEGRADED -> SYNCING|DISABLED|DELETE_PENDING`，
  `DISABLED -> SYNCING|DELETE_PENDING`，`DELETE_PENDING -> DELETED`；`DELETED` 为终态。本决策只冻结状态和转换，
  不提前决定同步重试、取消、删除保留期、硬删除或恢复政策，这些仍分别属于 `M7-SYNC-SEMANTICS` 与
  `M7-DELETE-SEMANTICS`。
- `SourceRevision` 为不可变记录，主键为 `source_id + revision_no`；`revision_no` 从 1 严格递增，记录 source
  fingerprint、manifest digest、parser/chunk schema versions 和构建结果。只有 `READY` 转换可原子更新
  `published_revision_no` 与 `published_generation`；失败 revision 不覆盖 last-good 指针。
- `SyncRun` 使用 canonical lowercase UUIDv7 `run_id`，记录 source、起止时间、请求策略、输入 revision、候选
  generation、稳定结果码和聚合计数；具体 full/incremental 行为仍由 `M7-SYNC-SEMANTICS` 冻结。
- `LifecycleError` 只保存稳定错误码、所属实体 ID、阶段、首次/末次时间和计数；`AuditEvent` 为 append-only，记录
  actor type、动作、前后状态、实体 ID、correlation ID 和结果，不保存正文、凭据或宿主路径。
- 唯一权威写入者固定为 `SourceLifecycleService`。API、同步执行器、parser、索引器和删除执行器不得直接写控制表，
  只能向该服务提交命令；repository 只在该服务事务边界内执行持久化。正式学习状态仍由
  `StudySessionService` 独占，M7 不获得学习状态写权限。

**默认、覆盖与适用范围**

- v1 默认启用乐观并发：所有 Source 状态命令必须携带 `expected_version`，成功后整数 `record_version` 加 1；
  不提供关闭 CAS、修改状态集合、修改 ID 公式或绕过权威写入者的环境变量/API 覆盖。
- schema 仅适用于未来获准后的 M7 用户源控制面；不接管默认 pack、M6a static extras、crawler candidate、
  学习 session、review history 或 M6b preview trace。
- `requested_sync_strategy` 的 schema 值域可表达 `FULL` / `INCREMENTAL`，但在 `M7-SYNC-SEMANTICS` 解决并获准前，
  生产入口不得接受或执行任何策略；字段可表达能力不构成同步政策批准。

**校验、拒绝与失败行为**

- 创建时拒绝非 canonical `source_id`、重复 ID、未知字段、缺失必填字段、非 UTC 时间、非法状态或非法枚举；
  外部请求不得自选 `revision_no`、`record_version`、审计 ID 或已发布 generation。
- 版本不匹配返回 `SOURCE_VERSION_CONFLICT`，非法转换返回 `SOURCE_INVALID_TRANSITION`，重复 ID 返回
  `SOURCE_ID_CONFLICT`，未知 schema 返回 `SOURCE_SCHEMA_UNSUPPORTED`；均不得发生部分写入。
- 一个命令必须在单个 SQLite 事务内原子写入实体变更和对应 `AuditEvent`；任一步失败则完整回滚。
- 启动读取 `schema_version > 1` 时 M7 用户源能力 fail closed 且不得自动降级写入；M0–M6 路径继续启动。
  v1 到未来版本只能通过显式、可回滚迁移执行，禁止启动时破坏性自动迁移；迁移失败保留原库和 last-good 数据。

**兼容、安全、隐私与保留**

- M0–M5 API/OpenAPI、默认 90 题、Network 显式扩展、旧 SQLite session 恢复和默认离线路径保持不变；
  `StudySessionService` 的领域写入权威不变。
- 生命周期记录和审计不得包含 prompt、文档正文、chunk 正文、密钥或 Windows/POSIX/UNC 宿主绝对路径。
  私有源定位信息若后续确需持久化，必须由 `M7-ISOLATION` / `M7-SOURCE-MANIFEST` 另行冻结，不得借本 schema
  写入公开响应、日志或审计。
- `AuditEvent` 在 Source 进入 `DELETED` 后默认保留 30 天，届时可按 source ID 成批清理；仅保留事件元数据。
  原文、解析缓存、索引和 tombstone 的保留/硬删除时点仍由 `M7-DELETE-SEMANTICS` 决定。

**可量化验收与 workload**

- 获准实施后必须以隔离 SQLite 运行 schema/transition contract workload：覆盖上列全部 16 条允许边及每个状态到
  所有未允许目标的拒绝矩阵；非法转换接受数必须为 0，合法转换原子提交率必须为 100%。
- 对同一 `expected_version` 发起 100 组双写竞争，每组必须恰好 1 次成功、1 次
  `SOURCE_VERSION_CONFLICT`，不得出现丢失更新或重复 revision number。
- 对 source/revision/run/error/audit 各至少 20 个 golden records 做写入、重启读取和 canonical JSON round-trip；
  100% 保持 ID、版本、状态、last-good 指针和审计关联。
- 使用正文、secret、Windows/POSIX/UNC 路径 canary 覆盖成功、拒绝、错误和迁移失败路径；API、日志和审计泄露数为 0。
- 故障注入覆盖实体写后、审计写前和提交前三个点；每点 20 次，部分提交数必须为 0。未知新版本 fixture 必须使
  M7 fail closed，同时既有 M0–M6 启动与只读路径保持可用。

**可追溯证据、责任人和日期**

- 选定依据：本节；统一完成标准：[`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3；继承身份、
  last-good、路径隐私与状态权威：本文 §2.1、[`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md)、
  `tests/M6a/test_protocols.py`、`tests/M6a/test_snapshot_publication.py`、`tests/regression/test_path_privacy.py`。
- M7-1 schema/transaction 阻断 workload 已实现并通过：16 条合法边及拒绝矩阵、100 组双写 CAS、五类记录各 20 条
  重启与 canonical JSON round-trip、三个故障点各 20 次零部分提交、完整 schema manifest 损坏 fixture 和 privacy canary。
  后续 sync/delete propagation/retrieval/benchmark workload 仍未实现，不得据此声明 M7 exit。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.2 `M7-SYNC-SEMANTICS`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-SYNC-SEMANTICS`，同步协议固定为 `sa.source.sync.v1`，并复用
  `sa.source.lifecycle.v1` 的 `SourceRecord`、`SourceRevision`、`SyncRun`、CAS 和状态转换。
- `FULL` 固定为默认策略：枚举当次可接纳文件，生成完整候选 manifest、normalized documents、chunks、BM25/vector
  索引和结果缓存命名空间；任何一项校验未通过都不发布。首次同步、无 `READY` revision、last-good 元数据不完整、
  manifest/parser/chunk schema 版本变化或增量前置校验失败时，只允许 `FULL`。
- `INCREMENTAL` 只允许 Source 已有可验证的 `READY` revision，且 manifest、parser/chunk schema 版本与 last-good
  一致时使用。它按稳定 `logical_uri` 和 fingerprint 计算 added/modified/removed 集，只重建 added/modified 文档，
  但必须生成并校验一个**完整候选检索视图**；removed 文档只从候选视图排除，物理清理、tombstone、保留和硬删除
  仍由 `M7-DELETE-SEMANTICS` 决定，本决策不提前闭合。
- 每个 Source 同时最多一个 active `SyncRun`；M7 v1 每进程全局最多一个 active run。并发请求不得排队或合并，
  固定返回 `SOURCE_SYNC_BUSY`。状态写入继续只经 `SourceLifecycleService`，同步执行器不得直接写控制表或发布指针。
- 每次同步必须携带 canonical lowercase UUIDv7 `request_id`、`source_id`、`expected_version` 和策略。同一
  `source_id + request_id` 重放返回既有 `SyncRun`，不得创建 revision、重复执行已完成阶段或再次发布 generation；
  同一 request ID 携带不同参数固定返回 `SOURCE_SYNC_REQUEST_CONFLICT`。

**重试、取消与中断恢复**

- 自动重试仅适用于 staging 区内、尚未发布的瞬时 I/O 错误和 SQLite busy/locked；每个阶段最多重试 2 次，固定等待
  1 秒、2 秒。校验、格式不支持、权限、超限、schema/parser 错配、数据损坏、CAS 冲突和取消均不重试。
  重试不得改写 last-good，不得重放已提交的 generation 发布事务。
- 取消是显式 `request_cancel(request_id, expected_version)`；执行器必须在枚举、单文件解析、切块、各索引构建和发布前
  检查取消标记。发布事务开始前收到取消，run 终止为 `CANCELLED`，丢弃候选 generation 并保留 last-good；发布事务
  一旦开始则不可中断，事务结果是唯一事实，成功不得伪报取消。
- `SyncRun` 每完成一个 staging 阶段，原子记录阶段名、输入 digest、候选 generation 和 checkpoint digest；运行中
  每 5 秒更新 lease heartbeat，30 秒未更新即视为 stale。进程重启后，只有 input digest、source `record_version`、
  manifest/parser/chunk schema versions 和 checkpoint digest 全部匹配时，才从最后完整阶段恢复；否则将旧 run 标为
  `INTERRUPTED_INPUT_CHANGED` 并以新的 request ID 执行 `FULL`。恢复永不从半个文件、半个索引或发布事务中间继续。

**generation 可见性与 last-good**

- staging revision、candidate generation 和 checkpoint 对 Search/QA/M6b preview 均不可见。发布前必须验证候选 manifest
  完整性、document/chunk 身份唯一性、BM25/vector 文档集合一致性、source/revision/generation 绑定和路径隐私。
- 发布固定为单个原子事务：CAS 校验 Source `expected_version`，写不可变 `SourceRevision`，将
  `published_revision_no` 与 `published_generation` 同时指向候选视图，并把 Source 转为 `READY`。查询在请求开始时
  固定一个 published generation，单个请求不得混读新旧 generation。
- 失败、取消、进程中断、重试耗尽或发布 CAS 冲突均不得改变 published 指针；已有 last-good 继续可读，Source 转为
  `DEGRADED`。首次同步失败且没有 last-good 时 Source 保持不可检索并转为 `DEGRADED`。旧 generation 的物理保留和
  清理仍由 `M7-DELETE-SEMANTICS` 决定。

**默认、覆盖、校验与失败行为**

- 默认策略为 `FULL`；调用方只有在上述前置条件满足时可显式请求 `INCREMENTAL`。不提供关闭单-run 互斥、扩大进程
  并发、放宽重试次数/等待、跳过候选校验、允许 staging 查询或非原子发布的环境变量/API 覆盖。
- 拒绝未知策略、未知字段、非 canonical request/source ID、缺失 `expected_version`、非法 Source 状态、未来 schema
  版本和不匹配 checkpoint。稳定错误码包括 `SOURCE_SYNC_BUSY`、`SOURCE_SYNC_REQUEST_CONFLICT`、
  `SOURCE_SYNC_PRECONDITION_FAILED`、`SOURCE_SYNC_VALIDATION_FAILED`、`SOURCE_SYNC_RETRY_EXHAUSTED`、
  `SOURCE_SYNC_CANCELLED`、`SOURCE_SYNC_INTERRUPTED` 和继承的 `SOURCE_VERSION_CONFLICT`；失败不得部分发布。
- 具体 source/document/chunk/bytes 上限遵循已闭合的 §3.8 `M7-SCALE-LIMITS`；本同步政策自身不另行定义或放宽限额，
  也不赋予生产同步入口。

**兼容、安全、隐私与保留**

- 本协议仅适用于未来获准的 M7 用户源；不自动同步或迁移默认 pack、M6a static extras、crawler candidates，
  不修改 M0–M5 API/OpenAPI、默认 90 题、Network 显式扩展、旧 session 恢复或 `StudySessionService` 写入权威。
- 同步状态、错误、checkpoint 和审计只保存逻辑 ID、digest、版本、计数和稳定错误码；不得保存文档/chunk 正文、
  凭据或宿主绝对路径。staging 内容、旧 generation 和解析缓存的保留与清理遵循已闭合的 §3.3
  `M7-DELETE-SEMANTICS` 和 §3.10 `M7-NORMALIZED-DOCUMENT`；本同步决策不另行改写这些政策。

**可量化验收与 workload**

- 获准实施后以可生成的 100-document/1,000-chunk 离线 fixture 各运行 20 次首次 `FULL`、无变化 `INCREMENTAL`、
  10% added/modified/removed `INCREMENTAL`；每次发布后的 manifest、BM25 与 vector document-ID 集合必须 100% 一致，
  staging 泄露和单请求混读 generation 次数必须为 0。性能阈值仍属于 `M7-BENCHMARK`，本 workload 不预设 p95。
- 对同一 Source 发起 100 组双并发请求，每组必须恰好 1 个 active run、1 个 `SOURCE_SYNC_BUSY`；对同 request ID
  重放 100 次，新增 run/revision/generation 数必须均为 0。
- 对每个可重试错误点注入 20 次“失败两次后成功”和 20 次“连续失败三次”；调用次数必须分别为 3，后者全部返回
  `SOURCE_SYNC_RETRY_EXHAUSTED`。对每个不可重试错误点注入 20 次，调用次数必须为 1。
- 在每个 checkpoint、发布前和发布事务内各执行 20 次取消/进程终止。发布前路径必须 100% 保持 last-good；发布事务内
  只允许完整旧视图或完整新视图。满足恢复前置的 run 必须从最后完整 checkpoint 恢复，不满足者必须 100% 转为新的
  `FULL`，不得恢复半成品。
- 使用正文、secret、Windows/POSIX/UNC 路径 canary 覆盖成功、失败、重试、取消和恢复；API、日志、审计及公开错误
  泄露数必须为 0。既有 M0–M6 默认启动、Search/QA/session 和 preview 隔离契约不得回退。

**可追溯证据、责任人和日期**

- 选定依据：本节与已闭合的 §3.1；统一完成标准：[`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3；
  继承 snapshot 原子发布、generation 隔离、缓存失效和路径隐私：本文 §2.1、
  [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md)、`tests/M6a/test_cache_lifecycle.py`、
  `tests/M6a/test_snapshot_publication.py`、`tests/regression/test_path_privacy.py`。
- 本轮决策记录的是冻结的可执行政策和既有 M6a 契约；不声称 M7 同步生产实现或性能证据已经存在。当前已新增的
  `tests/M7` 当前 143 项覆盖 lifecycle、manifest、parser、normalized document、source-local FULL 与受限 incremental sync 局部合同；后续 100-document/1k-3k workload 仍是 M7 阶段的阻断验收要求。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.3 `M7-DELETE-SEMANTICS`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-DELETE-SEMANTICS`，删除协议固定为 `sa.source.delete.v1`，并复用
  `sa.source.lifecycle.v1` 的 SourceRecord、CAS、AuditEvent 与已冻结的
  `DELETE_PENDING -> DELETED` 终态转换；本决策不增加任何反向状态边。
- 删除分为两步：权威删除命令先以 `expected_version` 将 Source 原子转换为 `DELETE_PENDING` 并写入
  deletion intent；随后删除执行器按 intent 幂等清理。进入 `DELETE_PENDING` 后，Source 对 Search/QA
  和所有 preview 均立即不可见，读时以 tombstone 拦截旧 generation、revision、document 和 chunk。
- tombstone 以 `source_id + logical_uri`（文件）及其派生 document/chunk identity 为粒度，记录 schema version、
  deletion intent、generation 上界、原因码和创建时间，不保存正文、凭据或宿主路径。它覆盖 full/incremental
  产生的所有已发布和 staging 对象；同一 identity 的旧缓存命中也必须被拒绝。
- 删除传播顺序固定为：先发布控制面 tombstone/read barrier，再使 BM25 文档集合、vector 文档集合和
  result-cache namespace 不可读，最后物理清理解析产物、chunks、BM25/vector entries、result cache、旧
  generation 与 tombstone 到期数据。任何顺序上的失败都保持 fail-closed，不得重新暴露对象。
- 最小审计保留期固定为 30 个自然日（UTC）；`AuditEvent`、deletion intent、hard-delete receipt 和
  必要 tombstone 元数据在此期间只允许审计角色读取，且只保留逻辑 ID、digest、计数、时间、结果码和
  actor/correlation 元数据。正文、密钥、绝对路径和用户查询不得进入删除记录。
- 30 天后执行 hard delete：删除原文引用的受管缓存、normalized-document/解析缓存、chunks、BM25/vector
  entries、result-cache namespace、旧 generation、tombstone 及可删除的删除元数据；不可删除的合规审计
  仅保留去正文、去路径的最小事件元数据。hard-delete receipt 是不可变记录，包含 source_id、范围摘要、
  对象计数、各存储确认 digest、开始/结束时间、策略版本和结果码，不包含内容。

**默认、覆盖与适用范围**

- 默认删除策略为逻辑删除立即生效、审计及删除证明保留至少 30 天、到期后 hard delete；删除命令和
  retention sweep 均只适用于未来获准的 M7 用户源，不接管默认 pack、M6a static extras、crawler candidates、
  study session 或 review history。
- 不提供关闭 tombstone、绕过读 barrier、缩短 30 天审计保留、跳过任一检索面清理或手工重用 source_id
  的 API/环境变量覆盖。实现可增加更长保留期，但不得短于 30 天，并须在策略版本中明确记录。
- “恢复”仅指删除执行器在进程中断、锁冲突或暂时 I/O 失败后依据未完成 intent 继续完成同一删除并重新生成
  receipt；不提供 undelete，不把 `DELETE_PENDING` 反向转换为其他状态，也不恢复已 hard-deleted 内容。

**校验、拒绝与失败行为**

- 删除请求必须携带 canonical source_id、request_id、expected_version、actor、reason 和协议版本；拒绝
  非 canonical ID、未知字段、缺失字段、非 UTC 时间、未来 schema、已 `DELETED` source 或版本冲突，分别返回
  `SOURCE_DELETE_INVALID_REQUEST`、`SOURCE_SCHEMA_UNSUPPORTED`、`SOURCE_ALREADY_DELETED` 或
  `SOURCE_VERSION_CONFLICT`，不得部分写入。
- 同一 source_id + request_id 必须幂等返回原 deletion intent/receipt；相同 request_id 携带不同参数返回
  `SOURCE_DELETE_REQUEST_CONFLICT`。删除执行器不得直接写 Source 状态，所有状态和审计变更仍经
  `SourceLifecycleService` 的单一事务边界。
- tombstone/read barrier 写入失败、任一索引/cache 清理未确认、receipt 校验失败或 hard delete 部分失败时，
  返回稳定错误码 `SOURCE_DELETE_FAILED` 或 `SOURCE_HARD_DELETE_INCOMPLETE`，保持 `DELETE_PENDING` 和
  不可检索；不得回滚为 READY/DEGRADED，不得宣称删除完成。可重试的暂时 I/O/SQLite busy 仅按 sync v1
  的有界重试规则执行，其他错误不重试。

**兼容、安全、隐私与保留**

- M0–M5 API/OpenAPI、旧 SQLite session 恢复、默认 OS/DS/CO 90 题、Network 显式扩展和
  `StudySessionService` 写入权威保持不变；M6b preview 继续隔离且不能绕过 tombstone。
- 删除后任何 Search/QA/preview 结果、BM25/vector 召回、result-cache 命中和 provenance 引用必须不可见；
  对外错误仅返回逻辑 source/document/chunk ID 与稳定错误码，不返回宿主路径、正文、secret 或原始 provider 数据。
- 删除审计与 receipt 必须支持按 source_id 追溯而不重建内容；hard delete 完成后不可通过应用接口恢复，
  备份/日志若受独立保留政策约束也不得重新进入检索或公开响应。

**可量化验收与 workload**

- 获准实施后，对可生成的 100-document/1,000-chunk fixture 执行 20 次删除；每次从请求提交到
  `DELETE_PENDING` 的 CAS/intent/audit 原子成功率为 100%，从 barrier 生效起 Search/QA/preview、BM25、
  vector 和 result-cache 的删除对象召回率必须为 0。
- 对 100 组相同 request_id 重放，新增 intent、状态转换、generation 或 receipt 数必须为 0；对 100 组
  相同 expected_version 并发删除，每组必须恰好 1 次成功、1 次 `SOURCE_VERSION_CONFLICT`。
- 在 tombstone 写入后、各索引/cache 清理中、receipt 写入前和提交前各注入 20 次进程终止/故障；每次
  重启后必须保持不可检索，未完成项 100% 可由同一 intent 恢复，且不得出现 READY/DEGRADED 反向转换。
- 30 天保留边界用 UTC 时钟 fixture 验证 20 次：未满 30 天的正文关联对象和审计元数据不得 hard-delete；
  到期后 20 次 sweep 必须生成可校验 receipt，声明范围内所有存储确认完成率 100%，receipt 内容泄露数为 0。
- 使用正文、secret、Windows/POSIX/UNC 路径和已缓存结果 canary 覆盖成功、失败、重试、恢复和 hard-delete
  路径；API、日志、trace、审计、receipt 与缓存键泄露数必须为 0，默认 M0–M6 路径不得回归。

**可追溯证据、责任人和日期**

- 选定依据：本节与已闭合的 §3.1/§3.2；统一完成标准：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
  §3；状态终态、CAS、单一写入者、原子发布、generation/cache 边界和路径隐私继承本文 §2.1、§3.1、§3.2，
  [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md)、`tests/M6a/test_cache_lifecycle.py`、
  `tests/M6a/test_snapshot_publication.py`、`tests/regression/test_path_privacy.py`。
- 本轮证据是冻结的可执行删除政策与既有 M6a 继承契约；当前 `tests/M7` 覆盖 lifecycle registry、manifest、parser matrix、normalized document、source-local FULL 与受限 incremental sync 局部合同（143 项）；不等于完整 M7 生产实现，不声称
  M7 删除生产实现或 hard-delete 性能证据已经存在；上述 workload 是获准实施后的阻断验收要求。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.4 `M7-ISOLATION`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-ISOLATION`，授权协议固定为 `sa.source.isolation.v1`。每个未来 M7 用户源必须绑定一个
  不可变 `owner_principal_id`；v1 不支持共享、公开、组、角色继承或跨 learner 授权，授权关系固定为 owner-only。
- `principal_id` 必须由服务端已认证上下文提供，调用方不得在 body、query、tool 参数或 Source metadata 中自报或覆盖。
  Source 创建、读取、同步、取消、删除、审计和检索均先由同一授权组件计算该 principal 的授权 source 集合。
- 默认 pack 与 M6a static extras 继续处于既有受信命名空间，不写入 M7 ownership 表；它们是否进入某请求仍由既有
  `DEFAULT_ONLY` / `DEFAULT_PLUS_EXTRAS` scope 决定。用户源只进入显式 `AUTHORIZED_USER_SOURCES` 集合，不得借用
  `knowledge-pack`、extra 或保留的 `user-` 以外 ID，也不得改变默认 pack 的可见性。
- 查询必须在 BM25、vector 和 result-cache lookup **之前**附加服务端生成的 principal/source allowlist；RRF、QA、
  M6b preview、出处组装和缓存回放只能消费已经过滤的候选。禁止先跨源召回再在响应层过滤。
- result cache key 固定包含 principal authorization-set digest、retrieval scope 和 published generation；授权集变化、
  Source 删除/tombstone 或 generation 切换必须使命中失效。BM25/vector 条目必须携带 source_id，缺失 source_id、
  未知 namespace 或无法验证 owner 的用户源条目一律 fail closed。

**默认、覆盖与适用范围**

- v1 默认 owner-only、deny-by-default、服务端强制过滤；不提供关闭授权检查、允许匿名用户源、放宽为共享源、从客户端
  接受 allowlist、跨 principal 合并缓存或查询后过滤的 API/环境变量覆盖。
- 本决策只冻结 M7 用户源的控制面和检索隔离，不新增认证机制，不定义 principal 如何登录，也不改变 M0–M6 既有
  endpoint 的认证状态。未来共享或组织模型必须新版本决策、迁移与重新批准，不能复用 v1 隐式开启。
- `StudySessionService` 继续独占正式学习状态转换与领域写入；M7 授权组件只能决定用户源是否可见，不能读取或修改
  另一 principal 的 session、mastery、review history，也不能把用户源内容扩散到 Quiz、Review Plan 或默认评测集。

**输入校验、拒绝与失败行为**

- 创建用户源必须有 canonical、非空的服务端 principal；拒绝客户端提供 `owner_principal_id`、非 canonical source ID、
  保留命名空间冲突、未知字段或未来协议版本，返回 `SOURCE_ISOLATION_INVALID_REQUEST`、`SOURCE_ID_CONFLICT` 或
  `SOURCE_SCHEMA_UNSUPPORTED`，且不得创建部分 Source/AuditEvent。
- 对未拥有、未知、已删除或不可见的用户 source_id，所有单源控制面和检索入口统一返回
  `SOURCE_NOT_FOUND`；响应状态、延迟分层、错误正文、日志和 trace 不区分“不存在”与“无权访问”，不得泄露 owner、
  Source 状态、标题、文件名、计数、generation 或路径。批量请求只处理授权交集，不回显被剔除 ID。
- principal 缺失或认证上下文不可验证时，用户源授权集为空并返回 `SOURCE_AUTH_REQUIRED`；授权存储不可用、过滤条件
  无法下推、条目缺 source_id、cache key 缺授权 digest 或授权快照在请求中途变化时返回
  `SOURCE_ISOLATION_UNAVAILABLE`，不得降级为全源查询、默认 owner 或响应后过滤。
- 请求开始时固定 principal、授权集 digest、retrieval scope 与各 Source published generation；请求中途 owner、状态、
  tombstone 或授权版本变化时，本次用户源结果必须丢弃并按新快照至多重试一次，仍冲突则 fail closed。

**兼容、安全、隐私与数据保留**

- M0–M5 API/OpenAPI、默认 OS/DS/CO 90 题、Network 显式扩展、旧 SQLite session 恢复、默认离线路径及
  `StudySessionService` 权威保持不变；M6b preview 继续只读，且仅能看到其服务端 principal 被授权的用户源。
- ownership/authorization 记录只保存 opaque principal ID、source ID、policy version、授权版本、UTC 时间与最小审计元数据；
  不保存 prompt、正文、chunk、凭据、登录标识或 Windows/POSIX/UNC 宿主绝对路径。日志、trace、metrics 和错误不得用
  source title、logical_uri 或 owner 标识作 label。
- 删除沿用 §3.3：`DELETE_PENDING` 后所有 principal 立即不可见，授权记录和授权集缓存同时失效；30 天最小审计期后
  随 hard delete 清理可删除的 ownership 元数据，只保留去内容、去路径且无法用于重新授权的最小 receipt/audit 证明。

**可量化验收与 workload**

- 获准实施后，用 10 个 principal、每人 10 个 source、每源 10 个 document（共 100 source/1,000 document）的可生成
  离线 fixture，执行每个 principal 对自有源与全部 90 个非自有源的 Search/QA/preview 访问矩阵；非自有 source、document、
  chunk、cache hit 和 provenance 泄露数必须为 0，自有授权查询成功率必须为 100%。性能阈值仍属于 `M7-BENCHMARK`。
- 对 BM25、vector、RRF、result cache、QA sources 和 M6b preview 六个边界各运行至少 100 个混合查询；服务端过滤前
  进入下游的未授权候选数必须为 0。移除 source_id、伪造 owner、客户端注入 allowlist 或复用另一 principal cache key
  各 100 次，成功越权数必须为 0。
- 对不存在与未授权 source 各执行 1,000 次同形请求，HTTP 状态、稳定错误码和响应 schema 必须 100% 相同；错误、日志、
  trace 与 metrics 的 owner/title/path canary 泄露数必须为 0。延迟不得作为安全承诺，但测试报告必须给出两组 p50/p95
  供人工检查，不得宣称常数时间。
- 在授权读取后、BM25/vector 查询前、RRF 前、cache lookup 前和响应组装前各注入 20 次授权变化、删除和存储故障；
  未授权结果返回数必须为 0，无法确认新快照时必须 100% 返回 `SOURCE_ISOLATION_UNAVAILABLE`。
- 既有默认 pack 的 Search/QA/session、90 题评测发现、旧 session 恢复和 M6b 阶段隔离契约必须保持通过；本 workload
  不替代独立的 M7 准入前保护基线或获准后的真实 benchmark。

**可追溯证据、责任人和日期**

- 选定依据：本节及已闭合的 §3.1–§3.3；统一完成标准：
  [`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3；默认/extra scope、逻辑身份、cache/generation、
  tombstone、路径隐私和状态权威继承本文 §2.1、[`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md)、
  `tests/M6a/test_extra_sources_retrieval.py`、`tests/M6a/test_cache_lifecycle.py`、
  `tests/M6a/test_snapshot_publication.py`、`tests/regression/test_path_privacy.py`。
- 本轮证据是冻结的可执行隔离政策与既有 M6a 继承契约，不声称认证实现、M7 生产隔离、`tests/M7` 或性能证据存在；
  上述 workload 是未来获准实施后的阻断验收要求。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.5 `M7-BENCHMARK`（`RESOLVED`）

**稳定 workload 与选定门槛**

- Decision ID 固定为 `M7-BENCHMARK`，报告协议固定为 `sa.source.benchmark.v1`；所有 fixture、query、标注、硬件和参数由 digest 标识，报告不得包含原文、secret 或宿主绝对路径。
- 提供可生成且不入 Git 的两个 workload：`1k-single` 为 100 documents / 1,000 chunks / 256 MiB 以内的单 Source；`3k-aggregate` 为 300 documents / 3,000 chunks / 768 MiB 以内的三 Source 聚合。两者均覆盖中文为主、简繁/全半角/英文/数字混合文本，并固定 query gold labels。
- 每个 workload 固定执行冷启动 FULL、warm no-op INCREMENTAL、10% added/modified/removed INCREMENTAL、冷重建和重启恢复；每种场景至少 20 次独立测量，前 5 次仅作 warm-up，不混入统计。硬件、Python、SQLite、jieba、embedding/backend、chunk/parser/tokenizer policy 版本必须写入报告。
- 正确性门槛固定为：Recall@1 ≥ 0.70、Recall@3 ≥ 0.85、Recall@5 ≥ 0.90；同一 fixture 的 manifest、normalized-document、chunk、BM25/FTS5 与 vector identity 集合一致率为 100%；增量与重建不得引入未标注结果或丢失已标注 gold。
- 性能与资源门槛固定为：`1k-single` 查询 p50 ≤ 150 ms、p95 ≤ 400 ms；`3k-aggregate` 查询 p50 ≤ 250 ms、p95 ≤ 750 ms；FULL 同步 p95 ≤ 30 s、冷重建 p95 ≤ 30 s、重启恢复 p95 ≤ 10 s；峰值 RSS ≤ 768 MiB（1k，2026-09-04 由 justtodo123 授权，自 BM25 校准的 512 MiB 修订为覆盖冻结 BGE/PyTorch 进程底盘）/ 1 GiB（3k），索引持久化大小 ≤ 2x accepted normalized text bytes。所有分位数按请求耗时统计，超时按失败计入。
- 失败/降级门槛固定为：任一 parser、manifest、tokenizer、index 或 generation 校验失败时不得发布候选；last-good 保持可读；离线启动与错误语义由 `M7-OFFLINE-FALLBACK` 另行冻结。本决策不把未运行的性能数字宣称为 M7 保护基线证据。

**默认、覆盖与证据**

- 默认报告同时产出 `1k-single` 与 `3k-aggregate`，不可用硬件或缺失依赖不得静默跳过；只允许在报告中标记 `UNAVAILABLE` 并阻断准入。不得以平均值替代 p50/p95，不得以单次成功替代 20 次样本。
- 阈值只适用于未来获准的 M7 用户源检索与生命周期 workload，不改变 M0–M6 默认 pack、90 题、M6b preview 或 runtime-contracts 的既有指标。
- 选定依据为本节冻结的 workload/门槛与 §2.1、§3.2、§3.3、§3.8 的容量和发布约束；决策责任人 `justtodo123`，决策日期 `2026-08-29`。本轮仅关闭“如何测”和“通过标准”，不声称已有 M7 实现、benchmark 报告或保护基线复验结果。

### 3.5.1 准入前保护基线 `sa.source.admission-baseline.v1`

本节定义准入前的当前态保护与容量参考，独立于 §3.5 的真实 M7 退出 benchmark。它只允许调用已经交付的 M6a
静态 extra、combined snapshot、snapshot publication 与 retrieval 接口，不实现或冒充 M7 lifecycle、manifest、parser、
normalized document、provenance、增量同步、删除或恢复能力。报告分类固定为 `disposable-reference`，不能用于宣称 M7 已实现、
已达到 3k 容量或已经满足退出条件。

**准入前 workload 与容量判定**

- `1k-single`：1 个 M6a 静态 extra，100 个纯合成 Markdown documents，严格生成 1,000 个 extra chunks；中文为主并覆盖
  简繁、全/半角、英文与数字，使用固定 query/gold labels。当前 M6a 配置的单 extra hard max 为 1,000 chunks、combined
  hard max 为 2,000 chunks；连同当前默认包后仍可在公开配置边界内运行，因此该 workload 必须真实执行。
- `3k-aggregate`：目标仍为 3 个 extra、300 documents、3,000 extra chunks。现行 M6a combined hard max 为 2,000 chunks，
  且 combined 计数包含默认包，因此该 workload 在不修改生产限制的前提下不可构造。准入报告必须把它标为
  `UNAVAILABLE_PRE_ADMISSION_CAPACITY_LIMIT`，并记录冻结 limit manifest/digest；不得提高 hard max、绕过
  `CombinedSnapshotBuilder`、拆成三个互不聚合的伪 workload，或写成 `PASS`。
- 该 3k 状态是 M7 要解决的已知容量差距，不是缺依赖、缺硬件或 reference harness 故障。它本身不阻断
  `M7-PROTECTED-BASELINE` 成为人工准入候选，但获准后的真实 `sa.source.benchmark.v1` 仍必须同时通过 1k/3k；在此之前
  不得关闭 M7、开始 M8 或宣称 3k 能力可用。

**测量、阈值与不适用场景**

- `1k-single` 前 5 次 warm-up 不计入统计，随后至少 20 次独立 measured。记录 Recall@1/3/5、查询 p50/p95、当前快照
  冷构建与从持久化 generation 重启加载的 p50/p95、峰值 RSS、持久化 snapshot bytes、accepted combined chunk-content
  bytes（默认包与 synthetic extra 的已接纳 chunk 正文之和）、accepted synthetic chunk-content bytes、CPU/墙钟成本和
  external service cost。
- 质量门槛为 Recall@1 ≥ 0.70、Recall@3 ≥ 0.85、Recall@5 ≥ 0.90；查询 p50 ≤ 150 ms、p95 ≤ 400 ms；峰值 RSS
  ≤ 512 MiB；持久化 snapshot bytes ≤ 2x accepted combined chunk-content bytes。分子是 persisted combined generation 与
  pointers，故分母必须覆盖同一 combined view；synthetic-only bytes 单独报告，不得拿范围较窄的分母制造不可比比率。构建/重启数据仅刻画 M6a 当前态，不套用未来 M7
  FULL/recovery SLA，也不得替代 §3.5 的同步、冷重建和重启恢复门槛。
- M6a 没有 M7 lifecycle，所以 warm no-op incremental、10% added/modified/removed incremental、delete propagation 和
  checkpoint/recovery 必须标为 `NOT_APPLICABLE_PRE_ADMISSION`，不得伪造为 `PASS`。
- 任何可执行 1k workload、继承保护回归、默认 90 题质量、隐私或兼容门禁失败，或者 harness/测量依赖不可用，都保持
  `M7-PROTECTED-BASELINE=OPEN`。只有这些项目通过，且 3k 不可用被精确绑定到现行冻结容量而非实验缺陷时，才可把保护
  基线登记为 `SATISFIED` 候选；该证据本身不产生准入、生产开工或退出结论。

**证据与实验边界**

- fixture/query/gold、harness、环境、limit manifest、原始报告和 canonical result 均使用 SHA-256 digest；报告使用唯一
  evidence ID 和 exclusive-create，不包含合成正文、secret、prompt 或宿主绝对路径。
- 一次性 harness 和 fixture 仅位于仓库外系统临时目录，使用固定离线 BM25，不扫描 `D:\\111_Others_Subjects`，不访问
  网络或 LLM，不修改生产模块、依赖、schema、API、runtime flag、CI 或 `tests/M7/`；证据固化后删除临时目录。
- 当时的计划执行批准只授权上述可丢弃 reference experiment，不是 M7 阶段准入批准。后续 §4 的人工批准才使
  M7 基础设施范围变为 `ADMITTED`；该准入当时仍不等于生产开工授权。

### 3.6 `M7-SOURCE-MANIFEST`（`RESOLVED`）

文件级 manifest 描述用户源里**每个枚举到的文件**及其接纳结果和可移植身份，不是 Unity Library 之类工程文件的全盘清单，
也不是 parser、normalized-document 或 provenance schema。

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-SOURCE-MANIFEST`，文件级协议固定为 `sa.source.manifest.v1`。每个 manifest 是一个不可变的
  Source-revision 输入记录，含 `schema_name`、`schema_version=1`、`source_id`、`manifest_digest`、规范化 UTC
  `created_at`、`entries` 和聚合计数；entry 必须含 `logical_uri`、`document_id`、`source_type`、`format`、`acceptance`
  （`accepted` / `rejected` / `unsupported`）、`size_bytes`、`content_fingerprint` 和 `fingerprint_algorithm`。
  `reject_code` 仅在非 accepted entry 必填；解析器版本、normalized-document ID、chunk 和 provenance 字段不属于本 schema。
- `logical_uri` 是 NFC 保留大小写的源内 POSIX 相对路径；`document_id` 继续按 M6a 的
  `sha256(source_id + logical_uri)` v1 派生，另以 `NFC(casefold(logical_uri))` 检测便携式冲突。entry 按该冲突键排序，
  manifest digest 为 canonical UTF-8 JSON（固定字段顺序、无空白、数值规范化）摘要，算法固定 `SHA-256`。
- `content_fingerprint` 固定为文件完整内容的 SHA-256：二进制文件摘要原始 bytes；文本文件先以 UTF-8 解码并按既定
  Unicode NFC、换行 `\\n`、连续空白折叠和首尾空白规则规范化，再摘要规范化 UTF-8 bytes。它是文件内容身份，不能由 mtime、
  文件名、大小、采样或宿主路径替代；M6a Markdown fingerprint 继续沿用其既有语义，M7 不回写或重解释默认 pack。
- `source_type` 是来源/治理策略，v1 用户注册源固定为 `user_registered`；`format` 是文件编码/容器格式，固定由受支持
  的 magic/解析探测结果确定（如 `md`、`txt`、`pdf`、`pptx`、`docx`），二者必须独立校验，扩展名不能冒充任一字段。
  `source_type`、`format`、`acceptance` 和 `reject_code` 的完整允许值由对应策略/Parser Matrix 交叉校验，但本决策不选择
  parser 或统一解析产物。
- Source `revision_no` 从 1 严格递增；本次 revision 的输入是完整 manifest digest，只有 manifest、后续解析/切块和索引
  全部通过后，按 §3.2 原子发布同时绑定 published revision/generation。任一 entry 的 fingerprint、acceptance、URI、
  source_type 或 format 改变都会生成新 Source revision；未变化文件可复用其 document identity/构建缓存，但不能复用旧
  revision 指针或只发布不完整的 manifest。revision 不由单文件号拼接，也不等同于 generation。

**默认、覆盖与适用范围**

- 默认仅枚举 Source 根目录内、可读且符合 M7 接纳策略的文件；`accepted` entry 进入候选检索视图，`rejected` 与
  `unsupported` entry 只保留逻辑 URI、格式（若可探测）、大小、fingerprint（若可安全计算）和稳定 `reject_code`，
  不进入 document/chunk/BM25/vector 集合。排除计数进入 manifest aggregate counts，不把调查工具的任意分类字段升级为生产字段。
- 仅允许启动前收紧允许的 source/format 策略或资源上限；不允许请求级改写 fingerprint、manifest digest、document ID、
  revision、acceptance、计数或路径根，也不允许把 collect-only JSON 直接注册为 manifest。该 schema 只适用于未来获准的
  M7 用户源，不接管默认 pack、M6a static extras、crawler candidates、study session 或 review history。

**校验、拒绝与失败行为**

- 拒绝绝对/UNC/盘符/越界/控制字符 URI、非法 UTF-8、重复或 case-fold 冲突 logical URI、无法读取的文件、探测结果与
  声明 format 不一致、未知 source_type/format/acceptance、未知字段、缺失必填字段、非 canonical JSON、digest 不匹配、
  非正整数 size 或未来 schema version；不得以排序优先、自动改名、采样摘要或静默跳过消歧。
- 单文件不可读、fingerprint 不可计算、超出已冻结容量或格式不支持时，生成带稳定拒绝码的完整候选 manifest，但该 entry
  不得进入检索；若 manifest 本身不完整、聚合计数不可信、任何 accepted entry 无法校验，整次 Source revision 拒绝，
  不发布 generation，保留 last-good 并按 §3.2 转为 `DEGRADED`。首次同步失败且无 last-good 时 Source 保持不可检索。
- 稳定错误码至少包括 `SOURCE_MANIFEST_SCHEMA_UNSUPPORTED`、`SOURCE_MANIFEST_INVALID`、`SOURCE_MANIFEST_IDENTITY_CONFLICT`、
  `SOURCE_MANIFEST_FINGERPRINT_MISMATCH` 和 `SOURCE_MANIFEST_UNREADABLE`；错误、日志和审计只记录 opaque ID、稳定码、
  版本、计数和 digest，不记录正文、凭据、文件名之外的宿主定位信息或绝对路径。

**兼容、安全、隐私、保留与验收**

- M0–M5 API/OpenAPI、默认 OS/DS/CO 90 题、Network 显式扩展、旧 SQLite session、默认离线路径和
  `StudySessionService` 写入权威保持不变；M6a/M6b 不读取或改写该未来用户源 manifest。manifest 不保存原文、解析正文、
  chunk 正文、凭据或宿主绝对路径；删除和保留沿用 §3.3，tombstone 生效后 manifest entry 不可用于检索或出处。
- 获准实施后，使用可生成的 1,000-entry fixture 运行 20 次冷构建、20 次重启恢复和 20 次 10% added/modified/removed
  增量；同一输入的 canonical manifest bytes/digest、entry document ID、fingerprint、接受/拒绝计数一致率必须为 100%，
  任一失败候选的 generation 发布数必须为 0。对 URI 冲突、格式伪造、fingerprint/digest 篡改、非法 UTF-8、绝对路径和
  超限各注入 100 次，整源越过校验或公开泄露正文/secret/宿主路径的次数必须为 0；这些是获准后的验收要求，不是已有
  M7 实现证据。

**可追溯证据、责任人和日期**

- 选定依据：本节及已闭合的 §3.1–§3.5、§3.7、§3.8、§3.12；统一完成标准：[`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3；
  identity、fingerprint/revision/generation 分离、路径隐私和快照发布继承本文 §2.1、[`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md)、
  [`runtime-contracts.md`](../standards/runtime-contracts.md)、`tests/M6a/test_protocols.py`、`tests/M6a/test_snapshot_publication.py`、
  `tests/regression/test_path_privacy.py`。`tools/source_inventory.py` 仅作为 collect-only 调查输入，不是生产 schema 或通过证据。
- 本轮证据包括 manifest 的局部实现与既有 M6a 继承契约，不声称完整 M7 manifest、增量同步或检索生产实现已经存在；`tests/M7` 当前 143 项覆盖 manifest、parser、normalized document、source-local FULL 与受限 incremental sync 等局部合同，
  它也不替代已独立登记的准入前保护基线，parser、normalized-document 和 provenance 的完整生产闭环仍分别受 §3.9–§3.11 约束。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.7 `M7-FTS5-TOKENIZER`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-FTS5-TOKENIZER`，tokenizer 协议固定为 `sa.source.fts5-tokenizer.v1`；中文 FTS5 使用
  `jieba==0.42.1` 的 search-mode 预分词，将 token 以单个空格连接后写入 FTS5 `unicode61` 默认 tokenizer，
  不使用 `porter`、`trigram` 或未锁定版本的系统分词器。
- 输入规范化固定为 Unicode NFC、换行归一为 `\\n`、连续空白折叠为一个空格并去除首尾空白；token stream 使用
  jieba search-mode 输出，空 token 丢弃，token 原文保留大小写/数字语义但比较时由 unicode61 的默认规则处理。
  `tokenizer_version`、规范化版本和 FTS schema version 必须进入 build input digest 与索引元数据。
- 默认 Markdown pack 不改变现有 `sa.chunk.markdown-h2.v1` 切块或其检索边界；该 tokenizer 只适用于未来获准的 M7
  用户源 FTS5 索引，不能改变默认 pack、M6a static extras 或 M6b preview 的既有索引行为。

**默认、覆盖与适用范围**

- 默认启用上述固定 tokenizer 与规范化；不提供切换分词器、放宽版本、跳过规范化、运行时热替换词典或改用客户端
  分词结果的 API/环境变量覆盖。词典如需更新必须递增 tokenizer policy version、重建索引并重新完成兼容评估。
- M7 用户源的 BM25/FTS5 建索引和查询必须使用同一版本化 tokenization pipeline；vector、RRF、QA 与 cache 只消费
  已按 source/generation/authorization 过滤的结果。该决策不提前闭合 `M7-SCALE-LIMITS`、`M7-BENCHMARK` 或
  `M7-OFFLINE-FALLBACK` 的总体阈值和系统级降级策略。

**输入校验、拒绝与失败行为**

- 拒绝未知 tokenizer、未知规范化版本、非法 UTF-8、无法规范化的输入、缺失 tokenizer metadata、混用 tokenizer 版本
  或 FTS schema digest 不匹配，返回稳定错误码 `SOURCE_TOKENIZER_UNSUPPORTED` 或 `SOURCE_TOKENIZER_MISMATCH`；
  不发布候选 generation，不让部分 token stream 进入检索。
- 启动或查询发现 `jieba` 不可导入、版本不是 `0.42.1`、字典加载失败、FTS5 tokenizer metadata 缺失或索引由其他
  tokenizer 构建时，M7 用户源能力 fail closed，返回 `SOURCE_TOKENIZER_UNAVAILABLE`；不得静默退回 unicode61、
  单字切分、英文 whitespace 或 vector-only。离线 fallback 的完整启动/修复策略留给 `M7-OFFLINE-FALLBACK`。
- FTS5 查询字符串必须经过相同规范化与 tokenization；查询解析异常、token 为空或包含不允许的控制字符时返回稳定
  `SOURCE_TOKENIZER_INVALID_QUERY`，不得拼接原始查询形成可注入的 MATCH 表达式。原始查询不得写日志或错误正文。

**兼容、安全、隐私与数据保留**

- M0–M5 API/OpenAPI、默认 OS/DS/CO 90 题、Network 显式扩展、旧 SQLite session 恢复、默认离线路径和
  `StudySessionService` 写入权威保持不变；M6a/M6b 现有 BM25 行为不迁移、不重建、不因 M7 tokenizer 改变。
- tokenizer 元数据只保存版本、schema、digest、计数和时间，不保存原文、查询正文、凭据、principal、宿主绝对路径
  或可识别用户信息；审计、日志、trace 与公开错误不得泄露这些内容。tokenized text 属于派生索引数据，删除传播遵循
  `M7-DELETE-SEMANTICS`，tombstone 生效后立即不可查询，保留与 hard delete 不由本决策重新定义。

**可量化验收与 workload**

- 获准实施后，使用可生成的中英文混合 fixture（至少 1,000 documents、每文至少 5 条中文术语与 5 条中文自然语言
  句子）执行 20 次冷构建与 20 次重启恢复；固定同输入的 token stream、tokenizer/normalization metadata 和
  FTS document set 的 byte-for-byte 一致率必须为 100%。
- 对 1,000 条包含简繁、全半角、组合音标、emoji、数字、英文和连续空白的 query canary，规范化输出必须 100% 可复现；
  控制字符、非法 UTF-8、空 query 和恶意 MATCH 语法各 100 次必须全部被稳定拒绝，原始 query 泄露数为 0。
- 对 tokenizer 版本、规范化版本、FTS schema digest 各注入 100 次不匹配，候选 generation 发布数必须为 0，稳定错误码
  必须分别为 `SOURCE_TOKENIZER_MISMATCH`；`jieba` 缺失/错误版本/词典失败各注入 100 次，必须全部返回
  `SOURCE_TOKENIZER_UNAVAILABLE` 且不启动 M7 用户源检索。
- 对同一 fixture 由两个独立进程各构建 100 次，token stream digest 和 FTS document-ID 集合一致率必须为 100%；对同一
  query 重放 100 次，结果排序输入必须一致，不把性能阈值或 Recall 阈值提前写入本决策。
- 使用正文、secret、Windows/POSIX/UNC 路径和原始 query canary 覆盖成功、失败、重建与删除路径；API、日志、trace、
  审计和索引元数据泄露数必须为 0，既有 M0–M6 默认启动/检索/会话/preview 契约不得回归。

**可追溯证据、责任人和日期**

- 选定依据：本节及已闭合的 §3.1–§3.4；统一完成标准：
  [`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3；现有 BM25、切块、向量和路径隐私边界继承
  [`runtime-contracts.md`](../standards/runtime-contracts.md) §1–§2、本文 §2.1、
  `tests/M6a/test_cache_lifecycle.py`、`tests/M6a/test_snapshot_publication.py`、
  `tests/regression/test_path_privacy.py`。
- 本轮证据是冻结的 tokenizer 设计政策与既有兼容契约；当前 `tests/M7` 覆盖 lifecycle registry、manifest、parser matrix、normalized document、source-local FULL 与受限 incremental sync 局部合同（143 项）；不等于完整 M7 生产实现，不声称
  `jieba`、M7 FTS5 生产实现、fallback 或性能/Recall 证据已经存在；上述 workload 是未来获准实施后的阻断验收要求。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.8 `M7-SCALE-LIMITS`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-SCALE-LIMITS`，限制协议固定为 `sa.source.scale-limits.v1`。v1 单个用户 Source 的硬上限为
  100 个 accepted documents、1,000 个 published chunks、256 MiB accepted raw bytes；单文件 raw bytes 上限为
  32 MiB。计数使用 manifest 中经接纳且将进入候选 generation 的文件，不把 unsupported/rejected 文件算作 document，
  但它们必须进入拒绝计数和审计。
- 单 principal 可注册最多 10 个未进入 `DELETED` 的用户 Source，但任一 published/候选可检索集合聚合硬上限为
  300 documents、3,000 chunks、768 MiB accepted raw bytes；超过聚合上限的 Source 可保持 `REGISTERED` 或
  `DISABLED`，不得进入同步或查询授权集。单服务进程可加载的 M7 用户源 published view 同样最多 3,000 chunks；
  默认 pack 与 M6a static extras 不计入此 M7 配额，也不得因用户源配额被驱逐。
- 限制在枚举后、解析前先按文件数/raw bytes 做预检，在切块后、索引前再按 document/chunk 和 principal/process 聚合量
  做最终校验。完整同步、增量同步、重建、恢复和发布都使用同一快照计数；不得通过并发 run、staging generation、
  删除中的 Source、cache 或不同检索后端重复占用来绕过配额。
- supported workload 固定覆盖 1,000-chunk 单源和 3,000-chunk 聚合视图的完整同步、10% added/modified/removed
  增量、冷重建、进程重启恢复和查询正确性。具体时间、内存、磁盘、Recall@k 与 p50/p95 阈值仍只由
  已由 `M7-BENCHMARK` 冻结，本决策不借容量数字提前宣称性能达标。

**默认、允许覆盖与适用范围**

- 上述值均是 hard cap 和默认值；只允许部署配置在启动前**收紧**单文件、单 Source、单 principal 和进程上限，且必须
  保持层级单调（file <= source <= principal，process chunks <= principal chunks）并写入非敏感 policy digest。
  不允许 API、请求参数或运行时热更新放宽上限，也不允许把 `0`、负数或缺失值解释为无限制。
- 本决策只适用于未来获准的 M7 用户源控制面、staging 和 published view，不修改默认 pack、M6a static extras、
  crawler candidates、学习 session、review history、M6b preview 预算或 M0–M6 既有配置。
- parser-specific 页数、幻灯片数、解压比例或格式限制仍由 `M7-PARSER-MATRIX` 决定，但不得超过本节 raw bytes、
  document/chunk 和聚合 hard cap；manifest 的计数字段与 fingerprint 规则仍由 `M7-SOURCE-MANIFEST` 决定。

**输入校验、拒绝与失败行为**

- 配置必须是正整数 MiB/计数，拒绝未知字段、非整数、溢出、层级倒置、放宽冻结上限或未来 policy version，启动时返回
  `SOURCE_LIMIT_CONFIG_INVALID`，M7 用户源能力 fail closed；M0–M6 路径继续启动。
- 注册达到 10 个未删除 Source 时返回 `SOURCE_COUNT_LIMIT_EXCEEDED`。枚举预检超过单文件、单 Source 或 principal raw
  bytes/document 上限时返回 `SOURCE_SIZE_LIMIT_EXCEEDED`；切块后超过 Source/principal/process chunk 上限时返回
  `SOURCE_CHUNK_LIMIT_EXCEEDED`。公开错误只含 limit kind、配置上限和实际计数，不含文件名、正文或宿主路径。
- 首次同步超限时不发布候选 generation，Source 转为 `DEGRADED` 且不可检索；已有 last-good 的同步、增量或重建超限时
  丢弃完整候选、保持 last-good 与原 published generation 可读并转为 `DEGRADED`。不得截断文件、丢弃尾部 chunk、
  只发布部分索引或降级为 vector-only/BM25-only 来伪装成功。
- 进程聚合容量不足时固定返回 `SOURCE_PROCESS_CAPACITY_EXCEEDED`，不得驱逐默认 pack、另一 principal 的已发布 Source、
  绕过 §3.4 隔离或超额排队。删除中的 Source 在 tombstone 生效后不再进入查询集合，但在 hard-delete receipt 完成前，
  其物理 bytes 不得被错误记作已回收磁盘容量。

**兼容、安全、隐私与数据保留**

- M0–M5 API/OpenAPI、默认 OS/DS/CO 90 题、Network 显式扩展、旧 SQLite session 恢复、默认离线路径及
  `StudySessionService` 权威保持不变；M6a/M6b 现有 source/cache/preview 上限不被本决策重写。
- 配额计数、policy digest、拒绝和审计只保存 source/principal 的 opaque ID、计数、字节数、版本、时间和稳定错误码；
  不保存原文、chunk、query、凭据、文件名或 Windows/POSIX/UNC 宿主绝对路径。metrics 不使用 principal/source ID 作 label。
- staging 失败与超限候选按 §3.2 丢弃；删除和物理回收按 §3.3 执行。为审计保留的最小计数不进入可检索容量，
  也不能用于恢复已 hard-deleted 内容。

**可量化验收与 workload**

- 获准实施后，用可生成 fixture 对每个边界运行 20 次 `limit-1`、`limit`、`limit+1`：单文件 32 MiB、单 Source
  100 documents/1,000 chunks/256 MiB、单 principal 10 registered Sources 与 300 documents/3,000 chunks/768 MiB、
  单进程 3,000 user chunks；边界内接受率必须为 100%，`limit+1` 拒绝率必须为 100%，部分发布数为 0。
- 对 1,000-chunk 单源和 3,000-chunk 三源聚合 fixture，各运行 20 次首次 FULL、10% 增量、冷重建和重启恢复；
  每次 manifest、BM25、vector 的 document/chunk identity 集合必须 100% 一致，超限候选不得改变 last-good。
- 对 100 组并发注册/同步制造 principal 与 process 配额竞争；每组最终成功集合必须不超过冻结上限，超额请求全部返回
  对应稳定错误码，不得出现负计数、重复扣减、越权驱逐或超过 3,000 published user chunks 的瞬时可见窗口。
- 在预检后、解析后、切块后、各索引构建后和发布前各注入 20 次计数变化、进程终止和 SQLite busy；恢复后配额账本、
  candidate digest 与真实对象计数必须 100% 一致，无法证明一致时必须 fail closed 并保留 last-good。
- 使用文件名、正文、secret、principal 和 Windows/POSIX/UNC 路径 canary 覆盖接受、拒绝、重试和审计路径；API、日志、
  trace、metrics 与公开错误泄露数必须为 0。性能与 Recall 只记录原始测量，不作为本决策的通过证据。

**可追溯证据、责任人和日期**

- 选定依据：本节及已闭合的 §3.1–§3.5、§3.7；统一完成标准：
  [`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3；完整候选、last-good、单 active run、隔离、tokenizer、
  cache/generation 与路径隐私继承本文 §2.1、§3.2–§3.5、§3.7、
  [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md)、`tests/M6a/test_cache_lifecycle.py`、
  `tests/M6a/test_snapshot_publication.py`、`tests/regression/test_path_privacy.py`。
- 本轮证据是冻结的容量政策与可执行验收设计，不声称 M7 生产配额、`tests/M7`、parser/manifest 或 benchmark 证据已经
  存在；上述 workload 不替代获准后仍须运行的 `M7-BENCHMARK`，也不替代已独立登记为 `SATISFIED` 的准入前保护基线。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.9 `M7-PARSER-MATRIX`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-PARSER-MATRIX`，协议固定为 `sa.source.parser-matrix.v1`。解析器选择、版本和输出协议均是构建输入的一部分，精确 `parser_id@version` 必须进入 M6a `build_input_digest`；同一 format 不允许按环境或文件扩展名选择不同解析器。
- v1 受支持格式及唯一解析器固定为：`md` → `markdown-it-py==4.0.0`（`commonmark` preset，源码编码 UTF-8）；`txt` → Python 标准库 `textio`（CPython `3.11.9`，UTF-8，`newline=None`）；`pdf` → `pypdf==6.0.0`；`pptx` → `python-pptx==1.0.2`；`docx` → `python-docx==1.2.0`。`parser_id` 分别固定为 `markdown-it-py`、`cpython-textio`、`pypdf`、`python-pptx`、`python-docx`；版本解析必须精确匹配，未知或不匹配即不可用。
- Markdown 默认 pack 不经过本矩阵改写，继续使用既有 `sa.chunk.markdown-h2.v1` 和默认 `knowledge/` 路径；M7 用户源的 `md` 解析只定义输入解析器，不提前决定 normalized-document 或 provenance。
- 解析成功必须产生可供后续切块的文本候选；解析器不得写入 Git、默认 `knowledge/` 或对外暴露原文。PDF 页、PPTX 幻灯片和 DOCX 标题的统一字段、稳定 chunk key、缓存与出处字段留给 §3.10–§3.11。

**默认、允许覆盖与适用范围**

- 默认启用上述五种格式；不提供按请求、Source 或单文件替换解析器、放宽版本、绕过 magic/编码探测或切换为另一库的覆盖。部署只能在启动前禁用格式或收紧其资源上限，并写入非敏感 policy digest；禁用格式按 unsupported 处理。
- 格式由 magic/容器探测与声明交叉校验确定，扩展名不能单独决定 format。`md`/`txt` 需要有效 UTF-8；PDF、PPTX、DOCX 必须是可打开且结构完整的容器。格式探测结果、parser id/version 和接受结果写入 manifest 所允许的字段，不把解析正文写入 manifest。
- 每文件 raw bytes 必须遵守 `M7-SCALE-LIMITS` 的 32 MiB 单文件硬上限；解析器不得通过解压、展开或临时文件绕过该上限。PDF 最多 500 页、PPTX 最多 500 张幻灯片、DOCX 最多 500 个正文段落；这些格式级限制只收紧并不能放宽 §3.8 的 document/chunk/byte 聚合上限。

**输入校验、拒绝与失败行为**

- 枚举阶段先做路径、大小、magic、编码和容器结构校验；解析前后均检查实际计数与 `M7-SCALE-LIMITS`。声明格式与探测不一致、UTF-8 无法解码、容器损坏、解析器缺失/版本不匹配、页/幻灯片/段落超限或解析结果为空，均生成完整 manifest entry 并以稳定 reject code 拒绝该 entry，不进入 document/chunk/BM25/vector。
- 单文件解析失败或超限不得静默跳过并发布其余候选：若当前 Source 没有可验证 last-good，则拒绝整个 Source revision 并保持不可检索；已有 last-good 时丢弃完整 candidate、保留 last-good 并将 Source 置为 `DEGRADED`。不得截断、部分发布、降级为文件名/标题或把错误内容送入 QA。
- 不支持或被部署禁用的格式固定为 `unsupported`，计入 manifest/审计但不计入 accepted document/chunk 容量，也不进入任何检索索引。稳定错误码至少包括 `SOURCE_FORMAT_UNSUPPORTED`、`SOURCE_FORMAT_MISMATCH`、`SOURCE_PARSER_UNAVAILABLE`、`SOURCE_PARSE_FAILED`、`SOURCE_PARSE_LIMIT_EXCEEDED`；公开错误只含逻辑 URI、稳定错误码及可执行修复类别，不含正文、凭据或宿主路径。
- 离线环境中任一选定解析器不可用、版本不匹配或初始化失败时，严格对齐 `M7-OFFLINE-FALLBACK`：用户源 fail closed，不查询、不发布 candidate、不使用替代库或文件名 fallback；仅在显式本地修复完成全量校验并满足 §3.2 原子发布条件后恢复。

**兼容、安全、隐私与数据保留**

- M0–M5 API/OpenAPI、默认 OS/DS/CO 90 题、Network 显式扩展、旧 session 恢复、默认离线路径、M6a static extras 和 M6b preview 均不改变；默认 Markdown pack 的 parser/chunk 行为保持既有契约。
- staging 解析产物、临时解压内容和失败候选不进入 Git 或默认知识库；其清理、last-good、tombstone 和 hard-delete receipt 完全遵循已闭合的 §3.2–§3.3，不在本决策新增保留期。日志、trace、metrics、manifest 和错误不得记录正文、secret、query、principal、文件名或 Windows/POSIX/UNC 绝对路径。
- 解析器版本变化、策略变化或输入 fingerprint 变化必须使构建输入 digest 失效并触发完整候选重建；不得复用未经版本绑定的解析缓存。解析失败不创建学习状态、review-log、QA 引用，也不扩散到 Quiz、Review Plan 或默认评测。

**可量化验收与 workload**

- 获准实施后，对五种 supported format 各生成至少 100 个中文为主、含简繁/全半角/英文/数字/组合音标/emoji/连续空白的 fixture，重复冷构建、重启恢复和 10% added/modified/removed 增量各 20 次；同一输入的 parser digest、接受/拒绝结果和候选 identity 必须 100% 可复现，失败 candidate 发布数为 0。
- 对每种格式分别注入损坏容器、错误编码、magic/扩展名冲突、解析器缺失/错误版本、空内容与 `limit-1`/`limit`/`limit+1` 页数或结构单元各 20 次；错误码一致率 100%，不支持项索引进入数为 0，超限和解析失败的部分发布数为 0。
- 在 `1k-single` 与 `3k-aggregate` workload 中覆盖五种格式及混合格式；accepted document/chunk/raw-byte 计数必须与 manifest、BM25、vector 集合 100% 一致，任一超出 `M7-SCALE-LIMITS` 的候选不得改变 last-good。缺失离线依赖各注入 100 次，查询启动和候选发布数必须为 0。
- 使用文件名、正文、secret、principal 和 Windows/POSIX/UNC 路径 canary 覆盖接受、拒绝、重试、恢复和审计路径；API、日志、trace、metrics 与公开错误泄露数必须为 0。性能与 Recall 仅记录原始测量，不作为本决策的通过证据。

**可追溯证据、责任人和日期**

- 选定依据：本节及已闭合的 §3.1–§3.8、§3.12；统一完成标准：[`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3。identity、build-input digest、原子发布、last-good、容量、离线 fail-closed 和路径隐私继承本文 §2.1、§3.2–§3.8、§3.12 及既有 M6a 契约。
- 本轮证据是冻结的 parser 选择、版本、失败/超限/unsupported 政策与可执行验收 workload，不声称完整 M7 生产解析器部署、依赖环境、增量同步、
  `tests/M7` 全面验收或真实 benchmark 已经存在；当前 `tests/M7` 的 143 项仅覆盖本地局部合同；它不替代已独立登记的准入前保护基线。§3.10 normalized-document 与
  §3.11 provenance 已在后续决策中分别闭合，本 parser 决策不替代或改写其协议。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.10 `M7-NORMALIZED-DOCUMENT`（`RESOLVED`）

Normalized document 是解析后、切块前的统一表示；它把受支持格式映射为可复现的结构化文本单元，绝不把二进制
直接当作 chunk，也不决定 provenance（provenance 仍由 §3.11 单独决定）。协议固定为
`sa.source.normalized-document.v1`。

**稳定 ID 与选定政策**

- 每个 document 记录固定字段：`schema_name`、`schema_version=1`、`source_id`、`document_id`、`logical_uri`、
  `format`、`content_fingerprint`、`parser_id`、`parser_version`、`units` 和 `normalized_text_digest`。每个
  unit 固定字段：`unit_kind`（`document`/`section`/`page`/`slide`/`heading`）、`ordinal`（从 0 严格递增）、
  `heading_path`（NFC 字符串数组）、`title`（NFC 字符串或 null）、`text`（NFC UTF-8 文本）、`visible`（布尔值）。
  不保存宿主绝对路径、原始二进制、prompt、secret 或 provenance 字段。
- 统一映射固定为：`md`/`txt` 产生一个 `document` unit，并按既定默认策略继续切块；`pdf` 每页一个 `page` unit；
  `pptx` 每张可见幻灯片一个 `slide` unit，并把可见标题纳入 `heading_path`；`docx` 按标题边界产生 `section` unit，
  标题本身进入 `heading_path`，标题前内容进入首个 section。空页、空幻灯片和空 section 不产生 unit；隐藏幻灯片
  不产生 unit，但其存在只计入解析统计，不得进入检索。
- `chunk_key` 固定为 `sha256(document_id + "\\x00" + unit_kind + "\\x00" + str(ordinal) +
  "\\x00" + chunk_schema_version)` 的 lowercase hex，chunk schema 固定为 `sa.chunk.normalized-unit.v1`。
  同一 document、parser、fingerprint 和 schema 输入必须得到完全相同的 key；不得使用数组位置之外的易变显示文本、mtime
  或宿主路径作为身份。unit 文本按 NFC、LF 换行、连续空白折叠和首尾空白规则规范化后再计算 digest。

**默认、覆盖与适用范围**

- 默认仅适用于未来获准的 M7 用户源和 §3.9 已选 parser；默认 pack Markdown 继续使用 `sa.chunk.markdown-h2.v1`，
  不由本决策改写。部署只能在启动前禁用格式或收紧既有资源上限，不得请求级更换模型、字段、chunk 公式或规则。
- 解析缓存逻辑位置固定为受管 cache root 下的 `normalized-documents/v1/<source_id>/<document_id>/`，对外只暴露
  逻辑 cache key；每个 artifact 以 `content_fingerprint`、`parser_id@parser_version`、`chunk_schema_version` 和
  canonical normalized-document digest 命名。artifact 属于 staging revision，成功发布后由 generation 引用，
  不复制到 Git 或外部资料根。

**输入校验、拒绝与失败行为**

- 校验 schema/version、document identity、logical URI、format/parser 精确版本、fingerprint、单位 ordinal 唯一连续、
  heading/text 的 NFC 与 UTF-8、digest 和 §3.8 资源上限；拒绝未知字段、非法 unit kind、重复/缺失 ordinal、隐藏内容、
  未声明空值、digest 不匹配、过大文本和 parser 输出不可确定的结果。mtime 只能作提示，不能作为有效性依据。
- 任一 document 解析或 normalized-document 校验失败，整次 revision fail-closed：不生成 chunk、不更新 BM25/vector、
  不发布 generation，保留 last-good。缓存缺失或损坏不得回退到二进制、旧 fingerprint 或另一 parser；只允许按 §3.2
  显式 FULL 重建。

**失效与清理**

- fingerprint 变化使该 document 的解析 artifact、units、chunks 和下游 BM25/vector/result-cache namespace
  全部失效并重建；parser version 或 normalized/chunk schema 变化使该 source revision 的全部 normalized documents
  与 chunks 重建。generation 变化本身不使构建 artifact 失效，但 result cache 必须按 published generation 隔离。
- staging artifact 在成功原子发布后立即删除；失败、取消或中断的 staging 只能由同一 revision 的幂等清理任务删除，期间
  绝不查询。extra 移除或用户源进入 `DELETE_PENDING` 时停止新建和读取该源缓存；物理删除、retain-1、审计保留和
  hard-delete receipt 的完成条件严格遵循已闭合的 `M7-DELETE-SEMANTICS`，本决策不另设 tombstone 或保留期。

**兼容、安全、隐私与验收**

- 保持 M0–M6 API/OpenAPI、默认 pack、旧 session、`StudySessionService` 写入权威和默认离线能力不变；normalized
  artifact 不进入 QA `sources`，其公开出处字段留给 §3.11。日志、trace、错误和指标只记录 opaque IDs、版本 digest、
  计数、阶段和时间，不记录正文或路径。
- 获准实施后，以 `1k-single` 与 `3k-aggregate` fixture 各执行 20 次冷 FULL、warm no-op、10% 变更增量、重建和重启恢复；
  同输入 canonical bytes/digest、unit 集合和 chunk_key 集合一致率必须 100%，失败候选 generation 发布数为 0。对 fingerprint、
  parser/schema 变更、损坏 artifact、空/隐藏 unit、越界 URI 和上限各注入 100 次，错误码稳定率 100%、staging 查询和正文/路径
  泄露数为 0；这些是获准后的验收要求，不是现有 M7 实现证据。

**可追溯证据、责任人和日期**

- 选定依据：本节、§3.1–§3.3、§3.6、§3.8、§3.9、`stage-admission-gates.md` §3、M6a 的 parser-version/cache/staging
  继承契约及 `tests/M6a/test_cache_lifecycle.py`、`tests/M6a/test_snapshot_publication.py`；这些证据支持设计决策，
  不声称完整 M7 生产实现或真实 benchmark 已经存在；`tests/M7` 当前 143 项仅覆盖 lifecycle、manifest、parser、normalized document、source-local FULL 与受限 incremental sync 局部合同，也不替代已独立登记的准入前保护基线。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.11 `M7-PROVENANCE`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-PROVENANCE`，出处协议固定为 `sa.source.provenance.v1`。每个已发布可检索 chunk 必须有一条不可变的 `ProvenanceRecord`，把 `source_id + published_revision_no + published_generation + logical_uri + file_fingerprint + parser_id/parser_version + normalized_document_id + unit_id + chunk_id/chunk_schema` 串成完整链；缺一字段、链上 identity 不一致或无法验证当前 published generation 时，该 chunk 不得发布、召回或进入 QA `sources`。
- 公开出处 URI 固定为：默认 pack 继续使用 `knowledge/{logical_uri}`，M6a static extra 继续使用 `extra://{source_id}/{logical_uri}`，M7 用户源使用 `user://{source_id}/{logical_uri}`。`source_id` 必须是 §3.1 的 canonical `user-` UUIDv7，`logical_uri` 必须是 §2.1 的 NFC POSIX 相对路径；不得接受绝对路径、`..`、反斜杠、authority/query/fragment、百分号编码的路径分隔符或其他 scheme。公开 URI 只表示应用内逻辑出处，不承诺可直接读取宿主文件。
- 内容谱系固定为 `origin_kind=original | human_refined | ai_draft`。注册文件默认是 `original`；人工基于原文生成可检索精炼笔记时，必须创建新的 `logical_uri`、document/chunk identity 和 `ProvenanceRecord`，并以 `derived_from_document_ids` 指向一个或多个同 owner 的原文 document，`source_type` 固定为 `human_markdown` 或 `web_reviewed`，只有权威人工晋升写入者可将 `ingest_status` 从 `candidate` 改为 `approved`。AI 输出固定为 `ai_draft + candidate`，不得原地改写为 approved；人工采用时必须另建 `human_refined` 文档并记录 `derived_from_document_ids`，AI 草稿本身仍不可检索。`web_candidate` 同样永不检索，只有另建 `web_reviewed + human_refined + approved` 文档后才可进入候选 generation。

**默认、允许覆盖与适用范围**

- QA `sources` 对 M7 用户源只新增并固定暴露 `uri`、`title`、`source_type`、`origin_kind`、`document_id`、`chunk_id`、`revision`、`generation` 和可选 `location`；`location` 只允许 `{kind: page|slide|heading|line, start: 正整数, end: 大于等于 start 的正整数}`。不对外暴露 `logical_uri` 独立字段、file fingerprint、parser/version、normalized document/unit ID、owner/principal、ingest actor、审核备注、派生链、宿主路径、原文全文、chunk 全文、密钥或内部审计 ID。现有默认 pack/extra 的 `file` 字段与响应形态保持不变；M7 获准实施时只能为用户源采用上述字段，不得借本决策破坏 M0–M6 API/OpenAPI。
- 内部 `ProvenanceRecord` 可保存上述链路字段、`origin_kind`、`source_type`、`ingest_status`、`derived_from_document_ids`、审核 actor 的 opaque ID、审核 UTC 时间和策略版本；不得保存 secret、宿主绝对路径、QA query/prompt、原文全文或 chunk 全文。审计读取继续受 §3.4 owner-only/角色边界约束。
- v1 不提供改用 `extra://` 表示用户源、隐藏用户源 revision/generation、允许客户端自报 provenance、原地把 AI/web candidate 晋升为可检索内容、让未批准内容参与检索，或放宽公开字段的 API/环境变量覆盖。实现只能通过省略可选 `location` 或禁用整个用户源进一步收紧公开面。

**输入校验、拒绝与失败行为**

- provenance 只能由 `SourceLifecycleService` 在同步 staging 中根据已验证 manifest、parser、normalized document 和 chunk 结果生成；客户端、模型、crawler、文件 frontmatter 或检索结果不得直接写 `ProvenanceRecord`、`origin_kind`、`derived_from_document_ids` 或审核 actor。晋升请求必须携带 canonical source/document IDs、候选 fingerprint、目标新 `logical_uri`、`expected_version`、actor、request_id 和协议版本；缺字段、跨 owner 派生、目标 URI 冲突、候选已变化、非 candidate 输入、AI/web candidate 原地批准或派生环统一拒绝且不得部分写入。
- 稳定错误码固定为：记录/URI/字段无效 `SOURCE_PROVENANCE_INVALID`，链不完整或不一致 `SOURCE_PROVENANCE_BROKEN`，晋升冲突 `SOURCE_PROMOTION_CONFLICT`，不可晋升 `SOURCE_PROMOTION_DENIED`。公开错误只返回稳定 code 与不可逆向内容的 opaque IDs；未知、未授权或已删除 Source 仍统一按 §3.4 返回 `SOURCE_NOT_FOUND`，不得暴露存在性、文件名、出处 URI、正文或审核状态。
- 任一可检索 chunk 缺失或无法验证 provenance 时，整个候选 revision fail closed，不发布部分 generation；QA/result cache 命中若无法绑定当前 published provenance，也必须拒绝并按 §3.12 要求显式修复，不得回退到旧 URI、文件名猜测、normalized artifact 或正文片段作为出处。

**更新、删除传播与兼容/隐私**

- 文件 fingerprint 变化必须生成新 immutable revision 的 normalized document、chunks 与 provenance；旧 generation 在新 generation 原子发布前仍作为 last-good 完整可见，发布事务完成后旧 chunk/provenance 立即不可召回，且绑定旧 `revision/generation/chunk_id` 的 QA/result cache 全部失效。不得在一个响应中混用新正文与旧出处，或复用已改变内容的旧 chunk identity。
- 原文更新不会静默改写人工精炼文档；任何 `human_refined` 记录只要其 `derived_from_document_ids` 指向的原文 fingerprint 已不是当前值，就标记 `STALE_DERIVATION` 并从下一候选 generation 排除，直到人工基于当前原文创建新 revision 并重新批准。AI 草稿和 web candidate 无论新旧都不得进入任何检索 generation、QA `sources`、Quiz、Review Plan、默认评测或 preview 工具结果。
- Source 或 document 进入删除流程时，tombstone/read barrier 必须同时使其 provenance、派生关系、QA `sources` 组装和所有绑定 cache 不可读；引用该已删原文的 `human_refined` 文档同步变为 `STALE_DERIVATION` 并不可检索，不得借精炼副本绕过删除。解析缓存、normalized documents、chunks、BM25/vector/result cache、provenance 与派生边的物理清理、30 天最小审计保留、重试/幂等和 hard-delete receipt 完成条件完全遵循已闭合的 `M7-DELETE-SEMANTICS`；receipt 未确认全部声明存储前保持 `DELETE_PENDING`、fail closed，且不得声称 hard delete 完成。
- 保持 `StudySessionService` 写入权威、旧 session 恢复、默认 90 题、Network 显式扩展、M6b 隔离与默认离线路径不变。API、模型/工具结果、日志、trace、metrics、审计和 receipt 均不得暴露宿主路径、原文/chunk 全文或密钥；日志与指标只允许 policy/error code、opaque IDs、digest、计数、阶段和 UTC 时间。

**可量化验收与 workload**

- 获准实施后，在 `1k-single` 与 `3k-aggregate` fixture 上对每种支持格式各生成 original、human_refined、ai_draft、web_candidate 样本，运行 20 次 FULL、10% 更新增量和重启恢复；每个可召回 chunk 到公开 QA source 的链完整率必须为 100%，URI/schema/location 校验通过率 100%，断链/跨 generation/未批准内容发布数为 0，`ai_draft` 与 `web_candidate` 召回及 QA sources 出现数为 0。
- 对 original → human_refined、ai_draft → 新 human_refined、web_candidate → 新 web_reviewed 各执行 100 次合法晋升及 URI/fingerprint/version/owner/环路故障注入；合法请求必须 100% 创建新 logical URI 和 identity，原候选状态不变，非法请求部分写入数为 0。原文更新或删除后，依赖精炼文档的 `STALE_DERIVATION` 漏标和召回数必须为 0。
- 对更新发布前/事务内/发布后及删除 barrier、各 cache/index/provenance 清理、receipt 写入前各注入 20 次取消或进程终止；读视图只能是完整旧 generation 或完整新 generation，删除 barrier 后相关 Search/QA/preview/cache 命中数必须为 0，未完成 receipt 的 hard-delete 完成声明数为 0。
- 使用正文、secret、Windows/POSIX/UNC 路径、`..`、编码分隔符和跨 owner canary 覆盖成功/失败/日志/trace/审计/receipt；公开字段集合偏差、宿主路径/全文/密钥泄露和未授权存在性泄露数必须均为 0。这些是获准后的验收要求，不是现有测量证据。

**可追溯证据、责任人和日期**

- 选定依据：本节、§2.1、已闭合的 §3.1–§3.4、§3.6、§3.9、§3.10、§3.12，以及 [`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3；继承证据包括 [`runtime-contracts.md`](../standards/runtime-contracts.md) §1、[`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md)、`tests/M6a/test_protocols.py`、`tests/M6a/test_cache_lifecycle.py`、`tests/M6a/test_snapshot_publication.py` 与 `tests/regression/test_path_privacy.py`。
- 本轮证据是冻结的出处、晋升、更新/删除传播政策及可执行验收 workload，不声称 M7 生产 provenance、用户源 QA schema、`tests/M7` 或 benchmark 测量已经存在；这些设计证据不替代已登记的准入前保护基线 `SATISFIED`。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

### 3.12 `M7-OFFLINE-FALLBACK`（`RESOLVED`）

**稳定 ID 与选定政策**

- Decision ID 固定为 `M7-OFFLINE-FALLBACK`，离线失败协议固定为 `sa.source.offline-fallback.v1`。M7 用户源必须在无外部
  LLM、无网络和无新外部服务的本地环境运行，但“离线可运行”不等于允许不完整检索：已由 §3.7 冻结的 tokenizer、BM25/FTS5、
  vector、授权、generation 和索引元数据必须全部可用且可验证，才允许启动该用户源的查询。
- **不存在可选 tokenizer 或 vector fallback**：`jieba==0.42.1`、固定 tokenizer metadata 或 M7 选定的 vector 运行依赖缺失、
  版本不匹配、初始化失败时，不得退回 `unicode61` 原始分词、whitespace/单字切分、BM25-only、vector-only、线性临时候选、
  默认 pack 索引代替用户源索引，或跳过任一检索面。不得以“尽力而为”结果标记用户源可查询。
- FTS5/BM25、vector、result cache、manifest/generation 绑定或必要索引元数据发生损坏、缺失、校验失败或集合不一致时，该 M7
  用户源固定 fail closed：不得启动或继续查询，不得读取可能过期的 cache，不得发布、部分发布或恢复候选 generation。已有经完整
  校验的 last-good 只有在其全部依赖、索引面、授权和 tombstone 状态仍可验证时才可继续读取；无法证明即不可读。
- 用户源根、受管原文引用或所需本地文件因卸载、离线介质移除、权限变化、I/O 错误或内容在同步外变化而不可用时，Source 转为或保持
  `DEGRADED`，停止该 Source 的新查询和同步发布；不得用旧正文、解析缓存、文件名、邻近目录或其他 Source 猜测替代。本离线决策
  不改写已由 §3.6、§3.9、§3.10 与 §3.11 分别闭合的 manifest、parser、normalized-document 和 provenance 协议。

**默认、允许覆盖与适用范围**

- 默认行为是逐 Source fail-closed。仅故障的 M7 用户源从授权查询集合排除；其他已独立验证的用户源、默认 pack 和 M6a static extras
  可按原有 scope 继续运行。若请求显式指定、或其语义要求包含故障用户源，则整个请求失败，不得静默返回删去该源后的不完整结果。
- 不提供放宽依赖版本、跳过启动/查询前校验、允许单索引面查询、忽略损坏、从未验证 cache 响应、发布部分候选或把 `DEGRADED`
  当 `READY` 的 API、环境变量或运行时覆盖。部署配置只能通过禁用某个用户源进一步收紧可见性，不能使其绕过本政策。
- 本政策只适用于未来获准的 M7 用户源能力；不迁移、不重建也不改变 M0–M6 默认 pack、M6a static extras、现有 BM25/vector fallback、
  M6b preview 隔离、默认 90 题、Network 显式扩展或旧 session 恢复。M7 故障不得阻止既有 M0–M6 应用路径启动。

**输入校验、拒绝、修复与失败行为**

- M7 用户源启动与每次查询前必须校验 policy/schema 版本、tokenizer/vector 依赖、授权快照、published revision/generation、tombstone、
  BM25/FTS5 与 vector identity 集合及索引完整性摘要。未知版本、缺失元数据、摘要不匹配、损坏或不可验证状态统一拒绝，不做部分查询。
- 稳定错误码固定为：依赖不可用 `SOURCE_OFFLINE_DEPENDENCY_UNAVAILABLE`，索引损坏/不一致
  `SOURCE_OFFLINE_INDEX_INVALID`，用户源不可用 `SOURCE_OFFLINE_SOURCE_UNAVAILABLE`，修复未完成
  `SOURCE_OFFLINE_REPAIR_REQUIRED`。公开响应只包含稳定错误码、不可逆向内容的 opaque source ID 和可执行的本地修复动作类别；
  不返回文件名、logical URI、正文、query、principal、依赖探测细节、堆栈、宿主路径或索引内容。
- 修复必须由授权主体显式触发本地 `FULL` rebuild；自动动作只允许把 Source 标为不可查询并记录最小错误元数据。修复在隔离 staging
  中重新校验全部依赖、输入、索引面、授权、tombstone、identity 集合和 generation 绑定，只有完整通过 §3.2 原子发布条件后才恢复
  `READY`。修复失败、取消、中断或进程重启均保留 fail-closed 与 last-good 指针，不发布候选，不允许查询 staging。
- 索引损坏不得原地修补已发布 generation；用户源重新可用也不得仅清除错误标记。必须完成显式重建和验证。修复请求的重放、并发、
  checkpoint 和发布继续遵循 §3.1–§3.3 的 CAS、单 active run、幂等及原子可见性，不新增旁路写入者。

**兼容、安全、隐私与数据保留**

- `StudySessionService` 继续独占正式学习状态转换与领域写入；M7 fail-closed 不创建学习状态、review-log 或候选引用，也不把故障用户源
  内容扩散到 Quiz、Review Plan、默认评测或 M6b 未授权上下文。
- 错误、审计、日志、trace 和 metrics 只允许记录 policy/error code、opaque source ID、版本 digest、计数、阶段和 UTC 时间；不得记录
  prompt、query、原文/chunk、凭据、principal、文件名、logical URI、Windows/POSIX/UNC 绝对路径或可用于推断源是否属于他人的信息。
  未授权与不存在的 Source 仍遵循 §3.4 的统一 `SOURCE_NOT_FOUND`，不得借 offline 错误泄露存在性或状态。
- staging、旧 generation、索引与错误元数据的删除继续完全遵循 §3.3；本决策不新增保留期，也不改变 hard-delete receipt。依赖或源恢复
  不得复活 tombstoned、`DELETE_PENDING` 或 `DELETED` 内容。

**可量化验收与 workload**

- 获准实施后，在 `1k-single` 与 `3k-aggregate` 可生成离线 fixture 上，对 tokenizer 缺失/错误版本/初始化失败、vector 依赖缺失/
  初始化失败各注入 100 次；M7 用户源查询启动数、单面 fallback 数和候选发布数必须均为 0，稳定错误码一致率必须为 100%。
- 对 BM25/FTS5、vector、result cache、generation metadata 和 identity 集合逐项执行缺失、bit corruption、摘要不匹配及陈旧 cache 注入，
  每类各 100 次；故障 Source 返回结果数、staging 查询数和部分发布数必须均为 0。仅当 last-good 的全部面独立校验通过时才允许继续读。
- 对用户源卸载、权限拒绝、I/O 失败和同步外内容变化各执行 100 次；显式包含该源的请求必须 100% 失败，未包含该源且只使用其他已验证
  scope 的请求必须 100% 不含故障源结果。公开响应、日志、trace、审计和 metrics 的正文、query、principal、文件名及绝对路径泄露数为 0。
- 对每种故障各运行 20 次显式 FULL 修复、取消、阶段中断与重启恢复；完整验证前查询/候选发布数必须为 0，成功修复后 BM25/vector/
  generation identity 集合一致率为 100%，失败路径不得改变可用 last-good 或复活 tombstone。M0–M6 默认启动和既有只读路径必须保持可用。

**可追溯证据、责任人和日期**

- 选定依据：本节及已闭合的 §3.1–§3.5、§3.7、§3.8；统一完成标准：
  [`stage-admission-gates.md`](../standards/stage-admission-gates.md) §3；固定 tokenizer、原子发布、last-good、删除、隔离、容量、benchmark
  和路径隐私继承本文 §2.1、§3.2–§3.5、§3.7、§3.8，
  [`m6a-harness-skeleton-plan.md`](m6a-harness-skeleton-plan.md) 与 `tests/regression/test_path_privacy.py`。
- 本轮证据是冻结的离线 fail-closed 政策与可执行故障注入 workload，不声称 M7 生产 fallback、修复入口或真实
  benchmark 已经存在；当前 `tests/M7` 仅覆盖局部合同，这些设计证据不替代已登记的准入前保护基线 `SATISFIED`。
- 决策责任人：`justtodo123`；决策日期：`2026-08-29`。

## 4. 准入、开工与完成批准记录

- [x] M6a Source 契约退出证据已映射到 `M7-M6A-SOURCE-CONTRACT`（见 §2.1）；该前置本身不构成 M7 批准
- [x] `M7-PROTECTED-BASELINE=SATISFIED`：`m7-admission-20260829-02` 的可执行 1k reference、继承保护回归与默认 90 题均通过；3k 精确登记为当时 M6a 容量差距
- [x] 十二项强制决策均为 `RESOLVED`，阶段计划与登记表证据一致
- [x] 正式检索接入、离线 fallback、冻结 1k/3k BGE benchmark、五格式 parser/normalized/identity 与 lifecycle/provenance E2E 已完成技术复验
- [x] `M7-BENCHMARK` 已按冻结 1k/3k fixture、中文标注、Recall@1/3/5、p50/p95、资源与同步/重建阈值通过；报告中的 `m7_exit=true` 只覆盖该 benchmark 协议
- [x] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表状态一致
- [x] 用户或项目负责人完成仅限基础设施范围的阶段准入批准
- [x] 用户或项目负责人完成独立生产开工授权（justtodo123，2026-08-31；从 M7-1 Source Registry 起步）
- [x] 用户或项目负责人另行完成阶段退出批准（justtodo123，2026-09-06；`批准 M7 COMPLETE`）

### 4.1 准入批准（保留原记录）

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | `justtodo123` |
| approved_at | `2026-08-31` |
| approval_reference | `User instruction: M7 基础设施可以获批；Network 数据仍不获批；M8/Milvus 继续阻断` |
| plan_revision | `v2.11` |
| decision_set_version | `m7-decision-set-v1` |

批准范围 `m7-infrastructure-only-v1`：

- **included**：Source lifecycle、provenance/manifest/parser、sync/delete/isolation、FTS5/offline fallback，以及真实
  1k/3k benchmark 的 M7 基础设施实现；
- **excluded**：Network 文档晋升、Network P0 语料治理闭环、任何 corpus 自动批准、M8 专业存储、Milvus 后端选择。

### 4.2 生产开工授权（保留原记录）

生产开工门禁为 `AUTHORIZED`，`authorized_by=justtodo123`，`authorized_at=2026-08-31`；授权参考为用户指令“批准开始实施 M7 基础设施，按 M7-1 Source Registry 起步；排除 Network 31 篇晋升、M8/Milvus、M9/M10，不修改已冻结治理结论”。

### 4.3 独立完成批准

| 完成批准字段 | 当前值 |
| --- | --- |
| approved_by | `justtodo123` |
| approved_at | `2026-09-06` |
| approval_reference | `User instruction: 批准 M7 COMPLETE` |
| approval_scope | `m7-infrastructure-only-v1` |
| evidence | `docs/PLAN.md`、本计划、`docs/baselines.md`、`tests/M7/README.md`、`tests/TEST_PLAN.md` |

该批准与准入批准、生产开工授权分开登记，不覆盖或扩大原批准范围。因此 M7 当前为 `ADMITTED / COMPLETE`。Network P0 仍未关闭，Network 文档与任意 corpus 未获自动批准；M8/Milvus、M9、M10 也未因 M7 完成而获准开工。

## 5. 获准后的实施顺序（M7 已完成技术验收并取得独立完成批准）

1. ✅ 已落地版本化 lifecycle schema、Source Registry repository contract 和事务/回滚测试；已补齐文件级 manifest、parser matrix、normalized document 与 source-local FULL candidate/原子发布局部合同；
2. ✅ 已落地受限增量同步、request/run 幂等、单 active run、cancel/retry/checkpoint/recovery 的 source-local 局部合同；
3. ✅ 已落地并冻结 source-local tombstone/read barrier、索引/cache 不可读传播、provenance 失效和检索隔离过滤局部合同；
4. ✅ 已落地 `jieba==0.42.1` / `sa.source.fts5-tokenizer.v1` generation-bound SQLite FTS5 与离线 fail-closed 校验/显式 FULL repair；
5. ✅ 已落地 Search/QA 的受信任内部 principal overlay：隔离后 FTS5+vector、generation/auth 缓存、跨源 RRF 与 `user://` provenance；preview/quiz/sessions 不含用户源；
6. ✅ 已落地 generation-bound source-local vector：与同一 published generation 的 FTS5 identity-set 100% 对齐，缺 metadata/模型/generation 时用户源 fail closed；
7. ✅ M7-2 manifest-bound snapshot cache：有界 LRU（16）、无变化 FULL 保持已发布 `manifest_digest`、磁盘 identity fail-closed；见下列退出清单。
8. ✅ M7-3 冻结 `sa.source.benchmark.v1`：已合并 runner 与 2026-09-04 实跑证据，报告 `m7_exit=false`（1k RSS、3k Recall@1/p50 未达标）。
9. ✅ M7-4 关闭冻结门槛：2026-09-04 完整 20+200 / FULL 5+20 BGE 复跑通过（1k RSS 授权 768 MiB）。报告 `m7_exit=true` 只覆盖 benchmark 门槛；M8 仍须独立评估。
10. ✅ M7-5 READY/CURRENT 指针一致性：registry 仍是生命周期权威；CURRENT 只是可修复便利指针，失败不得把 READY 降级。
11. ✅ M7-6 真实 parser 与 lifecycle/provenance 技术验收：五格式各 100 个运行时 fixture × 20 次全 PASS；完整根级、M7、回归与 platform 套件通过；justtodo123 于 2026-09-06 另行批准 `M7 COMPLETE`。


### M7-2：manifest-bound snapshot cache

本增量在已冻结的 source-local FULL candidate/原子发布之上，补齐 **已发布 snapshot 的身份绑定与有界缓存**。
它不是 M7 exit，也不替代冻结 20 次 1k/3k BGE 协议。

**范围**

- 已发布 FULL snapshot 的身份绑定到 `source_id + generation + source_fingerprint + manifest_digest + document/chunk counts`；
- 文件内容无变化的重复 FULL：不新增 revision，不因 manifest `created_at` 改写已发布 snapshot 或 `manifest_digest`；
- 进程内 snapshot 缓存使用 LRU，上限固定 `SNAPSHOT_CACHE_MAX_ENTRIES = 16`；历史 generation 仍可从磁盘加载；
- 磁盘 generation 与 expected snapshot identity 不一致时 fail-closed，不得把损坏 payload 当作 CURRENT；
- 不修改已冻结的 `sa.source.manifest.v1` 字段集；`created_at` 仍是审计时间，snapshot 身份以内容指纹和已发布 digest 为准。

**非目标**

- 冻结 `sa.source.benchmark.v1` 的 20 次 1k/3k BGE、RSS/p50 门槛或 M7 exit；
- Network 31 篇晋升、P0 语料闭环、默认 90 题扩容；
- M6b preview / Quiz / Review Plan / study-sessions 接入用户源；
- M8/Milvus、独立 `/api/v1/sources`、provenance 晋升链。

**测试矩阵**

| 用例 | 文件 | 通过标准 |
| --- | --- | --- |
| 无变化重复 FULL 忽略 volatile `created_at` | `tests/M7/test_full_snapshot.py` | 同 generation、同 `manifest_digest`、revision 仍为 1 |
| snapshot 缓存有界 | `tests/M7/test_full_snapshot.py` | `len(cache) <= 16`；当前 generation 仍可加载且 digest 校验通过 |
| 磁盘 identity 损坏 fail-closed | `tests/M7/test_full_snapshot.py` | SHA256 或 identity 字段不一致时不得激活/返回损坏 snapshot |
| 既有 FULL last-good / 指针 / 失败降级 | `tests/M7/test_full_snapshot.py` 原 4 项 | 不回退 |

回归：`tests/M7/` 全量 + `tests/regression/test_docs_consistency.py` / `test_governance_contract.py` / `test_document_governance.py`。不把 disposable 或冻结 BGE 报告当作本增量退出证据。

**退出清单（M7-2 increment，不是 M7 exit）**

- [x] `tests/M7/` 含新增 snapshot 合同全绿，既有 FULL/FTS5/vector/Search overlay 不回退
- [x] 无变化 FULL 不新增 revision，且已发布 `manifest_digest` 稳定
- [x] 进程内 snapshot 缓存不超过 16 条
- [x] 身份损坏 fail-closed；last-good 不被错误 generation 覆盖
- [x] 文档与实现一致：本计划、`tests/M7/README.md`、`tests/TEST_PLAN.md`、`docs/PLAN.md`
- [x] 不声称 M7 exit，不批准 Network，不改变默认 OS/DS/CO 90 题包


### M7-3：冻结 1k/3k BGE 验收证据

本增量只补齐 `sa.source.benchmark.v1` 的可执行冻结证据，不批准 Network，不启动 M8/Milvus，也不把未达标报告写成 M7 exit。

**范围**

- 可生成、不入 Git 的 `1k-single`（100 docs / 1,000 chunks）与 `3k-aggregate`（300 docs / 3,000 chunks）；
- 正式检索路径为 source-local FTS5 + 冻结 BGE `BAAI/bge-small-zh-v1.5`，禁止用 hash embedder 冒充冻结证据；
- 查询协议：每个 workload 20 次 warm-up + 200 次 measured；warm-up 不进入 p50/p95/Recall；
- FULL 协议：每个 workload 独立 OS 进程 5 次 warm-up + 20 次 measured，记录 FULL p95 与峰值 RSS；
- 附加探针：warm no-op INCREMENTAL、10% added/modified/removed INCREMENTAL、重启恢复、corruption fail-closed、delete-barrier；
- 门槛：Recall@1/3/5 ≥ 0.70/0.85/0.90；1k 查询 p50 ≤ 150 ms、p95 ≤ 400 ms、RSS ≤ 768 MiB；3k 查询 p50 ≤ 250 ms、p95 ≤ 750 ms、RSS ≤ 1 GiB；FULL p95 ≤ 30 s；identity 100%。全部通过才能把 `m7_exit` 标为 true。

**非目标**

- Network 晋升、默认 90 题扩容、preview/quiz/sessions 用户源、M8/Milvus。

**测试矩阵**

| 用例 | 文件 | 通过标准 |
| --- | --- | --- |
| frozen runner schema / 非 exit 冒烟 | `tests/M7/test_source_benchmark.py` | hash/tiny fixture；`m7_exit=false`；无宿主路径 |
| 1k/3k BGE 冻结报告 | `tools/run_m7_frozen_benchmark.py` | 实跑 artifacts；门槛逐项判定；不得静默跳过 |

**退出清单（M7-3 increment，不是自动 M7 exit）**

- [x] frozen runner 可在离线 BGE 缓存下跑完 1k 与 3k（2026-09-04 `artifacts/m7-frozen-benchmark.json`）
- [x] 查询 20+200、FULL 5+20、RSS/p50/p95/Recall/identity 写入报告
- [x] 任一门槛失败则 `m7_exit=false`，不得启动 M8（本次 1k RSS、3k Recall@1 与 query p50 失败）
- [x] 文档与 disposable hash smoke 仍然区分冻结协议（`docs/baselines.md` 已追加失败证据）

上述顺序按独立生产开工授权执行。公共 Search/QA 请求体不接受 caller-selected `principal_id`；仅在服务端可信内部边界提供 principal 时叠加授权用户源。默认启动不创建 registry，M6b preview 不含用户源。`tests/M7/` 当前收集 270 项；Python 3.13.3 下 TXT 真实 parser 用例按精确 `cpython-textio==3.11.9` 合同 fail closed。2026-09-06 已在 `platform/.venv311` 的 Python 3.11.9 精确依赖环境中独立复跑 seed `20260904` 的五格式协议：每格式 100 个运行时 fixture × 20 次全 PASS，失败计数均为 0，`external_source_reads=0`、`tmp_only=true`，临时报告不入库。benchmark 与 parser fixture 均在运行时生成，不把用户原始材料提交到 Git。2026-09-04 完整冻结 BGE 复跑 `sa.source.benchmark.v1` 门槛通过；五格式 parser/normalized/identity 证据与独立 lifecycle/provenance E2E、历史完整回归彼此分离。独立只读 Exit Evaluation 只形成 technical exit candidate；随后 justtodo123 于 2026-09-06 明确批准 `M7 COMPLETE`，因此 M7 为 `ADMITTED / COMPLETE`。该批准不自动批准或启动 M8。

### M7-4：关闭冻结门槛（Recall@1 / p50 / RSS，已完成）

本增量只关闭 2026-09-04 冻结 BGE 报告中的失败项，不降低门槛，不批准 Network，不启动 M8/Milvus。任一门槛失败则 `m7_exit` 保持 false。

**范围**

- 3k Recall@1：跨源 RRF 打平时，精确查询命中不得被近重复邻居或 source 排序抢占 top-1；
- 3k query p50：同一 search 请求内 BGE query 向量只编码一次，避免 3 源重复 encode；
- 1k peak RSS：现行门槛 768 MiB（justtodo123 于 2026-09-04 授权）；继续加载冻结 BGE `BAAI/bge-small-zh-v1.5`，禁止改用 hash 冒充；
- 复跑完整冻结协议：查询 20+200、FULL 独立进程 5+20，门槛仍按 `sa.source.benchmark.v1` 判定。

**非目标**

- 放宽 Recall@1 0.70 或 3k p50 250 ms；不得把 1k RSS 再放到超过已授权的 768 MiB；
- Network 晋升、默认 90 题扩容、preview/quiz/sessions 用户源、M8/Milvus。

**测试矩阵**

| 用例 | 文件 | 通过标准 |
| --- | --- | --- |
| 跨源精确查询 top-1 | `tests/M7/test_user_source_search.py` | 3 个近重复源时 gold file 为 Recall@1 |
| 查询向量单次编码 | `tests/M7/test_user_source_search.py` | 一次多源 search 只 `encode` 一次 query |
| 冻结门槛复跑 | `tools/run_m7_frozen_benchmark.py` | 实跑 artifacts；失败不得把 `m7_exit` 标 true |

**退出清单（M7-4 increment，不是自动 M7 exit）**

- [x] 3k Recall@1 ≥ 0.70，且不靠降低门槛或 hash backend（完整复跑 1.000）
- [x] 3k query p50 ≤ 250 ms（84.736 ms）
- [x] 1k peak RSS ≤ 768 MiB（约 549 MiB）
- [x] 完整 20+200 / FULL 5+20 BGE 复跑写入报告（`artifacts/m7-frozen-benchmark.json`）
- [x] 报告 `m7_exit=true` 仅表示 benchmark 通过；`m8_started=false`，不得自动启动 M8
- [x] 既有 isolation / identity / overlay 合同不回退（search/snapshot/benchmark/governance 41 passed）

### M7-5：READY 与 CURRENT 激活一致性（已完成）

本增量固定 `publish_full` 在 READY 提交之后激活 `CURRENT` 失败时的语义，并让删除与 hard-delete 恢复遵循同一 registry 权威；不批准 Network，不启动 M8，也不构成 M7 exit。Registry 的 `published_generation` 仍是生命周期权威；不得把文件指针反向升级为治理权威。不引入独立 repair marker：相同 FULL 重试就是指针修复路径。

**稳定语义**

- 顺序保持：materialize generation → registry `SYNCING -> READY` → 激活 `CURRENT`。
- 第 3 步失败：调用者收到 `PUBLICATION_FAILED`；Source 保持 `READY`；新 generation 可按名字加载；`CURRENT` 可缺失或仍指向旧 generation。
- 权威读取必须使用 registry `published_generation`。无 generation 的 `load_snapshot`/`published_path` 只反映便利指针，指针滞后不等于 last-good。
- 已有 last-good 时，旧 `CURRENT` 目录在修复前仍可读，但查询/索引不得把它当成已发布 generation。
- 相同内容的 FULL 重试必须幂等修复 `CURRENT`，不得新增 revision，也不得把已 `READY` 的 Source 降为 `DEGRADED`。

**测试矩阵**

| 用例 | 文件 | 通过标准 |
| --- | --- | --- |
| 首次发布激活失败 | `tests/M7/test_snapshot_pointer_consistency.py` | `READY`、无 `CURRENT`、generation 可按名字加载 |
| 旧 CURRENT 仍可读 | `tests/M7/test_snapshot_pointer_consistency.py` | 便利指针仍指向旧 generation；权威加载为新 generation |
| 重试修复指针 | `tests/M7/test_snapshot_pointer_consistency.py` | `CURRENT` 对齐且 revision 不增加 |
| 重试失败不得降级 | `tests/M7/test_snapshot_pointer_consistency.py` | 仍为 `READY` / `PUBLICATION_FAILED` |
| 删除时 CURRENT 缺失/滞后 | `tests/M7/test_source_delete.py` | 按 intent 的 `generation_upper_bound` 枚举文件级 tombstone |
| receipt 后终态转换失败 | `tests/M7/test_source_delete.py` | 重试复用同一 receipt 并完成 `DELETE_PENDING -> DELETED` |

**退出清单（M7-5 increment，不是自动 M7 exit）**

- [x] READY 后激活失败不回滚 registry 发布
- [x] 新 Source 无 CURRENT 时 generation 仍可按名字寻址
- [x] 旧 CURRENT 在修复前可读，但不替代 registry
- [x] 相同 FULL 重试修复 CURRENT 且不新增 revision
- [x] 指针修复失败不得把 READY 降为 DEGRADED
- [x] 删除按 intent 捕获的 published generation 发布文件级 tombstone，不依赖 CURRENT
- [x] receipt 已写入后的终态转换故障可重试恢复，且 receipt 保持不可变
- [x] M7-6 已闭合真实五格式 parser/normalized-document 与 provenance/recovery/delete E2E 技术证据；这不自动构成 M7 exit

## 6. 撤销与后续边界

任何 identity、删除、隔离、tokenizer、benchmark、文件级 manifest、parser matrix、normalized document
或 provenance 前提实质变化，都将已完成状态改为 `REVOKED` 并停止依赖其退出证据。M7 当前的 `COMPLETE`
只覆盖 `m7-infrastructure-only-v1`，不改变 Network、corpus 自动批准、M8 专业存储或 Milvus 的排除边界。
M8 的事实型 `M8-M7-EXIT` 前置现已满足，但 M8 自身仍为 `BLOCKED / NOT_STARTED`：八项强制决策、后端选择、
依赖、迁移、parity、fallback、benchmark 和独立人工批准均未闭合。M9/M10 同样不会因 M7 完成而自动获批或开工。

## 7. 收口后的缺陷修正（2026-09-22）

### 7.1 解析路径的墙钟上界（`PARSE_TIMEOUT_SECONDS`）

**缺陷**：`MAX_FILE_BYTES` / `MAX_PDF_PAGES` / `MAX_PPTX_SLIDES` / `MAX_DOCX_BODY_PARAGRAPHS`
约束的是解析器**拿到多少输入**，不是它**能跑多久**。一个在内部死循环的解析器既不返回也不抛异常，
因此 `_parse_pdf` 的 `except Exception` 以及解析路径上任何 `except` 子句对它**都是盲的**：调用永不返回。
在仓库强制的单 worker 拓扑下（`worker_topology.py` 的 `enforce_single_worker_topology`），这会把**整个进程**
卡死，而不是一个请求。

**触发证据（本仓外部，非本阶段证据）**：`pypdf` 6.0.0 有两个已公开的 DoS 通告
（CVE-2026-59935 / CVE-2026-59936，未终止的内联图片），其**全部影响**就是死循环；修复版本为 6.14.1 / 6.14.2。
本阶段**不**升级该 pin（理由见下），改为给解析路径本身加上界。

**修正**：`parse_document` / `parse_file` 新增 `timeout_seconds` 参数（默认 `PARSE_TIMEOUT_SECONDS = 30.0`），
校验与既有 `max_bytes` **同形**——必须是正的有限数且**不得超过**该冻结默认值，超过即
`PARSE_LIMIT_EXCEEDED` 且不触达解析器。执行经 `_run_bounded`：解析在 daemon 线程中运行，超时即抛新增的
稳定码 `ParserErrorCode.PARSE_TIMEOUT`（`SOURCE_PARSE_TIMEOUT`）。该接缝是**格式无关**的
（`units = _run_bounded(parser, timeout_seconds)` 对所有五种格式生效），与 `max_bytes` 一样统一施加。

**为何不升级 pypdf pin**：该 pin 是**承重**的，改它要同时动六处——`platform/requirements.txt`、
`parser_matrix.py` 的 `PARSER_SPECS`（`require_parser` 对不等于该版本的值 fail closed）、
`tests/M7/test_parser_matrix.py` 的精确断言、本文件第 678 行的冻结策略串，以及 M8 metadata-discovery 的
`SCOPE_ASSERTIONS` 与 scope builder（后者从 HEAD 读 `requirements.txt`，不是恰好一条 `pypdf==6.0.0` 就抛
`ValueError`，故在 HEAD 上升级会让 `tests/M8_metadata_discovery/` 变红，重冻需开一个 M8 新周期）。
更根本的是：**升级只修这两个 CVE，不改变「解析没有时间上界」这一缺陷本身**——下一个畸形输入仍会挂在别处。

**为何不触发 §6 撤销**：§6 的撤销前提是「identity、删除、隔离、tokenizer、benchmark、文件级 manifest、
parser matrix、normalized document 或 provenance 前提**实质变化**」。本次三者均未变：

- **parser matrix 未变**：五种格式的唯一解析器及其精确版本**逐字未动**（第 678 行的冻结策略串保持恰好一次
  出现），`require_parser` 的精确匹配语义未动；新增的是**解析调用外的时间边界**，不是 parser 身份。
- **normalized document / manifest / provenance 未变**：`ParsedDocument` / `ParsedUnit` 的形状与
  `document_id` 派生未动；正常解析的产出**逐字节不变**（`tests/M7/test_parser_timeout.py` 用真实
  Markdown 钉住这一点）。
- **兼容不变量未变**：未 bump `SCHEMA_VERSION`、未改公开路由、未改 `PUBLISHED` 语义。

**新增可观测行为（诚实记录）**：一个新的稳定失败码 `SOURCE_PARSE_TIMEOUT`。它经 `ManifestEntry.reject_code`
（自由字符串，无冻结词表）进入 manifest，因此旧 manifest 仍可读；既有测试未枚举 `ParserErrorCode` 全集，
故无既有断言被改动。

**本修正不消除的残留（逐字记录，不得后读时当作已解决）**：

1. **线程被放弃而非取消**：Python 无法强杀线程，超时后那个循环线程会继续跑到进程退出。与
   `plan_ai_adapter._run_blocking` 的 caveat 同形。泄漏在实践中被限制为**每次发布尝试至多一个**——
   `_build_candidate` 在首个坏文件上即 fail closed 并把异常抛出 `publish_full`，不会继续处理 manifest 余项。
2. **进程级隔离是更强的修法，本次不做**：真正的硬上界需要子进程 + 强杀（每次解析一次进程开销）或
   平台级作业对象。本次取的是与既有 `_run_blocking` 一致的**调用级**上界，不是**进程级**上界。
3. **默认值 30 秒是估计而非实测**：没有对最大合法输入（32 MiB / 500 页）的实测解析耗时基线。若将来出现
   合法大文件在 30 秒内跑不完，那是**新的**缺陷，需另行裁定默认值，不得靠放宽本上界来掩盖。
4. **`txt` 格式在本机不经此路径**：`cpython-textio==3.11.9` 的精确合同使其在 CPython 3.13.3 上
   `PARSER_UNAVAILABLE`，故本机测不到该格式的边界（新测试对该格式 skip 而非断言）。

**证据**：`tests/M7/test_parser_timeout.py`（7 项，新增文件，**未修改**任何存量 M7 测试）。变异验证：
把超时码改成 `PARSE_FAILED` → 3 项失败；去掉「只能收紧」的上限校验 → 1 项失败。
**另记一项无法用判红表达的结果**：完全移除该上界不会让测试判红，而是让测试**挂起**——因为死循环正是
没有 `except` 能捕获的东西。实施过程中一次把 mock 打错位置（替换了 `_run_bounded` 本身而非解析器）
就实测到了这一点：整套测试 300 秒不返回。这正是本修正存在的理由，也是「挂起不是失败」这条测试盲区的实证。

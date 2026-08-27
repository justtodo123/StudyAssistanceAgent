# M7 用户 Source 生命周期与千级检索准备计划

> 当前状态：设计准备；`BLOCKED / NOT_STARTED`，未获准开工
> 前置：`M7-M6A-SOURCE-CONTRACT` 已映射 M6a Source 契约与退出证据（`SATISFIED`）；`M7-PROTECTED-BASELINE` 仍为 `OPEN`
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)
> 本文件补全强制决策清单，不批准开工。Agent 不得自行批准 M7。

## 1. 范围与非目标

M7 在 M6a 稳定 Source identity 和静态快照边界后，规划用户源持久化注册、同步、删除、多源隔离以及
1k–3k chunk 可复现检索。它不迁移到 LanceDB/Qdrant，不实现目标规划或自主 Runner，也不把外部原始
PDF/PPT 复制进仓库。

本计划存在只表示准备工作。所有设定、证据和批准闭合前，不得创建生产 Source Registry、同步 worker、
schema migration、依赖、API 或运行时开关。只读盘点 `tools/source_inventory.py` 是 collect-only 调查，
不能替代下列强制决策，也不构成 M7 开工。

## 2. 前置证据与继承不变量

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M7-M6A-SOURCE-CONTRACT` | `SATISFIED` | M6a identity、额外源校验、generation 切换、缓存失效和路径隐私的退出证据；映射见 §2.1 |
| `M7-PROTECTED-BASELINE` | `OPEN` | M7 专属 workload、p50/p95、资源、成本、质量阈值及现有保护基线复验方案的证据 |

M7 完整继承统一准入政策中的 M0–M5 不变量：正式状态转换继续由 `StudySessionService` 掌握；旧 SQLite
session 可恢复；默认 OS/DS/CO 90 题和 Network 显式扩展边界不变；默认离线路径不依赖外部模型或新服务；
对外结果、日志和 trace 不泄露宿主机绝对路径。

`M7-M6A-SOURCE-CONTRACT=SATISFIED` 只表示 M6a 退出证据已登记，不能单独把本阶段改为 `ADMITTED`。

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
| `M7-LIFECYCLE-SCHEMA` | `OPEN` | Source/revision/sync/error/audit 的版本化 schema、状态转换、约束、升级兼容和权威写入者 |
| `M7-SYNC-SEMANTICS` | `OPEN` | 全量/增量同步、并发、重试、取消、中断恢复、generation 可见性和 last-good snapshot |
| `M7-DELETE-SEMANTICS` | `OPEN` | delete/tombstone/保留期/硬删除/恢复，以及 BM25/vector/result cache 的删除传播与可证明完成条件 |
| `M7-ISOLATION` | `OPEN` | learner/source namespace、授权模型、查询 filter、跨源隔离和越权拒绝语义 |
| `M7-FTS5-TOKENIZER` | `OPEN` | 中文 tokenizer 明确选型、规范化、打包可用性、索引兼容和不可用 fallback |
| `M7-SCALE-LIMITS` | `OPEN` | source/document/chunk/bytes 上限，同步、增量更新、重建和查询支持目标及超限行为 |
| `M7-BENCHMARK` | `OPEN` | 可复现 1k/3k chunk fixture、中文查询与标注、Recall@k、p50/p95、索引大小、同步/重建时间、硬件、样本数和阈值 |
| `M7-OFFLINE-FALLBACK` | `OPEN` | 无可选 tokenizer/vector、索引损坏或用户源不可用时的离线启动、查询、修复和用户可见错误语义 |
| `M7-SOURCE-MANIFEST` | `OPEN` | 文件级 schema；Source 类型与文件格式分离；fingerprint 与 revision 规则 |
| `M7-PARSER-MATRIX` | `OPEN` | 每种格式的解析器、parser version，以及失败、超限和不支持时的处理 |
| `M7-NORMALIZED-DOCUMENT` | `OPEN` | PDF 页 / PPT 幻灯片 / Word 标题等统一表示；解析产物缓存位置；缓存失效和清理 |
| `M7-PROVENANCE` | `OPEN` | 原始文件 → 解析文档 → Chunk → QA 引用；原文 / 人工精炼 / AI 草稿区分；删除和更新如何传播到出处 |

每项只有按统一政策记录明确选定值、默认与覆盖、校验/失败行为、兼容/隐私影响、适用阈值、证据、责任人和
日期后才能标为 `RESOLVED`。候选项、`TBD`、无 workload 的数字或“实施时决定”都保持 `OPEN`。
原有八项未选定值，本轮**不改状态、不填选定值**。下列四类只补澄清边界，同样保持 `OPEN`。

### 3.1 `M7-SOURCE-MANIFEST`（`OPEN`）

文件级 manifest 描述用户源里**每个被接纳文件**的可移植身份，不是 Unity Library 之类工程文件的全盘清单。

**已继承、不得改写**

- `source_id` 是逻辑命名空间；`logical_uri` 是源内相对 POSIX 路径；`document_id = sha256(source_id + logical_uri)` v1。
- `fingerprint` 表示规范化内容，`revision` 表示 Source 快照，`generation` 表示已发布检索视图；三者不得混用。
- `source_type`（来源策略：`human_markdown` / `web_reviewed` / `user_registered` 等）与文件 `format`
  （`pdf` / `pptx` / `md` 等）必须分离；不得用扩展名冒充 `source_type`。
- 公开出处不得包含宿主绝对路径。原始 PDF/PPT 留在仓库外，Git 不收原文。

**准入前仍须选定（当前无选定值）**

- 文件级 schema 名称与版本（例如是否新建 `sa.source.manifest.v1`，字段必选/可选表）。
- 用户源 `fingerprint` 算法：全文摘要、采样摘要还是规范化文本摘要；与 M6a Markdown 内容 fingerprint 的兼容规则。
- `revision` 如何由文件集合 fingerprint 聚合；单文件变更是否只使该 document 失效。
- 哪些分类进入用户源 manifest、哪些只记排除计数；不得把 collect-only 盘点字段直接当作生产 schema。

`tools/source_inventory.py` 的字段（`logical_uri` / `format` / `size` / `fingerprint` / `classification` 等）
只是调查输入。**不得**因其存在而把本决策标为 `RESOLVED`。

### 3.2 `M7-PARSER-MATRIX`（`OPEN`）

Parser matrix 决定每种 `format` 用什么解析器把原文变成可切块文本。解析器名称和版本必须能进入
M6a 已闭合的 `build_input_digest`（含 parser version）。

**已继承、不得改写**

- Markdown 默认 pack 继续使用现有 `sa.chunk.markdown-h2.v1`；M7 不得悄悄改默认 90 题切块。
- 解析失败不得把原文复制进仓库或写进默认 `knowledge/`。
- 不支持的格式不得假装已检索；公开错误只含逻辑 URI 与错误码。

**准入前仍须选定（当前无选定值）**

- 每种拟支持格式的唯一解析器及精确版本（PDF / PPTX / DOCX / Markdown / 纯文本等）；禁止“实现时再选库”。
- 失败语义：跳过该文件、拒绝该 Source generation，还是降级为“仅文件名/标题”。
- 超限语义：与尚未闭合的 `M7-SCALE-LIMITS` 对齐，本决策不提前发明字节上限。
- 不支持格式：显式 `unsupported`，计入 manifest/审计，不进入 chunk 索引。
- 离线不可用解析器时的 fallback：与 `M7-OFFLINE-FALLBACK` 对齐，本决策不提前指定替代库。

### 3.3 `M7-NORMALIZED-DOCUMENT`（`OPEN`）

Normalized document 是解析后、切块前的统一表示，用来把 PDF 页、PPT 幻灯片、Word 标题映射到稳定
`chunk_key`，而不是直接把二进制当 chunk。

**已继承、不得改写**

- 默认 Markdown 仍按 `##` 小节切块；最短切片与 embedding 参数见 runtime-contracts，M7 不改默认 pack。
- 解析产物不是 Git 资产，不得写入 `knowledge/` 或外部资料根。
- 缓存键必须能随 fingerprint 与 parser version 失效；mtime 不得作为唯一失效输入。

**准入前仍须选定（当前无选定值）**

- 统一文档模型：页 / 幻灯片 / 标题 / 节的字段表、稳定 `chunk_key` 公式、空页/隐藏幻灯片规则。
- 解析产物缓存根（逻辑位置，不写宿主绝对路径）、是否按 `source_id` 分目录、与 snapshot generation 的关系。
- 失效：源文件 fingerprint 变、parser version 变、chunk schema 变时的重建范围。
- 清理：成功发布后如何删除 staging 解析缓存；extra/用户源移除后是否立即删除该源缓存；是否沿用
  M6a retain-1。具体删除完成条件仍由 `M7-DELETE-SEMANTICS` 决定，本决策不提前闭合 tombstone。

### 3.4 `M7-PROVENANCE`（`OPEN`）

Provenance 连接“原始文件 → 解析文档 → Chunk → QA 引用”，并区分原文、人工精炼笔记和 AI 草稿。

**已继承、不得改写**

- 默认可检索出处：默认 pack 为 `knowledge/{logical_uri}`，extra 为 `extra://{source_id}/{logical_uri}`。
- `source_type` / `ingest_status` 已决定能否进入检索：`ai_draft`、`web_candidate` 永不检索。
- 引用、日志、trace 不得暴露宿主路径、原文全文或密钥。

**准入前仍须选定（当前无选定值）**

- 用户源公开出处 URI 方案（是否沿用 `extra://`、另设 `user://`，以及与保留 `user-` source_id 的关系）。
- provenance 记录字段：原始 logical_uri、parser version、normalized document id、chunk_id、source_type、
  ingest_status；哪些出现在 QA `sources`，哪些只留内部审计。
- 原文 / 人工精炼 / AI 草稿的晋升规则：谁写 `ingest_status`，精炼笔记是否生成新 `logical_uri`。
- 更新传播：文件 fingerprint 变化后，旧 chunk 何时不可召回、QA 缓存何时失效。
- 删除传播：出处链上的解析缓存、chunk、BM25/vector/result cache 的可见性；硬删除完成条件仍属
  `M7-DELETE-SEMANTICS`，本决策只要求 provenance 能证明“引用指向的对象已不可检索”。

## 4. 准入检查与批准记录

- [x] M6a Source 契约退出证据已映射到 `M7-M6A-SOURCE-CONTRACT`（见 §2.1）；**不构成 M7 批准**
- [ ] `M7-PROTECTED-BASELINE` 仍为 `OPEN`，专属 workload / p50/p95 / 成本 / 质量阈值未闭合
- [ ] 十二项强制决策全部为 `RESOLVED`，阶段计划与登记表证据一致
- [ ] 生命周期状态机、删除传播、隔离和离线 fallback 可通过契约/故障注入方案验证
- [ ] benchmark fixture、workload、硬件和阈值在写性能代码前冻结
- [ ] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表状态一致
- [ ] 用户或项目负责人完成批准

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准为空，M7 保持 `BLOCKED / NOT_STARTED`。Agent 不得自行批准。

## 5. 获准后的拟实施顺序

1. 先落地版本化 lifecycle schema、文件级 manifest、repository contract 和迁移/回滚测试；
2. 在 parser matrix 与 normalized document 契约冻结后，实现单源完整快照，再实现受限增量同步和并发/中断语义；
3. 实现 tombstone、索引/cache 删除传播、provenance 失效和隔离过滤；
4. 在离线 fallback 可用后接入明确选定的 FTS5 tokenizer；
5. 运行冻结的 1k/3k workload，根据证据决定是否进入 M8，而不是预先引入专业后端。

上述顺序在批准前不得执行。拟新增测试仅作为获准后方案：`tests/M7/` 覆盖 lifecycle、sync、delete、isolation、
fallback；benchmark 使用可生成 fixture，不把用户原始材料提交到 Git。退出条件包括所有契约/保护回归通过、
默认 90 题不退化、删除后各索引不可召回、隔离零越权，以及冻结 benchmark 达标。

## 6. 撤销与后续边界

任何 identity、删除、隔离、tokenizer、benchmark、文件级 manifest、parser matrix、normalized document
或 provenance 前提实质变化，都将已准入状态改为 `REVOKED` 并停止实施。
M8 只能使用 M7 的真实退出证据，不能把本计划、collect-only 盘点或 M6a 映射当作专业存储开工依据。

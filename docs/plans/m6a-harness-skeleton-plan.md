# M6a Harness 骨架（契约先行）执行计划

> 版本：v2.3
> 制定日期：2026-08-21
> 当前状态：八项强制设计决策、保护基线与负责人批准均已闭合；`ADMITTED / IN_PROGRESS`，M6a-1 协议契约正在实施
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)；最终状态权威为 [`docs/PLAN.md`](../PLAN.md)
> 适用范围：Source/Store/Tool/Runner 契约、现有状态机兼容、启动期静态额外 Markdown 源
> 后续阶段：M7 用户数据源生命周期；M6b 为独立的只读 Agent 预览

## 0. 准入状态与强制设定

M6a-P0 crawler 与 2026-08-25 保护基线均已形成真实前置证据；八项强制设计决策已经用户逐项确认并
按 §0.4 闭合为 `RESOLVED`。用户/项目负责人于 2026-08-25 明确批准“M6a 可以开工”，因此本计划现为
`ADMITTED / IN_PROGRESS`。M6a-1 已开始生产实施；该状态只授权按第 3 节实施，不代表整个 M6a 已完成。

### 0.1 前置证据

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M6A-P0` | `SATISFIED` | `tests/M6_crawler/` 与 `.github/workflows/offline-ci.yml` |
| `M6A-PROTECTED-BASELINE` | `SATISFIED` | 2026-08-25 候选树真实证据：`docs/baselines.md`；路径隐私 blocker 已关闭；focused privacy/API/SSE/recovery 32 项、M3b 13 项、原始 `platform/tests/` 40 项、根级 271 项通过（1 项显式 online smoke 跳过）、crawler offline 52 项通过（1 项 online deselected）、slow 90 题质量门禁 3 项通过；评测 OS 38 + DS 28 + CO 24 = 90，Recall@3 为 0.987 / 0.929 / 1.000，汇总 0.972，报告 SHA-256 `5db638a9cdb59081c2dc6ecea09a873fb31ad07e369364d6bcaa6a3ecbba00ca`。该 prerequisite 已闭合；M6a 准入状态另见 §0.3 |

### 0.2 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M6A-SOURCE-POLICY` | `RESOLVED` | 最终选定值、行为、阈值、证据、责任人与日期见 §0.4 |
| `M6A-IDENTITY` | `RESOLVED` | 最终选定值、行为、阈值、证据、责任人与日期见 §0.4 |
| `M6A-EXTRA-SOURCES` | `RESOLVED` | 最终选定值、行为、阈值、证据、责任人与日期见 §0.4 |
| `M6A-CACHE-KEYS` | `RESOLVED` | 最终选定值、行为、阈值、证据、责任人与日期见 §0.4 |
| `M6A-SNAPSHOT-SWITCH` | `RESOLVED` | 最终选定值、行为、阈值、证据、责任人与日期见 §0.4 |
| `M6A-SOURCE-LIMITS` | `RESOLVED` | 最终选定值、行为、阈值、证据、责任人与日期见 §0.4 |
| `M6A-WORKER-TOPOLOGY` | `RESOLVED` | 最终选定值、行为、阈值、证据、责任人与日期见 §0.4 |
| `M6A-TRACE-RETENTION` | `RESOLVED` | 最终选定值、行为、阈值、证据、责任人与日期见 §0.4 |

八项决策已按统一政策记录唯一选定值、默认与覆盖、失败语义、兼容性、隐私、量化阈值、证据、责任人和日期，
并同步为 `RESOLVED`。实现、保护基线、阶段批准和退出测试仍是相互独立的后续门禁；不得以设计决策已闭合
宣称能力已经实现或阶段已经准入。

### 0.3 全量准入检查与批准

- [x] 八项强制决策全部为 `RESOLVED`，且阶段计划与登记表证据一致；
- [x] M6a-P0 与保护基线证据在待实施候选树上真实有效；
- [x] 已由保护基线逐项验证统一政策中的 M0–M5 兼容不变量；
- [x] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表当前状态一致；
- [x] 用户或项目负责人完成批准记录。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-08-25 |
| approval_reference | 用户指令：“M6a 可以开工” |
| plan_revision | v2.3 |
| decision_set_version | m6a-decision-set-v1 |

批准记录已经闭合，M6a 已按第 3 节顺序开始生产实施。M6a-1 协议契约及其隔离 contract tests 正在完成，交付状态为
`IN_PROGRESS`。第 4 节 contract tests 和 benchmark 是实施/退出门禁，不是准入前置证据。

### 0.4 八项强制决策（最终选定）

> decision_set_version：`m6a-decision-set-v1`
> 原始提案：Codex / `m6a-codex-2026-08-25-v1`
> 决策确认：justtodo123 / 2026-08-25
> 当前状态：八项均为 `RESOLVED`；这里只闭合设计决策，不代表 M6a 已准入或已经实现。

本节按统一政策记录唯一选定值、默认与覆盖、失败语义、兼容性、隐私、量化阈值、证据和责任人。
现有代码引用只证明兼容约束或实施差距；实现、保护基线与阶段批准仍须分别留证。

#### M6A-SOURCE-POLICY

- **状态 / 选定值**：`RESOLVED` —
  `trusted-default-missing-fields; reject-explicit-invalid; reviewed-crawler-override; last-good-default-pack`。
- **默认与范围**：默认检索源固定为 `source_id=knowledge-pack`。只允许 `human_markdown`、`web_reviewed` 且
  `ingest_status=approved`；`web_candidate`、`ai_draft` 永不检索。可信默认 pack 缺失 `source_type` /
  `ingest_status` 时分别兼容为 `human_markdown` / `approved`；显式非法枚举拒绝该文件并记录逻辑 URI，不得
  回退为 approved。额外源不享受缺字段兼容，任一 frontmatter 错误都拒绝整源。
- **允许覆盖**：保留 crawler 的显式人工 `allow_knowledge_write=True` / `--allow-knowledge-write`，但它只绕过
  输出目录门禁，不改变候选 frontmatter，也不自动批准或索引。`SA_KNOWLEDGE_ROOT` 可替换可信默认 pack 根，
  source ID 不变；`SA_EXTRA_SOURCES_STRICT=false` 只允许忽略失败额外源，不能放宽内容规则。
- **校验与失败**：缺 `course`、README、`_templates/`、`_inbox/` 按既有 eligibility 跳过。默认 pack 根不可读、
  解析后无可检索文件或构建失败时，有 last-good 就继续服务 last-good；首次无 last-good 则启动失败，
  `SOURCE_LOAD_FAILED`。额外源失败时 strict 模式启动失败，非 strict 模式整源省略；禁止部分提交。
- **兼容、隐私与阈值**：合法的 M0–M5 笔记行为不变；获准实施时只收紧显式非法枚举的兼容回退。
  错误只记录 source ID、logical URI、错误码和计数，不记录正文或绝对路径。默认 pack 不得被静默截断或变成
  空集合，默认 90 题集合须在保护基线中复验。
- **证据**：`docs/standards/runtime-contracts.md` §1、`platform/app/source_policy.py`、
  `tests/M6_crawler/test_ingest_gate.py`、`tests/regression/test_runtime_contracts.py`。
- **责任人 / 日期**：justtodo123 / 2026-08-25（用户逐项确认）。

#### M6A-IDENTITY

- **状态 / 选定值**：`RESOLVED` — `sha256(source_id+logical_uri) v1; portable-casefold-conflict; no-host-paths`。
- **默认与范围**：身份 schema 为 `sa.source.identity.v1`，切块 schema 为 `sa.chunk.markdown-h2.v1`。
  默认 source ID 为 `knowledge-pack`。对外 `logical_uri` 保存发现时大小写并规范为 NFC、POSIX 相对路径；另以
  `NFC(casefold(NFC(logical_uri)))` 作为可移植冲突键。`document_id` 和 `chunk_id` 使用现有候选 SHA-256 公式的
  32 个十六进制字符；fingerprint、revision、generation 的职责保持分离。
- **允许覆盖**：额外源必须显式提供匹配 `^[a-z][a-z0-9-]{1,62}$` 的 source ID。`knowledge-pack`、
  `crawler-candidates` 以及所有以 `user-` 开头的值均为保留命名空间。不得用绝对路径、mtime 或查询串派生 ID；
  schema 公式变更必须 bump version 并全量失效。
- **校验与失败**：绝对/UNC/盘符/越界/控制字符/非 Markdown URI 拒绝。任一源内出现 case-fold 冲突时拒绝该
  候选源 generation，不以“排序后第一份”消歧。manifest 同时保存每个截断 ID 的完整 preimage digest；同一
  截断 ID 对应不同 preimage 时以 `SOURCE_IDENTITY_CONFLICT` 拒绝整源，不自动加盐或重编号。
- **兼容、隐私与阈值**：默认 pack 公开 `file` 继续为 `knowledge/{logical_uri}`；内部 ID 重算只触发索引重建。
  `/health.knowledge_root` 保留字段与 string 类型，但值改为逻辑标识 `knowledge-pack`，不得返回宿主路径。
  响应、模型/工具结果、日志和 trace 的宿主绝对路径泄露数必须为 0；1200 chunks 内 ID 冲突必须为 0。
- **证据**：本计划 §2.1、`platform/app/knowledge_index.py::_chunk_id`、`platform/app/models.py`、
  `platform/app/main.py` 的现行 `/health` 差距。
- **责任人 / 日期**：justtodo123 / 2026-08-25（用户逐项确认）。

#### M6A-EXTRA-SOURCES

- **状态 / 选定值**：`RESOLVED` — `SA_EXTRA_SOURCES JSON; DEFAULT_ONLY / DEFAULT_PLUS_EXTRAS scopes`。
- **默认与范围**：未配置时行为与 M5 相同。`SA_EXTRA_SOURCES` 为禁止附加字段的 JSON 数组，每项必须含合法
  `source_id`、本地可读 `root` 和 `human_markdown|web_reviewed`。定义内部检索 scope：公开 Search、QA 和
  QA SSE handler 显式使用 `DEFAULT_PLUS_EXTRAS`；Study Session、Quiz、Review Plan、Review Due、默认评测和
  crawler 固定使用 `DEFAULT_ONLY`，调用方不得依赖全局默认值。scope 必须进入结果 cache key。
- **允许覆盖**：仅允许启动期 `SA_EXTRA_SOURCES` 与 `SA_EXTRA_SOURCES_STRICT`；不提供请求级 scope、运行时
  注册、YAML 或目录自动发现。`SA_KNOWLEDGE_ROOT` 是操作员显式信任的默认 pack 根，即使位于仓库外也继续使用
  `knowledge-pack` 与公开 `knowledge/{logical_uri}`；所有根 realpath 后不得互相包含或重叠。
- **校验与失败**：非法 JSON/schema/source ID/type/root、符号链接越界、根重叠，或 extra 位于仓库生产/测试树、
  `.git`、crawler candidate cache 时，报 `SOURCE_CONFIG_INVALID`。内容失败遵循 strict 策略且不发布部分结果。
  extra 的公开 file 为 `extra://{source_id}/{logical_uri}`，不得回显 root。
- **兼容、隐私与阈值**：不配置 extra 时 API/OpenAPI 和默认集合零变化；公开 Search/QA 只增加既有 sources
  数组中的逻辑出处，不新增必填字段。Study Session 持久化来源中 extra 命中数必须为 0；默认 90 题发现集中
  extra 文件数必须为 0。最多 3 个 extra，具体资源 cap 由 `M6A-SOURCE-LIMITS` 约束。
- **证据**：`platform/app/config.py`、`platform/app/qa.py`、`platform/app/study_session.py` 及本计划 §3 M6a-3。
- **责任人 / 日期**：justtodo123 / 2026-08-25（用户逐项确认）。

#### M6A-CACHE-KEYS

- **状态 / 选定值**：`RESOLVED` — `build-input digest separated from published generation; scoped atomic cache`。
- **默认与范围**：解析/构建缓存使用 `build_input_digest`，只包含 source ID/revision、identity/chunk schema、
  parser version 和 chunk 配置，不包含 generation。向量 key 包含 chunk ID/fingerprint、embedding 模型/维度/
  归一化和 schema。检索结果 key 包含已发布 generation、HMAC query digest、scope、top-k、threshold、course、
  BM25/RRF/vector 配置；默认容量 128。M6a 不缓存 LLM 答案。
- **允许覆盖**：`SA_RESULT_CACHE_SIZE=0..512`，默认 128；0 关闭。非法值启动失败并返回
  `CACHE_CONFIG_INVALID`。mtime 不得作为唯一失效输入。
- **校验与失败**：缺 key、schema 不匹配或解码失败均为 miss，并清理损坏条目。BM25、vector、manifest 先在
  同一 staging generation 完成；结果缓存为该 generation 创建空 namespace，只有 `CURRENT` 成功切换后才可写。
  任一持久存储失败不得发布；旧 generation 结果不得被新请求读取。
- **兼容、隐私与保留**：无向量模型时仍可 keyword-only；`/health.cache_status` 语义保留。缓存仅位于
  `platform/.cache/`，query 使用与 runtime trace 相同的进程内 HMAC 假名化；不缓存答案、用户答案或密钥。
  extra 移除后，成功切换时立即清理所有含该源的未发布缓存和旧结果 namespace；快照正文/向量按
  `M6A-SNAPSHOT-SWITCH` 清理。当前 cap workload 下 cache-hit p95 target ≤20ms，须由准入 benchmark 留证。
- **证据**：`platform/app/knowledge_index.py`、`platform/app/retrieval.py`、`platform/app/vector_store.py` 的现行
  key/mtime/fingerprint 行为，以及本计划 §2.5。
- **责任人 / 日期**：justtodo123 / 2026-08-25（用户逐项确认）。

#### M6A-SNAPSHOT-SWITCH

- **状态 / 选定值**：`RESOLVED` — `staging-validate-atomic; revision-bound reduction confirmation; retain-1`。
- **默认与范围**：BM25、vector 和 manifest 写入 `platform/.cache/index/gen-{n+1}/`；全部 fsync/校验后，以
  `os.replace` 原子更新 `CURRENT`。请求开始时固定 generation，重建期间继续读 last-good。成功发布后通常保留
  一个 `PREVIOUS`；M6a 只做完整快照，不做 M7 的增量 tombstone。
- **允许覆盖**：`SA_INDEX_REBUILD_TIMEOUT_S` 默认 180，范围 30–300 秒；snapshot retain 固定 1。若默认 pack
  chunk 数相对 last-good 减少超过 50%，首次构建以 `SNAPSHOT_REDUCTION_CONFIRMATION_REQUIRED` 拒绝并输出候选
  revision 与逻辑计数；只有重启时设置 `SA_EXPECTED_DEFAULT_PACK_REVISION=<candidate-revision>` 精确匹配才允许
  发布。确认只绑定该 revision，不授权后续删减。
- **校验与失败**：发布前验证身份唯一、无宿主路径、scope 隔离、存储 manifest/checksum 一致和资源 cap。
  校验、timeout、fsync 或 CURRENT 切换失败时删除 staging、保留 last-good，报 `SNAPSHOT_SWITCH_FAILED`；首次
  无 last-good 则启动失败。结果缓存只在切换后启用新 namespace。
- **兼容、隐私与保留**：学习状态 SQLite、review history 和旧 session 不参与切换。若新配置删除 extra source，
  新 generation 成功后立即删除所有含该 source ID 的 staging、构建缓存和 `PREVIOUS`；该次允许无 PREVIOUS，
  不为回滚保留已撤下源正文或向量。其他情况下只保留一个 PREVIOUS，更旧和失败 staging 在启动/切换后清理。
- **workload / 阈值**：keyword 重建 target ≤15s，本地模型已缓存的向量重建 target ≤180s；重建期间有
  last-good 时空结果响应数必须为 0。目标须按 `M6A-SOURCE-LIMITS` 的固定 benchmark 留证。
- **证据**：本计划 §2.5、§3 M6a-3，以及 `platform/app/vector_store.py::replace_all/is_synced` 的现行差距。
- **责任人 / 日期**：justtodo123 / 2026-08-25（用户逐项确认）。

#### M6A-SOURCE-LIMITS

- **状态 / 选定值**：`RESOLVED` — `per-source plus aggregate caps; fail-whole-default-pack; measured targets`。
- **默认上限**：

  | 资源 | 每源默认 | 聚合默认 | 可配置硬顶 |
  | --- | ---: | ---: | ---: |
  | Source 数 | — | 1 默认 + 3 extra | 固定 4 |
  | Markdown 文件 | 250 | 500 | 500 / 1000 |
  | 源总字节 | 4 MiB | 8 MiB | 8 MiB / 16 MiB |
  | chunks | 600 | 1200 | 1000 / 2000 |
  | 单文件 | 256 KiB | — | 512 KiB |

- **允许覆盖**：分别使用 `SA_SOURCE_MAX_FILES_PER_SOURCE/TOTAL`、`SA_SOURCE_MAX_BYTES_PER_SOURCE/TOTAL`、
  `SA_SOURCE_MAX_CHUNKS_PER_SOURCE/TOTAL` 和 `SA_SOURCE_MAX_FILE_BYTES`；必须为正整数、每源值不大于 total、
  且不超过表中“每源 / 聚合”硬顶。非法配置启动失败，`SOURCE_CONFIG_INVALID`。
- **校验与失败**：在解析后、发布前同时检查逐源和聚合 cap，不静默截断。默认 pack 任一文件/源/聚合 cap
  超限都拒绝整个候选 generation并保留 last-good；首次无 last-good 启动失败，`SOURCE_LIMIT_EXCEEDED`。
  extra 超限拒绝整源并遵循 strict 策略。错误只含 source ID 和逻辑计数。
- **兼容、隐私与 workload**：当前默认 pack 应低于默认 cap，但 Codex 的 142 文件/261730 B/约 688 sections
  只作为待复现实测的观察值，不是准入证据。准入 benchmark 固定到待实施 revision：Windows、8 GiB RAM、
  本地 SSD、单进程；以达到默认聚合 cap 的默认+合成 extra workload 跑 5 次冷启动，keyword 每次 ≤15s、已缓存
  embedding 模型的 vector 每次 ≤180s；至少 200 个固定查询测 Search p95 ≤200ms、cache-hit p95 ≤20ms。
  记录命令、revision、硬件、样本和原始 JSON。1k–3k workload 留给 M7。
- **证据**：`docs/standards/runtime-contracts.md` §2、M7 计划的规模边界及 Codex 2026-08-25 观察记录。
- **责任人 / 日期**：justtodo123 / 2026-08-25（用户逐项确认）。

#### M6A-WORKER-TOPOLOGY

- **状态 / 选定值**：`RESOLVED` — `strict single service process / single uvicorn worker`。
- **默认与范围**：M6a 只支持一个服务进程和一个 worker；不提供 `SA_INDEX_READONLY` 或第二只读进程。
  服务进程在整个生命周期持有 `platform/.cache/index/service.lock`；generation 发布另用同进程互斥，避免线程/
  task 重入。`--reload` 的 watcher 不算服务进程，实际 app 子进程获取 lifetime lock，重启交接最多等待 5 秒。
- **允许覆盖与失败**：`WEB_CONCURRENCY`、`UVICORN_WORKERS` 或受支持启动器的 worker 值必须为 1；大于 1、
  检测到第二服务进程、5 秒内无法取得 service lock，均启动失败并报 `WORKER_TOPOLOGY_UNSUPPORTED`。
  不允许“拿不到锁但只读服务”。文档和 `tools/start_local.py` 只提供单 worker 命令。
- **兼容、隐私与阈值**：现有本地启动、测试和评测均为单进程，行为不变；不引入 broker、worker 或外部服务。
  lock 只含 PID、随机 nonce 和启动时间，不含源路径或正文；并发 publisher 数必须为 1。多 worker 吞吐和 p95
  不属于 M6a 承诺。
- **证据**：`tools/start_local.py`、`platform/README.md` 及 `platform/app/retrieval.py` 的进程内缓存模型。
- **责任人 / 日期**：justtodo123 / 2026-08-25（用户逐项确认）。

#### M6A-TRACE-RETENTION

- **状态 / 选定值**：`RESOLVED` — `runtime_trace separate; memory-1000; opt-in 7d/8MiB JSONL`。
- **默认与范围**：新观测数据统一命名 `runtime_trace`，不得称为或写入 M5 持久化 `tool_trace`；状态机的
  domain events 保持原语义。默认 `SA_TRACE_SINK=memory`、ring 容量 1000。允许字段仅为 operation/status/
  duration/error/side-effect/generation/cache-hit 和假名化后的 correlation/source/document/chunk/query 标识；禁止
  正文、答案、prompt、Thought、密钥、原始 query 和绝对路径。
- **假名化与覆盖**：进程启动时用 OS CSPRNG 生成不落盘的 HMAC-SHA256 key，标识截取 128 bits；同一进程内
  可关联，跨重启不可关联。`SA_TRACE_SINK=memory|jsonl|off`；memory max 100–5000。jsonl 默认 7 天/8 MiB，
  可配 1–30 天、上限 32 MiB，最多 2 个轮转文件，固定写入 `platform/.cache/traces/runtime-trace.jsonl`。
- **校验与失败**：非法 sink/range/path 启动失败，`TRACE_CONFIG_INVALID`。目录/文件以 0700/0600 请求创建并
  继承当前用户 ACL，禁止符号链接和 cache 外路径。序列化前 allowlist；redaction 失败丢弃事件并增加
  `trace_redaction_failed_total`。运行期写入、轮转或删除失败时立即禁用本进程磁盘 sink，继续 memory ring，并
  增加 `trace_sink_disabled_total`；不得因审计 IO 终止学习服务。
- **兼容、隐私与阈值**：现有 `log_operation()` 字段和 `/health` 聚合样本保留；不改变 session、review history
  或公开 API。默认磁盘 trace 字节数为 0；opt-in 最长 30 天/32 MiB/2 rotations；密钥、正文、答案和宿主路径
  落盘条数必须为 0。trace 不提交 Git、不发送外部服务。
- **证据**：本计划 §2.5、`platform/app/observability.py`、`docs/standards/runtime-contracts.md` §4，以及现有
  persisted `tool_trace` 契约。
- **责任人 / 日期**：justtodo123 / 2026-08-25（用户逐项确认）。

## 1. 背景与边界

M0–M5 已形成可离线运行的学习闭环：OS/DS/CO 三课 60 篇课程条目、默认 90 题评测、FastAPI
学习会话状态机、SQLite 持久化和工作台。现有代码仍以具体服务之间的直接调用为主，M6a 先收敛
契约，再做薄适配，不能用抽象破坏已经冻结的 API 和状态机。

`tools/crawler/` 与 `tests/M6_crawler/` 已存在，但 crawler 还不是完整 Source 生命周期。它在 M6a
开工前单独收口：只生成候选 Markdown，经过人工审核和显式目录配置后才可进入知识源；不得自动改变
默认 `knowledge/` 或默认三课 90 题评测。持久化源注册、增量同步、删除传播、多源隔离和千级索引留给 M7。

### 1.1 阶段目标

1. 定义与现有实现一致的职责契约，不先创建泛化的“一统 Store”或一次性 Runner。
2. 将现有学习状态机、确定性检索/测验/复习服务包装为可测试的适配边界。
3. 支持启动期配置的额外 Markdown 源，同时保持默认源和 API 行为不变。
4. 固化 crawler 的依赖、测试、CI 和人工审核边界。

### 1.2 非目标

- 不实现 ReAct、Function Calling、Agent preview 或自主 Runner；
- 不新增 `SA_RUNNER=react`，不改变 `/api/v1/study-sessions` 的执行路径；
- 不把 `SqliteLearningStore` 改写成向量、文档或源注册的总 Store；
- 不做用户源持久化注册、增量同步、删除、UI 或 1k–3k chunk 优化；
- 不把 crawler 输出自动写入默认知识包或扩大默认评测集合；
- 不引入新的外部存储依赖。

## 2. M6a-0：契约收敛与开工门禁

先写契约说明和 contract tests，再实现适配器。四类边界如下：

### 2.1 Source

Source 至少描述 `source_id`、`source_type`、source/document/chunk 的稳定命名空间、logical URI、
内容 fingerprint、revision，以及未来的删除/失效语义。下列内容是 §0.4 已闭合身份政策的契约摘要：

- `source_id` 是逻辑命名空间，不直接使用本机挂载目录或绝对路径；移动本地目录不改变对外身份；
- `logical_uri` 是 Source 内可移植的文档地址；不同 Source 中相同相对路径不得冲突；
- `document_id` 由 `source_id + logical_uri` 稳定派生；
- `fingerprint` 表示规范化文档内容，`revision` 表示 Source 快照；两者职责不可混用；
- `chunk_id` 由稳定 `document_id`、确定性 chunk key 和 chunking schema version 派生，切块规则升级可显式失效旧 ID。

M6a 的 `MarkdownPackSource` 只在启动时读取默认 `knowledge/` 和显式配置的额外目录。绝对路径只允许留在
受控本地配置，不得出现在 API 响应、模型/工具结果、日志或 trace 中。

### 2.2 存储职责

不要使用原计划中混合会话和向量的 `Store`。按职责记录以下边界：

- `LearningStateRepository`：复用现有 `StudySessionRepository` / `SqliteLearningStore`，负责会话、答题、
  掌握度和恢复所需的控制状态，不复制已有持久化；
- `ReviewRepository`：复用现有 `ReviewHistoryRepository`、`ReviewHistoryRepositoryAdapter` 与 SQLite 实现，
  负责复习历史和待复习查询；
- `SourceRegistryRepository`：M7 才负责持久化用户源注册；M6a 仅保留启动配置；
- `RetrievalIndex`/`VectorStore`：检索索引和向量生命周期；复用现有 `VectorStore` 协议及实现，
  不把 LanceDB/Qdrant 写成学习状态存储。

新增协议只能按这些职责适配现有实现，不得复制数据库表、形成平行仓储或重新引入承载所有领域数据的泛化 Store。

### 2.3 Tool

Tool 使用 `ToolContext`（learner、source namespace、权限、取消/预算和 correlation ID）和结构化
`ToolResult`（数据、来源、错误码、是否可重试、trace 元数据）。参数使用 JSON Schema；工具明确标记
read-only、idempotent 或具有副作用。M6a 适配确定性服务，领域写入仍由 `StudySessionService` 和领域
服务控制；工具存在不等于允许 Agent 调用。

### 2.4 Runner

Runner 必须表达跨请求生命周期，而不是只有 `run(context)`：至少定义 `start`、`resume/get` 和
`step(event)`（或等价的状态快照、等待输入、取消、错误和副作用语义）。`StateMachineRunner` 是当前
正式路径的薄包装；`StudySessionService` 仍是状态转换、答案评估、持久化和 review-log 的唯一领域权威，
适配器不得建立第二套状态机。M6b 不消费它来替换正式 API，也不得在 preview 失败时把它作为无条件回退；
完整自主 Runner 留给 M10。

### 2.5 缓存、索引与可见性

索引/缓存键和失效输入必须显式覆盖 Source identity、revision/fingerprint、解析与切块 schema version、
检索配置，以及 embedding 模型/维度。额外 Source 加载失败时保持默认 pack 的上一完整快照；禁止把部分加载
结果与默认索引混合提交。完整快照替换后必须移除 stale BM25、vector 和 result-cache 数据。

同一工具执行结果分三层表达：

1. **用户响应**：保留兼容字段和安全、可解释的出处；
2. **模型/工具可见结果**：限量内容、logical identity 与授权范围内 metadata，不含宿主机绝对路径；
3. **audit trace**：只记录 correlation ID、稳定逻辑 ID、状态、耗时、错误码和副作用分类等安全元数据。

现有状态机的 `domain_trace` 与未来 preview 的 `agent_trace` 分离，不把知识正文、用户答案或密钥复制到 trace。

## 3. 子阶段

### M6a-P0：crawler 前置收口

任务：

- 登记 `tools/crawler/`、`tests/M6_crawler/` 及 `tools/crawler/requirements.txt`；
- 明确 fetch/clean/convert/dedup/pipeline 的输入输出、依赖安装和离线/在线边界；
- 已落地独立 marker `m6_crawler`、CI job `crawler-offline` 和 mock HTTP 夹具；在线 smoke 仅显式启用；
- 明确候选 Markdown 必须经人工审核、显式目录配置后才入源；默认 pack 和默认评测不受影响。

退出条件：✅ crawler 阶段测试可独立运行（`m6_crawler and not online`），依赖和 CI job `crawler-offline` 已文档化，且不被宣称为 M7 Source 生命周期。

### M6a-1：协议与契约测试

- 创建 `platform/app/protocols.py`，定义 Source、职责拆分后的存储边界、Tool、Runner 数据类/协议；
- 定义 `SourceChunk`、`ToolContext`、`ToolResult`、`RunnerContext`、`RunnerResult`；
- 协议层不导入业务实现；
- 覆盖结构化错误、权限/副作用标记、source/chunk ID 稳定性和跨请求状态契约。

### M6a-2：现有服务适配

- 创建 `platform/app/tools/`，提供 Retrieve、Quiz、ReviewDue 等确定性适配器；
- ReviewLog 若保留为领域服务适配，必须标为写工具，不能进入 M6b preview allowlist；
- `StudySessionService` 保持直接、类型安全的领域调用，不强制通过通用 Tool envelope；
- 创建 `platform/app/runners/state_machine.py`，包装现有状态机而不改变 API schema。

### M6a-3：启动期静态额外源

- 创建 `MarkdownPackSource`，包装现有索引能力；
- 通过 `SA_EXTRA_SOURCES` 注册额外 Markdown 目录；
- 为额外源生成不冲突的 source/document/chunk ID，并在 Search/QA 结果中以兼容方式附加 source metadata；
  现有公开 `file` 字段继续保留；
- M6a 的额外 Source 只传播到 Search/QA 及 QA 提供的安全出处，不自动改变 Quiz、Review Plan、默认评测或
  crawler 注册；
- 不持久化注册、不做运行时同步/删除、不泄露外部绝对路径；默认无额外源时与 M5 一致；
- 静态 Source 重建采用完整快照替换并清理 stale BM25、vector 和 result-cache 数据。M6a 只承诺这种
  重建清理；运行时 delete API、tombstone、增量删除传播和生命周期历史属于 M7。

### M6a-4：文档与收口

同步 `platform/README.md`、`docs/PLAN.md`、`docs/plans/README.md` 和 `tests/TEST_PLAN.md`。完整验收顺序：

```text
tests/M6_crawler/
  → tests/M6a/
  → tests/M0_M2/ + tests/regression/ + platform/tests/
  → 默认 OS/DS/CO 90 题离线 RAG 评测
  → API/OpenAPI/链接检查 → 人工审查
```

## 4. 测试与验收门禁

新增测试放在 `tests/M6a/`，不修改 M0–M5 存量测试，至少覆盖：

- 协议 contract tests、旧会话恢复、`start/resume/step` 生命周期；
- ToolContext、JSON Schema 参数、结构化错误和写工具拒绝；
- 多 source ID 不冲突、revision/fingerprint、额外源 Search/QA 检索融合；
- 缓存与索引失效覆盖 Source/revision/fingerprint、解析/切块版本、检索配置、embedding 模型与维度；
  加载额外源失败不得污染默认 pack，完整快照替换必须清理 stale 索引与结果缓存；
- 验证额外源不自动进入 Quiz、Review Plan、默认评测或 crawler 注册；
- 默认 API/OpenAPI 契约不变，现有 `file` 字段兼容，外部绝对路径不出现在响应、模型/工具结果、日志或 trace；
- 默认评测发现集合仍为 OS/DS/CO 共 90 题，Network 扩展集不自动加入；
- crawler 依赖/测试可复现，候选产物不自动污染默认知识包。

退出条件：M6a 测试和回归通过；默认三课 Recall@3 不退化；正式学习状态机仍是唯一当前 Runner；文档
与实现边界一致。M6a 退出证据只是 M6b 与 M7 的共同必要前置；两阶段仍须分别完成各自决策、专属保护基线和负责人批准，彼此不构成前置。M6b 是独立只读 preview，不是正式 Runner 替换。

## 5. 代码结构与配置规划

```text
platform/app/
  protocols.py
  tools/                 # 确定性工具适配器；写工具单独标记
  runners/state_machine.py
  sources/markdown_pack.py

tests/M6_crawler/       # crawler 前置收口（既有目录）
tests/M6a/               # 契约、适配器、Runner、Source
```

计划配置：`SA_EXTRA_SOURCES` 只表示启动期静态目录列表。crawler marker、独立依赖和 CI 安装是 M6a-P0
实施项；在实际配置落地前不得宣称已完成。

## 6. 风险与拟定方向（不得替代强制决策）

下表只是风险备忘。八项强制决策的最终选定值和约束以 §0.4 为准。

| 风险 | 决策 |
| --- | --- |
| 抽象层破坏已有状态机 | 先做契约测试，适配器保持薄，`StudySessionService` 仍为领域权威 |
| Store 边界继续混淆 | 学习状态、复习、源注册和检索索引分责，复用现有实现 |
| crawler 污染默认 pack | 候选产物须人工审核并显式注册，默认评测集合固定 90 题 |
| 额外源 ID 或路径泄露 | 稳定 namespace/逻辑 URI；绝对路径只留在受控本地配置；用户/模型/audit 三层可见性 |
| 快照替换残留 stale 数据 | 失效键覆盖 Source/解析/检索/embedding 输入；原子替换并清理 BM25/vector/result cache |
| 静态额外源意外扩散 | M6a 仅接 Search/QA，不自动改变 Quiz、Review Plan、默认评测或 crawler 注册 |
| M6b 误用写工具 | 工具记录副作用分类，preview 另有只读 allowlist |

## 7. 分支、提交与下一步

```text
feature/m6a-harness-skeleton
```

建议提交：crawler 收口、协议与 contract tests、适配器与 StateMachineRunner、静态 Source、文档与回归。
不自动 push、不修改历史。M6b 与 M7 均以 M6a 退出证据为共同必要前置，并在各自准入、专属保护基线和批准闭合后独立推进，彼此不互为前置；完整自主 Runner、写工具、checkpoint/幂等和 Agent 评测依赖 M7–M9 后在 M10 实现。

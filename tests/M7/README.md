# M7 阶段测试

本目录覆盖已授权、但仍处于 `ADMITTED / IN_PROGRESS` 的 M7 基础设施局部实现：M7-1 Source Registry，
不接入应用运行时的单源 FULL 构建链，source-local FULL/INCREMENTAL sync worker、已冻结的 source-local delete/isolation 合同，source-local FTS5/offline fail-closed 校验与显式 FULL repair，以及 generation-bound source-local vector 与 FTS5 identity-set 合同。

- `sa.source.lifecycle.v1` 显式 schema 与未来版本 fail-closed；
- `user-{UUIDv7}` 稳定身份和 owner-only 控制面读取；
- 生命周期 16 条合法边、`DELETED` 终态与 expected-version CAS；
- `SourceRecord`、不可变 `SourceRevision`、`SyncRun`、`LifecycleError` 与 append-only `AuditEvent`；
- 表/列/约束/索引/trigger/foreign-key schema manifest fail-closed；
- 100 组独立 registry/service 双写竞争，每组恰好一次成功与一次版本冲突；
- 五类 lifecycle record 各 20 条重启读取与 canonical JSON round-trip；
- 三个事务故障点各 20 次零部分提交，以及正文、secret、Windows/POSIX/UNC 路径 canary；
- `sa.source.manifest.v1` 文件级 canonical manifest、URI/身份/格式校验、文本与二进制 fingerprint、
  接纳计数及路径隐私；
- `sa.source.parser-matrix.v1` 的五格式冻结 parser contract、格式探测、依赖版本 fail-closed 与无正文错误；
- `sa.source.normalized-document.v1` 的跨格式 unit、稳定 chunk identity、canonical digest 与受管 staging；
- source-local FULL candidate 的 revision 绑定、校验和、`CURRENT`/`PREVIOUS` convenience pointers、
  idempotent repeat、失败降级、last-good 保留及 registry 失败不推进指针；
- `sa.source.sync.v1` 的 request/run 幂等、单 active run、`SOURCE_SYNC_BUSY`/`REQUEST_CONFLICT`、
  无变化与 added/modified/removed INCREMENTAL、cancel-before-publish、发布中不可伪报取消、
  checkpoint 恢复与 input-changed 中断、瞬时错误重试/耗尽；
- `sa.source.delete.v1` 的删除命令 CAS、`DELETE_PENDING` 读屏障、文件级 tombstone、
  BM25/vector/result-cache/provenance 不可读传播、幂等 request_id、并发 VERSION_CONFLICT、
  故障恢复、30 天保留后 hard-delete receipt，以及派生 provenance 的 `STALE_DERIVATION`；
- `sa.source.isolation.v1` 的服务端 principal 授权快照、查询前过滤、统一 `SOURCE_NOT_FOUND`、
  缺 source_id/授权 digest 时 `SOURCE_ISOLATION_UNAVAILABLE`、默认 pack 直通与零越权；
- `sa.source.fts5-tokenizer.v1` 的 `jieba==0.42.1` search-mode 预分词、NFC/空白规范化、generation-bound SQLite FTS5 unicode61 索引与 identity-set；
- `sa.source.offline-fallback.v1` 的依赖/metadata/索引完整性 fail-closed、不自动修复与显式 FULL repair；
- Search/QA 可选 `principal_id` overlay：隔离后 FTS5+vector、auth/generation 缓存、跨源 RRF 与 `user://` provenance；preview/quiz/sessions 不含用户源。
- `sa.source.vector.v1` 的 generation-bound source-local vector：绑定 source_id/revision/generation/embedding/chunk policy 与 identity-set；与 FTS5 chunk_id 集合 100% 一致；缺 metadata、generation/模型/identity 不一致或 vector 未附着时用户源 fail closed，不回退默认包 keyword-only。
- 协议内热路径复用：已校验 generation 的 FTS5/vector runtime、snapshot chunk 缓存与隔离批处理；热缓存后 identity 被篡改仍 fail closed。`tests/M7/` 当前 205 项。冻结 20 次 1k/3k BGE 仍不是本目录的通过条件。
- M7-3 已合并：冻结 1k/3k BGE runner 与 2026-09-04 失败证据。hash smoke 不是冻结证据。
- M7-4：完整冻结 1k/3k BGE 已通过（1k RSS 768 MiB 授权）。报告 `m7_exit=true` 不是自动 M8 开工。
- M7-5：READY 提交后 CURRENT 激活失败保持 registry 权威；删除按 intent 捕获的 generation 发布 tombstone；receipt 后故障可恢复终态；相同 FULL 重试修复指针且不得降级。不是 M7 exit。
- M7-2：manifest-bound snapshot cache。已发布 FULL snapshot 绑定 `source_id/generation/source_fingerprint/manifest_digest`；无变化重复 FULL 不得因 `created_at` 改写 digest 或新增 revision；进程内 LRU 上限 16；磁盘 identity 损坏 fail-closed。不覆盖冻结 BGE、Network 或 preview 用户源。

测试 fixture 仅在运行时以 `tmp_path` 生成；不会读取或复制 `D:\111_Others_Subjects`，也不会提交 PDF、PPTX、DOCX
等二进制文件。sync 套件使用合成 Markdown parser fixture，不构成真实五格式 parser 成功。

FULL/INCREMENTAL、delete/isolation、FTS5/offline 与 generation-bound vector 仍是 source-local 工件；Search/QA 可通过可选 `principal_id` 叠加授权用户源。
M6b preview、Quiz、Review Plan 与 study-sessions 不包含用户源。`CURRENT` 仅为本地便利指针，权威 published generation 仍由 lifecycle 的 immutable revision
决定。本套件与 disposable 1k/3k 证据不构成 M7 exit；冻结 20 次 BGE 协议已通过，但报告 `m7_exit=true` 不是自动 M8 开工。

M7-2 测试矩阵（`test_full_snapshot.py` 增量，不是 M7 exit）：

| 用例 | 通过标准 |
| --- | --- |
| 无变化重复 FULL 忽略 volatile `created_at` | 同 generation、同 `manifest_digest`、revision=1 |
| snapshot 缓存有界 | `len(cache) <= 16`，当前 generation 仍可加载 |
| 磁盘 identity 损坏 fail-closed | SHA256/identity 不一致不得当作已发布 snapshot |
| 既有 FULL last-good / 指针 / 失败降级 | 原 4 项不回退 |

M7-2 退出清单：上述矩阵全绿；既有 `tests/M7/` 不回退；不声称 M7 exit、不批准 Network、不扩大默认 90 题。

M8/Milvus、M9、M10 与 Network 晋升仍不在本阶段范围内。

运行命令：

```bash
PYTHONPATH=platform ./platform/.venv/Scripts/python -m pytest tests/M7/ -v
PYTHONPATH=platform ./platform/.venv/Scripts/python -m pytest -m m7 -v
```

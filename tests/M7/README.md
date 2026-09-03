# M7 阶段测试

本目录覆盖已授权、但仍处于 `ADMITTED / IN_PROGRESS` 的 M7 基础设施局部实现：M7-1 Source Registry，
不接入应用运行时的单源 FULL 构建链，source-local FULL/INCREMENTAL sync worker、已冻结的 source-local delete/isolation 合同，以及 source-local FTS5/offline fail-closed 校验与显式 FULL repair。

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
- `sa.source.offline-fallback.v1` 的依赖/metadata/索引完整性 fail-closed、不自动修复与显式 FULL repair。

测试 fixture 仅在运行时以 `tmp_path` 生成；不会读取或复制 `D:\111_Others_Subjects`，也不会提交 PDF、PPTX、DOCX
等二进制文件。sync 套件使用合成 Markdown parser fixture，不构成真实五格式 parser 成功。

FULL/INCREMENTAL、delete/isolation 与 FTS5/offline 链路仅产生内部 source-local 工件，未接入 `app.main`、Search、QA、preview、默认/extra scope、
公开 API 或 OpenAPI。`CURRENT` 仅为本地便利指针，权威 published generation 仍由 lifecycle 的 immutable revision
决定。缺失或版本不精确的 parser/jieba 依赖会 fail closed；本套件不构成正式检索接入、1k/3k benchmark 或 M7 exit 证据。

M8/Milvus、M9、M10 与 Network 晋升仍不在本阶段范围内。

运行命令：

```bash
PYTHONPATH=platform ./platform/.venv/Scripts/python -m pytest tests/M7/ -v
PYTHONPATH=platform ./platform/.venv/Scripts/python -m pytest -m m7 -v
```

# M7 阶段测试

本目录只覆盖已授权的 M7-1 Source Registry 基础设施：

- `sa.source.lifecycle.v1` 显式 schema 与未来版本 fail-closed；
- `user-{UUIDv7}` 稳定身份和 owner-only 隔离；
- 生命周期 16 条合法边、`DELETED` 终态与 expected-version CAS；
- `SourceRecord`、不可变 `SourceRevision`、`SyncRun`、`LifecycleError` 与 append-only `AuditEvent`；
- 表/列/约束/索引/trigger/foreign-key schema manifest fail-closed；
- 100 组独立 registry/service 双写竞争，每组恰好一次成功与一次版本冲突；
- 五类 lifecycle record 各 20 条重启读取与 canonical JSON round-trip；
- 三个事务故障点各 20 次零部分提交，以及正文、secret、Windows/POSIX/UNC 路径 canary。

`SyncRun` 与 `LifecycleError` 当前仅为持久化控制面骨架，不表示 sync worker、重试调度或错误恢复已实现。
本阶段不覆盖 Network 31 篇晋升、parser/sync/index/delete propagation 生产链路、M8/Milvus、M9 或 M10。
运行命令：

```bash
./platform/.venv/Scripts/python -m pytest tests/M7/ -v
./platform/.venv/Scripts/python -m pytest -m m7 -v
```

# 应用组合层（platform/app/）

本目录是 FastAPI 应用、RAG/学习领域服务、用户源生命周期和 Runner 的生产代码。

## 配置与应用构造

- `config.py` 提供冻结的 `Settings` 与 `load_settings()`。普通 import 不再隐式读取 `.env`；调用方只有显式传入
  `dotenv_path` 才读取 dotenv，显式环境映射优先。
- `main.py` 提供 `create_app(settings)`，每个 FastAPI 实例独占 `app.state.services` 中的 `RuntimeServices`。
- `main.py` 仍导出 `app = create_app()`，保持 `uvicorn app.main:app` 兼容。
- Preview 与 Runner 继续由 Settings 在应用构造时决定是否注册；默认 OpenAPI 中结构性不存在。
- module-level `_qa`、`_study_sessions` 等只作过渡兼容，新测试和调用方应使用 `app.state.services`。

本地一键启动由 `tools/start_local.py` 显式读取 `platform/.env`；直接使用 uvicorn 时，如需 dotenv，应执行：

```bash
uvicorn --env-file .env app.main:app --workers 1
```

## 主要模块

- `main.py`：composition root、API 路由和应用生命周期。
- `combined_snapshot.py` / `snapshot_publisher.py`：默认包和额外源的不可变检索快照。
- `retrieval.py` / `qa.py`：多路召回与带出处问答。
- `goal_planner.py` / `plan_lifecycle.py`：目标驱动计划和计划状态。
- `source_registry.py` 及用户源模块：M7 生命周期、隔离、索引和离线修复。
- `runner_service.py` 及 Runner 模块：M10 默认关闭的受控写与恢复链。

更完整的 API、配置和运行说明见 [`platform/README.md`](../README.md)。

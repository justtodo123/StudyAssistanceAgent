# M6b 测试

本目录验证默认关闭、只读 Agent Preview 的阶段隔离契约。默认测试只使用本地 fake provider，禁止网络访问，
不要求 Anthropic API key；真实 provider smoke 不属于默认门禁。
检索类 fixture 与 blocking benchmark 均显式关闭向量路，固定 BM25，不依赖本机是否安装 embedding 模型。
2026-08-28 首轮为 111 项；当前 stabilization 收集 129 项，其中普通套件 126 项、专用 benchmark 3 项。

当前覆盖：

- `ToolRegistry` 显式 allowlist、strict schema、本地双重校验与结果投影；
- Anthropic adapter 的 provider-neutral 请求、原生 content block、完整 replay、usage 与安全错误映射；
- bounded native tool loop、call ID、retry、timeout、取消、预算、重复调用和稳定终止语义；
- 独立默认关闭路由、Bearer 认证、容量限制、OpenAPI/422 错误净化与配置收紧规则；
- 隐私边界、HMAC trace、正式学习状态零写入以及 `DEFAULT_PLUS_EXTRAS`/`DEFAULT_ONLY` scope 隔离；
- 20 次 warm-up、200 次 measured、并发 2 的 blocking 离线 p95 benchmark。

## 执行

```bash
PYTHONPATH=platform SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ./platform/.venv/Scripts/python -m pytest tests/M6b -m "not m6b_benchmark" -q --tb=short
```

阻断 benchmark 独立使用 `m6b_benchmark` marker；普通套件不会隐式运行它：

```bash
M6B_BENCHMARK_EVIDENCE_ID=stabilization-20260829-XX \
M6B_BENCHMARK_REPORT=.tmp-test/m6b-offline-preview-benchmark-stabilization-20260829-XX.json \
PYTHONPATH=platform SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ./platform/.venv/Scripts/python -m pytest tests/M6b -m m6b_benchmark -q --tb=short
```

记录型 benchmark 必须提供安全的 `M6B_BENCHMARK_EVIDENCE_ID`；报告文件名必须包含该 ID，并以 exclusive-create
方式写入，已存在的目标不会被覆盖。CI 使用 `${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}` 作为 ID、报告文件名和
artifact 名。报告只包含脱敏统计、workload/snapshot digest、termination/replay 结果和 evidence identity。
`collect-only` 只能确认收集结果，不能代替测试通过。M6b 已在全部 closeout 门禁与本轮稳定化验证通过后保持
`ADMITTED / COMPLETE`。后续 M7 当前为 `ADMITTED / IN_PROGRESS`，其 Source Registry、manifest/parser、normalized document、source-local FULL/INCREMENTAL sync 与 delete/isolation 局部合同已冻结且独立实施；该状态变化不修改本目录的 M6b 行为、测试或 closeout 证据。

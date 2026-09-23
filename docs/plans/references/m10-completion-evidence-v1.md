# M10 完成证据汇总 v1

> 状态：`ADMITTED / IN_PROGRESS`；本文件汇总技术退出证据，不构成 `completion_approval`。
> M10 的独立完成批准仍需由负责人明确批准；批准前不得修改阶段登记表的 `delivery_status`。
> 汇总日期：2026-09-23。

## 一、范围与前置

- 阶段范围：`m10-autonomous-runner-v1`。
- M7、M8、M9 三项前置：均为 `SATISFIED`。
- M10 十一项强制 Decision：全部 `RESOLVED`。
- 已完成实施步骤：§5 步骤 1–7。
- 明确排除：M11 数据扩展、M12 云部署、多 worker 拓扑、M8 backend selection、真实 10K/100K 数据。
- 正式默认仍为 `StudySessionService` 状态机；Runner 为显式可选路径，默认关闭。

## 二、七项退出条件证据

### 1. 权威边界与写授权闭合

**判据**

- 正式学习状态仍由领域服务/学习状态仓储负责。
- Runner 只拥有 job、checkpoint、EffectLedger 状态。
- 写 allowlist 与只读 preview allowlist 不相交。
- capability、scope、confirmation token、撤销和追加式摘要审计均 fail closed。
- 越权调用不产生领域副作用。

**证据**

- `platform/app/runner_authority.py`
- `platform/app/effect_ledger.py`
- `platform/app/runner_service.py`
- `tests/M10/test_authority_boundary.py`
- `tests/M10/test_write_authorization.py`
- `tests/M10/test_runner_service.py`
- `tests/M9/test_mastery_write_authority.py`

**结果**

- 动态源码枚举确认正式领域表写入者仍为 `learning_store.py`。
- M10 模块不导入领域仓储、不引用领域写方法。
- Runner 写入只经已批准的 `log_review` 领域服务路径。
- Arm A 越权率为 `0`，并带有真实非空探针。

### 2. Checkpoint、幂等和 EffectLedger 闭合

**判据**

- Runner 使用独立 SQLite 文件，不触碰学习状态库。
- effect 状态按 `proposed → authorized → pending → applied/failed/compensated` 约束跃迁。
- `pending` 必须先于领域写入。
- 幂等键由 job/tool/参数摘要/scope 派生。
- 同键重放复用已记录结果；同键不同参数稳定冲突。
- checkpoint 按 job 单调编号，不使用时间 checkpoint。

**证据**

- `platform/app/effect_ledger.py`
- `platform/app/runner_authority.py`
- `platform/app/runner_recovery.py`
- `tests/M10/test_effect_ledger.py`
- `tests/M10/test_recovery.py`
- `tests/M10/test_write_authorization.py`

**结果**

- 独立台账、版本化 meta、非法跃迁、参数/结果原文不落库均有测试。
- replay 不重复领域写入。
- crash window 中 `pending` 顺序和恢复分类均有行为化断言。

### 3. Recovery、reconcile、补偿和人工介入闭合

**判据**

- 十个单进程 crash point 均有预期终态。
- `proposed/authorized` 不盲目重放。
- `pending` 只由领域对账判定，不猜测。
- unknown 结果 defer，不伪造 applied/failed。
- poison effect 停止 job；不可补偿失败进入人工介入终态。
- reconcile 重复执行无额外副作用。

**证据**

- `platform/app/runner_recovery.py`
- `platform/app/effect_reconcile.py`
- `tests/M10/test_recovery.py`
- `tests/M10/test_reconcile.py`
- `tests/M10/test_runner_evaluation.py`

**结果**

- crash matrix 覆盖率 `10/10 = 1.0`。
- resume、cancel、revocation、poison、non-compensable failure 均有反面测试。
- Arm A 重复副作用计数为 `0`。

### 4. 异步 job、预算、取消与发布门禁闭合

**判据**

- job 有稳定状态、进度、取消和 terminal state。
- wall-clock、CPU、磁盘、并发、保留期等预算有真实执行点或明确归类。
- 取消在每个 step boundary 检查。
- generation 由 manifest 摘要派生。
- 读取方复验 manifest；半发布 generation 不可见。
- pointer 原子切换，不产生半发布可见状态。

**证据**

- `platform/app/job_envelope.py`
- `platform/app/generation_publication.py`
- `tests/M10/test_job_envelope.py`
- `tests/M10/test_generation_publication.py`
- `tests/M10/test_runner_evaluation.py`

**结果**

- 每项预算按 `ENFORCED_LOCALLY` / `ENFORCED_ELSEWHERE` / `NOT_ENFORCED_LOCALLY` 分类。
- 取消、CPU、墙钟、磁盘、并发和 retention 均有行为化测试。
- 发布 crash points 的半发布计数为 `0`。

### 5. 默认关闭、状态机兼容和 rollout 闭合

**判据**

- 未设置 `SA_RUNNER` 时不构造 Runner、不注册 Runner 路由。
- 默认 OpenAPI 不增加自主 Runner 路由。
- 状态机仍是正式默认路径。
- kill switch 在每个 effect boundary 生效。
- 关闭 Runner 后既有 session/plan/review 数据仍可读。
- 不引入第二个 worker 拓扑。

**证据**

- `platform/app/config.py`
- `platform/app/main.py`
- `platform/app/runner_service.py`
- `platform/app/worker_topology.py`
- `tests/M10/test_runner_service.py`
- `tests/M6a/test_closeout_contracts.py`
- `tests/M0_M2/`
- `tests/M5c/test_recovery.py`

**结果**

- 默认关闭是结构性行为，不是运行后补偿。
- M10 Runner 开关打开/关闭均有测试。
- M0–M5 API、旧 session 恢复和平台原始测试保持通过。

### 6. Agent 评测与 MCP/manifest 对外边界闭合

**判据**

- 冻结 Agent 任务集摘要不漂移。
- 越权率、重复副作用、半发布 generation 为零。
- crash matrix 覆盖率为 100%。
- knowledge-pack manifest canonical digest 可重复，并绑定既有 source/generation identity。
- MCP 首发只读、stdio-only、无 listener、token ≥32 UTF-8 字节、默认关闭。
- MCP 不暴露 Runner 写工具或 native backend。
- MCP 使用 `TOOL_PERMISSION_DENIED` / `BUDGET_EXCEEDED`，并以 daemon read-only worker 对同步工具施加真实 deadline 上界。

**证据**

- `tests/M10/frozen_tasks.py`
- `tests/M10/test_runner_evaluation.py`
- `platform/app/knowledge_pack_manifest.py`
- `tests/M10/test_manifest.py`（12 项）
- `platform/app/mcp_server.py`
- `tests/M10/test_mcp_conformance.py`（16 项）
- `docs/standards/runtime-contracts.md`

**结果**

- M10 测试集收集 `148` 项并全部通过。
- 冻结 workload digest 仍为 `196df3dd489df4f1398a9e460aeb837ef5d36f3f78999e54f90c4ea00bcaaf95`。
- M10 + regression 收集 `231` 项并全部通过。
- platform 原始测试 `40` 项全部通过。

### 7. 全项目兼容与回归闭合

**判据**

- M0–M5 保护基线不退化。
- 默认 90 题质量基线继续由既有套件保护。
- API/OpenAPI、数据完整性、路径隐私、治理和 CI contract 保持通过。
- 新增 M10 能力不隐式启动 M8/M11/M12。

**证据**

- `tests/M0_M2/`
- `tests/regression/`
- `platform/tests/`
- `tests/M10/`
- `README.md`
- `docs/PLAN.md`
- `docs/standards/stage-admission-gates.json`

**结果**

- `tests/regression/`：`83 passed`。
- `platform/tests/`：`40 passed`。
- 根级测试：`1426 passed, 2 skipped, 3 failed`。
- 3 个失败均为当前 Python 3.13.3 环境下既有 M7 TXT parser 精确合同失败，不是 M10 新增回归。

## 三、已知限制与未覆盖范围

以下限制已知、明确记录，并不被本次完成证据解除：

1. **真实 10K/100K 数据未验证**：M10 只验证合成 job/generation 行为；真实数据扩展属于 M11/M8 范围，且被当前 approval scope 排除。
2. **专业化 backend 未选择**：当前维持 SQLite registry + linear cosine + BM25；LanceDB/Qdrant 仍为待命参考。
3. **多 worker / 云端重试未覆盖**：M10 保持单 worker；多 worker 和云端 worker 属 M12。
4. **M10 没有 provider 路径**：Arm B 的真实 provider 失败/延迟/成本场景对 M10 不适用；M10 评测使用确定性 Arm A。
5. **M10 预算不是性能声明**：合成长任务证明本地预算被执行，不产生真实吞吐、p95、成本或容量声明。
6. **MCP 首发不含写工具**：`log_review` 仍只属于显式 Runner HTTP 路径，不进入 MCP surface。
7. **MCP 仅 stdio**：没有网络 listener，也没有云端 MCP transport。
8. **manifest 首版未签名**：当前为 canonical SHA-256 / unsigned policy；签名和密钥管理不在 M10 范围。
9. **不承诺 exactly-once**：实际语义是基于幂等键的 at-least-once / 每键 at-most-once 约束。
10. **TXT parser 基线限制**：Python 3.13.3 根级仍有 3 个既有 M7 TXT parser fail-closed 失败；冻结 CPython 3.11.9 环境仍是该合同的目标环境。
11. **默认 90 题不是 M10 新门禁**：由既有 M0–M5 / regression 保护；M10 仅声明不破坏该基线。

## 四、技术退出结论

在 `m10-autonomous-runner-v1` 的批准范围内，七项技术退出条件均有实现与测试证据；未覆盖项均属于明确排除、非适用或已接受限制。

本证据文件本身不产生批准；负责人已于 2026-09-23 以用户指令「批准 M10 COMPLETE (Recommended)」
独立批准在原 `m10-autonomous-runner-v1` 范围内完成，并接受本文件记录的已知限制。权威登记现为：

```text
admission_status: ADMITTED
delivery_status: COMPLETE
completion_approval: present
```

该批准不扩大范围、不解除限制，也不批准 M11/M12、多 worker、M8 backend 或真实 10K/100K 数据。

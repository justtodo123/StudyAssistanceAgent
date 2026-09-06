# M10 自主 Runner 与 Harness 对外准备计划

> 当前状态：设计准备；`BLOCKED / NOT_STARTED`，未获准开工
> 前置：M7、M8、M9 全部退出证据
> 准入政策：[`stage-admission-gates.md`](../standards/stage-admission-gates.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. 范围与非目标

M10 才规划可选自主 Runner、受授权写工具、checkpoint/resume、幂等副作用、恢复、Agent 任务评测、knowledge-pack
manifest 和 MCP 最小对外面。状态机继续作为正式默认与无 LLM fallback，自主 Runner 不因 M6b preview 或计划文件
存在而启用。

本阶段不承诺分布式 exactly-once；通过能力授权、幂等键、EffectLedger、事务边界、reconcile 和补偿定义可验证的
副作用语义。设定未闭合前不得添加自主执行开关、写工具、MCP server、schema migration 或发布配置。

## 2. 前置证据与继承不变量

| Prerequisite ID | 当前状态 | 准入所需证据 |
| --- | --- | --- |
| `M10-M7-EXIT` | `SATISFIED` | M7 Source lifecycle/delete/isolation/fallback 与独立完成批准；证据见 `docs/PLAN.md`、M7 计划与 `docs/baselines.md` |
| `M10-M8-EXIT` | `OPEN` | control schema、后端 parity/migration/fallback 或批准的维持现状结论 |
| `M10-M9-EXIT` | `OPEN` | plan/mastery authority、deviation/replan、外部 AI fallback 和评测退出证据 |

正式默认仍是 `StudySessionService` 状态机；旧 SQLite session 可恢复；M0–M5 API/OpenAPI、默认 90 题与离线路径
保持兼容；M6b 只读 preview 不能作为写权限、checkpoint 或副作用幂等已实现的证据。

## 3. 强制决策

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M10-AUTHORITY` | `OPEN` | `StudySessionService`、可选 Runner、repository 和 tool 的唯一权威边界、冲突处理与状态机默认规则 |
| `M10-WRITE-AUTHORIZATION` | `OPEN` | 写 capability、用户/learner/source scope、显式确认、拒绝/撤销语义和不可变审计字段 |
| `M10-CHECKPOINT` | `OPEN` | checkpoint schema/version、边界、频率、存储、加密/保留、取消、兼容和 resume 校验 |
| `M10-IDEMPOTENCY` | `OPEN` | idempotency key 派生、作用域、唯一约束、保留、重放、并发、冲突和结果复用 |
| `M10-EFFECT-LEDGER` | `OPEN` | proposed/authorized/pending/applied/failed/compensated 状态、事务边界、outbox/reconcile 和审计 |
| `M10-RECOVERY` | `OPEN` | retry/resume/compensation、poison effect、人工介入、进程 crash-point matrix 和不可补偿失败 |
| `M10-EVALUATION` | `OPEN` | Agent 任务集、成功率、工具/参数合法率、越权率、终止、恢复、cost、p95 和发布阈值 |
| `M10-MCP` | `OPEN` | protocol/transport、tool/resource surface、认证、schema/error mapping、写限制和 conformance |
| `M10-MANIFEST` | `OPEN` | knowledge-pack manifest identity、版本、完整性、能力、来源、兼容和签名/校验政策 |
| `M10-OFFLINE-DEFAULT` | `OPEN` | 状态机正式默认、无 LLM fallback、自主路径不可用/失败时的隔离和不得重复副作用 |
| `M10-ROLLOUT` | `OPEN` | 自主 Runner 默认关闭、启用条件、环境/用户范围、观测、kill switch、回滚和迁移兼容 |

每项必须记录明确政策、默认与覆盖、校验/失败、兼容/隐私、量化阈值、证据、责任人和日期。笼统的
“exactly-once”、未定义 crash point 的恢复宣称或仅有 happy-path demo 都不能闭合决策。

## 4. 准入检查与批准记录

- [ ] M7–M9 退出证据全部真实有效；
- [ ] 十一项强制决策全部 `RESOLVED`，authority、authorization、ledger 和 recovery 一致；
- [ ] 写副作用 crash-point、越权和重放测试方案可执行；
- [ ] Agent 评测任务集、样本、硬件/provider、成本与发布阈值冻结；
- [ ] MCP/manifest 的认证、兼容和 conformance 边界明确；
- [ ] [`docs/PLAN.md`](../PLAN.md)、本计划与 JSON 登记表一致；
- [ ] 用户或项目负责人完成批准。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准为空，M10 保持 `BLOCKED / NOT_STARTED`。`M10-M7-EXIT` 已满足，但 M8/M9 退出、十一项强制决策与独立批准仍为阻断项。Agent 不得自行批准。

## 5. 获准后的拟实施顺序

1. 冻结 authority、capability 和 EffectLedger schema，先实现拒绝路径；
2. 为单一受控写工具实现 idempotency、checkpoint 和逐 crash point 恢复；
3. 建立 reconcile/人工介入和不可补偿失败处理，再扩大写工具集合；
4. 接入默认关闭的可选 Runner，并保持状态机路径与数据兼容；
5. 在冻结 Agent 任务集达标后，分阶段交付 manifest 和最小 MCP surface。

拟新增 `tests/M10/` 覆盖 authorization、checkpoint、idempotency、effect ledger、recovery、offline default、rollout、
manifest/MCP conformance；真实 provider 或 transport smoke 必须显式启用且不阻断默认离线 CI。退出条件包括零越权、
重放不重复副作用、crash matrix 达标、状态机默认可回滚、旧 session 恢复、默认 90 题不退化及任务评测达到批准阈值。

## 6. 撤销与发布边界

写 capability、ledger/checkpoint schema、provider/MCP 协议、任务集或发布阈值实质变化时必须改为 `REVOKED`，停止
自主实施并重新批准。只有 `ADMITTED` 后实现且退出条件真实通过，才能把 M10 标为 `COMPLETE` 或对外宣称能力已交付。

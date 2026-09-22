# 迭代测试计划 · StudyAssistanceAgent

> 起始日期：2026-08-17 · 更新：2026-09-06（M7 correctness 收口；`tests/M7/` 当前收集 270 项；Python 3.13.3 下 3 个 TXT 用例按精确 parser 合同 fail closed；`m7_exit=true` 不是 M7 阶段退出）；2026-09-20（M8 selected-scope hardening：`tests/M8_metadata_discovery/` 收集 74 项、74 passed；历史 replay 88/88 与 77/77 通过且明确 non-gating）；2026-09-21（M9 只读 mastery 投影 + 计划身份修复：`tests/M9/` 收集 83 项、83 passed，并修复 `test_planner_does_not_write_state` 的空转缺陷；`tests/M8_metadata_discovery/` 与 `tests/M9/` 均纳入 CI）；2026-09-21（M9 只读 Source 摘要投影：`tests/M9/` 收集 125 项、125 passed；全量 1042 collected、1038 passed、1 skipped、3 failed）；2026-09-21（M9 先修关系 topic graph 投影：`tests/M9/` 收集 187 项、187 passed；全量 1104 collected、1100 passed、1 skipped、3 failed）；2026-09-21（M9 步骤 4a 受限检索接缝：`tests/M9/` 收集 219 项、219 passed；全量 1136 collected、1132 passed、1 skipped、3 failed）；2026-09-21（M9 步骤 4b 计划身份往返保真：`tests/M9/` 收集 245 项、245 passed；全量 1162 collected、1158 passed、1 skipped、3 failed）；2026-09-21（M9 步骤 4c 复习历史活投影：`tests/M9/` 收集 263 项、263 passed；全量 1180 collected、1176 passed、1 skipped、3 failed）；2026-09-21（M9 步骤 4d 准入留痕字段覆盖：`tests/M9/` 263 项不变、`tests/regression/` 62 → 79 项；全量 1181 collected、1177 passed、1 skipped、3 failed）；2026-09-21（M9 步骤 6 窄口径：默认关闭的外部 AI 排序路径 + 冻结任务集 1K 比较；`tests/M9/` 263 → 316 项（`m9` 313 + `m9_benchmark` 3），`tests/regression/` 79 项不变（`test_ci_contract.py` 为**就地扩写**既有用例，非新增）；全量 1234 collected、1230 passed、1 skipped、3 failed。**该增量不证明容量**：1K 读数只证明输入有界，10K/100K 仍属 M8（`BLOCKED`）/ M11；`M9-EVALUATION` 未动、评测 workload 未冻结）；2026-09-21（M9 **退出条件证据**——唯一写权威：新增 `tests/M9/test_mastery_write_authority.py`（8 项），`tests/M9/` 316 → 324 项（`m9` 313 → 321 + `m9_benchmark` 3）；全量 1242 collected、1238 passed、1 skipped、3 failed。该增量**不新增写路径**、不改 `plan_revision`、不写 `admission_history`、未新增公开路由；M9 退出条件中仅「冻结评测达标」仍未挣得）；2026-09-22（M9 解冻 `M9-EVALUATION` 的延迟/成本维度，plan_revision v1.5，并因此触发 §4 撤销过渡：arm A **就地扩写** `tests/M9/test_plan_ai_benchmark.py`（6 场景冻结预算矩阵，无新增 marker、无新增 CI 步骤），arm B 新增 `tests/M9/test_plan_ai_provider_smoke.py`（3 项，`online` + skip 门控、**非门禁**、本次未运行）；`tests/M9/` 324 → 327 项（`m9` 321 → 324 + `m9_benchmark` 3），`tests/regression/` 79 项不变；全量 1245 collected、1240 passed、2 skipped、3 failed。**该增量不证明性能**：arm A 证明的是预算被**强制执行**（stub 下延迟是桥接开销、成本由脚本化 usage 算出），真实 provider 的延迟/成本/失败模式**仍未验证**，冻结范围**仅限 M9 外部 AI 路径**，遵循度仍为定性；10K/100K 仍属 M8（`BLOCKED`）/ M11；本次**未**启动 M9 收口）；2026-09-22（M9 三处**缺陷修正**，均**不触发 §4 撤销**：外部 AI 路径的单轮 output 预算（累积值曾被当单轮值传给 `create_turn`，默认配置下每次调用都在发出任何 HTTP 请求前抛 `ValueError` 并收敛成 `provider_unavailable`，整条路径静默失效而既有测试全绿）+ 分日的每日容量（`_distribute` 曾把余量一次性倾倒进一个不设上限的溢出天，默认请求下 114 个任务 / 3890 分钟对可用 110 分钟）+ 预算环境变量清单的宣传面（`limit_env_names()` 按字段名推导，曾宣传配置层**不兑现**的 `SA_PLAN_AI_MAX_RETRIES`，操作者照它设值会静默无效）；新增 `tests/M9/test_day_distribution.py`（18 项）并就地扩写 `tests/M9/test_plan_ai_adapter.py`（+9 项，含驱动**真实桥**的回归、配置层接线与「宣传的预算环境变量名 == 兑现的」护栏）；`tests/M9/` 327 → 354 项（`m9` 354；`m9_benchmark` 3 与 `online` 3 均为其**子集**，不另计），`tests/regression/` 79 项不变；全量 1245 → 1272 collected、1267 passed、2 skipped、3 failed（3 项为 M7 TXT parser 按设计 fail closed）。另修**标记卫生**：`tests/M9/test_mastery_write_authority.py` 缺 `pytestmark`，致 `-m m9` 少收集 8 项而文档按 324 报数（实际 319）。**残留**：单条任务超容量时该天仍会超出（保证是「每天至多一个任务造成超出」），且**第 2 天起**当 `hours_per_day × 60 − 10 < 25`（即 `hours_per_day < 35/60 ≈ 0.5833`）时该保证**完全空转**（第 1 天不扣复习缓冲，容量是 `hours_per_day × 60`，要靠最小任务保证则需 `hours_per_day < 25/60 ≈ 0.4167`）；另与 `review_plan.py` 刻意分叉——该服务有同一缺陷但 `platform/tests/test_review_plan.py` 明确容忍且该套件冻结不动）；2026-09-22（M9 **收口**：owner 在 `m9-plan-lifecycle-v1` 范围内批准 `M9 COMPLETE`，登记表 `delivery_status` 由 `IN_PROGRESS` 改为 `COMPLETE` 并新增 §4 要求的**独立** `completion_approval`（五字段齐全、`approval_scope` 与准入批准逐字相同）；`M10-M9-EXIT` 由 `OPEN` 改为 `SATISFIED`（**只登记事实，不构成 M10 的准入批准**）。本次为**纯治理记录变更**：未改生产代码、未新增公开路由、未 bump `SCHEMA_VERSION`；`tests/M9/` 354 项与全量 1272 collected / 1267 passed / 2 skipped / 3 failed 均不变。`tests/regression/test_docs_consistency.py` 的 M9 状态断言随事实由 `IN_PROGRESS` 改为 `COMPLETE`，并**加强**为同时校验完成批准五字段与「scope 不扩大、原准入批准不被覆盖」。三条 caveat 随收口**一并接受而非解除**：冻结评测范围仅限 M9 外部 AI 路径、真实 provider 延迟/成本/失败模式仍未验证（arm B 未运行）、10K/100K 属 M8/M11。另登记一条**已知限制**：外部 AI 路径的 `PlanAIRequest` **不含先修关系**，而 `_ai_order` 拿先修违反数作闸门丢弃整个置换——模型被要求满足一个从不告诉它的约束；第三方 provider 探针（**非 arm B、非 M9 证据、不进门禁**）实测披露先修边可把采纳率由 `5/10` 提到 `8/10`，仅改措辞无效（`4/10`）；修复需动 `M9-EXTERNAL-AI` 的披露范围，本次不动）；2026-09-22（M9 收口**补全**：收口提交只改了 `docs/PLAN.md` 的里程碑表，另有 8 个文档的 15 处「登记表已改、叙述未改」漂移被漏掉——`docs/standards/stage-admission-gates.md`、根 `README.md`、`docs/README.md`（3 处）、`docs/prds/README.md`（2 处）、`docs/prds/study-assistance-agent-project-plan-v1.0-prd.md`、`docs/plans/README.md`（4 处）、`docs/plans/m10-autonomous-runner-plan.md` 的 `M10-M9-EXIT` 前置行（仍写 `OPEN`）、`docs/baselines.md`、`docs/PLAN.md` 正文。根因可指认：`test_authority_and_navigation_match_registry_state` 的状态聚合断言包在 `if len(current_states) == 1:` 里，而登记表有 3 种状态组合，该分支**永不执行**。新增两道护栏——`test_stage_plans_track_registry_prerequisites`（阶段计划前置表 == 登记表）与 `test_navigation_docs_do_not_contradict_registry_state`（导航文档的阻断区间与状态对 == 登记表，按「逻辑行」判定，归属不明则保守跳过；**刻意不覆盖** `docs/PLAN.md` 正文与 `docs/plans/references/` 历史记录）。`tests/regression/` 79 → 81 项，全量 1272 → 1274 collected、1267 → 1269 passed、2 skipped、3 failed（3 项仍为 M7 TXT parser 按设计 fail closed）；`tests/M9/` 354 项、生产代码与公开路由均不变；2026-09-22（M10 前置 `M10-M8-EXIT` **维持现状结论**：owner 裁定走该分支，登记表 `M10-M8-EXIT` 由 `OPEN` 改为 `SATISFIED`，M10 计划新增 §2.1 记录裁定字段、三条依据与五条「本裁定不做什么」，并在 §4 标注三项前置均已满足、阻断项只剩十一项强制决策与独立批准；同步 `docs/PLAN.md`（M10 里程碑行、依赖顺序段、v2.36 修订）、`docs/baselines.md`（2026-09-06 那段的更新注）、`docs/plans/README.md` 的 M10 行、`docs/prds/README.md` 与 v1.0 PRD 的依赖段。**同时就地标注一处下游缺口**：M8 走维持现状分支后**不会**产生「真实退出证据」，故 `m11-data-scaling-plan.md` §8 的 `M8/M9/M10 真实退出证据有效` 一条需在 M11 准入前重新澄清（不得读成「M8 迟早会给」而无限期挂起）。本次为**纯治理记录变更**：`admission_status` 仍 `BLOCKED`、`approval` 五字段仍为空、不写 `admission_history`、不改生产代码；`tests/regression/` 81 项与 `tests/M9/` 354 项均不变）；2026-09-22（M10 **十一项决策设计草案**：新增 `docs/plans/references/m10-decision-design-draft.md`（**非授权**，不产生 `RESOLVED`、不创建任何生产物件），M10 计划 §3 加引用、`docs/plans/references/README.md` 加索引行。§0.1 逐条登记起草时核实的仓库事实并带 `文件:行号`，其中两条**改变决策内容**：① `learning_store.py` **只有 `CREATE TABLE IF NOT EXISTS`**，该文件 0 处 `ALTER TABLE`、全仓 0 处 `PRAGMA user_version`——故 checkpoint 需要的迁移机制必须**先显式裁定**（草案给出三条现成范式：`source_registry.py` 的 meta 表版本、`source_delete.py` 的数值版本 + `ALTER`、或新建独立 SQLite 文件）；② job / EffectLedger / outbox / 补偿 / crash matrix 在 `platform/app` 代码中 **0 命中**（只在 M10/M12 规划文档里），故这五类是**从零建设**而非「接入既有」；另记一处既有口径差——`runtime-contracts.md` 的 `TOOL_PERMISSION_DENIED` / `BUDGET_EXCEEDED` 标为预留但 **M6b 从未消费**（preview 走 `terminated` envelope）。草案末尾列四项**待 owner 裁定**的开放点（迁移机制、两个预留错误码、worker 拓扑、全部数值阈值），草案不自行决定。本次为**纯文档变更**：未改登记表、未改生产代码、`tests/regression/` 81 项与 `tests/M9/` 354 项均不变）；2026-09-22（M10 草案的**四项 owner 裁定**落地：存储机制取**独立 SQLite 文件**（连带代价写进 §5——跨库事务不可用，outbox + reconcile 由可选变**必需**，台账行必须在领域写入**之前**落 `pending`）、预留错误码由 **M10 消费**（**不改写** M6b 已交付的 `terminated` 表达）、**维持单 worker**（多 worker 与云端重试留给 M12，M10 计划 §1.1 同步改口径，crash 矩阵只需覆盖单进程）、评测取 **0 容忍组**。四项裁定**只关闭草案内的开放点**，**不产生任何 `RESOLVED`**、不改登记表、不批准准入、不创建生产物件。`tests/regression/` 81 项与 `tests/M9/` 354 项均不变）变异验证：6 个变异各自恰好判红对应护栏，其中**首版区间规则是空转的**（60 字符窗口跨行读到下一个列表项的阶段名而跳过整条断言），已修为「逻辑行 + 只看到阻断表述为止」并复验）

## 一、测试策略总览

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **阶段隔离** | 每阶段测试独立目录，新增阶段不修改存量测试代码 |
| **回归前置** | 每阶段开发完成后，先跑本阶段测试，再跑回归套件 |
| **共享复用** | 公共 fixtures/工具函数集中在 `tests/conftest.py`，各阶段 import 使用 |
| **增量扩展** | 新阶段只需新增目录 + conftest + 测试文件，零改动旧代码 |

### 1.2 目录结构

```
tests/
├── TEST_PLAN.md          # 本文件（测试计划）
├── conftest.py           # 根 conftest：跨阶段共享 fixtures
│
├── M0_M2/                # 基线回归（对应 platform/tests/ 已有测试）
│   ├── conftest.py       # M0-M2 阶段特有 fixtures
│   └── test_baseline.py  # 基线功能验证（从 platform/tests/ 提炼的关键断言）
│
├── M3a/                  # 向量库迁移测试
│   ├── conftest.py       # 向量库 fixtures（mock/真实引擎切换）
│   ├── test_store_interface.py   # 存储接口一致性
│   ├── test_migration.py         # 数据迁移完整性
│   └── test_fallback.py          # 降级路径
│
├── M3b/                  # 可观测性测试
│   ├── conftest.py       # 日志/metrics fixtures
│   ├── test_metrics.py           # 指标采集
│   ├── test_logging.py           # 结构化日志
│   └── test_health_enhanced.py   # 增强 health 端点
│
├── M3c/                  # 面经库测试
│   ├── conftest.py       # 面经数据 fixtures
│   └── test_interview_bank.py    # 面经条目验证
│
├── M3d/                  # 文档完整性测试（M3d 文档闭环）
│   └── test_docs.py              # 文档结构与链接验证
│
├── M4/                   # 课程知识库规模补齐测试
│   ├── test_knowledge_scale.py   # 数量、frontmatter、导航与评测引用
│   └── test_retrieval_priority.py # 课程笔记/面经/README 检索优先级
│
├── M5a/                  # 统一评测入口测试
│   ├── conftest.py               # 评测脚本导入
│   ├── test_cli.py               # 参数解析
│   ├── test_discovery.py         # 评测集发现
│   ├── test_metrics.py           # 指标聚合
│   └── test_report.py            # 报告格式
│
├── M5b/                  # 学习会话状态机测试
│   ├── helpers.py                # Fake QA/Quiz/Review
│   ├── test_state_machine.py     # 状态转换与错误分支
│   ├── test_evaluation.py        # 确定性评估
│   └── test_api.py               # 会话 API 契约
│
├── M5c/                  # 学习状态持久化测试
│   ├── helpers.py                # SQLite fixtures
│   ├── test_repository.py        # 仓储读写
│   ├── test_migration.py         # JSON 迁移
│   ├── test_recovery.py          # 重启恢复与损坏降级
│   ├── test_idempotency.py       # 答案/复习幂等
│   └── test_concurrency.py       # 并发写入
│
├── M5d/                  # 学习工作台测试
│   ├── conftest.py               # 静态页路径与 API 白名单
│   ├── test_page.py              # 首页与必要视图
│   ├── test_client_contract.py   # 只调用正式 API
│   └── test_flow.py              # 学习闭环字段
│
├── M5e/                  # 可复现交付测试
│   ├── test_ci.py                # 离线 CI 工作流
│   ├── test_start.py             # 一键启动与健康检查
│   ├── test_eval_smoke.py        # 评测冒烟
│   └── test_docs.py              # 基线/缓存/演示文档
│
├── M6_crawler/             # crawler P0（独立 marker，离线 CI job）
│   ├── conftest.py         # m6_crawler 自动标记 + 拦截真实 HTTP
│   ├── test_cleaner.py     # 清洗
│   ├── test_converter.py   # Markdown 转换
│   ├── test_dedup.py       # 去重
│   ├── test_fetcher.py     # mock HTTP 抓取
│   ├── test_pipeline.py    # pipeline 编排
│   ├── test_ingest_gate.py # 默认不入库
│   ├── test_offline_contract.py  # 候选目录 / 90 题隔离 / 路径隐私
│   ├── test_ci.py          # crawler CI 契约
│   └── test_online_smoke.py      # 显式在线 smoke（默认跳过）
│
├── M6a/                    # M6a 契约、默认包、工具/状态机、静态额外源与拓扑门禁
│   ├── test_protocols.py              # Source/Tool/Runner 协议契约
│   ├── test_default_pack_adapter.py   # 默认包身份、索引、快照与路径隐私
│   ├── test_tool_adapters.py          # 确定性 Retrieve/Quiz/ReviewDue 适配器
│   ├── test_state_machine_runner.py   # 状态机 Runner 兼容与恢复
│   ├── test_extra_sources_config.py   # SA_EXTRA_SOURCES 启动配置与限额
│   ├── test_extra_sources_retrieval.py # 组合快照 scope 与检索隔离
│   ├── test_snapshot_publication.py   # 原子发布与 last-good
│   ├── test_worker_topology.py        # 单进程 service lock / worker 门禁
│   ├── test_cache_lifecycle.py        # default/combined generation 与缓存生命周期
│   └── test_closeout_contracts.py     # M6a-4 API/OpenAPI/链接收口
│
├── M6b/                    # 默认关闭、只读 Agent Preview 阶段测试
│   ├── README.md                      # 范围、离线命令与 benchmark 说明
│   ├── test_llm_client.py             # Anthropic adapter、native replay 与隐私
│   ├── test_preview_agent.py          # tool loop、预算、重试、取消与终止
│   ├── test_preview_service.py        # route、Bearer auth、容量与 HTTP envelope
│   ├── test_main_preview_integration.py # 默认关闭/启用 app 与 OpenAPI
│   ├── test_preview_config.py         # 严格布尔值与只能收紧的配置
│   ├── test_tool_registry.py          # allowlist、schema、授权与结果投影
│   ├── test_preview_read_only.py      # scope 隔离与 SQLite 零领域写入
│   ├── test_preview_privacy.py        # prompt/body/secret/path 日志边界
│   └── test_preview_benchmark.py      # 20 warm-up、200 measured、并发 2、p95
│
├── M7/                     # M7 lifecycle/FTS5/vector/offline + Search/QA internal overlay（270 项）
│   ├── README.md                      # 范围、排除项与运行命令
│   ├── real_fixtures.py               # 运行时生成五格式最小合法 fixture（不入库）
│   ├── test_source_registry.py        # schema、身份、CAS、状态机、事务与隔离
│   ├── test_source_manifest.py        # 文件 manifest、canonical digest 与路径隐私
│   ├── test_parser_matrix.py          # 冻结 parser matrix、真实 bytes/file 解析与 fail-closed
│   ├── test_normalized_document.py    # 跨格式 unit、稳定 normalized/chunk identity 与 staging
│   ├── test_full_snapshot.py          # source-local FULL、last-good、M7-2 manifest identity/LRU cache
│   ├── test_snapshot_pointer_consistency.py # M7-5 READY 后 CURRENT 激活失败/重试修复
│   ├── test_source_sync.py            # request/run 幂等、增量、cancel/retry/recovery
│   ├── test_source_lifecycle_e2e.py   # FULL/INCREMENTAL、Search/provenance、重启、删除 E2E
│   ├── test_source_delete.py          # tombstone、删除传播、实际索引清理、hard-delete receipt 与 provenance 失效
│   ├── test_source_isolation.py       # 查询前 owner-only 过滤与统一 NOT_FOUND
│   ├── test_fts5_tokenizer.py         # jieba FTS5 tokenizer 与 generation-bound 索引
│   ├── test_source_offline.py         # 离线 fail-closed 校验与显式 FULL repair
│   ├── test_user_source_search.py     # principal overlay、RRF、provenance、查询校验与缓存
│   ├── test_user_source_vector.py     # generation-bound vector、identity 与无全局 torch 状态变更
│   └── test_source_benchmark.py       # 冻结 benchmark schema 与非 exit 冒烟
│
├── source_inventory/       # 外部资料只读盘点（不构成 M7 开工）
│   ├── conftest.py         # source_inventory marker + 迷你资料树
│   ├── test_classify.py    # 格式/课程/跳过规则
│   ├── test_scan.py        # 排除工程文件、去重、只读
│   ├── test_inventory_cli.py # 默认根目录与输出隔离
│   └── test_privacy.py     # 无宿主绝对路径、不解析/不索引
│
├── M8_metadata_discovery/       # M8 Metadata Discovery 离线治理（不执行 discovery/acquisition）
│   ├── README.md                 # 范围、排除项与运行命令
│   ├── test_metadata_discovery_governance.py # schema、Git binding、intent 与 fail-closed 边界
│   └── test_metadata_discovery_scope_governance.py # selected pypdf scope 与独立审查边界
│
├── M9/                     # M9 目标驱动计划（生成 / 生命周期 / 偏差 / 只读复习历史、mastery、Source 摘要与先修关系投影 / 受限检索接缝 / 默认关闭的外部 AI 路径与 1K 冻结比较 / 唯一写权威证据 / v1.5 冻结预算矩阵 + opt-in 非门禁的真实 provider 读数）
│   ├── README.md           # 范围、排除项与运行命令
│   ├── conftest.py         # 空复习历史的确定性 Planner fixture
│   ├── test_goal_planner.py           # 确定性生成、身份、只读与输入有界
│   ├── test_plan_lifecycle.py         # 采纳 / 进度 / 重规划与 revision 链
│   ├── test_deviation_signals.py      # 跳过+逾期偏差信号与 parent 前向链
│   ├── test_deviation_consumption.py  # 未消费阈值与消费台账
│   ├── test_mastery_projection.py     # 跨会话聚合、file 路径映射、只读守卫、计划身份摘要
│   └── test_source_summary_projection.py # usable 规则矩阵、隐藏态排除、懒装配不建库、Planner 接缝
│
├── regression/             # 跨阶段回归套件
│   ├── conftest.py         # 回归专用 fixtures（离线 BM25-only，恢复 vector 全局状态）
│   ├── test_api_contract.py      # API 契约稳定性
│   ├── test_rag_quality.py       # RAG 质量回归（显式 BM25-only）
│   ├── test_data_integrity.py    # 数据完整性
│   ├── test_runtime_contracts.py # 错误码、分位数、入库门禁、生成分层
│   ├── test_sse_contract.py      # SSE 帧序、结束标记与路径隐私
│   ├── test_path_privacy.py      # API/SSE/日志及治理文档路径隐私
│   ├── test_ci_contract.py       # 结构化解析 offline/platform/RAG/crawler CI 门禁
│   ├── test_docs_consistency.py  # 跨文档耐久事实、M6a–M12 状态与 M8 历史边界
│   ├── test_document_governance.py # Network/Interview 文档身份、来源、许可与 fail-closed 入库
│   └── test_governance_contract.py # Registry 引用、docs 导航与阻断期未来生产树一致性
│
└── utils/                # 测试工具（非测试文件）
    ├── helpers.py        # 通用断言与辅助函数
    └── markdown_links.py # Markdown/Registry 仓库相对引用与锚点校验
```

### 1.3 执行规则

```
开发任务完成
    ↓
运行本阶段测试（pytest tests/M3x/ -v）
    ↓
通过 → 运行回归套件（pytest tests/regression/ -v）
    ↓
全部通过 → 提交代码
    ↓
失败 → 定位修复 → 重新运行
```

## 二、各阶段测试规划

### M8 Metadata Discovery（离线治理）

`tests/M8_metadata_discovery/` 只验证 committed-intent inventory、candidate schema、Git object binding、角色隔离和 failed-closed 状态。测试不得访问网络、DNS、PyPI、metadata endpoint，不得下载、解析、安装、调用 resolver/collector，亦不得启动其他 M8 stage。

selected-scope 增量覆盖 Owner 选择的 `pypdf==6.0.0`、严格单包 `dependency_scope: ["pypdf"]`、未选择 artifact/URL、有限但未生效的 proposed policy、全零 limits/counts、全 false/null authorization，以及 deterministic candidate validation 与 genuine independent review 的角色区分。六阶段链固定为 candidate publication → Builder self-check → review request → review prompt → review target → dispatch manifest；dispatch-rooted validator 只沿 committed content-addressed references 读取固定 path，并验证 direct-parent forward-only 顺序、exact stage schema、cycle/protocol/candidate continuity。链测试拒绝 self/forward/deferred reference、重复 record、错误 parent、篡改 predecessor、任意 committed text 和 target/dispatch divergence。

Git 读取测试覆盖 full lowercase SHA-1 OID、禁用 replacement/lazy fetch、对象类型与声明大小预检、单对象及整链累计预算、Git OID/blob/SHA-256 复算、`ordinary_single_parent_commit_only` 和统一 `MetadataGovernanceError` 边界；root/merge、wrong type、oversized、truncated/extra framing 或缺失对象必须 fail closed。caller-authored Reviewer identity、自签 independence 或 legacy review package 不能产生 independent approval；当前完整 dispatch 校验最多返回 `READY_FOR_EXTERNAL_INDEPENDENT_REVIEW`。这些测试仍不执行 metadata discovery 或任何 acquisition。

```bash
python -m pytest tests/M8_metadata_discovery -v
```

`m8_metadata_discovery` marker 用于显式筛选该阶段测试。

### 当前测试基线

selected-scope 测试文件已登记在 `tests/M8_metadata_discovery/`，与历史 generic governance 测试保持阶段隔离。

| 测试范围 | 收集数量 | 当前结果 | 说明 |
|----------|----------|----------|------|
| 根级 `tests/`（含 M6_crawler、M6a、M6b、M7、source_inventory，不含 `platform/tests/`） | 826 项 | 2026-09-06 CPython 3.13.3：822 passed、1 skipped、3 failed；CPython 3.11.9 精确环境：825 passed、1 skipped | 三个 3.13 失败仅为 TXT 精确 `cpython-textio==3.11.9` 合同 fail closed；唯一 skip 为显式 online crawler smoke；历史 810/809 passed/1 skipped 仅作历史证据 |
| `tests/M6b/` | 129 项 | 2026-08-29 当前：普通套件 126 passed、3 deselected；benchmark 3 passed；2026-08-28 首轮：111 passed | fake provider；native tool loop、API/auth、隐私、零写入与独立 blocking benchmark |
| `tests/M6a/` | 124 项 | 2026-08-28：124 passed | 含 worker topology、generation 分离、缓存生命周期与 API/OpenAPI/链接收口 |
| `tests/M7/` | 270 项 | 当前 collect-only：270 项；Python 3.13.3 执行 267 passed / 3 failed（TXT 精确 `cpython-textio==3.11.9` 合同导致的预期 `PARSER_UNAVAILABLE`，非代码放宽项）；2026-09-06 Python 3.11.9 精确依赖环境的五格式 100×20 冻结协议独立全 PASS | source-local FTS5+vector identity、delete/isolation、Search/QA internal overlay、M7-2 snapshot cache、M7-4 exact-query/query-encode、M7-5 READY/CURRENT 与 correctness 收口；parser 证据报告只写系统临时目录且不入库 |
| `tests/M8_metadata_discovery/` | 75 项 | 2026-09-21：75 passed（孤立运行）；全量运行时曾出现的 15 项跨阶段失败已于同日修复，见下方 2026-09-21 记录 | 离线治理；generic unresolved intent 仍为 `METADATA_DISCOVERY_INTENT_OWNER_SELECTION_REQUIRED`；pypdf==6.0.0 selected-scope 的 bounded Git reader、六阶段 dispatch-rooted chain、single-parent policy、provenance fail-closed 与最大 `READY_FOR_EXTERNAL_INDEPENDENT_REVIEW` 均已覆盖 |
| `tests/M9/` | 354 项（`m9` 标记覆盖全部 354 项；其中 `m9_benchmark` 3 项，已排除在阶段步骤外、作为独立 CI 步骤运行；另有 `online` 3 项为 opt-in、默认 skip、**非门禁**。后两者均为 `m9` 的**子集**，故不另计） | 2026-09-22：353 passed、1 skipped（孤立运行；skip 即 arm B 的 opt-in 门控）；同日前基线分别为 44 项、83 项、125 项、187 项、219 项、245 项、263 项、316 项、324 项、327 项 | 确定性生成、**分日每日容量**（任何一天的任务分钟数不得超出当日容量、追加的天与窗口内的天同受容量约束且日期连续、窗口够用时不追加、`total_days`/`total_hours` 与逐日明细自洽、空任务集仍是 1 个空天、分日确定性；**第 2 天起** `hours_per_day < 35/60 ≈ 0.5833` 时保证**完全空转**，第 1 天不扣缓冲、要靠最小任务保证需 `hours_per_day < 25/60 ≈ 0.4167`，被钉成可见事实而非留白）、计划身份（含派生输入摘要）、采纳/进度/重规划、跳过+逾期偏差与消费台账、只读 mastery 投影（跨会话聚合、知识条目 file 路径映射三分支与 `_log_review` 同序、不可映射排除、真只读守卫、输入有界）、只读 Source 摘要投影（`usable` 规则 7 态 × 有无 generation 矩阵、隐藏态排除、恰好一次 bulk 读、懒装配不建库、principal 守卫、有界输入、Planner 接缝）、只读先修关系投影（行内列表解析含块状形式静默丢弃陷阱、同目录兄弟边与嵌套目录不跨目录连边、丢弃规则、环与环下游诊断、零写入与每条目恰好解析一次、空图等价于无图的逐字节不变量、真图拓扑序与 `violations` 三种成因、置顶闭包交互、60 条语料数据完整性、受限检索接缝（四类预算与放宽拒绝、stale/deleted/未发布/未就绪/禁用/待删源在接缝上被丢弃、fail-closed、真只读守卫、证据有界）、计划身份按 principal 分隔与记录往返保真（`summary` 落记录、replan 还原 principal 与源范围、principal 不出现在任何读取路径、身份反 churn 逐字节护栏、源码级单点剥离护栏，动态枚举公开方法）、只读复习历史投影（只返回成员资格、刻意不缓存、恰好一次批量读、无写面、构造 Planner 之后落的复习必须可见、快照参数仍冻结、`plan_id` 随复习变化、`main.py` 装配护栏）、**默认关闭的外部 AI 排序路径**（载荷字段级白名单、预算只允许收紧、每类失败收敛为回退、关闭时逐字节相同、失败不落库、先修闸门与必选置顶非空转）、**冻结任务集 1K 比较**（语料只读复用 M7 生成器且 chunk 数实测、输入有界、两路径先修违反为 0、确定性可重放、合法/非法对换两臂均非空转）、**唯一写权威证据**（动态枚举 `platform/app/` 全部 60 个源文件后断言写者恰好唯一、M9 模块与写权威导入不可达、检测器正反对照与表名上游契约钉桩）、**v1.5 冻结预算矩阵**（6 场景 × 稳定原因码，驱动**真实** `build_anthropic_proposer(client_factory=…)` 接缝而非 `proposer=` 注入，断言 `prompt` 预算在调用 provider **之前**返回、`cost` 预算在收到**合法**置换时仍丢弃、`deadline` 被强制，并钉住价目表常量不漂移与 stub 延迟上界绑在冻结 `deadline_seconds` 之下）、**真实 provider 读数**（`online` + `M9_PROVIDER_SMOKE` skip 门控、显式 opt-in、**非门禁**、本次未运行；只记脱敏字段、花费上限事后累加、报告先落盘再断言））；自 2026-09-21 起纳入 CI |
| `tests/source_inventory/` | 21 项 | 2026-08-27：21 passed | 外部资料只读盘点；tmp_path 迷你树，不扫描真实外部目录，不构成 M7 开工 |
| `tests/regression/`（含 slow） | 79 项 | 2026-09-21：79 passed；2026-09-06 当前 checkout 离线 keyword mode：62 项 / 62 passed（历史读数） | 含 SSE、结构化 CI、准入治理、导航与生产树契约；含显式 active-delivery 开工授权门禁；2026-09-21 起 `_registry_references` 白名单**同时枚举 `admission_history[].reference`**，并有非空性护栏与五键键集断言 |
| `tests/regression/test_rag_quality.py` slow | 3 项 | 2026-09-01 复测：3 passed；2026-08-28：3 passed | 默认 OS/DS/CO 90 题 Recall@3 门禁 |
| `platform/tests/` | 40 项 | 2026-09-06 当前 checkout 离线 keyword mode：40 passed | 受保护的原始平台冒烟/功能测试，不由根级测试取代，且本轮无 tracked diff |

> 本表各行（含根级行）是各范围在**各自标注日期**的读数，且阶段行均为**孤立运行**。全量运行的跨阶段差异以
> 下方 2026-09-21 记录为准——M8 的 15 项失败正是只在全量运行中出现、孤立运行全绿，单看本表无法发现。

**2026-09-22 当前全量读数**（CPython 3.13.3，`pytest tests/ -q`，M9 三处缺陷修正 + 标记卫生后）：**1272 collected、
1267 passed、2 skipped、3 failed**。同日的两个更早读数已被本条取代：v1.5 评测解冻后为 1245 collected / 1240 passed
（本次三处缺陷修正 +27：`test_day_distribution.py` 18 项 + `test_plan_ai_adapter.py` 9 项，后者 50 → 59），
2026-09-21 为 1242 / 1238 / 1 skipped / 3 failed。各增量：mastery +39、Source 摘要 +42、先修关系 +62、
受限检索接缝 +32、计划身份往返保真 +26、复习历史活投影 +18、准入留痕字段覆盖 +1、外部 AI 路径 +53
（`test_plan_ai_adapter.py` 50 + `test_plan_ai_benchmark.py` 3）、唯一写权威证据 +8；arm B 的
`test_plan_ai_provider_smoke.py` +3 使 skipped 由 1 → 2，arm A 为**就地扩写**故 collected 不变
文件内**唯一**受 `M9_PROVIDER_SMOKE` 门控的用例（该文件另两项为 run-id 与报告独占创建的离线用例，不受门控）。）
3 failed 仍是 `tests/M7/test_parser_matrix.py` 与 `test_normalized_document.py` 的 TXT 用例
（3.11.9 精确 parser 合同下的预期 fail-closed），与上一读数逐项相同。

3 项失败全部是 `tests/M7/` 的 TXT 真实 parser 用例，属精确 `cpython-textio==3.11.9` 合同下的**预期 fail-closed**：
`platform/app/parser_matrix.py` 的 `_installed_version()` 对 `cpython-textio` 返回 `platform.python_version()`，
本机为 3.13.3，与冻结值不符即 `PARSER_UNAVAILABLE`。**不得放宽为通过**——该合同是已冻结的治理结论，
放宽会改变 parser identity 语义；在 CPython 3.11.9 精确环境下这 3 项通过（825 passed、0 failed）。
另注：`offline-ci.yml` 使用 Python 3.12 且**不运行** `tests/M7`，故上述 3 项 TXT 读数差异不进入 CI。
M8 的离线治理套件（`tests/M8_metadata_discovery/`，75 项）自 2026-09-21 起已纳入 CI 的 stage 测试步骤。
此前该套件不在 CI 中——这正是那 15 项「只在全量运行出现、孤立运行全绿」的跨阶段失败无法被 CI 发现的原因；
补入 CI 后，同一类 `sys.path` 污染交互会在 CI 中直接暴露。CI 的 3.12 与 metadata-discovery 套件无版本耦合
（带 Python 版本断言的 `m8_probe_s1_environment_v3.py`、`m8_validate_minimal_1k_protocol*.py` 等属
minimal-1k/S1 家族，不在该套件的 import 闭包内），但该结论是静态推断，本地 3.13.3 无法验证 3.12 行为。
`tests/M9`（354 项，其中 `m9_benchmark` 3 项由**独立步骤**运行，另有 `online` 3 项 opt-in 且默认 skip；两者均为 `m9` 标记集的子集）同样自
2026-09-21 起纳入该步骤；**该步骤不排除 `online` 标记**，故「真实 provider 默认不跑」完全靠
`M9_PROVIDER_SMOKE` 未设时的 `pytest.skip`（该 skip 门控是**承重**的），且真实 provider 臂**不得**被加进 CI；
`tests/M7`（270 项）仍不在 CI 中，因其 3 项 TXT 用例
是 3.11.9 精确合同下的预期 fail-closed，需另建钉住 Python 3.11.9 的独立 job 才能合法纳入。

**2026-09-21 增量（M9 只读 mastery 投影 + 计划身份修复）**：新增 `tests/M9/test_mastery_projection.py`（39 项），
并修复 `tests/M9/test_goal_planner.py::test_planner_does_not_write_state` 的空转缺陷——该用例此前构造了
`Spy` 却从未注入服务，`spy.saves == 0` 恒真，等于什么都没验证；现改为真 store + 写入口全部 fail +
连接级 `total_changes` 审计 + 库快照比对，用例名保留。修复后该用例**仍然通过**，说明它过去并未掩盖真实写入
（守卫本身已单独验证有牙：写入产生非零 delta、读取为 0、fail-trap 确实触发）。该修复属 M9 当前阶段目录，
不是阶段隔离所禁改的「其他阶段存量文件」。

**2026-09-21 增量（M9 只读 Source 摘要投影）**：新增 `tests/M9/test_source_summary_projection.py`（42 项）与
`platform/app/source_summary_projection.py`。规则是 `published_generation is not None and state in
{READY, DEGRADED}`，逐字对齐 `source_offline.py` 的内联判断（规范来源），字段名用 `usable` 而**不是** M7
`IsolationSnapshot.authorized_source_ids` 的 `authorized`——后者含 REGISTERED / SYNCING / DISABLED，集合严格更大。
`DELETE_PENDING` / `DELETED` 的排除是 M7 既有 `list_sources` WHERE 子句的构造性结果，因此那两个用例必须用
**直接 SQL** 种入（经服务层种是空转的），且钉的是 M7 的既有保证、不是本次新增证据；`count_non_deleted_sources`
的 WHERE 是 `state != DELETED`（**含** `DELETE_PENDING`），测试用 monkeypatch 让它一旦被调用即失败。
**不加公开 principal 通道**：`GoalPlanRequest` 未变，`generate()` 只多一个可选关键字参数，路由不传它，
因此本套件不新增任何公开 API 契约。残留：摘要今天不可能影响计划内容（两个命名空间无映射，且本仓
`platform/.cache/` 无 registry 库，懒守卫恒返回空表），`M9-EVALUATION` 的
`STALE_DELETED_SOURCE_ENTRY_ZERO` 是**检索路径**判据，本次只到规则层。

**2026-09-21 增量（M9 先修关系 topic graph 投影）**：新增 `tests/M9/test_topic_graph_projection.py`（62 项）、
`platform/app/topic_graph_projection.py`，并给 `knowledge/{os,ds,co}/` 共 60 条条目补 `prerequisites:` frontmatter。
`parse_frontmatter` 抽出共用的行内列表 helper（`tags` 与 `prerequisites` 共用，`tags` 取值形态逐字节不变），
其余键仍一律保留为字符串——刻意不「看到方括号就当列表」。本增量**修掉一处实现缺陷**：`_pin_required` 的块内
短路分支原先以「闭包没新增节点」为门，而必选主题**互为先修**时闭包恰好只含这两个节点但块内存在边，会产出
违反该边的顺序；门已改为 `not edges`，并由 `test_pin_required_respects_prerequisites_inside_the_block` 钉住。
数据完整性用例按**原始文件**断言 60 条只用行内方括号形式，并逐条断言「声明的 stem 数 == 解析出的边数」——
块状 YAML 会被解析器**静默**丢成空列表，只有按原始文件断言才拦得住拼写错误。**不加公开路由**、**不 bump
`SCHEMA_VERSION`**。检索面实测无变化：90 题离线 BM25 Recall@5 = 0.989、Recall@3 = 0.978，与改动前逐位相同
（frontmatter 在切块前已被整块剥掉，`document_id` 也不含 frontmatter）。残留：期考复盘类条目不声明先修，
故图**不会**把复盘条目推到末尾；「先修违反=0」只对**计划任务集内的边**成立，被 `excluded_topics` 移除的
先修不计违反；跨目录/跨课程先修与 `unorderable` 进 `summary` 均未实现。

**2026-09-21 增量（M9 步骤 4c 复习历史活投影）**：新增 `tests/M9/test_review_history_projection.py`（18 项）与
`platform/app/review_history_projection.py`。修的是**装配**缺陷而非 Planner：`main.py` 原先传
`review_history=_learning_store.all_reviews()`，那是 import 时求值一次的**快照**，于是同一进程内新记录的复习
永不反映到计划上——`reviewed` 标志、排序优先级，以及经 `_derived_digest` 参与 `plan_id` 的身份全部停在进程
启动时刻；而紧邻的 mastery 投影刻意传活对象，两条同源只读输入一个冻结一个实时。现注入
`ReviewHistoryProjection`（只返回成员资格 `frozenset[str]`，不交 review payload），每轮 `generate` 只重读一次；
未注入时回落到构造时的快照，既有调用方行为逐字节不变。**语义变化须诚实记录**：进程内新落的复习现在会改变
`plan_id`（`reviewed` 参与派生摘要），这与既有 docstring 的承诺一致，只是此前该承诺在 mastery 侧成立、在复习侧
不成立；旧 id 仍可 `GET`/`adopt`/`progress`/`replan`，不回填、不改写。**不加公开路由**、**不 bump
`SCHEMA_VERSION`**、**不改批准字段与 `admission_history`**（步骤 3 已把该残留逐字记录，本次是修复而非范围
扩张）。装配护栏单独存在是必要的：其余用例直接构造 `GoalPlannerService`，把装配改回快照它们仍然全绿，而缺陷
原本就长在装配上。变异验证：改回冻结快照 → 恰好 1 项失败（装配护栏本身）；`_reviews()` 改回恒读快照 → 4 项失败。

**2026-09-21 增量（M9 步骤 4d 准入留痕字段覆盖）**：关闭 M9 计划 §4 已记录的覆盖缺口。`stage-admission-gates.md`
§7 明文要求 `admission_history[].reference`「必须是仓库内可移植路径」，但该字段此前**未纳入**
`tests/regression/test_governance_contract.py` 的 `_registry_references` 白名单枚举，只靠人工约束。修法是把它
折进**同一**白名单（`approval_reference` / `authorization_reference` 走的就是这条规则，复用一个校验器胜过并行
维护两套），而非另写校验器——这也正是缺口原文所说的「补入枚举需改存量测试」。**补了非空性护栏**：
`admission_history` 目前只有 M9 登记，若被清空，新增的那段 yield 就空转，而 allowlist 用例仍会全绿；故
`test_admission_history_records_are_well_formed` 先断言 `records` 非空，再逐条断言键集恰为 §7 的
`from`/`to`/`at`/`reason`/`reference` 五键、`from`/`to` 属 `{BLOCKED, ADMITTED, REVOKED}` 且不相等（键集断言是
本次**新增**的覆盖，不在缺口原文范围内）。**只紧不松**：未放宽任何既有断言，未改批准字段与
`admission_history` 内容，未新增能力 / 路由 / 字段。变异验证：`reference` 换成宿主绝对路径 → allowlist 用例
**恰好 1 项**失败；整个 `admission_history` 删掉 → allowlist 用例**仍然全绿**、只有键集用例变红（后者正是护栏的
存在理由）。`tests/M9` 263 项不变，`tests/regression` 62 → 79 项（含同日既有增量）。

**2026-09-22 增量（M9 三处缺陷修正 + 标记卫生）**：三个各自独立、都已实测证实的缺陷。

*① 外部 AI 路径的单轮 output 预算。* `PlanAILimits.max_output_tokens`（累积，2048）曾被直接当作
`create_turn` 的 `max_tokens` 传下去，而 `llm_client.create_turn` 硬拒大于 `MAX_TURN_OUTPUT_TOKENS`(1024)
的值。于是**默认配置下**每次调用都在发出任何 HTTP 请求之前抛 `ValueError`，被 `propose` 的回退路径收敛成
`provider_unavailable`——整条外部 AI 路径静默失效，**而既有 50 项 adapter 测试全绿**：其中凡是构造 adapter
的都经 `proposer=` 注入同步 stub（其余只碰 dataclass / 载荷 / 解析 / 预算校验等接缝，根本不构造 adapter），
故没有一项触到那个调用点（「守卫必须长在缺陷所在处」）。**但这不是全貌**：修复前**默认运行**的真实桥驱动者
`test_plan_ai_benchmark.py` **穿过**了那个调用点却仍全绿，因为它的 `_StubClient.create_turn` 把 `max_tokens`
丢掉（`del … max_tokens …`），超限的 2048 照样通过（`test_plan_ai_provider_smoke.py` 同样走真实桥，但默认
skip）。故真教训是**桥接 stub 必须复刻客户端的硬拒**，
不只是「`proposer=` 注入会绕过调用点」。修法是照搬 `preview_agent` 的房屋模式，拆成两个字段：新增
`max_turn_output_tokens`（默认 `MAX_TURN_OUTPUT_TOKENS`）才是传给 `create_turn` 的值，并校验 `单轮 ≤ 累积`；
`max_output_tokens` 保持累积，但修复把唯一送出它的调用点换成了单轮值，故它**此后没有运行期执行点**
（不送 provider，也无用量累计核验）——**但它并非无人读**：`_validate_limits` 在构造期校验它（正整数、
≤ 冻结默认、≤ `max_input_tokens`）并据此给单轮值定上界。故回归用例**必须驱动真实桥**
`build_anthropic_proposer(client_factory=…)`，另加一条配置层用例钉住 `SA_PLAN_AI_MAX_TURN_OUTPUT_TOKENS`
真被读且只能收紧。变异验证：把调用点改回 `max_tokens=limits.max_output_tokens` → 新增用例**恰好 2 项**失败
（`seen == []`，客户端根本没被调用；原因码为 `provider_unavailable`）；同一变异下 `-m m9_benchmark`
**仍 3 项全绿**，这就是上面那个盲区的实证。

*② 分日的每日容量。* `_distribute` 把 `total_days`（请求窗口）当成硬截断，排不完的任务被**一次性倾倒**进一个
不设上限的「第 `total_days + 1` 天」：默认请求下该天 114 个任务 / 3890 分钟，而当日可用容量 110 分钟；全部
课程 / 1 小时下 128 个任务 / 4590 分钟对可用 50 分钟。倍数**依赖分母口径**，引用须连分母一起：默认请求对
当日可用容量（`hours_per_day × 60 − 10`）是 35.4 倍、对 `hours_per_day × 60` 是 32.4 倍；探针集内最高是
`0.5 小时/天` 的 4590/20 = **229.5 倍**（`8 小时/天` 下窗口内就排完，不触发）。判据取自声明而非自造——
`hours_per_day` 是每日**容量**、
`target_date` 是**视野**，超出**窗口**本就合法（`review_plan.py` 的「剩余任务追加到最后一天（如果超出天数）」
是唯一的正面声明，M9 逐字继承），违反声明的是**每日容量**。修法是**逐天追加**，追加的天受同一容量约束。
新增 `tests/M9/test_day_distribution.py`（18 项）钉住不变量：任何一天的任务分钟数不得超出当日容量，**唯一
例外**是单条任务本身就装不下且该天**恰好只装一个**任务（`and day_tasks` 守卫的必然结果）。这条残留必须按
准确口径读：最小原子任务 25 分钟，故**第 2 天起**（当日容量扣了复习缓冲，`hours_per_day × 60 − 10 < 25`，
即 `hours_per_day < 35/60 ≈ 0.5833`）**每一天**都踩到守卫，容量保证在该区间内**完全空转**；**第 1 天不扣
缓冲**（`if d > 0` 才减 `REVIEW_BUFFER_MINUTES`），容量是 `hours_per_day × 60`，只有当日首条任务本身就超过
它时才超出——要靠最小任务保证则需 `hours_per_day < 25/60 ≈ 0.4167`。`0.5 小时/天`（合法下界）下默认请求
（全部课程）实测 142 天，其中 **120 天**超出声明的每日上界（40 分钟），最大 60 分钟，第 1 天也在其中
（该请求首条任务 50 分钟 > 30）。残留的准确表述是「每天至多**一条**任务造成超出」，不是「绝不超出」。变异验证：把 `_distribute` 换回旧实现 → 8 项失败（5 个参数化的容量用例 + 溢出天用例 +
窗口用例 + 空转用例；`os-2.0` / `os-8.0` / `None-8.0` 三个参数**仍绿**，因为它们的任务集在窗口内就排完，
旧实现从不进入那个溢出天分支，故对本次修正不构成证据）。

*③ 预算环境变量清单的宣传面。* `limit_env_names()`（步骤 6 引入，docstring 自述「供配置层与测试共用同一份
清单」）按 `PlanAILimits` 的**字段名**推导，于是把 `SA_PLAN_AI_MAX_RETRIES` 也列进了「可收紧的预算环境
变量」——而配置层**真正兑现**的 `config._PLAN_AI_LIMIT_ENV` 里**没有**这一项（`max_retries` 有字段但刻意
不可由环境变量覆盖，见 `platform/README.md`「model 与 retry 次数不可由环境变量覆盖」）。操作者照该清单设值
会**静默无效**：配置层不报错，预算也不收紧。实测（`git stash` 回旧代码后直接调用）宣传清单 9 项、兑现清单
8 项，差集恰为 `SA_PLAN_AI_MAX_RETRIES`。修法是改为直接取自 `config._PLAN_AI_LIMIT_ENV`，使「宣传的清单」
与「兑现的清单」**同源**；护栏用例断言两者逐个相同，并断言宣传清单**非空**（否则「相等」会因两边都空而
平凡成立）。影响面是三者中最小的一处：该函数**当前无生产调用方**，故运行期行为不变。

**三者均不触发 §4 撤销**（M9 计划 §4.4）：`M9-EXTERNAL-AI` 的决策值不含任何数字，2048/1024 是实现常量；
两个冻结摘要（`_workload_digest` / `_budget_scenario_digest`）修正后重算**逐字节不变**，故 1K 与预算矩阵的
历史读数继续可比；`plan_id` 不随分日变化（把 `_distribute` 换成只产出一个空天的桩，`plan_id` 逐字节不变），
计划身份这一兼容不变量未被触碰。故属**兑现**既有决策而非**改判据**。

**与 `review_plan.py` 刻意分叉**：该服务有同一处分日缺陷，但 `platform/tests/test_review_plan.py:59` 的
`actual_days <= max_days + 1` 明确**容忍**它，且 `platform/tests/` 按仓库约定冻结不动。故修正只落在
`goal_planner.py`，两个服务在这一点上**有意不一致**，不得被读成遗漏。

**标记卫生**：`tests/M9/test_mastery_write_authority.py` 缺 `pytestmark`，致 `-m m9` 少收集 8 项，而文档按
324 报数（实际 319）。现补上，`tests/M9` 354 项**全部**带 `m9` 标记；另更正一处长期误报：`m9_benchmark` 3 项
与 `online` 3 项**都是** `m9` 标记集的子集，文档此前按「`m9` N + `m9_benchmark` 3 + `online` 3」相加是
**重复计数**。CI 不受影响（阶段步骤按**路径**选 `tests/M9` 并用 `-m "not slow and not m6b_benchmark and not
m9_benchmark"`，该排除串由 `test_ci_contract.py:39` 逐字钉住）。

**2026-09-21 修复（M8 跨阶段双导入）**：`tests/M8_metadata_discovery/` 在全量运行中的 15 项失败已修复。
根因是 `tools/m8_*.py` 的双路径导入（`try: from m8_x … except ImportError: from tools.m8_x …`）：当
`tests/M5a`、`tests/M5e`、`tests/M6_crawler` 的 conftest 把 `TOOLS_DIR` 放进 `sys.path` 后，`try` 分支胜出，
于是同一个 schema 模块产生**第二个模块对象**与**第二个 `MetadataGovernanceError` 类**，测试的 `except`
无法捕获工具抛出的异常。修复方式：把这 6 个文件的导入顺序改为优先 `tools.m8_x`（以脚本方式从 `tools/` 内
直接执行时仍回退到裸名，两条路径均已验证），使模块身份与测试的 `from tools import …` 一致。
修复后 `tests/M5a + tests/M8_metadata_discovery` 由 15 failed 变为 101 passed，全量读数由 18 failed 变为 3 failed。
| 合并 `tests platform/tests` | 866 项 | 2026-09-06 collect-only：866 项；根级与受保护平台套件分别验证后的合计口径为 862 passed、1 skipped、3 failed，本次单次 combined run 未取得完整终态 | 三个失败仅为 TXT 精确 parser contract；唯一 skip 为显式 online crawler smoke；历史 850 项及其通过数不代表当前 checkout |
| `tests/M6_crawler/` 离线 | 52 项 + 1 deselected | 2026-08-28：52 passed | `m6_crawler and not online` |
| `tests/M0_M2/` | 18 项 | 2026-09-01 复测：18 passed；2026-08-28：18 passed | 基线回归 |
| 根级 `tests/M0_M2/` | 18 项 | 历史基线 | 从平台原始测试提炼的关键断言，与 `platform/tests/` 同时保留 |
| M6 crawler 前置门禁 | `tests/M6_crawler/` | 独立 job `crawler-offline` | marker `m6_crawler`；默认 mock HTTP；在线 smoke 仅 workflow_dispatch |

M3c 的 10 项测试和 M3d 的 6 项文档测试已启用并全部通过。2026-08-28 M6b 首轮 closeout 复验中，根级测试为
527 passed、1 skipped，平台原始测试为 40 passed；2026-08-29 stabilization 复测中，合并 `tests platform/tests`
套件为 585 passed、1 skipped。2026-09-01 M7 workload 扩展后根级为 631 passed、1 skipped；扩展前根级为 618 passed、1 skipped，平台原始测试
40 passed，合并口径为 671 passed、1 skipped。M7 加入前 2026-08-31 P0 语料治理冻结复测仍为历史证据：根级 553 passed、1 skipped，平台原始测试
40 passed，合并口径为 593 passed、1 skipped；默认 OS/DS/CO 90 题 keyword-only Recall@3 为 0.978，Network
30 题显式评测 Recall@1/3/5 均为 0.000，符合 candidate 不进入索引的预期。当前 limiter/evidence stabilization 使用
显式 marker 分离：M6b 普通套件 126 passed，benchmark 3 passed。当前 blocking benchmark 使用 20 次 warm-up、
200 次 measured、并发 2，evidence `stabilization-20260829-03` 的 p95 为 9.252 ms，200 次均以 `completed` 结束且
规范化重放一致率 100%。受限 Windows 环境若默认临时目录不可写，可使用工作区内的
`pytest --basetemp=.tmp-test\...`。

### 阶段 0：基线建立（M0-M2 回归）

**目的**：将 `platform/tests/` 的 40 个测试提炼为根级回归基线，确保后续阶段不破坏已有功能。

**对应开发任务**：无（已有功能固化）

**测试范围**：

| 测试类 | 验证点 | 回归价值 |
|--------|--------|----------|
| 知识库索引 | frontmatter 解析、按 `##` 切块、课程过滤 | 数据层基础 |
| BM25 检索 | 二元组分词、关键词召回、排序 | 检索层基础 |
| 向量检索 | BGE 嵌入、余弦相似度、top-k | 检索层基础 |
| 多路召回 | RRF 融合、文件去重、模式标识 | 核心链路 |
| 问答服务 | 出处标注、降级摘要、无 LLM 可用 | 核心链路 |
| 复习计划 | 条目去重、日期分配、时间限制 | 业务功能 |
| 测验生成 | 三数据源、难度/标签筛选、答案完整 | 业务功能 |
| 复习排程 | 间隔序列、逾期查询、历史持久化 | 业务功能 |
| 多轮编排 | QA→Quiz→Review-log 串联、来源传递 | 集成链路 |

**执行命令**：
```bash
# 基线回归
pytest tests/M0_M2/ -v

# 完整回归（含 platform/tests/ 原始测试）
pytest -v
# 或显式指定两个测试根目录
pytest tests/ platform/tests/ -v

# Windows 受限环境：将 pytest 临时目录放到仓库内
pytest --basetemp=.tmp-test -v
```

---

### 阶段 1：M3a — 向量库迁移（已完成）

**对应开发任务**：落地共享 `VectorStore` 协议与持久化 `SqliteVectorStore`，保留内存
`LocalVectorStore` 和 BM25 降级；当前两种向量后端均为线性余弦检索。

**测试时间**：M3a 开发完成后

#### 1.1 业务需求验证

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_store_interface.py` | 接口一致性 | 新存储实现与原 `LocalVectorStore` 的 `search()` 签名、返回类型一致 |
| `test_store_interface.py` | 维度兼容 | 嵌入向量维度（BGE-small-zh 为 512）读写一致 |
| `test_store_interface.py` | 空库行为 | 空索引时 `search()` 返回空列表而非报错 |
| `test_migration.py` | 数据完整性 | 迁移后 `count()` 与原索引一致 |
| `test_migration.py` | 检索一致性 | 相同 query 的 top-k 结果文件集合相同（允许排序微调） |
| `test_migration.py` | 幂等性 | 重复迁移不产生重复数据 |
| `test_fallback.py` | 降级路径 | SQLite 向量后端或编码器不可用时按契约回退至内存 linear 或 BM25 |
| `test_fallback.py` | 配置开关 | `SA_VECTOR_STORE=linear` 显式使用内存 `LocalVectorStore` |

#### 1.2 回归校验

```bash
pytest tests/M3a/ -v           # 本阶段测试
pytest tests/regression/ -v    # 回归套件（含 RAG 质量回归）
pytest tests/M0_M2/ -v         # 基线回归
```

#### 1.3 预期风险与缓解

| 风险 | 测试缓解 |
|------|----------|
| 新存储引入精度差异 | `test_migration.py` 允许排序微调，但文件级召回必须一致 |
| 依赖安装失败 | `test_fallback.py` 验证无依赖时自动降级 |
| 数据格式不兼容 | `test_migration.py` 验证向量维度、ID 格式 |

---

### 阶段 2：M3b — 可观测性（已完成）

**对应开发任务**：检索延迟、缓存命中率、问答日志

**测试时间**：M3b 开发完成后

#### 2.1 业务需求验证

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_metrics.py` | 检索延迟记录 | 每次 `/api/v1/search` 调用产生延迟指标 |
| `test_metrics.py` | 缓存命中率 | 索引缓存命中时 `cache_hit=true` |
| `test_metrics.py` | 问答日志 | `/api/v1/qa` 调用写入日志文件 |
| `test_logging.py` | 结构化格式 | 日志为 JSON 格式，含 `timestamp`、`level`、`event` 字段 |
| `test_logging.py` | 敏感信息过滤 | 日志中不出现 `LLM_API_KEY` 等敏感值 |
| `test_health_enhanced.py` | 增强健康检查 | `/health` 返回向量引擎类型、索引大小、缓存状态 |
| `test_health_enhanced.py` | 指标端点 | `/metrics` 或 `/health` 包含延迟统计 |

#### 2.2 回归校验

```bash
pytest tests/M3b/ -v           # 本阶段测试
pytest tests/regression/ -v    # 回归套件
pytest tests/M0_M2/ -v         # 基线回归
```

#### 2.3 预期风险与缓解

| 风险 | 测试缓解 |
|------|----------|
| 日志影响性能 | `test_metrics.py` 验证日志写入为异步/非阻塞 |
| 日志文件膨胀 | `test_logging.py` 验证日志轮转配置 |
| 指标采集改变返回格式 | `test_health_enhanced.py` 验证原有字段不丢失 |

---

### 阶段 3：M3c — 面经库（已完成）

**对应开发任务**：`knowledge/interview/` 按知识点聚合面经题 ≥50

**测试时间**：M3c 开发完成后

#### 3.1 业务需求验证

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_interview_bank.py` | 条目数量 | `knowledge/interview/` 下条目 ≥50（含子目录） |
| `test_interview_bank.py` | frontmatter 完整 | 每条面经含 `title`、`course`、`tags`、`difficulty`；面经统一使用 `course: interview`，课程分类由目录和 tags 表示 |
| `test_interview_bank.py` | 知识点覆盖 | 三门主课（os/ds/co）各有 ≥10 条面经 |
| `test_interview_bank.py` | 检索集成 | 面经条目可被 RAG 检索到（`search("面试 进程")` 命中面经） |
| `test_interview_bank.py` | 格式一致 | 面经遵循 `knowledge/README.md` 写作规范 |

#### 3.2 回归校验

```bash
pytest tests/M3c/ -v           # 本阶段测试
pytest tests/regression/ -v    # 回归套件（含数据完整性）
pytest tests/M0_M2/ -v         # 基线回归
```

---

### 阶段 4：M3d — 文档闭环与最终回归（已完成）

**对应开发任务**：统一项目状态、文档导航、测试统计和 M3 退出条件；不在本阶段新增课程条目。

**测试时间**：M3d 文档变更完成后；6 项文档完整性测试已通过

#### 4.1 业务需求验证

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_docs.py` | README 链接 | 每个子目录 README 中的相对链接可解析 |
| `test_docs.py` | PLAN 一致性 | `docs/PLAN.md` 中标记 ✅ 的条目对应文件实际存在 |
| `test_docs.py` | 知识库导航 | 每门课程 README 的章节地图与实际文件一一对应 |

---

### 阶段 5：回归套件（跨阶段）

**目的**：每次阶段交付后运行，确保新增功能不破坏历史链路。

| 测试文件 | 验证范围 | 运行时机 |
|----------|----------|----------|
| `test_api_contract.py` | 核心 API 端点的请求/响应 schema 不变 | 每阶段 |
| `test_rag_quality.py` | OS/DS/CO 三课 Recall@3 ≥ 0.8（默认 90 题基线） | M3a/M6a/M6b |
| `test_data_integrity.py` | 知识库条目 frontmatter 完整、默认评测集格式合法 | 数据变更 |
| `test_runtime_contracts.py` | 错误码、延迟分位数、入库门禁与生成分层 | 契约或策略变更 |
| `test_sse_contract.py` | SSE metadata/delta/`[DONE]` 帧序、媒体类型与路径隐私 | API/QA 变更 |
| `test_ci_contract.py` | 结构化解析 workflow 的 job/env/step，验证平台基线、非 slow 回归、完整 RAG 门禁与 crawler 隔离 | CI 变更 |
| `test_docs_consistency.py` | 当前/历史基线、默认评测范围、可演进准入状态组合、Decision/Prerequisite ID、批准逻辑与 M6b/M7 sibling 关系 | 文档/路线图/准入变更 |
| `test_governance_contract.py` | docs 导航链接；全部未来阶段未准入时，拒绝受限生产路径、runtime 标识和未来专属依赖 | 文档导航/阻断期生产树变更 |
| `test_path_privacy.py` | `/health` 逻辑 Source 标识、Search/QA/SSE/OpenAPI/日志无宿主路径泄露；治理文档严格扫描（不可变 `docs/plans/references/*-returned.md` 历史归档除外） | API、配置、可观测性或治理测试契约变更 |

### 阶段 5：M4 — 课程知识库规模补齐（已完成并进入 master）

**对应开发任务**：将 OS、DS、CO 三门课程各补齐到至少 20 篇条目，并验证 frontmatter、课程导航和评测集引用。

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_knowledge_scale.py` | 条目数量 | OS/DS/CO 各至少 20 篇 |
| `test_knowledge_scale.py` | frontmatter | 新旧课程条目均含必填字段且 course 正确 |
| `test_knowledge_scale.py` | 课程导航 | 每门课程 README 链接全部条目 |
| `test_knowledge_scale.py` | 评测引用 | `tools/evaluations/*.json` 仅引用实际文件 |
| `test_retrieval_priority.py` | 检索优先级 | 学习问题优先课程笔记、面试问题优先面经、README 不占位 |

### 阶段 6：M5a — 评测入口可复现化（已完成）

**对应开发任务**：统一三课 90 题离线评测入口，支持课程筛选、汇总指标和 JSON 报告。

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_cli.py` | 参数解析 | 默认离线、课程筛选、`--test-set`、`--use-vector` |
| `test_discovery.py` | 评测集发现 | 自动发现 OS/DS/CO，合计 90 题；缺失文件跳过 |
| `test_metrics.py` | 指标聚合 | 未标注跳过、按文件去重命中、加权汇总 |
| `test_report.py` | 报告格式 | 控制台含 mode/summary，JSON 可回读 |

### 阶段 7：M5b — 学习会话状态机（已完成）

**对应开发任务**：把 QA、Quiz、Review-log 编排成服务端学习会话，支持确定性评估和工具轨迹。

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_state_machine.py` | 状态转换 | 创建后 awaiting_answer；答对完成并记复习；答错重试；两次答错结束 |
| `test_state_machine.py` | 错误分支 | 未知会话、完成后再次作答 |
| `test_evaluation.py` | 确定性评估 | 精确匹配、空答案、无关答案、无参考答案降级 |
| `test_api.py` | API 契约 | 200/404/409/422，无 LLM 可运行 |

### 阶段 8：M5c — 学习状态持久化（已完成）

**对应开发任务**：用 SQLite 保存学习会话、答题记录和复习历史，支持 JSON 兼容读取、重启恢复和幂等写入。

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_repository.py` | 仓储读写 | 会话/复习可回读，重复复习写入不加倍 |
| `test_migration.py` | JSON 迁移 | 空库导入、已有数据不覆盖、损坏 JSON 忽略 |
| `test_recovery.py` | 恢复 | 新进程可继续作答；损坏 DB 隔离后重建 |
| `test_idempotency.py` | 幂等 | 重复提交同一答案不占新尝试；同会话复习不递增 |
| `test_concurrency.py` | 并发 | 多线程写入全部可见 |

### 阶段 9：M5d — 最小学习工作台（已完成）

**对应开发任务**：用 FastAPI 静态页提供讲解、作答、反馈和复习记录交互，且不复制服务端状态机。

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_page.py` | 首页 | `GET /` 返回工作台 HTML，必要视图齐全 |
| `test_page.py` | 静态资源 | JS/CSS 可访问 |
| `test_client_contract.py` | API 边界 | 只调用 review-due 与 study-sessions |
| `test_flow.py` | 闭环 | 正式 API 可完成作答并返回下次复习日期 |

### 阶段 10：M5e — 可复现交付（已完成）

**对应开发任务**：离线 CI、一键启动、BGE 缓存/离线说明、冷热启动与学习会话基线。

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_ci.py` | 工作流 | 离线环境变量，独立跑平台 40 项、非 slow 阶段/回归、完整 90 题 RAG 门禁和评测冒烟 |
| `test_start.py` | 启动脚本 | 默认 BM25，`--check` 不拉起服务 |
| `test_eval_smoke.py` | 冒烟 | `--smoke` 限制已标注题量 |
| `test_docs.py` | 文档 | 冷/热启动与会话基线、缓存说明、工具链 |

### 阶段 11：M6a-P0 — crawler 前置收口（marker / 离线 CI 已落地）

**对应开发任务**：登记既有 crawler、固定独立依赖/marker/CI 策略，明确人工审核和 Source 边界。

| 测试文件 | 验证点 |
| --- | --- |
| `test_cleaner.py` / `test_converter.py` / `test_dedup.py` / `test_pipeline.py` | 离线 fixture 下清洗、转换、去重、编排可复现 |
| `test_fetcher.py` | mock HTTP；默认拦截真实 `httpx.Client` |
| `test_ingest_gate.py` / `test_offline_contract.py` | 默认写入候选目录；候选不进检索；默认评测仍为 OS/DS/CO 90 题；统计不含绝对路径 |
| `test_ci.py` | CI 安装 `tools/crawler/requirements.txt`，独立运行 `m6_crawler and not online` |
| `test_online_smoke.py` | 仅 `CRAWLER_ONLINE=1` 或 workflow_dispatch 在线 smoke |

M6a-P0 不等同于 M7 Source 生命周期；持久化注册、同步、删除传播和多源隔离留待 M7。

### 阶段 12：M6a 契约收口与 M6b 只读 Agent Preview（已完成 closeout）

M6a 已于 2026-08-25 获准，现已收口为 `ADMITTED / COMPLETE`。M6a-1 至 M6a-4 冻结了逻辑
Source/document/chunk 身份、职责分离存储、Tool 权限与副作用、稳定安全错误、跨请求 Runner 生命周期、默认
`knowledge-pack` 兼容、静态额外源、default/combined generation 分离和单进程 service lock。正式
`StudySessionService` 仍独占状态转换、答题评估、持久化与 review-log。

M6b 已按独立批准进入 `ADMITTED / COMPLETE`，并实现隔离、默认关闭、只读的 provider-native Agent Preview：
官方 Anthropic adapter、provider-neutral turn/call/usage、只读 `ToolRegistry`、native `tool_use/tool_result` replay、
有限 loop、独立 Bearer 入口、预算/终止语义和 HMAC 元数据 trace。Preview 使用 `DEFAULT_PLUS_EXTRAS`；正式学习
会话保持 `DEFAULT_ONLY`。所有成功和失败路径均不得创建 session、提交答案或写 review/mastery/source 状态。

`tests/M6b/` 当前 129 项（普通套件 126 项、专用 benchmark 3 项；2026-08-28 首轮为 111 项）覆盖 adapter、原生调用与 replay、注册/授权、malformed arguments、retry/timeout/cancel、
budget、duplicate/multiple call、provider stop reason、默认无路由、auth-before-provider-config、并发、scope 隔离、
SQLite 零领域写入、隐私 canary、真实同步工具容量与确定性重放。阻断性 benchmark 使用真实 PreviewService/PreviewAgent/ToolRegistry、
三个真实只读工具、BM25 warm snapshot 和 scripted fake provider，固定 20 次 warm-up、200 次 measured、并发 2；
专用 `m6b_benchmark` marker 从普通 M6b 套件中显式分离。2026-08-29 evidence `stabilization-20260829-03` 的 p95 为
9.252 ms，200 次均 `completed`，规范化重放一致率 100%。默认门禁不配置 provider 凭据、
不联网；真实 Anthropic smoke 仅手工显式 opt-in，本次未运行，也不作为默认 CI 或性能声明。

M6b 不实现 ReAct Runner、写工具、checkpoint、幂等写或正式状态机替换；这些仍属于 M10。M7 已在独立人工批准后成为
`ADMITTED / COMPLETE`；M7 Source Registry、source-local FULL/INCREMENTAL/delete/isolation 与 FTS5/vector/offline
fail-closed 合同的 `tests/M7/` 已独立落地，技术测试本身不产生批准，也不改变 M6b 行为。离线 M6b 检索测试固定 BM25，
不依赖本机向量模型；请求 timeout/cancellation 后不再继续 Agent 工作，已开始的非协作同步函数仍占用实际工作槽至自然结束。

## 三、执行矩阵

| 阶段 | 本阶段测试 | 回归测试 | 基线测试 | RAG 评测 |
|------|-----------|----------|----------|----------|
| M0-M2 基线 | — | — | `tests/M0_M2/` | `tools/run_evaluation.py` |
| M3a 向量库 | `tests/M3a/` | `tests/regression/` | `tests/M0_M2/` | `tools/run_evaluation.py` |
| M3b 可观测性 | `tests/M3b/` | `tests/regression/` | `tests/M0_M2/` | — |
| M3c 面经库 | `tests/M3c/` | `tests/regression/` | `tests/M0_M2/` | `tools/run_evaluation.py` |
| M3d 文档闭环 | `tests/M3d/` | `tests/regression/` | `tests/M0_M2/` | — |
| M4 知识库规模补齐 | `tests/M4/` | `tests/regression/` | `tests/M0_M2/` | `tools/run_evaluation.py` |
| M5a 评测入口 | `tests/M5a/` | `tests/regression/` | `tests/M0_M2/` | `python tools/run_evaluation.py` |
| M5b 学习会话 | `tests/M5b/` | `tests/regression/` | `tests/M0_M2/` | — |
| M5c 学习持久化 | `tests/M5c/` | `tests/regression/` | `tests/M0_M2/` | — |
| M5d 学习工作台 | `tests/M5d/` | `tests/regression/` | `tests/M0_M2/` | — |
| M5e 可复现交付 | `tests/M5e/` | `tests/regression/` + `platform/tests/` | `tests/M0_M2/` | smoke + 独立 slow 90 题门禁 |
| M6 crawler 前置 | `pytest tests/M6_crawler -m "m6_crawler and not online"` | `tests/regression/` | `tests/M0_M2/` | 默认 90 题发现 + smoke |
| M6a-1/M6a-2/M6a-3 契约、适配与拓扑门禁 | `tests/M6a/`（`m6a`） | `tests/regression/` | `tests/M0_M2/` + `platform/tests/` | `tools/run_evaluation.py` |
| M6b 只读预览 | `tests/M6b/`（`m6b`）+ blocking offline benchmark | `tests/regression/` | `tests/M0_M2/` + `platform/tests/` | 默认 90 题；真实 provider smoke 仅手工可选 |
| 外部资料只读盘点 | `tests/source_inventory/`（`source_inventory`） | 不要求 | 使用 tmp_path 迷你树 | 不建索引、不计入 RAG 门禁 |
| M7 lifecycle + FTS5/vector/offline + Search/QA overlay | `tests/M7/`（`m7`，270 项） | `tests/regression/` | `tests/M0_M2/` + `platform/tests/` | 证明 source-local 合同、generation-bound vector identity、Search/QA 的受信任内部 principal overlay、M7-2 snapshot identity/LRU、M7-4 exact-query/query-encode、M7-5 READY/CURRENT 指针一致性、M7-6 真实五格式 parser/normalized-document 与 lifecycle/provenance E2E；不证明 preview 用户源或 M7 阶段退出。`m7_exit=true` 只覆盖 `sa.source.benchmark.v1` |
| M8–M10 准入准备 | 不创建 `tests/M8/`、`tests/M10/` 等阶段生产测试树；M8 离线治理套件 `tests/M8_metadata_discovery/`（75 项）与 M9 套件 `tests/M9/`（354 项）均自 2026-09-21 起纳入 CI | `test_docs_consistency.py` + `test_governance_contract.py` | 已有保护基线 | 不构成能力、性能通过或开工批准 |
| M9 目标驱动计划（生成 / 分日每日容量 / 生命周期 / 偏差 / 只读复习历史、mastery、Source 摘要与先修关系投影 / 受限检索接缝 / 计划身份往返保真 / 默认关闭的外部 AI 路径与 1K 冻结比较 / 单轮 output 预算 / 唯一写权威证据 / v1.5 冻结预算矩阵 + opt-in 真实 provider 读数） | `tests/M9/`（`m9` 354 项；其中 `m9_benchmark` 3 项与 `online` 3 项 opt-in 非门禁均为其子集，2026-09-21 起纳入 CI） | `tests/regression/` + `tests/M0_M2/` | `platform/tests/` + `tests/M5b/` + `tests/M5c/` | 证明确定性生成与**每日容量**（判据是「超出当日可用容量 `hours_per_day × 60 − 10` 的天**恰好只装一个**任务」——不是「绝不超出」：单条任务本身就装不下时该天必然超出，且**第 2 天起**（当日容量扣了复习缓冲，`hours_per_day × 60 − 10 < 25`，即 `hours_per_day < 35/60 ≈ 0.5833`）**每一天**都踩到这条守卫，保证在该区间内**完全空转**；**第 1 天不扣缓冲**，容量是 `hours_per_day × 60`，要靠最小任务保证则需 `hours_per_day < 25/60 ≈ 0.4167`，`0.5 小时/天` 下 142 天里 120 天超出声明的每日上界（第 1 天也在其中，因为该请求首条任务 50 分钟 > 30）；`total_days` 回报真实天数、允许超过请求窗口，且 `total_days`/`total_hours` 与逐日明细自洽）、计划身份含派生输入摘要（复习/mastery/每日学时）、采纳/进度/重规划与消费台账、只读 mastery 投影的 file 路径映射与零写入、只读 Source 摘要的 `usable` 规则与懒装配不建库、只读先修关系投影的同目录兄弟边解析与先修合法顺序（真语料 `violations == 0`）；4a 起在**服务层接缝**上证明 stale/deleted 源拒绝（未新增公开路由，故**不是**公共 API 上的端到端隔离）；4b 起证明计划身份按 principal 分隔与记录往返保真（principal 是内部记录键，经单点 `_public_plan` 剥离，不进 HTTP 响应体）；4c 起证明复习历史是**活投影**而非构造时快照（同一进程内新落的复习立即反映到 `reviewed`、排序与 `plan_id`，且守卫钉在 `main.py` 的装配上）；步骤 6 窄口径起在**离线 stub provider** 上证明外部 AI 路径的最小披露是结构性的、每类失败逐字回退且不落库，并在冻结任务集 1K 语料上证明**输入有界**（prompt 不随语料规模增长）、两路径先修违反为 0、确定性可重放；另以**动态源文件枚举**证明「正式 mastery 只有一个写入权威」——写 `study_sessions`/`answer_attempts` 者恰好是 `learning_store.py`，M9 的 8 个模块与写权威**导入不可达**（既有测试是逐模块证明「我没写」，本项补的是**闭包**）。**不证明**：mastery 写入本身（`m9.mastery-write` 仍在 `excluded`——该证据只证明**不存在第二套权威**，不证明 M9 获得写能力）、10K/100K 容量、**性能**（v1.5 的冻结预算矩阵证明预算被**强制执行**，不是被测量——stub 下延迟是桥接开销、成本由脚本化 usage 算出；`max_input_tokens`/`model_timeout_seconds` **不在本地执行**；累积值 `max_output_tokens` 则**没有运行期执行点**（不送 provider、也无用量累计核验，但**构造期被校验**并据此给单轮值定上界）——**别把这条读成「output 预算整体没有执行点」**：`max_turn_output_tokens`（**单轮**值，默认 1024）自 2026-09-22 起**在本地执行**，它就是传给 `create_turn` 的 `max_tokens`；`deadline` 守卫**放弃**线程而非取消它；每日容量的**绝对**保证（单条超容量任务仍会让该天超出——保证是「每天**至多一个**任务造成超出」，且与 `review_plan.py` 刻意分叉）、真实 provider 的延迟/成本/失败模式（arm B 显式 opt-in、**非门禁**且本次未运行；1K 读数**不是**容量声明——M9 既不存储也不索引 1K chunks）；冻结范围**仅限 M9 外部 AI 路径**，遵循度仍为**定性**。**2026-09-22 收口**：owner 已批准 `M9 COMPLETE`（`completion_approval` 见 M9 计划 §4.5），故「不构成阶段退出」一条**不再成立**；但上列**不证明**各项**仍然成立**——收口**不**产生真实 provider 读数、**不**扩大冻结范围、**不**给 mastery 写入能力。另登记一条**已知限制**：外部 AI 路径的 `PlanAIRequest` **不含先修关系**，而 `_ai_order` 拿先修违反数作闸门丢弃整个置换——模型被要求满足一个从不告诉它的约束；第三方 provider 探针（**非 arm B、非 M9 证据、不进门禁**）实测披露先修边可把采纳率由 `5/10` 提到 `8/10`，仅改措辞无效（`4/10`） |

## 四、pytest 配置

```bash
# 运行全部测试
pytest tests/ -v

# 运行指定阶段
pytest tests/M3a/ -v -m m3a

# 运行 M5a 评测入口测试
pytest tests/M5a/ -v -m m5a

# 运行 M5b 学习会话测试
pytest tests/M5b/ -v -m m5b

# 运行 M5c 持久化测试
pytest tests/M5c/ -v -m m5c

# 运行 M5d 学习工作台测试
pytest tests/M5d/ -v -m m5d

# 运行 M5e 可复现交付测试
pytest tests/M5e/ -v -m m5e

# 运行 crawler P0 离线测试（需 tools/crawler/requirements.txt）
pytest tests/M6_crawler -v -m "m6_crawler and not online"

# 运行 M6b fake-provider 普通套件（默认离线，不需要 Anthropic key；显式排除 blocking benchmark）
PYTHONPATH=platform SA_USE_VECTOR=false pytest tests/M6b -m "not m6b_benchmark" -q --tb=short

# 单独运行阻断性 M6b benchmark。必须同时给出证据 ID；报告路径文件名必须包含该 ID。
# 报告以 exclusive-create 写入，已存在则失败，禁止覆盖历史 artifact。
M6B_BENCHMARK_EVIDENCE_ID=stabilization-20260829-03 \
M6B_BENCHMARK_REPORT=reports/m6b-offline-preview-benchmark-stabilization-20260829-03.json \
  PYTHONPATH=platform SA_USE_VECTOR=false pytest tests/M6b -m m6b_benchmark -q --tb=short

# 运行 M7 lifecycle + source-local FULL/INCREMENTAL/delete/isolation/FTS5/offline contract 阶段测试
# parser 合同冻结于 CPython 3.11.9；先确认解释器版本，避免在 3.13 下把预期 fail-closed 误判为实现回归。
test "$(./platform/.venv311/Scripts/python -c 'import platform; print(platform.python_version())')" = "3.11.9"
PYTHONPATH=platform SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ./platform/.venv311/Scripts/python -m pytest tests/M7/ -v -m m7

# 完整根级冻结环境复验（online crawler smoke 仍按 marker 跳过）
PYTHONPATH=platform SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ./platform/.venv311/Scripts/python -m pytest tests/ -v

# 运行外部资料只读盘点测试（使用 tmp_path 迷你树，不扫描真实 D:\111_Others_Subjects）
pytest tests/source_inventory -v -m source_inventory

# 显式 crawler 在线 smoke（默认不跑）
# Unix: CRAWLER_ONLINE=1 pytest tests/M6_crawler -v -m "m6_crawler and online"
# PowerShell: $env:CRAWLER_ONLINE=1; pytest tests/M6_crawler -v -m "m6_crawler and online"

# 运行回归套件
pytest tests/regression/ -v

# 运行基线 + 回归
pytest tests/M0_M2/ tests/regression/ -v

# 仅运行慢速测试（如 RAG 评测）
pytest tests/ -v -m slow

# 并行执行（需 pytest-xdist）
pytest tests/ -v -n auto
```

## 五、测试维护规范

### 5.1 新增阶段流程

1. 在 `tests/` 下新建目录（如 `tests/M4/`）
2. 创建 `conftest.py`，import 根 conftest 的共享 fixtures
3. 编写测试文件，遵循命名 `test_*.py`
4. 如需回归，在 `tests/regression/` 新增文件（不修改已有回归文件）
5. 更新本计划文档

### 5.2 修改存量测试的红线

- ❌ **不要**修改 `tests/conftest.py` 的已有 fixtures（只能追加）
- ❌ **不要**修改其他阶段的测试文件；若已冻结的公开契约与安全/隐私不变量直接冲突，必须在获批计划中逐项记录唯一迁移例外
- ⚠️ **已知缺口：后续阶段新增默认公开路由没有合法渠道**（2026-09-21 记录）。上述唯一例外只覆盖「与安全/隐私
  不变量直接冲突」，但 `tests/M6a/test_closeout_contracts.py::test_openapi_public_paths_remain_exact` 断言的是默认
  公开面的**精确集合**（同时断言子集与「无未登记路径」）。因此后续阶段只要新增一条**默认开启**的公开路由，该断言
  必然失败；而该测试在 `offline-ci.yml` 中运行且无 `continue-on-error`，回退会让 CI 永久变红，且仓库规则中不存在
  「已知基线失败」这一记录类别可登记。结论：现行规则下，后续阶段新增默认公开路由**没有合法登记渠道**。
  - 先例：M9 的 5 条 `/api/v1/plans*` 路由由 `f03d205` 登记进 `PUBLIC_API_PATHS`（纯追加 8 行，未改动既有断言）；
    owner 于 2026-09-21 追认为**一次性迁移例外**，逐项记录在 `docs/plans/m9-goal-driven-planning-plan.md`。该追认
    不满足原例外的字面前提（公开面扩张，非安全/隐私冲突），属 owner 对例外机制的一次性扩展。
  - 反例（正向数据点，2026-09-21）：M9 只读 mastery 投影增量**未新增任何公开路由**，能力经既有
    `POST /api/v1/plans` 与 `replan` 可达，`PUBLIC_API_PATHS` 未改动、`test_openapi_public_paths_remain_exact`
    保持绿。说明该缺口虽无合法登记渠道，但**不是**「后续阶段必然触雷」——把新能力挂在既有路由上即可完全规避。
  - 历史先例（已核实）：本红线在 M9 之前已被越过两次，且均未登记迁移例外——`5eae89e`（2026-09-11，M6a 冻结后
    16 天）重构了 `tests/M6a/test_closeout_contracts.py` 的 markdown 链接 helper；`ee73dd2`（2026-09-06，M7）
    改写了 `tests/M6b/test_preview_service.py`。M9 的 `f03d205` 是其中**唯一**有记录的一次。
  - 后续同类改动：必须同样在获批计划中**逐项列出**新增路由，并经 owner 明确追认后方可登记；不得默认沿用。
- ✅ 可以在 `tests/regression/` 新增回归用例
- **`tests/regression/test_docs_consistency.py` 是例外，且是既成惯例**：它是跨阶段文档一致性套件，
  在**每次阶段状态变更**时都随事实移动（`git log` 计 13 次，含 `081f203`/`b847ed4` 两次 M9 准入与
  2026-09-22 的 M9 收口）。§5.1 步骤 4 的「不修改已有回归文件」按字面不覆盖它，故在此显式登记：
  M9 收口把 M9 状态断言由 `IN_PROGRESS` 改为 `COMPLETE` 并**加强**为同时校验完成批准五字段；
  同日补全时又在同一文件**新增**两道防漂移护栏（见头部 2026-09-22 第二条）。这是**就地扩写既有
  套件**，不是新增文件；记在此处以免日后被读成「规则本就允许」。
- 本次 `/health.knowledge_root` 从宿主路径迁移为逻辑标识 `knowledge-pack`，仅收紧
  `tests/M3b/test_health_enhanced.py::test_health_shows_knowledge_root` 的旧 suffix 断言；其他历史阶段测试保持不变
- ✅ 可以在 `tests/utils/` 新增工具函数

### 5.3 测试数据管理

| 数据类型 | 来源 | 隔离方式 |
|----------|------|----------|
| 知识库内容 | `knowledge/` 真实数据 | 只读，不修改 |
| 复习历史/学习状态 | SQLite（`learning_state.sqlite3`） | `tmp_path` 下独立数据库；`review_history.json` 仅用于兼容迁移测试 |
| 评测集 | `tools/evaluations/*.json` | 只读 |
| 向量索引 | 测试内存或 `tmp_path` SQLite | fixture 隔离 |
| M7 Source Registry | `tmp_path` 下独立 SQLite | 不接触默认启动路径、学习状态库或真实用户资料 |

---

*维护：每阶段开发完成后更新本计划。当前根级/回归总数以 `pytest --collect-only` 为准，collect-only 不等于
测试通过。2026-09-06 当前 collect-only 为根级 826 项、与 `platform/tests/` 合并为 866 项；当前 checkout 的离线
keyword-mode 完整根级结果为 CPython 3.13.3 的 822 passed、1 skipped、3 个精确 TXT contract failures，CPython 3.11.9
精确环境的 825 passed、1 skipped；与受保护 `platform/tests/` 分别验证后的合计口径为 CPython 3.13.3 的
862 passed、1 skipped、3 个相同 TXT contract failures，但本次单次 combined run 未取得完整终态；
`tests/regression/` 为 62 passed，受保护 `platform/tests/` 为 40 passed。`tests/M7/` 当前收集 270 项；Python 3.13.3 执行结果为 267 passed / 3 failed，三个失败均是精确
`cpython-textio==3.11.9` 合同下的 TXT `PARSER_UNAVAILABLE` fail-closed 行为。此前的根级/合并统计均为历史证据：2026-09-02 为根级 657 collected、656 passed、1 skipped与合并
697 collected、696 passed、1 skipped；2026-09-01 M7 workload 扩展后为根级 632 collected、631 passed、1 skipped
与合并 672 collected、671 passed、1 skipped；扩展前为根级 619 collected、618 passed、1 skipped，合并 659 collected、
658 passed、1 skipped。M7 当前 isolated 基线为 2026-09-04 M7-5 delete generation/recovery 合同 205 collected / 205 passed（历史过程证据）；同日 pointer 合同历史 202 collected；历史 M7-4 收口复验为 198 collected / 198 passed；历史 M7-2 snapshot 为 195 collected / 195 passed；2026-09-03 协议内 p50 复用优化历史为 190 collected / 190 passed；同日 generation-bound vector 历史为 189 collected / 189 passed；同日 Search overlay 历史为 177 collected / 177 passed；同日 FTS5/offline 历史为 162 collected / 162 passed；历史 2026-09-02 为 143 collected / 143 passed；历史 sync 合同为 119 collected / 119 passed；历史 M7-1 基线为
77 collected / 77 passed。M7 加入前的 2026-08-31 P0 语料治理冻结复测仍保留为历史证据：根级 554 collected、553 passed、
1 skipped；根级与平台原始测试合并为 594 collected、593 passed、1 skipped。2026-08-28 M6b closeout 首轮中，根级实际
结果为 528 collected、527 passed、1 skipped；2026-08-29 stabilization 合并套件复测为 586 collected、585 passed、
1 skipped。平台原始测试固定保留 40 项并在 offline CI 独立运行。M6b 2026-08-28 首轮 111 项；当前普通套件
126 passed、3 deselected，专用 benchmark 3 passed（共收集 129 项）；blocking fake-provider benchmark 已通过；2026-08-31
默认评测仍固定为 OS/DS/CO 90 题，Network candidate 显式评测 Recall@1/3/5 均为 0.000；crawler P0 使用独立 marker
`m6_crawler` 和 job `crawler-offline`；只读盘点使用 `source_inventory`；默认 OS/DS/CO 90 题质量门禁独立运行 slow 回归。*

# 迭代测试计划 · StudyAssistanceAgent

> 起始日期：2026-08-17 · 更新：2026-08-18（M0-M4 已完成；M5a~M5e 已完成）

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
│   └── test_knowledge_scale.py   # 数量、frontmatter、导航与评测引用
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
├── regression/           # 跨阶段回归套件
│   ├── conftest.py       # 回归专用 fixtures
│   ├── test_api_contract.py      # API 契约稳定性
│   ├── test_rag_quality.py       # RAG 质量回归
│   └── test_data_integrity.py    # 数据完整性
│
└── utils/                # 测试工具（非测试文件）
    └── helpers.py        # 通用断言与辅助函数
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

### 当前测试基线

| 测试范围 | 收集数量 | 当前结果 | 说明 |
|----------|----------|----------|------|
| 根级 `tests/` | 187 项 | 187 collected | 阶段测试 + 回归套件（M0_M2 18、M3a 22、M3b 13、M3c 10、M3d 6、M4 14、M5a 26、M5b 18、M5c 14、M5d 10、M5e 15、regression 21） |
| `platform/tests/` | 40 项 | 40 passed | 原始平台冒烟/功能测试 |
| M3 验收门禁 | 130 项 | 130 passed | 根级测试 90 项 + 平台原始测试 40 项；包含 M3d 文档检查 |
| M4 验收门禁 | 144 项 | 144 passed | 根级测试 104 项 + 平台原始测试 40 项；包含知识库规模检查 |
| M5a 本阶段 | 26 项 | 26 passed | 参数解析、评测集发现、指标聚合、报告格式 |
| M5b 本阶段 | 18 项 | 18 passed | 状态机、评估、降级、API 契约 |
| M5c 本阶段 | 14 项 | 14 passed | 仓储、迁移、恢复、幂等、并发 |
| M5d 本阶段 | 10 项 | 10 passed | 首页视图、API 白名单、学习闭环 |
| M5e 本阶段 | 15 项 | 15 passed | CI、一键启动、评测冒烟、交付文档 |

M3c 的 10 项测试和 M3d 的 6 项文档测试已启用并全部通过。受限 Windows 环境若默认临时目录不可写，可使用工作区内的 `pytest --basetemp=.tmp-test\...`。

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

**对应开发任务**：接入 sqlite-vec/Chroma 替换线性扫描

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
| `test_fallback.py` | 降级路径 | sqlite-vec 不可用时自动降级为线性扫描 |
| `test_fallback.py` | 配置开关 | `SA_VECTOR_STORE=linear` 强制使用旧引擎 |

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
| `test_api_contract.py` | 全部 8 个 API 端点的请求/响应 schema 不变 | 每阶段 |
| `test_rag_quality.py` | OS/DS/CO 三课 Recall@3 ≥ 0.8（量化基线） | M3a（向量库变更）|
| `test_data_integrity.py` | 知识库条目 frontmatter 完整、评测集格式合法 | M3c（数据变更）|

### 阶段 5：M4 — 课程知识库规模补齐（已完成并进入 master）

**对应开发任务**：将 OS、DS、CO 三门课程各补齐到至少 20 篇条目，并验证 frontmatter、课程导航和评测集引用。

| 测试文件 | 测试项 | 验证点 |
|----------|--------|--------|
| `test_knowledge_scale.py` | 条目数量 | OS/DS/CO 各至少 20 篇 |
| `test_knowledge_scale.py` | frontmatter | 新旧课程条目均含必填字段且 course 正确 |
| `test_knowledge_scale.py` | 课程导航 | 每门课程 README 链接全部条目 |
| `test_knowledge_scale.py` | 评测引用 | `tools/evaluations/*.json` 仅引用实际文件 |

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
| `test_ci.py` | 工作流 | 离线环境变量，不下载模型，跑阶段/回归/评测冒烟 |
| `test_start.py` | 启动脚本 | 默认 BM25，`--check` 不拉起服务 |
| `test_eval_smoke.py` | 冒烟 | `--smoke` 限制已标注题量 |
| `test_docs.py` | 文档 | 冷/热启动与会话基线、缓存说明、工具链 |

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
| M5e 可复现交付 | `tests/M5e/` | `tests/regression/` | `tests/M0_M2/` | — |

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
- ❌ **不要**修改其他阶段的测试文件
- ✅ 可以在 `tests/regression/` 新增回归用例
- ✅ 可以在 `tests/utils/` 新增工具函数

### 5.3 测试数据管理

| 数据类型 | 来源 | 隔离方式 |
|----------|------|----------|
| 知识库内容 | `knowledge/` 真实数据 | 只读，不修改 |
| 复习历史 | `review_history.json` | `tmp_path` + mock |
| 评测集 | `tools/evaluations/*.json` | 只读 |
| 向量索引 | 内存构建 | session 级 fixture |

---

*维护：每阶段开发完成后更新本计划，新增测试项与执行结果。当前基线：121 项收集，107 passed、14 skipped（2026-08-17）。*

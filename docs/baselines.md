# RAG 评测基线记录

> 记录每次评测的数据，追踪检索效果随知识库和策略迭代的变化。
> 评测集：`tools/evaluations/{os,ds,co}.json`，共 90 题（OS 38 + DS 28 + CO 24）。
> 评测工具：`tools/run_evaluation.py`（M5a 起默认一条命令跑完全部三课，离线 BM25）

## 基线 v0 — 2026-08-12（M1 起点，OS 知识库 6 篇）

### keyword-only（仅 BM25 bigram 关键词）

| k | Recall@k | Precision@k | F1 | AvgLatency(ms) |
|---|---|---|---|---|
| 1 | 0.850 | 0.850 | 0.850 | 3.5 |
| 3 | 1.000 | 0.333 | 0.500 | 2.5 |
| 5 | 1.000 | 0.205 | 0.340 | 2.4 |

- 模式：纯 BM25，无向量路
- Recall@3 已达 1.000，OS 知识库规模小（6 篇 20 切片）时关键词检索已足够
- 延迟极低（~3ms），无 GPU 依赖

### hybrid（BM25 + BGE 向量 + RRF 融合 k=60）

| k | Recall@k | Precision@k | F1 | AvgLatency(ms) |
|---|---|---|---|---|
| 1 | **0.950** | 0.950 | 0.950 | 1166.2 (首次) / 33.7 (warm) |
| 3 | 1.000 | 0.333 | 0.500 | 33.7 |
| 5 | 1.000 | 0.200 | 0.333 | 34.3 |

- 模式：向量 + BM25 双路 RRF 融合
- 嵌入模型：`BAAI/bge-small-zh-v1.5`（本地 CPU 推理）
- 首次请求需加载模型（~1.2s），后续请求 ~34ms
- Recall@1 提升 **+11.8%**（0.85 → 0.95）— BGE 向量语义匹配在 top-1 有显著增益

### 对比分析

| 指标 | keyword-only | hybrid | 差值 |
|---|---|---|---|
| Recall@1 | 0.850 | **0.950** | +11.8% |
| Recall@3 | 1.000 | 1.000 | 持平 |
| Recall@5 | 1.000 | 1.000 | 持平 |
| Precision@1 | 0.850 | 0.950 | +11.8% |
| Precision@5 | 0.205 | 0.200 | -2.4%（可忽略） |
| Latency (warm) | 2.5ms | 34ms | +13×（仍 < 100ms 目标） |

### 结论

1. **hybrid 模式在 Recall@1 上有明显优势**（+11.8%），语义匹配帮助精确定位
2. **当前 OS 知识库仅 6 篇，两种模式 Recall@3 均达 1.000** — 内容密度高、覆盖充分
3. **随着知识库扩写（6→15+ 篇），hybrid 优势会更显著** — 更多条目意味着关键词命中噪声增加，向量语义消歧价值更大
4. **延迟在可接受范围**：warm 后 34ms < 100ms 目标
5. **M1 目标 Recall@3 ≥ 0.8 已提前达成** — 后续扩写知识库时持续跟踪，防止退化

### 下一步

- ~~M1a 扩写 OS 知识库至 15 篇后重新评测~~ → 已完成，见下方基线 v1
- 后续课程（DS/CO）建评测集时同步跑基线

## 基线 v1 — 2026-08-12（OS 知识库 15 篇，评测集扩至 33 题）

### 扩容后回归与根因

- 知识库 6→15 篇后，切片 20→89 片，重跑评测（原 20 题评测集）出现**回归**：
  `Recall@3 1.000 → 0.650`（Recall@1 0.850 → 0.650），触发了 M1 退出条件（Recall@3 ≥ 0.8）告警。
- **根因（代码缺陷，非知识库问题）**：BM25 候选池 `SA_BM25_POOL=50` 只检索**前 50 片**（按文件路径排序）。
  扩容后 process-scheduling.md（idx 50-55）与 synchronization.md（idx 70-75）等条目**落在候选池之外**，
  BM25 关键词路完全看不到它们 → 调度/同步相关 7 题全部失配，只能靠向量路兜底。
- **修复**：`SA_BM25_POOL` 默认改为 `0` = 不限制（全库检索）。个人知识库规模（几百片）全量 BM25 毫秒级，
  截断池在扩容后静默丢文件，是纯负收益的「优化」。改动：`config.py` / `retrieval.py` / `main.py` / `.env.example` / `platform/README.md`。

### 修复后：hybrid，15 篇 / 89 片 / 33 题评测集

| k | Recall@k | Precision@k | F1 | AvgLatency(ms) |
|---|---|---|---|---|
| 1 | 0.833 | 0.879 | 0.855 | 448.6 (含模型加载) / ~45 (warm) |
| 3 | **0.970** | 0.343 | 0.507 | 52.2 |
| 5 | 1.000 | 0.218 | 0.358 | 51.2 |

- 评测集扩至 33 题，**覆盖全部 15 篇条目**（原 20 题只标注了 6 篇，无法验证扩容后的知识库）
- 33 题中 32 题 top-3 命中全部相关文件；2 题标注了「双相关文件」，top-3 只返回了最优单篇
  （如「分页和分段的区别」top-3 全为 segmentation-paging.md，未含 memory-management.md），故 Recall@3=0.970 而非 1.000
- Recall@5 = 1.000：所有 33 题的相关文档都在 top-5 内，检索无系统性漏洞
- **M1 退出条件 Recall@3 ≥ 0.8 达标**（0.970），且评测集覆盖面从 6 篇扩到 15 篇，指标更可信

### 扩容 v1 与基线 v0 对比（hybrid，口径均为「标注相关文档全命中」）

| 指标 | v0（6 篇/20 题） | v1（15 篇/33 题） | 说明 |
|---|---|---|---|
| Recall@1 | 0.950 | 0.833 | 条目增多后 top-1 竞争加剧，语义消歧仍有提升空间 |
| Recall@3 | 1.000 | 0.970 | 达标；双相关题返回单篇的度量口径差异 |
| Recall@5 | 1.000 | 1.000 | 持平，全量召回无遗漏 |
| Latency (warm) | ~34ms | ~52ms | 全库 BM25 + 更多切片，仍在目标内 |

### 结论与经验

1. **「评测集覆盖 = 知识库覆盖」**：知识库扩到 15 篇后必须同步扩评测集，否则指标验证的是旧知识库
2. **候选池截断是静默正确性缺陷**：规模小时无害，扩容后丢文件不报错只降指标；宁可全库检索也不要截断
3. **回归 → 定位 → 修复 → 数据驱动验证**的闭环有效：从 0.650 恢复到 0.970，退出条件重新达成

---

## 基线 v2 — 2026-08-18（M5a，三课 90 题离线 BM25；历史基线）

命令：

```bash
python tools/run_evaluation.py -k 1,3,5
```

- 模式：`keyword-only`（`SA_USE_VECTOR=false`）
- 环境：无网络、无 BGE 模型缓存、无 LLM key
- 题数：OS 38 + DS 28 + CO 24 = 90，全部带标注
- 延迟按每题一次 `max(k)` 检索统计

| 课程 | 题数 | Recall@1 | Recall@3 | Recall@5 | Precision@3 | F1@3 | AvgLatency(ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OS | 38 | 0.776 | **1.000** | 1.000 | 0.360 | 0.529 | 37.2 |
| DS | 28 | 0.536 | **0.929** | 0.964 | 0.310 | 0.464 | 39.0 |
| CO | 24 | 0.625 | **1.000** | 1.000 | 0.333 | 0.500 | 35.7 |
| 汇总 | 90 | 0.661 | **0.978** | 0.989 | 0.337 | 0.501 | 37.4 |

### 结论

1. **一条命令可复现三课评测**，不再依赖内置 3 题示例或手工指定 `--test-set`。
2. **M5a 当时的退出条件 Recall@3 ≥ 0.8 全部达标**，与 M4 离线口径一致（OS 1.000、DS 0.929、CO 1.000）。
3. 这组数字是 2026-08-18 的历史验收证据，不代表任意后续 checkout 的实时结果。
4. JSON 报告默认写到未跟踪的 `reports/`，只有确认后的数字才追加到本文档。

## 当前 checkout 复测 — 2026-08-24（三课 90 题离线 BM25）

命令（Git Bash）：

```bash
SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ./platform/.venv/Scripts/python tools/run_evaluation.py -k 1,3,5
```

- 模式：`keyword-only`；默认发现集合固定为 OS/DS/CO，Network 30 题未进入本次评测。
- 题数：OS 38 + DS 28 + CO 24 = 90，全部带标注。
- 环境：离线开关开启，不下载 BGE，不要求 LLM key。
- 延迟按每题一次 `max(k)` 检索统计，只作为本次本机快照，不作跨机器性能承诺。

| 课程 | 题数 | Recall@1 | Recall@3 | Recall@5 | Precision@3 | F1@3 | AvgLatency(ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OS | 38 | 0.645 | **0.987** | 1.000 | 0.351 | 0.518 | 39.2 |
| DS | 28 | 0.607 | **0.929** | 0.964 | 0.310 | 0.464 | 38.8 |
| CO | 24 | 0.625 | **1.000** | 1.000 | 0.333 | 0.500 | 38.3 |
| 汇总 | 90 | 0.628 | **0.972** | 0.989 | 0.333 | 0.496 | 38.8 |

### 复测结论

1. OS Recall@3 相对 2026-08-18 历史快照由 1.000 变为 0.987；历史记录保留，不静默覆盖。
2. DS 与 CO Recall@3 分别为 0.929 和 1.000；三门课程仍全部满足自动质量门槛 `Recall@3 >= 0.8`。
3. 当前加权 Recall@3 为 0.972；自动门禁仍按每门课程阈值判断，不把某次精确快照固化为硬编码阈值。
4. Network 评测集继续通过 `--test-set tools/evaluations/network.json` 显式运行，不扩大默认 90 题集合。

## M6a-2 自动化门禁复验 — 2026-08-26（历史检查点 `b9bb31b`）

本记录是提交 `b9bb31b` 的历史证据：当时只关闭 M6a-2 默认 `knowledge-pack` 兼容适配的自动化复验，
不批准或完成整个 M6a。数字、命令和状态都绑定该检查点，不得当作当前工作区结果。当时 M6a-3
（确定性工具、StateMachineRunner 与启动期静态额外源）尚未开始。

- 分支：`feature/m6a-harness-skeleton`；记录提交 `b9bb31b`；当时工作区在证据文档提交后保持干净。
- 环境：Windows 11 Home，Python 3.13.3，pytest 9.1.1，Git Bash；使用现有 `platform/.venv`。
- 默认离线评测命令：
  `SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./platform/.venv/Scripts/python tools/run_evaluation.py -k 1,3,5`
- 默认评测发现 OS 38 + DS 28 + CO 24 = 90；Network 未自动加入。
- Recall@3：OS 0.987、DS 0.929、CO 1.000，汇总 0.972；三课均满足 `Recall@3 >= 0.8`。
- 根级测试命令：`./platform/.venv/Scripts/python -m pytest tests/ -q`；312 collected，311 passed、1 skipped。
- 根级 skip 为显式在线 crawler smoke，符合默认离线门禁，不是失败。
- M6a 阶段测试：`tests/M6a/` 共 36 项，全部通过（协议契约 26 项、默认包适配 10 项）。
- 受保护平台测试命令：`./platform/.venv/Scripts/python -m pytest platform/tests/ -q`；40 项全部通过。
- 边界人工审查：API/OpenAPI 兼容字段未发现无意变化；Search/QA/SSE/OpenAPI、日志和 LLM fallback
  未发现宿主绝对路径；默认评测仍固定为 OS/DS/CO 三课 90 题；未发现 M6b ToolRegistry/preview 或
  M7 运行时 Source 生命周期能力被提前接入。当时 M6a-3 生产目录尚未创建。

### 当时结论

M6a-1 协议契约与 M6a-2 默认包适配的自动化门禁通过，默认 RAG 质量未低于保护基线；当时 M6a 仍为
`ADMITTED / IN_PROGRESS`。当前交付状态与测试数字见下方 M6a-4 收口复测，不要回写本检查点。

## M6a-4 收口复测 — 2026-08-26（当前 checkout，parent `b9bb31b`）

本记录关闭整个 M6a 的退出证据，绑定 parent `b9bb31b` 之上的本提交工作区，
而不是 `b9bb31b` 的 36/312 历史数字。报告文件本身位于 gitignored 的 `reports/`，
以 SHA-256 作为可核验证据。

- 分支：`feature/m6a-harness-skeleton`；parent commit `b9bb31b` + 本提交工作区。
- 环境：Windows 11 Home，Python 3.13.3，pytest 9.1.1；使用现有 `platform/.venv`。
- 离线环境：`SA_USE_VECTOR=false`、`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`。
- 验证矩阵（当前 checkout 复跑）：
  - `./platform/.venv/Scripts/python -m pytest tests/M6_crawler -m "m6_crawler and not online" -q`：52 passed, 1 deselected
  - `./platform/.venv/Scripts/python -m pytest tests/M6a -q`：124 passed
  - `./platform/.venv/Scripts/python -m pytest tests/M0_M2 -q`：18 passed
  - `./platform/.venv/Scripts/python -m pytest tests/regression -q`：52 passed
  - `./platform/.venv/Scripts/python -m pytest platform/tests -q`：40 passed
  - `./platform/.venv/Scripts/python -m pytest tests -q`：396 collected，395 passed, 1 skipped
- 根级 skip 仍为显式在线 crawler smoke，不是失败。
- 默认 90 题离线评测命令：
  `SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./platform/.venv/Scripts/python tools/run_evaluation.py -k 1,3,5 --report reports/m6a-closeout.json`
- 评测发现 OS 38 + DS 28 + CO 24 = 90；Network 未自动加入。
- Recall@3：OS 0.987、DS 0.929、CO 1.000，汇总 0.972；三课均满足 `Recall@3 >= 0.8`。
- JSON 报告 SHA-256：
  `54ba84bb8bfae744ed827502004106058c9dc1823863d865251fd421bf9a55e6`。
- 结论：M6a 交付状态现为 `ADMITTED / COMPLETE`；M6b/M7 仍须单独准入。

## M3b 可观测性基线 — 2026-08-18

### 测试环境与统计口径

- 测试命令：`platform/.venv/Scripts/python.exe -m pytest tests/M3b/ -q`
- 运行环境：Windows，Python 3.13.3，pytest 9.1.1；M3b fixture 关闭可选向量编码器。
- 检索模式：BM25 `keyword-only`，避免未缓存的本地 BGE 模型下载影响可重复性。
- 延迟从 `time.perf_counter()` 计算；服务指标只保留进程内最近最多 200 个样本/操作。
- 缓存命中指同一 `MultiRecallService` 实例中的重复检索命中结果缓存；索引缓存命中指 JSON 索引未重新扫描知识库。

### 冷启动与缓存命中

| 场景 | 延迟 | 结果数 | 说明 |
|---|---:|---:|---|
| 首次检索（cold） | 23.897 ms | 3 | BM25 全库检索，首次加载知识索引 |
| 重复检索（warm） | 0.060 ms | 3 | 命中进程内检索结果缓存 |

- 该数据用于验证 M3b 的可观测性和缓存行为，不代表所有机器或向量模式下的性能承诺。
- 后续若启用本地 BGE 向量检索，应单独记录模型加载（cold）与模型已加载（warm）的数据。

## 交付基线 v1 — 2026-08-18（M5e，离线 BM25）

记录冷启动、热启动和一次完整学习会话，便于新环境对照。数字来自本机离线模式
（`SA_USE_VECTOR=false`，未配置 LLM），不代表所有机器。

| 场景 | 口径 | 延迟 | 说明 |
| --- | --- | --- | --- |
| 冷启动 | 首次 `GET /health`（含应用导入与索引加载） | 9.0 s | 无模型下载，无 LLM |
| 热启动 | 再次 `GET /health` | 19.8 ms | 进程内缓存已热 |
| 学习会话 | `POST /study-sessions` + `POST /answers` | 139.8 ms | 检索→讲解→出题→作答→评估 |

### 本机实测（2026-08-18）

| 场景 | 延迟 |
| --- | --- |
| 冷启动 | 9.0 s（导入 8967.5 ms + 首次健康检查 58.5 ms） |
| 热启动 | 19.8 ms |
| 学习会话 | 139.8 ms |

- 启动命令：`python tools/start_local.py`
- 健康检查：`python tools/start_local.py --check`
- 评测冒烟：`python tools/run_evaluation.py --smoke`
- 可选 BGE 不纳入本基线；启用向量后应单独记录模型加载时间。

---

## M6a 保护基线复验 — 2026-08-25（历史候选树 `86e4ed8`，当时未提交）

本记录只关闭当时 `M6A-PROTECTED-BASELINE` 前置证据，不批准或启动 M6a。
数字绑定候选树 `86e4ed8`，不得改写成当前 checkout。

- 候选树：`HEAD=86e4ed8ae5f08d3dcd532e3d0e492553f03f91b4`；受测环境为 Windows 11、Python 3.13.3、pytest 9.1.1。
- 离线环境：`SA_USE_VECTOR=false`、`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`。
- 受测实现/测试变更的 tracked diff digest（证据文档更新前）：
  `b8119aadc2c5abd36a5a71517ad3aeeb67f25b606a49a4bc608a2cb80db27672`。
- 新增隐私回归文件 SHA-256：
  `a161d60fc684d8dd5276472899b9efb64700c5602105aa26340ae7b4f5b7ae8e`。
- 真实测试结果：
  - focused API/OpenAPI/SSE/privacy/recovery：32 passed；
  - `tests/M3b/`：13 passed；`platform/tests/`：40 passed；
  - `tests/`：271 passed, 1 skipped（仅显式 online crawler smoke）；
  - crawler offline gate：52 passed, 1 deselected；
  - `tests/regression/test_rag_quality.py -m slow`：3 passed。
- 默认评测命令：
  `SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./platform/.venv/Scripts/python tools/run_evaluation.py -k 1,3,5 --report reports/m6a-protected-baseline.json`
- 评测发现 OS 38 + DS 28 + CO 24 = 90，Network 未自动加入；Recall@3：OS 0.987、DS 0.929、CO 1.000，汇总 0.972。
- JSON 报告 SHA-256：
  `5db638a9cdb59081c2dc6ecea09a873fb31ad07e369364d6bcaa6a3ecbba00ca`。
- 路径隐私回归同时覆盖 `/health`、Search、QA、QA SSE、OpenAPI、日志及 LLM 异常 fallback；宿主路径未出现在响应或日志中。

## M6b 准入保护基线 — 2026-08-27（证据同步前候选 payload）

本记录只满足 `M6B-PROTECTED-BASELINE` 前置，不批准 M6b，不授权添加 provider 依赖、preview 路由、
运行时开关、生产模块、`tests/M6b/` 或 CI job。M6b 在独立人工批准前继续为
`BLOCKED / NOT_STARTED`；M7 继续为 `BLOCKED / NOT_STARTED`。

### 候选标识与环境

受测 payload 是在追加本证据记录**之前**冻结的纯文档候选内容。由于把 digest 写入自身会形成不可解的自引用，
以 parent `HEAD`、tracked binary diff 和唯一未跟踪 runbook 的 digest 组成可复核证据元组：

- 分支：`docs/m6b-admission-prep`；parent `HEAD`：
  `65fa55af051ba4751464752edba9255f076496f1`；
- `git diff --binary` SHA-256：
  `c6cd2a1e2cddab913e4072ec84a69693d45c904bb299dfdbd39aa47004b48410`；
- `docs/plans/data-expansion-runbook.md` SHA-256：
  `86d68d8395f159cb322d33e97ae2a0a77531ea7e280cfa707965b1ae7b964662`；
- 以上三个带标签字段按记录顺序组成的 candidate evidence digest：
  `a8e33b5345b12c5e10da5294b49e699cf838fcb4cb17550d0879186fe3fe0d2c`；
- 评测报告 `reports/m6b-admission-baseline.json` SHA-256：
  `a45f733cc633dedbb836c89d00de4808116f62d7e32d7335e17f572120480f33`。

环境：Windows 11 Home `10.0.26200`，CPU `AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD`，
Python 3.13.3，pytest 9.1.1；使用现有 `platform/.venv`。离线变量固定为
`SA_USE_VECTOR=false`、`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`。

### 实测矩阵

| 门禁 | 实测结果 |
| --- | --- |
| crawler offline | 53 collected；52 passed，1 deselected；0.51 s |
| M6a contracts/closeout | 124 collected；124 passed；14.86 s |
| M5c recovery/idempotency/concurrency | 7 collected；7 passed；10.69 s |
| M0_M2 | 18 collected；18 passed；9.34 s |
| regression（非 slow） | 52 collected；49 passed，3 deselected；8.98 s |
| RAG quality（slow） | 3 collected；3 passed；16.76 s |
| platform 原始套件 | 40 collected；40 passed；10.88 s |
| 根级完整套件 | 417 collected；416 passed，1 skipped；26.58 s |
| M3d 文档完整性 | 6 collected；6 passed；0.03 s |

根级唯一 skip 为 `tests/M6_crawler/test_online_smoke.py` 的显式在线 crawler smoke，符合默认离线门禁。
M5c 聚焦套件确认旧 SQLite session 恢复、幂等与并发兼容；M6a、regression 和 platform 套件共同覆盖
既有 API/OpenAPI、QA SSE、路径隐私、治理状态、运行时契约和原始 40 项平台行为。

### 默认 90 题质量

命令：

```bash
SA_USE_VECTOR=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  ./platform/.venv/Scripts/python tools/run_evaluation.py -k 1,3,5 \
  --report reports/m6b-admission-baseline.json
```

- 模式：`keyword-only`；默认发现 OS 38 + DS 28 + CO 24 = 90，90 题均有标注；
- Network 30 题未自动进入默认集合；
- 加权结果：Recall@1 0.628、Recall@3 0.972、Recall@5 0.989、平均延迟 112.8 ms；
- 延迟只描述本次本机快照，不是 M6b preview 的 p95 验收结果。

| 课程 | 题数 | Recall@1 | Recall@3 | Recall@5 | AvgLatency(ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| OS | 38 | 0.645 | **0.987** | 1.000 | 112.8 |
| DS | 28 | 0.607 | **0.929** | 0.964 | 116.1 |
| CO | 24 | 0.625 | **1.000** | 1.000 | 109.0 |
| 汇总 | 90 | 0.628 | **0.972** | 0.989 | 112.8 |

三门课程均满足 `Recall@3 >= 0.8`。

### 边界审查与结论

- 默认应用和 OpenAPI 中没有 `/api/v1/agent-preview`；既有 API、QA SSE 与工作台契约未增加 preview 表面；
- `platform/requirements.txt` 中没有 `anthropic`，且 `platform/app/llm_client.py`、
  `tool_registry.py`、`preview_agent.py`、`preview_service.py`、`tests/M6b/` 均不存在；
- 没有 preview runtime flag、`m6b` pytest marker 或 M6b CI job；
- 路径隐私与治理回归通过，未发现宿主绝对路径或未授权 M6b/M7 生产表面；
- 本次只读文档候选未修改正式状态机、SQLite schema、默认 Source scope 或评测发现规则。

因此 `M6B-PROTECTED-BASELINE=SATISFIED`。证据同步后的文档/JSON 变更另跑治理与文档一致性检查，
但不会回写或伪造上述受测 payload digest。批准字段仍为空，所以本结论不改变 M6b 的准入/交付状态，也不影响 M7。

## M6b 首轮 closeout 基线 — 2026-08-28（最终文档复核前 payload）

本节是追加式交付证据，不改写上方 M6b 准入保护基线。它记录获批实现完成后的首轮 closeout payload；由于证据
写入自身以及后续 `COMPLETE` 状态切换都会改变工作树，以下 identity 明确绑定**追加本节之前**的未提交 payload，不能冒充
最终提交对象。M6b 在文档后复核通过前仍为 `ADMITTED / IN_PROGRESS`；M7 仍为 `BLOCKED / NOT_STARTED`。

### 实现身份与环境

- 分支：`feature/m6b-readonly-preview`；`HEAD=65fa55af051ba4751464752edba9255f076496f1`；
- 追加本节前 `git diff --binary` SHA-256：
  `3dd1c6b4df6158b41cce1308437b7c6c144ea38007718f2318aeab50f71074c6`；
- 15 个未跟踪文件按路径排序，以 `path + NUL + file_sha256 + LF` 组成 manifest，其 SHA-256：
  `0cc5bcdc5135050a76dd1ba5c1e36b98458948f5618f9b20a727afcf04070a5b`；
- 上述 `HEAD`、tracked diff digest、untracked manifest digest 按带标签三行组成的 payload identity SHA-256：
  `35e5f0cd42f7862edfc4542fbbe14c0dbf9f3b1501164cf14490617728685459`；
- 环境：Windows 11 `10.0.26200`，CPU `AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD`，Python 3.13.3，
  pytest 9.1.1，官方 `anthropic` SDK 1.2.0；
- 离线变量：`SA_USE_VECTOR=false`、`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`；没有配置 provider key 或
  preview secret，没有发起真实 Anthropic API 请求。

### 首轮实测矩阵

| 门禁 | 实测结果 |
| --- | --- |
| M6b 阶段套件 | 111 collected；111 passed；13.95 s |
| M6a contracts/closeout | 124 passed；9.27 s |
| M5c recovery/idempotency/concurrency | 7 passed；7.72 s |
| M0_M2 | 18 passed；15.70 s |
| regression（非 slow） | 52 collected；49 passed，3 deselected；15.68 s |
| RAG quality（slow） | 3 passed；18.04 s |
| platform 原始套件 | 40 passed；11.96 s |
| M3d 文档完整性 | 6 passed；0.05 s |
| privacy + SQLite zero-write 聚焦复验 | 11 passed；8.78 s |
| 根级完整套件 | 528 collected；527 passed，1 skipped；30.35 s |
| crawler offline | 53 collected；52 passed，1 deselected；0.36 s |

根级唯一 skip 仍是显式 online crawler smoke。M6b 测试使用本地 scripted fake provider，覆盖 adapter 原生 block/replay、
registry 双重授权、预算/retry/timeout/cancel/duplicate/stop reason、默认路由缺席、认证与容量、scope 隔离、隐私和真实
隔离 SQLite 的零领域写入。`platform/tests/` 历史 40 项未修改。

### 阻断性离线 preview benchmark

命令通过 `M6B_BENCHMARK_REPORT=reports/m6b-offline-preview-benchmark.json` 运行真实 `PreviewService`、`PreviewAgent`、
`ToolRegistry` 与三个只读工具，provider 为本地 fake，检索为已发布 warm BM25 combined snapshot。

- workload：final-only、retrieve、quiz-preview、review-due；workload digest：
  `3f6b208e5269c609263102086645ae1e53cba76f533b5e93429eb9551d9ed050`；
- snapshot generation：`8c4a7a0b01a0b13134c8206c0e301a1622343f537de64166e301f51e796e581c`；
- 20 次 warm-up，200 次 measured，并发 2；1 passed，11.84 s；
- p50 0.948 ms，p95 5.179 ms，p99 5.792 ms，max 8.622 ms，满足阻断阈值 p95 `<= 1,000 ms`；
- termination histogram：`completed=200`；unexpected termination/timeout 为 0；归一化 replay consistency 为 100%；
- 报告内 canonical digest：`795b05fdf08d89aa2bd6ddfeb37bf268b3243f33b5492a255f7a909f2282d6d1`；
- 完整 JSON SHA-256：`3c8a1c7f22bfac1de7013c8f6d1b19cd4c923ec7f246be11ecf6c0c9347de084`。

这是离线 fake-provider service benchmark，不是外部网络或真实模型 SLA。真实 Anthropic smoke 保持显式、非阻断且本次未运行；
不得从上述延迟推导真实 provider 性能。

### 默认 90 题质量与边界结论

`reports/m6b-closeout.json` 为 `keyword-only`、90/90 labeled；OS 38、DS 28、CO 24，Network 未自动进入。Recall@3
分别为 0.986842、0.928571、1.000000，加权 0.972222，三课均满足 `>= 0.8`；完整报告 SHA-256：
`279d11a50248dc497f9ac52dd7d85388c0da5b5dc68641d51a705e1aac1904f7`。

默认 app/OpenAPI 无 preview route；启用态需要独立 Bearer auth，且认证先于 provider 配置披露。preview 使用
`DEFAULT_PLUS_EXTRAS`，正式 `StudySessionService` 保持 `DEFAULT_ONLY`；成功与失败路径均不创建 session、不提交答案，
不写 review/mastery/source 状态。prompt 与受限工具结果会发送给 Anthropic；本地日志、trace、错误、OpenAPI、持久化和
未授权边界未发现 prompt/正文/凭据/绝对路径/provider 原始响应 canary 泄漏。

上述为文档同步前首轮 closeout 证据，并保持其状态切换前 payload 身份不变。后续文档一致性、治理、M3d、M6b、
回归、完整根套件和 `git diff --check` 均已通过，M6b 随后切换为 `ADMITTED / COMPLETE`；该最终状态不回写本节的
历史 identity，也未改变任何 M7 决策、baseline 或批准字段。

## M6b stabilization 收口补丁 — 2026-08-29（复测证据）

本节是对 2026-08-28 首轮 closeout 的稳定性补丁复测结果，采用追加方式记录，**不是改写首轮 closeout**，
也不改写其 payload identity 或报告 digest。稳定性补丁包括：

- 离线 M6b 检索 fixture / benchmark 固定 `USE_VECTOR=false` 与 `VECTOR_ENABLED=false`，走 BM25，不加载本机向量模型；
- preview 同步工具改为真实 deadline（`asyncio.wait_for` + worker thread）；超时或工具异常后不 continuation、不回放 tool_result；
- Anthropic adapter 对 SDK 初始化失败、token-count 结构异常、message block/usage 解析异常 fail-closed，只暴露稳定 `ProviderError`；
- `platform/README.md` 过期 “closeout 证据同步阶段” 表述已与 `ADMITTED / COMPLETE` 对齐。

### stabilization 复测矩阵

以下数字由监督方核对 pytest 原始输出，**不在本轮重跑**。2026-08-28 首轮 `tests/M6b/` 的 111 项历史记录保留；
本次 stabilization 复测收集数为 124（含 benchmark）。

| 测试范围 | 复测结果 |
| --- | --- |
| `tests/M6b` | 124 collected；124 passed；10.87 s（含 benchmark） |
| `tests/M6a -m m6a` | 124 passed；10.82 s |
| `tests/M5c -m m5c` | 14 passed；6.74 s |
| `tests/M0_M2` | 18 passed；7.38 s |
| `tests/regression -m "not slow"` | 49 passed；3 deselected；7.60 s |
| `tests/regression/test_rag_quality.py -m slow` | 3 passed；17.32 s |
| `platform/tests` | 40 passed；9.28 s |
| 根级 `tests` + `platform/tests` | 580 passed；1 skipped（`tests/M6_crawler/test_online_smoke.py`）；27.31 s |

### 默认三课 90 题 BM25 复测

- Recall@1：0.628；Recall@3：0.972；Recall@5：0.989；平均延迟：92.1 ms；
- Recall@3：OS 0.987、DS 0.929、CO 1.000。

历史 closeout digest 仍以本节之前的记录为准：payload identity
`35e5f0cd42f7862edfc4542fbbe14c0dbf9f3b1501164cf14490617728685459`，benchmark canonical digest
`795b05fdf08d89aa2bd6ddfeb37bf268b3243f33b5492a255f7a909f2282d6d1`。M7 仍为 `BLOCKED / NOT_STARTED`。

## M6b stabilization evidence `stabilization-20260829-03` — 2026-08-29

本节只追加 limiter / marker / evidence-identity stabilization 的独立 benchmark 证据，**不改写** 2026-08-28 首轮 closeout，也**不改写**上一节 2026-08-29 复测矩阵。

- Evidence ID：`stabilization-20260829-03`
- workload：20 次 warm-up、200 次 measured、并发 2
- p50 `1.149 ms`，p95 `9.252 ms`，p99 `10.066 ms`，max `11.980 ms`
- termination histogram：`completed=200`；意外终止 / timeout 为 0；规范化重放一致率 100%
- Report digest：`acd2828eafc7bfda3d474ab5b6949719b4cc7ab7dd65bbfe731d85090f46669a`

普通 M6b 套件与专用 benchmark 用独立 marker `m6b_benchmark` 分离：普通套件 `126 passed, 3 deselected`，benchmark `3 passed`。记录型报告必须把 evidence ID 写入文件名，并以 exclusive-create 落盘；全量回归不得再次生成同名报告。

本轮权威套件实测（未再次写出 `stabilization-20260829-03` 报告）：

- 根级 `tests/`：546 collected；545 passed；1 skipped
- 合并 `tests platform/tests`：586 collected；585 passed；1 skipped

M6b 保持 `ADMITTED / COMPLETE`；M7 仍为 `BLOCKED / NOT_STARTED`。

## M7 准入前保护基线 `m7-admission-20260829-02` — 2026-08-29

本节是 M7 人工准入候选的追加式证据。分类固定为 `disposable-reference`：一次性 harness 位于仓库外临时目录，
只使用纯合成 Markdown、既有 M6a static extra / combined snapshot / BM25 接口和离线环境；未扫描或复制
`D:\\111_Others_Subjects`，未访问网络、外部 LLM 或 provider，外部服务成本为 USD 0.0。报告位于被忽略的
`reports/`，权威文档只登记 evidence ID 与 digest，不把原始报告作为受跟踪生产文件。

### 不自引用的候选身份与报告完整性

- Evidence ID：`m7-admission-20260829-02`；schema：`sa.source.admission-baseline.v1`；
  overall：`PASS_WITH_STRUCTURAL_3K_GAP`；
- parent commit：`ca714066295908333964533d311b1375d971b5d2`；
- gate-spec diff SHA-256：`79709fa0bad3aad3ebc2897779a64a7cef5805d51e4e1bdde614a07c711770a2`；
- plan-spec diff SHA-256：`ba7f5b8516abc1117397917ff99fddc4d9c8a7d2a9cc9acbacfd910e2192d1d4`；
- tracked candidate diff SHA-256：`c439ea115fab4a6398e926100ec334625d4979a0298799adf6ead4a030ac689e`；
  candidate identity SHA-256：`a9c753993e15e6ec71801fca73e1432082b66e3915d70aabab99a3c66d9c9c17`；
- fixture manifest SHA-256：`8a60db52f8b253aa3baca847d69995b6593eb3c5635347c25f3c38c1125a4f46`；
  query/gold manifest SHA-256：`d8c36f50d4a9fbb07e091a0c63f9910310f1c6702f81f22f2fa79be48eaace68`；
- harness SHA-256：`db6f5f0e7036ad3328d6aaf8e86049fe9d3f766873e0558d3f0b036288120a71`；
  environment manifest SHA-256：`44bca41cfac605c64b03d230c04da1fe8e4a96ef850f0c7c02f09c2f87965b9e`；
  limit manifest SHA-256：`e379d13b2d28eccb11275dfad68982e5d79497afe06478428c50496feb5b5a3c`；
- raw report SHA-256：`d35befc6b9376dc911ba5aaf65003798ab60edef036ec395973b4e92b6516757`；
  canonical result SHA-256：`fcda6e52b5463b9dce05f250128509a90719824b50184f8571dcf59964d5b2bb`。

上述 identity 绑定证据同步前的受测 payload；后续把证据本身追加到文档会自然改变 tracked diff，因此不得把最终包含
本节的文档 diff 伪称为原始受测 payload，也不得回写历史 digest。

### 可执行 1k current-state reference

- fixture：1 个静态 extra、100 个 synthetic documents、1,000 个 extra chunks；默认包 682 chunks，combined 共
  1,682 chunks；100 个固定 query/gold，5 次 warm-up、20 次 measured，共 2,000 次查询观察；
- 质量：Recall@1/3/5 均为 `1.000`，分别通过 `0.70 / 0.85 / 0.90` 下限；
- 查询延迟：p50 `108.695 ms`、p95 `216.757 ms`、max `696.645 ms`，通过 p50 `150 ms`、p95 `400 ms` 上限；
- combined snapshot 冷构建 20 次：p50 `155.286 ms`、p95 `202.913 ms`；持久化 generation 重启加载 20 次：
  p50 `21.142 ms`、p95 `38.989 ms`；
- 资源：峰值 RSS `430,669,824 bytes`，通过 `512 MiB` 上限；持久化快照 `1,020,421 bytes`，accepted combined
  text `610,186 bytes`，比率 `1.672311`，通过 `2.0` 上限；
- 成本：CPU `292.90625 s`、wall `313.159033 s`、外部服务成本 USD `0.0`；全部冻结检查为 true。

### 3k 结构性容量差距

3k 未运行且未写成 PASS。目标 3,000 extra chunks 加当前默认 682 chunks，需要 combined `3,682` chunks；现行
M6a combined hard max 为 `2,000`。对 `2,001` 的 hard-max probe 已被拒绝，`attempted_builder_bypass=false`，因此
状态精确登记为 `UNAVAILABLE_PRE_ADMISSION_CAPACITY_LIMIT`。未提高限制、未绕过 `CombinedSnapshotBuilder`、未拆成
误导性的独立运行。该差距允许当前保护基线进入人工准入候选，但真实 M7 获准后仍必须用
`sa.source.benchmark.v1` 同时通过 1k 与 3k。

### 继承保护矩阵与默认质量

在同一候选树上固定 keyword-only / offline 边界后，实测如下；唯一 skip 是显式 online crawler smoke：

| 范围 | 结果 |
| --- | --- |
| 根级 `tests/` | 546 collected；545 passed；1 skipped |
| 合并 `tests/ platform/tests/` | 586 collected；585 passed；1 skipped |
| M0–M5 + regression 保护选择 | 216 passed；3 benchmark tests deselected |
| M6a/M6b 普通保护选择 | 250 passed；3 benchmark tests deselected |
| crawler offline | 52 passed；1 online test deselected |
| `platform/tests/` | 40 passed |
| slow RAG quality | 3 passed |
| M6b 专用 benchmark | 3 passed；126 non-benchmark tests deselected |

M6b 专用报告均为 20 warm-up、200 measured、并发 2、200 completed、0 unexpected termination、replay
consistency 100%。inherited / root / combined 三份 raw SHA-256 分别为
`ae35f5d7a3120f9aa7a6b32fdc7426ac8246e47ae4d96d8096607dace2211173`、
`a0176b07fe0eeee3c4d9d22e4b3105ce8bd9189c4737be9cdf2639af8290564a`、
`3fe39d6fb70b519c2fafd5a9b9f7840f6ae727d191a550187385f77558412f6e`；对应 p95 为 `10.636 / 10.257 /
10.689 ms`，内部 report digest 为 `1bc15a1a4df0cfe59f0a872c77c0ff641787fddf2febcf8cec2583648ee03785`、
`2a45408113411334ecbc2864c75f42225336acbb7f1940460fca9b47ecdfab97`、
`34979348163ee892530eb5e2168a086731225d6964d1daf465bd945627374add`。

默认 OS/DS/CO 90 题 report raw SHA-256 为
`238249d77f9f42c327c6221f16df382997449121a49e883df9186c2da866e90d`。keyword-only 下 Recall@3 为
OS `0.986842`、DS `0.928571`、CO `1.000000`，加权 `0.972222`；三课均通过继承下限 `0.8`。Recall@1/5
加权为 `0.627778 / 0.988889`，平均延迟 `119.813 ms`；Network 未自动加入。

### 证明边界与状态结论

该证据只证明既有 M6a static-extra materialization、combined snapshot publication/reload、BM25 1k current-state
质量/容量和 2,000 combined hard max 的拒绝行为。它**不证明** M7 lifecycle、manifest、parser matrix、normalized
document、provenance、增量同步、删除传播、checkpoint recovery、M7 3k 容量、任何 M7 退出条件，或网络/provider/
跨机器性能。`warm_noop_incremental`、`ten_percent_incremental`、`delete_propagation` 与 `checkpoint_recovery` 均为
`NOT_APPLICABLE_PRE_ADMISSION`。

所有可执行 reference、继承回归、质量、隐私和兼容门禁通过，因此仅将
`M7-PROTECTED-BASELINE` 从 `OPEN` 登记为 `SATISFIED`。M7 仍为 `BLOCKED / NOT_STARTED`，全部批准字段保持空值；
仓库中没有新增 M7 生产模块、依赖、schema、API、runtime flag、worker、CI job 或 `tests/M7/`。本候选必须停在
独立人工批准检查点，Agent 不得自行批准或开始 M7 生产实现。

## 治理冻结复测 — 2026-08-31（P0 文档级 mapping 与 candidate 隔离）

本节是追加式当前 checkout 证据，不改写 2026-08-29 的 M7 准入前保护基线或其 digest。治理范围仅包括
Network/Interview 文档级身份、来源、许可与 fail-closed 入库声明；未新增 M7 runtime 生产能力，M7 仍保持
`BLOCKED / NOT_STARTED`，批准字段保持为空。

- OS/DS/CO 继续使用历史可信默认 `knowledge-pack` 政策；默认评测固定为 90 题（OS 38 + DS 28 + CO 24），
  不自动纳入 Network。
- 默认 keyword-only 评测：Recall@1/3/5 为 `0.672 / 0.978 / 0.989`，平均延迟 `137.6 ms`；
  Recall@3 分课程为 OS `1.000`、DS `0.929`、CO `1.000`。
- Network 30 题仅显式通过 `--test-set tools/evaluations/network.json` 运行；Recall@1/3/5 均为 `0.000`。
  这是 31 篇文档显式 `candidate`、不进入索引的预期 fail-closed 结果，不是默认 OS/DS/CO 质量回归。
- 完整根级 `tests/`：554 collected；553 passed；1 skipped。根级与 `platform/tests/` 合并：594 collected；
  593 passed；1 skipped。`platform/tests/` 受保护功能套件为 40 passed；唯一 skip 是显式 online crawler smoke。
- mapping SHA-256 已按 LF 基准重新冻结为 `a8b9a1a949d053740943b877bcbcfd6369f73b1cc2a7457ac0bfb8df2531e652`（`.gitattributes` 固定 `text eol=lf`，消除 Windows CRLF 检出与 Linux LF 检出的平台差异）；`git diff --check` 通过。

本节只冻结当前治理验证结果，不代表 Network 来源/许可证已闭环，不代表 M7 admission，也不替代独立人工复核。

## M7 基础设施受限准入登记 — 2026-08-31

本节追加记录治理状态迁移，不回写上述历史测量时点的 `BLOCKED / NOT_STARTED` 原文。准入来自项目负责人
`justtodo123` 的明确用户指令“`M7 基础设施可以获批；Network 数据仍不获批；M8/Milvus 继续阻断`”，不是由 benchmark、
测试或 P0 mapping 自动推导。

- M7 当前为 `ADMITTED / IN_PROGRESS`，批准 scope 为 `m7-infrastructure-only-v1`；
- scope 只包含 Source lifecycle、provenance/manifest/parser、sync/delete/isolation、FTS5/offline fallback 和真实 1k/3k
  benchmark 基础设施；
- `implementation_start=AUTHORIZED`；lifecycle/FTS5/offline 与 Search/QA overlay 已实施，`tests/M7/` 当前 177 项通过；disposable 1k/3k FTS5 证据 vector 未挂接，不构成 M7 exit；
- Network 31 篇继续为 `review / candidate / unresolved`，不可发布、不可索引；
- M8 继续 `BLOCKED / NOT_STARTED`，`M8-M7-EXIT` 仍 `OPEN`；Milvus 未选择、未批准、未接入。

## M7 source-local delete/isolation 冻结 — 2026-09-02

本节是追加式当前 checkout 证据，不回写 2026-08-31 准入登记原文。2026-09-02 复验：`tests/M7/` 143 passed（其中 delete/isolation 24 passed），`tests/regression/` 61 passed。`sa.source.delete.v1` 与 `sa.source.isolation.v1` 的 source-local 合同自此冻结：不接入 `app.main`、Search、QA、preview 或公开 API。后续 FTS5、正式检索接入与 1k/3k benchmark 不得静默修改已冻结的删除/隔离 schema、错误码或不可读语义。

## M7 source-local FTS5/offline checkout — 2026-09-03

本节追加记录 source-local FTS5/jieba 与离线 fail-closed 校验/显式 FULL repair 的局部落地，不回写 2026-09-02 delete/isolation 冻结原文，也不改变 M7 `ADMITTED / IN_PROGRESS`。2026-09-03 复验：`tests/M7/` 162 passed（新增 FTS5/offline 19 passed），`tests/regression/` 61 passed。未接入 `app.main`、Search、QA、preview 或公开 API；未跑冻结 1k/3k benchmark；不得把 162 项局部合同视为 M7 exit 证据。M8/Milvus/Network 仍不在本范围。



## M7 Search overlay + disposable 1k/3k FTS5 — 2026-09-03

本节追加记录 Search/QA 的受信任内部 principal overlay，不回写 FTS5/offline 162 项原文，也不改变 M7 `ADMITTED / IN_PROGRESS` 或 M8 `BLOCKED / NOT_STARTED`。2026-09-03 复验：`tests/M7/` 177 passed。`tools/run_m7_benchmark.py` 的 disposable FTS5 跑数为：1k-single Recall@1/3/5=1.000，查询 p50 135 ms / p95 149 ms；3k-aggregate Recall@1/3/5=1.000，查询 p50 392 ms / p95 458 ms。vector 仍 `not_attached`；FULL 样本为 1 而非冻结 20 次；3k p50 超过 250 ms 门槛。该报告不是 M7 exit 证据，也不批准 Network 或 M8/Milvus。

## M7 generation-bound vector checkout — 2026-09-03

本节追加记录 source-local generation-bound vector 与 FTS5 identity-set 合同，不回写 Search overlay 177 项原文，也不改变 M7 `ADMITTED / IN_PROGRESS` 或 M8 `BLOCKED / NOT_STARTED`。2026-09-03 复验：`tests/M7/` 189 passed。用户源 vector 绑定 source_id、immutable revision、published generation、embedding model/version、chunk policy 与 identity-set digest；与同一 normalized published generation 的 FTS5 chunk_id 集合 100% 一致。vector metadata 缺失、generation/模型/identity 不一致时 M7 用户源 fail closed，不降级默认包 keyword-only。M0–M6 默认 pack/extras 的既有 vector fallback 保持不变。Preview/Quiz/Review/study-sessions 仍不含用户源。冻结 20 次 1k/3k BGE 协议与 3k p50 仍未达标，本记录不是 M7 exit 证据，也不批准 Network 或 M8/Milvus。



## M7 协议内 3k p50 复用优化 — 2026-09-03

本条追记 source-local generation-bound 检索热路径的协议内优化，不改写 generation-bound vector 189 项原记录，也不改变 M7 `ADMITTED / IN_PROGRESS` 与 M8 `BLOCKED / NOT_STARTED`。2026-09-03 复验：`tests/M7/` 190 passed。优化保持 fail-closed：identity-set、generation 绑定、删除屏障与 owner allowlist 仍在查询前生效；vector 未附着或 metadata 损坏不降级到 keyword-only。`tools/profile_m7_search.py` 对 3k-aggregate 的 source-local hash 剖析为 query p50 约 105 ms / p95 约 109 ms，vector 已附着，但不是冻结 20 次 BGE 协议，不能当作 M7 exit 证据，也不批准 Network 或 M8/Milvus。

## M7-3 冻结 1k/3k BGE 协议 — 2026-09-04

本节追加记录 `sa.source.benchmark.v1` 冻结协议实跑，不回写 2026-09-03 hash 剖析原文，也不改变 M7 `ADMITTED / IN_PROGRESS` 或 M8 `BLOCKED / NOT_STARTED`。命令为 `platform/.venv` 下的 `tools/run_m7_frozen_benchmark.py --backend bge --workload all --report artifacts/m7-frozen-benchmark.json`；查询 20 warmup + 200 measured，FULL 独立 OS 进程 5+20，后端 `source_local_bge`（`BAAI/bge-small-zh-v1.5`）。本地报告 SHA-256 `ed495f7173f33b125c08d974f80a29f936c9fd59131f8811647df5456684f9a7`，不入库。`m7_exit=false`，`network_promoted=false`，`m8_started=false`。

- 1k-single：Recall@1/3/5=1.000；query p50 5.596 ms / p95 190.223 ms；peak RSS 600,309,760 B（约 573 MiB）；FULL p95 4.923 s；identity 100%；vector `attached`。失败原因：peak RSS 超过 512 MiB。
- 3k-aggregate：Recall@1/3/5=0.400/1.000/1.000；query p50 459.874 ms / p95 532.508 ms；peak RSS 659,996,672 B（约 629 MiB，低于 1 GiB）；FULL p95 9.496 s；identity 100%；vector `attached`。失败原因：Recall@1 低于 0.70，query p50 超过 250 ms。

本报告不是 M7 exit 证据，也不批准 Network 或 M8/Milvus。不得用 `tools/run_m7_benchmark.py` 的 disposable hash smoke 替代本记录。

## M7-4 1k RSS 门槛修订 — 2026-09-04

本节追加记录 justtodo123 授权将冻结 BGE 协议的 `1k-single` 峰值 RSS 从 512 MiB 修订为 **768 MiB**，不回写 2026-08-29 准入前 BM25 保护基线，也不回写 2026-09-04 首轮冻结报告原文。3k RSS 仍为 1 GiB；Recall 与 p50/p95 门槛不放宽。修订原因：512 MiB 按无 BGE 的 BM25 1k（430 MiB）校准，无法覆盖 `sentence-transformers` + `BAAI/bge-small-zh-v1.5` 进程底盘。M7-4 探针约 551 MiB，低于 768 MiB，但仍须完整 20+200 / FULL 5+20 复跑后才能评估 `m7_exit`。不批准 Network，不启动 M8/Milvus。

## M7-4 冻结 1k/3k BGE 复跑 — 2026-09-04

本节追加完整冻结协议证据，不回写 2026-09-04 首轮失败原文，也不自动把 M7 阶段标为 `COMPLETE`。命令为 `platform/.venv` 下 `tools/run_m7_frozen_benchmark.py --backend bge --workload all --report artifacts/m7-frozen-benchmark.json`；查询 20+200，FULL 独立进程 5+20。本地报告 SHA-256 `aaad2d0246627e659c844003c06389b488e7d5ab6572825ba7307e72f428fd75`，不入库。`network_promoted=false`，`m8_started=false`。报告内 `m7_exit=true` 只表示 `sa.source.benchmark.v1` 门槛通过，不是 M8 开工授权。

- 1k-single：通过。Recall@1/3/5=1.000；query p50 2.753 ms / p95 36.586 ms；peak RSS 575,467,520 B（约 549 MiB，低于授权后 768 MiB）；FULL p95 3.035 s；identity 100%；vector `attached`。
- 3k-aggregate：通过。Recall@1/3/5=1.000；query p50 84.736 ms / p95 96.274 ms；peak RSS 575,467,520 B（约 549 MiB，低于 1 GiB）；FULL p95 7.282 s；identity 100%；vector `attached`。

默认 OS/DS/CO 包与 Network candidate 边界不变。M8/Milvus 仍为 `BLOCKED / NOT_STARTED`，须另做 M7 阶段退出评估。

## M7-6 真实 parser 与生命周期/provenance 验收 — 2026-09-05

本节追加运行时生成 fixture 的局部验收证据，不读取或复制 `D:\111_Others_Subjects`，不提交 PDF/PPTX/DOCX
二进制。环境为 Windows 11、CPython 3.11.9、pytest 9.1.1；精确 parser contract 为
`markdown-it-py==4.0.0`、`cpython-textio==3.11.9`、`pypdf==6.0.0`、`python-pptx==1.0.2`、
`python-docx==1.2.0`。首轮定向命令覆盖 parser、normalized-document 与 lifecycle E2E，共 40 passed；当时
`tests/M7/` 为 230 passed（1 个第三方 deprecation warning，61.80 s），作为 M7-6 扩展过程的历史证据保留。后续补齐查询校验顺序、非正 `top_k` 与最终 E2E 覆盖后，阶段口径曾增至 237 passed；2026-09-05 的 correctness 中间口径为 255 passed。首轮同时暴露并修正了检索结果顺序假设。
E2E 覆盖 Source 注册、真实 Markdown
FULL/INCREMENTAL、权威 generation/revision、`user://` provenance、服务重启、显式 offline FULL repair、principal
隔离、DELETE_PENDING 搜索屏障及 BM25/vector/result-cache/provenance 不可读、30 天 hard-delete receipt 和幂等重试；
receipt 还验证实际 generation-bound FTS5/vector 目录已清除，并在 Windows 删除前释放活动索引 runtime。
这不是每格式 100 fixtures × 20 runs、真实外部课程资料或整个 M7 exit 的证据；M7 仍为
`ADMITTED / IN_PROGRESS`，M8/Milvus 仍为 `BLOCKED / NOT_STARTED`。

2026-09-05 完整根级回归复验（历史证据）：`tests/` 收集 810 项，809 passed、1 skipped；最终复验运行耗时 87.94 s。唯一 skip
仍为显式 online crawler smoke。此前 M6b semaphore/deadline 用例的调度竞态已改为等待两个请求实际 admission，
并修正由总 deadline 限定 semaphore wait 时的边界判定；未放宽终止原因断言，也未加入不确定 sleep。
`tests/M7/` 同轮独立复验为 237 passed（60.24 s），`tests/regression/` 为 61 passed，`platform/tests/` 为 40 passed。
该数字保留为 M7-6 当时的历史证据；2026-09-05 correctness 中间结果为 255 passed（72.96 s）。
这组结果收口 M7-6 的完整回归缺口，但不等于整个 M7 exit。

五格式冻结证据另以 `tools/run_m7_parser_evidence.py` 完整协议执行：seed `20260904`，Markdown/TXT/PDF/PPTX/DOCX
各 100 个运行时 fixture、各 20 次，并逐项比较 parser output digest、normalized digest、document ID、chunk ID、
当前进程与独立重启进程 deterministic identity digest。报告 schema 为
`sa.source.parser-normalized-identity-evidence.v1`，本地报告 SHA-256
`075094bea0f4f9e591ee4d69002b2d96284635d8273eec9c6e90fac43075f3be`（不入库）；五格式均 `PASS`，
`parser_unavailable/parse_failed/normalization_failed/cold_restart_mismatch/deterministic_identity_mismatch` 均为 0，
`external_source_reads=0`、`tmp_only=true`。该 parser/normalization/identity 证据不声称执行 source registry/sync/delete；生命周期与 provenance 由独立 E2E 测试覆盖。它与 1k/3k BGE 检索 benchmark 分离，仍不自动构成 M7 阶段退出或
M8 开工授权。

## Correctness 收口当前执行状态 — 2026-09-06

2026-09-06 当前 `tests/M7/` 收集 270 项；Python 3.13.3 执行 267 passed / 3 failed。三个失败均为 TXT 真实 fixture 在精确
`cpython-textio==3.11.9` 合同下返回 `PARSER_UNAVAILABLE`，属于环境不满足冻结 parser contract 时的预期 fail-closed，
不应通过放宽断言或伪造版本修复。2026-09-06 使用 `platform/.venv311`（CPython 3.11.9 与精确冻结依赖）独立复跑
seed `20260904` 的完整五格式协议：每格式 100 个运行时 fixture × 20 次，全部 `PASS`，五类失败计数均为 0，
`external_source_reads=0`、`tmp_only=true`；报告只写入系统临时目录且不入库。该结果验证冻结环境，但不把 Python 3.13.3
结果伪装为全绿。根级 `tests/` 当前收集 826 项，当前 checkout 离线 keyword mode 执行为 CPython 3.13.3 的 822 passed、1 skipped、3 个精确 TXT contract failures；同一套件在 CPython 3.11.9 精确环境为 825 passed、1 skipped。
与 `platform/tests/` 合并收集 866 项；按根级 822 passed、1 skipped、3 个精确 TXT contract failures，加受保护
`platform/tests/` 40 passed，可得当前已分别验证的合计口径为 862 passed、1 skipped、3 failed；本次未取得单次 combined run 的完整终态，不能把该合计写成一次独立执行结果。`tests/regression/` 62 passed，
受保护 `platform/tests/` 40 passed。此前 810/850 等数字均保留为历史证据。公共 Search/QA 不接受 caller-selected `principal_id`；可信 principal 仅作为服务端内部边界。
用户源读路径的 operation-lock final revalidation 是有界进程内保护，不是跨进程 read lease。
本 correctness 执行状态在独立人工完成批准前仍记为 M7 `ADMITTED / IN_PROGRESS`；随后状态见下节。M8 仍为
`BLOCKED / NOT_STARTED`。

## M7 独立完成批准 — 2026-09-06

上述 technical exit candidate、冻结 benchmark、五格式 parser evidence 与全量测试证据本身不产生阶段批准。其后，
justtodo123 于 2026-09-06 通过 `User instruction: 批准 M7 COMPLETE`，在原批准范围
`m7-infrastructure-only-v1` 内作出独立完成批准；原 2026-08-31 admission 与 production implementation
authorization 记录保持不变。当前 M7 为 `ADMITTED / COMPLETE`。

该批准使 `M8-M7-EXIT`、`M9-M7-EXIT`、`M10-M7-EXIT` 三项事实型前置成为 `SATISFIED`，但不批准任何下游
阶段。M8、M9、M10 仍为 `BLOCKED / NOT_STARTED`；Network 文档晋升、P0 语料治理闭环、任意 corpus 自动批准、
M8 专业化存储、Milvus/LanceDB/Qdrant 选择以及 M9/M10 实现继续处于原批准范围之外。

## M9 v1.5 外部 AI 路径评测读数 — 2026-09-22

本节记录 `M9-EVALUATION` 延迟/成本维度解冻（plan_revision v1.5）后的**本地复现读数**。范围**仅限
M9 外部 AI 路径（`m9.external-ai`）**，**不是**全项目评测，也**不是** provider 性能。证据绑定：

- **arm A（门禁）**：`tests/M9/test_plan_ai_benchmark.py`，提交 `6ba6ce8`；报告 schema
  `m9-plan-ai-evaluation-v2`；`workload_digest`
  `0e6de48f48dabb6b45f58f53198ea80f7f5f37848aad2d4005f98ac50cd1bf8f`（冻结 workload，五个：
  `os-baseline`/`os-required-deadlock`/`os-excluded-memory`/`ds-baseline`/`network-baseline`）、
  `budget_scenario_digest`
  `508707a16a1b0ee0367dc22b9bdc8628f11dfc1a5b2da5aebda4e7d250d667f1`（冻结 6 场景）。两个摘要都是冻结
  常量的纯函数，故可复算比对；报告本体经 `M9_BENCHMARK_REPORT` 独占创建写入**本地临时目录**（不入库）。
- **arm B（非门禁）**：`tests/M9/test_plan_ai_provider_smoke.py`，提交 `51220d6`。**本次未运行**。

**arm A 读数**（Windows 11 `10.0.26200`、CPython 3.13.3、`provider: deterministic-stub (no network)`，
本地探针 `evidence_id=m9-v15-local-probe`）：6 场景观测原因码与期望**逐项一致**，`budget_enforcement`
`enforced=6 / total=6 / rate=1.0`。结构性三例：`prompt-budget`（`max_prompt_bytes=16`，prompt 实测 3876 字节）
**provider 调用数为 0** —— 钉住 prompt 预算判定位于 provider 调用**之前**；`cost-budget` 收到的是**合法置换**
却仍 `order_returned=false`、`estimated_cost_usd=0.30 > max_cost_usd=0.10` —— 钉住成本是**硬上限**而非建议；
`deadline`（`deadline_seconds=0.2`）实测 `latency_ms≈215` 后判 `deadline_exceeded`。1K 侧读数不变：
`input_bounded=true`（同一 workload 在 10 chunks 与 1000 chunks 下 prompt 字节数**逐字相同**，
3555–5280 字节）、`prerequisite_violations_total=0`、`deterministic_replay_consistency=true`。

**该读数不能用来声称什么**（逐条，报告内亦有机器可读副本）：

1. **不是性能**：`stub_latency_ms` 标签逐字为 `deterministic-stub end-to-end; NOT provider latency`。
   同轮 200 样本为 p50 1.15 / p95 1.56 / max 1.90 ms，而同日更早一次本地探针为 p50 2.16 / p95 3.40 /
   max 10.76 ms —— **同一冻结负载下相差数倍**，这本身就是「它不是稳定 SLA」的实证。成本同理，由脚本化
   usage 算出，非计量。
2. **两项预算不在本地执行，另有一项累积值没有运行期执行点**：`max_input_tokens`（本仓无本地 tokenizer，
   本地用的是字节预算）与 `model_timeout_seconds`（仅传给 provider）**不在本地执行**；`max_output_tokens`
   （**累积**值）不属同一类——它**没有运行期执行点**（**既不送给 provider，也没有用量累计核验**，见下），
   但**构造期被校验**。报告 `not_enforced_locally` 是这条的机器可读证据。**注意别读成
   「output 预算整体无本地执行点」**：自 2026-09-22 起 `max_turn_output_tokens`（单轮值，默认 1024）
   **在本地执行**——它是传给 `create_turn` 的 `max_tokens`，`llm_client` 硬拒超限值。修复前累积值被当
   单轮值传下去，默认配置下每次调用都在发出任何 HTTP 请求之前抛 `ValueError` 并被收敛成
   `provider_unavailable`，即整条外部 AI 路径静默失效（M9 计划 §4.4）。
   **累积值自身**：修复把唯一的送出点（旧 `max_tokens=limits.max_output_tokens`）换成了单轮值，故
   `max_output_tokens` 现在**没有运行期执行点**——provider 的请求体里没有「累积产出上限」这种参数，
   也没有 `preview_agent.py:226` 那样的用量累计检查。**但它并非完全无人读**：`_validate_limits` 在每次
   构造 `PlanAIAdapter` 时校验它（正整数、不超过冻结默认、且不得大于 `max_input_tokens`），并据此给
   单轮值定上界。本路径每个计划只发一次调用，故单轮值在效果上也是总量上界；那是**单次调用的后果**，
   不是设计保证。
3. **`deadline_seconds` 的守卫放弃线程而非取消它**：挂住的 provider 调用可以活过 deadline。
4. **arm B 本次未运行**：真实 provider 的延迟 / 成本 / 失败模式**仍未验证**。运行它需要 owner 的 key
   与真实花费（opt-in 命令、默认 $1.00 上限与「最坏为 cap + 单次调用」的说明见 `tests/M9/README.md`）。
   **不得**从上述 stub 延迟/成本推导任何 provider 性能数字。
5. **不是容量**：1K 语料**不被 M9 存储或索引**；10K/100K 仍是 M8（`BLOCKED`）/ M11 依赖。
6. **不是全项目评测口径冻结**：冻结范围仅限 M9 外部 AI 路径；遵循度仍为**定性**，未冻结数值阈值。
7. **不构成 M9 阶段退出**：`COMPLETE` 需要独立的 `completion_approval`，本次**不申请**。

该变更是 M9 **第一次触发** `stage-admission-gates.md` §4 撤销的变更（决策值实质变更 ⇒
`admission_history` 追加 `ADMITTED→REVOKED`、`REVOKED→ADMITTED` 两条），live 字段仍为
`ADMITTED / IN_PROGRESS`；理由与未变项清单见 M9 计划 §4.3。

*创建：2026-08-12 · 更新：2026-09-22（追加 M9 v1.5 外部 AI 评测读数；不启动 M9 收口）·
维护：知识库、评测集或检索策略变化后复测并追加记录*

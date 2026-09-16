# 辅助工具（tools/）

> RAG 评测、索引生成、资料整理引导等辅助脚本。用于数据驱动优化知识库检索效果。

## 目录结构

```
tools/
├── README.md              # 本文件（工具文档）
├── run_evaluation.py      # ★ 统一 RAG 评测入口
├── start_local.py         # 一键启动工作台并做 /health 检查
├── source_inventory.py    # 外部资料只读盘点（不复制、不解析全文、不建索引）
├── m8_prepare_p2_draft011.py # 校验并在仓库外生成 draft-0.11 P2 binding 候选；不签发 P2
├── m8_generate_minimal_1k_v3_fixtures.py # 生成 v3 validator 微型持久 fixture；不是 1K evidence
├── m8_validate_minimal_1k_graph_v3.py # 读取真实 artifact directory，校验跨文件证据图
├── m8_test_minimal_1k_graph_v3.py # 在临时目录重放 5 个图、重密封 mutation 与敏感性证明
├── m8_freeze_minimal_1k_v3_review.py # 从明确 commit 的 Git object bytes 生成 canonical 冻结摘要
├── m8_test_freeze_minimal_1k_v3_review.py # 冻结工具确定性、输入拒绝和 worktree divergence 自测
├── run_m7_benchmark.py    # M7 1k/3k disposable source-local hash smoke（不构成 exit）
├── run_m7_frozen_benchmark.py # M7-3 冻结 1k/3k BGE 协议（20+200 查询，FULL 独立进程 5+20）
├── profile_m7_search.py   # M7 3k search stage profile（非正式 exit 证据）
├── run_m7_parser_evidence.py # M7 五格式 parser/normalized/identity 冻结证据
├── crawler/               # 候选 Markdown 抓取/清洗/转换（M6a-P0 离线 marker/CI 已收口）
│   ├── requirements.txt   # crawler 独立依赖
│   └── fetcher/cleaner/converter/dedup/pipeline
└── evaluations/           # 课程评测集
    ├── os.json            # 操作系统 38 题（默认）
    ├── ds.json            # 数据结构 28 题（默认）
    ├── co.json            # 计算机组成原理 24 题（默认）
    └── network.json       # 计算机网络 30 题（独立扩展，不自动发现）
```

## run_evaluation.py — RAG 效果评估

一条命令跑完三课 90 题，输出控制台表格和可选 JSON 报告。默认使用离线 BM25（`SA_USE_VECTOR=false`），不依赖网络、模型缓存或 LLM key。

### 用法

```bash
# 默认：自动发现 OS/DS/CO 共 90 题，离线 BM25，@1/3/5
python tools/run_evaluation.py

# 只评其中几门课
python tools/run_evaluation.py --courses os,ds -k 1,3,5

# 保留单文件模式
python tools/run_evaluation.py --test-set tools/evaluations/os.json -k 1,3,5

# 写出 JSON 报告（默认不要提交；确认后再记入 docs/baselines.md）
python tools/run_evaluation.py --report reports/eval.json

# 显式启用向量/hybrid 评测
python tools/run_evaluation.py --use-vector

# 评测冒烟（CI 使用，每课只取少量已标注题）
python tools/run_evaluation.py --smoke

# 使用 platform 虚拟环境
./platform/.venv/Scripts/python tools/run_evaluation.py
```

### 指标

| 指标 | 含义 | 目标 |
| --- | --- | --- |
| **Recall@k** | top-k 结果中出现相关文档的比例 | ≥ 0.8（M5a 看 Recall@3） |
| **Precision@k** | top-k 结果中相关文档的比例 | 越高越好 |
| **F1** | Recall 与 Precision 的调和平均 | 综合评价 |
| **AvgLatency** | 每题平均检索耗时（ms，按 max k 测一次） | < 100ms（个人规模） |

报告字段还包括：`mode`、`use_vector`、每课题数、汇总指标。`reports/` 已加入 `.gitignore`。

### 评测集格式

```json
{
  "问题文本": ["knowledge/os/file.md", "..."],
  "另一个问题": []
}
```

- key 为自然语言检索问句
- value 为「相关文档」的 `knowledge/` 相对路径数组
- 空数组 `[]` 表示无标注相关文档，该样本跳过不参与计分

### 优化迭代流程

1. 建评测集（每门课覆盖实际条目）
2. 跑 `python tools/run_evaluation.py` 得离线基线
3. 调整切块策略 / BM25 参数 / 分词逻辑
4. 再跑测评 → 看指标变化
5. 面试时直接报数字（如「切片从整篇改为按小节切分后，Recall@3 从 62% 提到 79%」）

## evaluations/ — 评测集

按课程组织，每个文件一个 JSON：

| 文件 | 课程 | 题数 | 状态 |
| --- | --- | --- | --- |
| [os.json](evaluations/os.json) | 操作系统 | 38 | ✅ 已建 |
| [ds.json](evaluations/ds.json) | 数据结构 | 28 | ✅ 已建 |
| [co.json](evaluations/co.json) | 计算机组成原理 | 24 | ✅ 默认套件 |
| [network.json](evaluations/network.json) | 计算机网络 | 30 | 🧩 独立扩展；仅通过 `--test-set` 显式运行 |

默认套件合计 **90 题**。2026-08-24 当前 checkout 离线 BM25 Recall@3：OS 0.987、DS 0.929、
CO 1.000，加权 0.972；2026-08-18 的 1.000/0.929/1.000、加权 0.978 作为历史 M5a 基线保留，
详见 [docs/baselines.md](../docs/baselines.md)。Network 30 题和其他新增 JSON 文件都不会自动扩大默认发现集合；
默认课程仍由评测入口显式限定为 OS/DS/CO。额外课程先使用 `--test-set tools/evaluations/{course}.json` 运行，
待路线图和测试契约
更新后再考虑加入默认套件。

## crawler/ — 候选 Markdown 资料处理

crawler 提供 fetch、clean、convert、dedup 和 pipeline 能力，依赖单独记录在
`tools/crawler/requirements.txt`。M6a-P0 已固定离线测试与独立 CI job：

- 默认输出 `platform/.cache/crawler-candidates/{course}`，不自动写入或注册默认 `knowledge/`；
- 未加 `--allow-knowledge-write` 时拒绝写入课程目录；候选必须人工审核后才能检索；
- 离线测试：`pytest tests/M6_crawler -m "m6_crawler and not online"`（mock HTTP，不访问公网）；
- 在线 smoke 非默认：`CRAWLER_ONLINE=1 pytest tests/M6_crawler -m "m6_crawler and online"`；
- CI：`.github/workflows/offline-ci.yml` 的 `crawler-offline` job 安装 crawler 依赖并跑离线 marker；
  在线 smoke 仅 `workflow_dispatch` + `crawler_online_smoke=true`；
- crawler 的存在不代表 M7 的持久化源注册、同步、删除传播或多源隔离完成；这些能力后来在 M7 基础设施范围内完成，crawler 仍不自动注册 Source。


## M8 v3 实现级 graph validator

v3 把跨 artifact 的 REF 解析、摘要/字节/JSONL 计数复算、observer ledger 聚合和 S0→S3 authority 映射交给读取真实目录的实现级 validator。仓库内 fixture 只测试 validator，不导入 LanceDB、不生成真实 1K 输入，也不构成 S1/S2。

```bash
# 在明确的 disposable 空目录生成 5 个微型图，不改 committed fixture
python tools/m8_generate_minimal_1k_v3_fixtures.py --output-root <empty-output-dir>

# 仅在明确选择时，经临时 staging 后刷新 committed fixture
python tools/m8_generate_minimal_1k_v3_fixtures.py --replace-tracked

# 校验单个成功或合法失败图
python tools/m8_validate_minimal_1k_graph_v3.py \
  docs/plans/references/fixtures/m8-minimal-1k-v3/success

# 在 disposable tree 重放 5 个图、22 个 fail-closed mutation 和边界敏感性证明
python tools/m8_test_minimal_1k_graph_v3.py

# 对明确仓库中的完整 commit SHA，从 Git objects 生成确定性 canonical freeze
python tools/m8_freeze_minimal_1k_v3_review.py \
  --commit <full-40-hex-commit> \
  --repo <absolute-repository-path> \
  --output <freeze.json>

# 非标准 Git 安装可显式提供经检查的绝对 executable；可选比较工作区 bytes
python tools/m8_freeze_minimal_1k_v3_review.py \
  --commit <full-40-hex-commit> \
  --repo <absolute-repository-path> \
  --git-executable <absolute-git-executable> \
  --compare-worktree \
  --output <freeze.json>
python tools/m8_test_freeze_minimal_1k_v3_review.py
```

freeze 工具拒绝相对仓库、缩写/不存在/非 commit 对象、不可信 Git executable、缺失或非 blob path、路径逃逸和重复逻辑路径。
Git stdout/stderr 采用流式固定上限；单个 Git blob、累计 99-file bytes、worktree file 与 fixture traversal 也有固定 safety bound；
超限时受控失败且不发布 partial artifact。每个 `cat-file` 返回值还会按 Git blob framing 独立重算 SHA-1 并绑定 `ls-tree` OID；
worktree comparison 禁用仓库本地 `core.fsmonitor`，且 freeze output 必须位于被检查仓库之外，避免发布动作使 `MATCH` 立即失效。
摘要中的 `source_commit` 固定为调用方选择的完整 commit；排序 inventory 固定包含 9 个非 fixture 文件和 90 个 fixture 文件，
合计 99 个 candidate path。工具逐文件输出 SHA-256、bytes、LF 与 Git blob OID，并按 `fixture-tree-v1` 输出 fixture tree 摘要。
`worktree_comparison.status` 在未请求比较时为 `NOT_REQUESTED`，完整仓库 HEAD、clean status 与 99 个 candidate path
都一致时为 `MATCH`；否则为 `DIVERGENT`。除具体 candidate path 外，`divergent_paths` 可包含
`<repository-head>`（当前 HEAD 不是 source commit）或 `<repository-status>`（仓库存在任何 tracked/untracked 状态）。
该 repository-wide 比较不会覆盖或替代 Git object 摘要；指定 `--output` 时，divergence 返回非零且不发布或覆盖目标文件。
发布的 Draft 2020-12 schema 提供通用 envelope/局部定义；当前 graph validator 读取其中的 envelope 声明，并自行机械执行
role-specific primitive 与跨文件检查，不宣称调用了通用 JSON Schema engine。

协议见 [`m8-minimal-1k-dry-run-protocol-v3.md`](../docs/plans/references/m8-minimal-1k-dry-run-protocol-v3.md)。独立 S0 接受和 owner S1 授权前，禁止创建真实实验环境、安装 LanceDB 或执行 1K dry-run。

## m8_prepare_p2_draft011.py — draft-0.11 P2 binding 候选准备

读取已提交的 protocol、P1、identity 及最新 parent 只读测量，在仓库外生成 candidate-only parent/repository
binding。脚本要求仓库干净，验证摘要、P1 前驱、物理身份形状及五种 publication purpose；不会在
`docs/plans/references` 下写 canonical binding 或 P2 gate。

```bash
python tools/m8_prepare_p2_draft011.py \
  "D:/面试实习/draft011-parent-validation-final.json" \
  "D:/面试实习/draft011-p2-candidates"
```

输出仅供 owner 作 P2 决策前核验；不得把仓库外候选当作已冻结 binding 或 `AUTHORIZED / request-p3`。

## source_inventory.py — 外部资料只读盘点

扫描 `D:\\111_Others_Subjects`（或 `--root`）生成机器可读的文件级 manifest。只读：不复制原始文件、不解析全文、不修改外部目录、不建立向量索引。也不构成 M7 Source 生命周期开工。

### 用法

```bash
# 默认扫描 D:\\111_Others_Subjects，写出 reports/source-inventory.json
# 和精简 summary（均 gitignored）
python tools/source_inventory.py

# 指定根目录与输出
python tools/source_inventory.py --root "D:/111_Others_Subjects" --output reports/source-inventory.json
```

每条记录至少包含：`logical_uri`、`course_candidate`、`format`、`size`、`fingerprint`、`classification`、`extraction_support`、`duplicate_status`、`risk_flags`。
`logical_uri` 是相对 POSIX 路径，报告不回显宿主机绝对路径。

默认排除并计入 summary，而不是当成学习资料：

- Unity `Library` / `Temp` / `Logs`（以及 Unity 工程内的 `Assets` / `ProjectSettings` / `Packages`）
- `.venv`、`site-packages`、`node_modules`、`__pycache__`
- DLL / EXE / OBJ / PDB 等构建产物
- 虚拟磁盘（ISO / VMDK / VDI / VHD 等）
- 模型与超限二进制
- 重复文件（manifest 保留 duplicate 标记，unique_candidates 不计）
- 超限压缩包（默认 64MiB）

`classification` 把课件/笔记记为 `study_document`，把 HTML 另记为 `webpage`，避免 Unity 教程网页缓存被算成几千份课件。
目标是得到真正可整理的资料规模，而不是把 Unity Library 里的工程文件误认为学习资料。

离线测试：`pytest tests/source_inventory -m source_inventory`。

## start_local.py — 一键启动

```bash
python tools/start_local.py          # 离线启动并等待 /health
python tools/start_local.py --check  # 只检查健康状态
python tools/start_local.py --use-vector  # 本机已缓存 BGE 时可选
```

默认设置 `SA_USE_VECTOR=false`、`HF_HUB_OFFLINE=1`，并以 `--workers 1` 启动唯一 uvicorn worker；不要求 LLM key。演示步骤见 [docs/demo.md](../docs/demo.md)。

## run_m7_parser_evidence.py — M7 五格式解析/规范化/生命周期证据

运行时在临时目录生成 Markdown、TXT、PDF、PPTX、DOCX fixture，逐格式执行默认 100 个
fixture、20 次运行，并比较当前进程与独立重启进程的解析结果、规范化摘要、文档 ID、chunk
ID 及确定性 identity 摘要。脚本只读取临时生成的输入，不扫描外部资料目录，也不提交 fixture 或二进制
文件。解析器依赖必须匹配 M7 冻结版本；缺失或版本不符时 fail-closed，并在报告中标记
`SKIPPED_UNAVAILABLE`。

```bash
# 完整证据（Git Bash；必须使用 Python 3.11.9，并把报告写入系统临时目录）
test "$(./platform/.venv311/Scripts/python -c 'import platform; print(platform.python_version())')" = "3.11.9"
./platform/.venv311/Scripts/python tools/run_m7_parser_evidence.py \
  --report "${TEMP:?}/m7-parser-evidence.json"

# 快速冒烟：每种格式 1 个 fixture、1 次运行
./platform/.venv311/Scripts/python tools/run_m7_parser_evidence.py --quick

# 允许部分解析器不可用并继续其他格式（仍会在报告中记录 UNAVAILABLE）
./platform/.venv311/Scripts/python tools/run_m7_parser_evidence.py --allow-unavailable
```

PowerShell 中的完整证据报告路径使用
`--report "$env:TEMP\m7-parser-evidence.json"`。不要在 Git Bash 中写 `%TEMP%`：它不会展开，反而会在仓库内创建字面量
`%TEMP%/` 目录。

报告 schema 为 `sa.source.parser-normalized-identity-evidence.v1`，包含 fixture digest、解析器
版本、规范化 digest、稳定 document/chunk identity、冷启动/重启不一致计数及外部读取计数。

2026-09-05 历史完整冻结结果：seed `20260904`，五种格式各 100 个运行时 fixture、各 20 次运行，全部
`PASS`；parser、normalization、cold-restart、deterministic identity 失败均为 0，`external_source_reads=0`、
`tmp_only=true`。2026-09-06 已在 `platform/.venv311`（CPython 3.11.9 与精确冻结依赖）再次完成相同
100×20 协议，五格式全部 `PASS`，失败计数均为 0；报告只写入系统临时目录且不入库。Python 3.13.3 对 TXT
精确版本合同返回 `PARSER_UNAVAILABLE` 是预期 fail-closed。该 parser/normalization/identity 证据与独立的 source lifecycle/provenance E2E 及 1k/3k BGE 检索 benchmark 分离，本身不自动构成 M7 exit 或 M8 开工授权；M7 后续由 2026-09-06 的独立人工完成批准关闭，M8 仍未获批。

## run_m7_benchmark.py — M7 用户源 1k/3k 评测

运行时可生成 fixture，不入库。当前 smoke 使用 source-local hash vector（已附着且 identity 对齐），报告仍 `m7_exit=false`，不是冻结 20 次 BGE 协议，不能当作 M7 退出证据，也不批准 M8/Milvus 或 Network。

```bash
./platform/.venv/Scripts/python tools/run_m7_benchmark.py --report artifacts/m7-benchmark.json
./platform/.venv/Scripts/python tools/run_m7_benchmark.py --quick
./platform/.venv/Scripts/python tools/profile_m7_search.py --report artifacts/m7-search-profile.json
```

`profile_m7_search.py` 只剖析 Search 热路径阶段延迟，默认 5 次 warmup + 20 次独立 3k 查询。2026-09-03 source-local hash 剖析 p50 约 105 ms，仍 `m7_exit=false`，不能覆盖冻结 20 次 BGE 协议。

## run_m7_frozen_benchmark.py — M7-3 冻结 BGE 证据

冻结协议，不是 disposable hash smoke：

```bash
./platform/.venv/Scripts/python tools/run_m7_frozen_benchmark.py --workload 1k-single --report artifacts/m7-frozen-1k.json
./platform/.venv/Scripts/python tools/run_m7_frozen_benchmark.py --report artifacts/m7-frozen-benchmark.json
./platform/.venv/Scripts/python tools/run_m7_frozen_benchmark.py --quick
```

默认查询 20 warm-up + 200 measured；FULL 每个样本独立 OS 进程 5 warm-up + 20 measured；backend 为 BGE `BAAI/bge-small-zh-v1.5`。报告按冻结门槛判定，任一失败则 `m7_exit=false`。不得把 `--quick`/hash 冒充冻结证据，也不得据此启动 M8。


2026-09-03 disposable 一次样本：1k-single Recall@5=1.000、查询 p95 149 ms；3k-aggregate Recall@5=1.000、查询 p50 392 ms（超过冻结 250 ms）。FULL 样本数为 1，不是冻结的 20 次。

---

*创建：2026-08-11 · 更新：2026-09-06（M7 五格式冻结证据仍须在 Python 3.11.9 精确依赖环境执行）· 维护：随新增工具脚本与评测集同步更新*

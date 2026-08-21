# 辅助工具（tools/）

> RAG 评测、索引生成、资料整理引导等辅助脚本。用于数据驱动优化知识库检索效果。

## 目录结构

```
tools/
├── README.md              # 本文件（工具文档）
├── run_evaluation.py      # ★ 统一 RAG 评测入口
├── start_local.py         # 一键启动工作台并做 /health 检查
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

默认套件合计 **90 题**。M5a 离线 BM25 Recall@3：OS 1.000、DS 0.929、CO 1.000。
新增 JSON 文件不会自动扩大默认发现集合；默认课程仍由评测入口显式限定为 OS/DS/CO。额外课程先使用
`--test-set tools/evaluations/{course}.json` 运行，待路线图和测试契约更新后再考虑加入默认套件。

## crawler/ — 候选 Markdown 资料处理

crawler 提供 fetch、clean、convert、dedup 和 pipeline 能力，依赖单独记录在
`tools/crawler/requirements.txt`。M6a-P0 已固定离线测试与独立 CI job：

- 默认输出 `platform/.cache/crawler-candidates/{course}`，不自动写入或注册默认 `knowledge/`；
- 未加 `--allow-knowledge-write` 时拒绝写入课程目录；候选必须人工审核后才能检索；
- 离线测试：`pytest tests/M6_crawler -m "m6_crawler and not online"`（mock HTTP，不访问公网）；
- 在线 smoke 非默认：`CRAWLER_ONLINE=1 pytest tests/M6_crawler -m "m6_crawler and online"`；
- CI：`.github/workflows/offline-ci.yml` 的 `crawler-offline` job 安装 crawler 依赖并跑离线 marker；
  在线 smoke 仅 `workflow_dispatch` + `crawler_online_smoke=true`；
- crawler 的存在不代表 M7 的持久化源注册、同步、删除传播或多源隔离已经完成。

## start_local.py — 一键启动

```bash
python tools/start_local.py          # 离线启动并等待 /health
python tools/start_local.py --check  # 只检查健康状态
python tools/start_local.py --use-vector  # 本机已缓存 BGE 时可选
```

默认设置 `SA_USE_VECTOR=false`、`HF_HUB_OFFLINE=1`，不要求 LLM key。演示步骤见 [docs/demo.md](../docs/demo.md)。

---

*创建：2026-08-11 · 更新：2026-08-21（crawler P0：离线 marker 与独立 CI）· 维护：随新增工具脚本与评测集同步更新*


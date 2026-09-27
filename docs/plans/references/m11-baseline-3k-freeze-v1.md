# M11 Baseline / 3K 冻结物 v1（历史准入准备物）

> 当前地位：本文件形成于准入前，保留当时 2000 hard max 与非授权时态作为审计记录；后续 M11 v1.1
> 已批准开工、创建 `tests/M11/`、将 total hard max 提至 4000（默认仍 1200）并处理冻结 P0 白名单。
> 真实外部下载和正式发布仍需单次确认。
>
> 状态：**准入准备物**。关闭 M11 计划 §8 的「Baseline/3K workload、来源、许可、parser、chunk、质量和检索阈值冻结」一项。
> 权威决策见 [`m11-decision-closure-v1.md`](m11-decision-closure-v1.md)。本文只回答「**冻结什么**」。
>
> **不**批准 M11 准入或开工，**不**创建 `tests/M11/`，**不**下载、抓取、导入、解析、embedding、建索引或发布语料，
> **不**提高 `max_chunks_total`。`admission_status` 仍为 `BLOCKED`，`approval` 五字段仍为空。

## 0. 计量与硬上限（`M11-SCALE-GATES`）

| 项 | 冻结值 |
| --- | --- |
| 计量单位 | 可检索 **approved chunks** |
| Baseline | 当前默认知识包 OS/DS/CO；约 **682** chunks（`docs/baselines.md` 2026-08-31 / 1k current-state reference） |
| 3K | 首个真实扩展 Gate：3,000 真实 approved chunks；**不是**完成 |
| 10K | M11 退出目标：10,000 真实 approved chunks |
| 30K / 100K | 不阻塞 M11 完成 |
| 形成时硬上限 | 本准备物形成时默认 **1200**、环境变量硬顶 **2000**；后续 v1.1 已批准并实施 hard max **4000**，默认仍 1200 |
| 提额边界 | 仅 `SA_SOURCE_MAX_CHUNKS_TOTAL` hard max 到 4000；per-source 与额外来源数量不变，超过 4000 需重新批准 |
| 计入 | 禁止纯 synthetic / 半合成 / overlap 膨胀 / Network candidate |
| 报告必含 | document 数、chunk 数、source 数；缺任一即 fail closed |
| 隐私 | 计量报告不含正文、宿主路径、凭据 |

**停止条件**：任一 Gate 许可不明、静默丢解析、或默认 90 题退化即停止。

## 1. Baseline 保护面

| 项 | 冻结值 |
| --- | --- |
| 默认评测 | OS/DS/CO 90 题（OS 38 + DS 28 + CO 24）；Network 30 题仍为显式扩展集 |
| 2026-08-31 Recall@3 | OS **1.000** / DS **0.929** / CO **1.000**，加权 **0.978**（`docs/baselines.md` 治理冻结复测） |
| 下限 | 默认 90 题 Recall@3 **不得低于**上述冻结值 |
| Network | 31 篇保持 `review / candidate / unresolved`，**不算** M11 approved |
| chunk schema | 默认包继续 `sa.chunk.markdown-h2.v1`（`platform/app/sources/markdown_pack.py`） |
| parser | Markdown 为 3K 生产正文；PDF/PPTX/DOCX/TXT 沿用 M7 五格式 freeze；`PARSE_TIMEOUT_SECONDS = 30.0` 只能收紧 |
| TXT | 当前 Python 3.13.3 上按精确 `cpython-textio==3.11.9` 合同为 `PARSER_UNAVAILABLE` fail-closed；M11 **不**放宽 |
| 数据面 | SQLite registry + linear cosine + 默认 BM25（`M11-M8-EXIT` 维持现状） |

## 2. 3K 来源白名单与领域配额（`M11-SOURCE-ALLOWLIST`）

3K **只允许 P0**。Linux Kernel Documentation 为 P1，不进 3K。Stack Exchange 为 P2，3K/10K 默认关闭。

| source_id | 领域层 | 3K 最大占比（chunks） | 许可核验入口（官方 URL，不含私人路径） |
| --- | --- | --- | --- |
| `knowledge-pack`（OS/DS/CO 默认包） | 教学解释 | ≤ 30% | 项目原创；`project_authored=true` |
| `project-authored-evals` | 评测 | ≤ 15% | 项目原创 |
| `mit-ocw-6-004-2017` | 教学解释 / CO | ≤ 20% | https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/ ；条款 https://ocw.mit.edu/pages/privacy-and-terms-of-use/ |
| `opendsa-main` | 教学解释 / DS | ≤ 25% | https://github.com/OpenDSA/OpenDSA |
| `rfc-editor-index` | 权威规范 / 网络 | ≤ 20% | https://www.rfc-editor.org/ ；IETF Trust https://trustee.ietf.org/documents/trust-legal-provisions/ |
| `iana-registries` | 权威规范 / 网络事实 | ≤ 10% | https://www.iana.org/protocols |

**合计约束**（必须同时成立）：

- 非白名单 chunks = 0
- 单一来源不得超过上表占比
- 权威规范层（RFC + IANA）合计 ≤ 25%
- 教学解释层合计 ≥ 50%
- 评测层 ≤ 15%
- Network 31 篇、未授权题库、付费墙、登录墙、robots 禁止页、全量 SE dump = 0

占比在 **3K Gate 开跑前**按上表冻结；覆盖只能收紧，不能把 Network candidate 或未审 dump 算进 Gate。
每个来源仍须重新做许可 / revision 核验；runbook 是**非权威**参考。

## 3. 许可与 provenance（`M11-LICENSE-PROVENANCE`）

每个 approved document 必须同时有：

1. canonical URL **或** 核验过的 `project_authored=true`（二选一）
2. 许可标识，且 `license_status=approved`
3. revision
4. 抓取 / 导入时间
5. 内容 digest

每个 chunk 必须追溯到 document、Source revision、chunk policy、embedding generation、发布 snapshot。
`license_status=unresolved`、缺 canonical URL 且非项目原创、第三方材料未剥离 → 保持 `candidate`。
文档级 P0 登记仍是 `docs/reference/document-mapping.json`；运行时权威仍是 M7 Source Registry。
映射表**不**自动晋升 runtime approved。

## 4. Parser / chunk / publication / sync

| 决策 | 冻结身份 |
| --- | --- |
| Parser | Markdown 生产正文；五格式 fail-closed；超时码 `SOURCE_PARSE_TIMEOUT`；静默丢文件 = 0 |
| Chunk | 默认包 `sa.chunk.markdown-h2.v1`；用户源走 M7 normalized units；`chunk_id = sha256(document_id + chunk_key + chunk_schema)`；精确重复 approved = 0；禁止 overlap 膨胀 |
| Publication | candidate → approved → generation publication；复用 M10 `GenerationGate` 与 M7 CURRENT/PREVIOUS / last-good；半发布可见 = 0 |
| Incremental sync | fingerprint 驱动 INCREMENTAL upsert/delete 为常规路径；`replace_all()` 禁止作为常规；删除后零召回 |

## 5. 质量与检索（`M11-QUALITY-EVALUATION` / `M11-RETRIEVAL-EVALUATION`）

### 5.1 每个 Gate 开跑前必须写入报告的形状（本冻结物钉住「必须有」，不发明未核验百分数）

| 指标 | Baseline | 3K / 10K |
| --- | --- | --- |
| 许可 / URL 或项目原创 / digest / revision 完整率 | 100%（默认包按 `project_authored`） | 100% |
| 静默丢解析 | 0 | 0 |
| 精确重复 approved | 0 | 0 |
| 私人语料 | 0 | 0 |
| 领域配额 | 默认包三课 | 见 §2 |
| 人工抽样事实准确率 | 不在本准备物发明百分数 | **必须有阈值**；每个 Gate 开跑前写入该 Gate 报告 |
| 默认 90 题 Recall@3 | ≥ 2026-08-31 冻结值 | 不得退化 |
| 3K/10K 独立 query/gold | 不适用 | **必须有**；不得用 90 题冒充 10K 质量 |
| Recall@3 / Recall@5 / MRR / no-hit / hard-negative | 90 题保护基线 | 独立报告；绝对值在开跑前冻结 |
| 删除 Source 后召回 | 0 | 0 |
| 100K synthetic | 不得当作质量 PASS | 只能复用工程资源门槛（延迟 / RSS / 磁盘） |
| Planner 输入 | 有界目录 / 摘要 | 10K 下仍有界，不得把全书塞进上下文 |

### 5.2 3K query/gold 形状（冻结类别，不冻结具体语料）

实施时物化为机器可读文件并钉住摘要。本版冻结的是**类别 × 来源层 × 期望**：

| 类别 | 来源层 | 期望 |
| --- | --- | --- |
| 中文教学事实（进程 / 树 / CPU） | 默认包或 OpenDSA / OCW 解释层 | top-3 命中对应 document |
| 协议编号 / RFC 标题 | RFC 权威层 | 命中对应 RFC；不得被教学层淹没到零召回 |
| 注册表事实（端口 / 媒体类型） | IANA | 命中 registry 短事实 chunk |
| 跨语言（中文问、英文权威） | RFC 或 OCW | 至少一击中权威层 |
| hard-negative（无关课程） | 任意 | 不得把无关 Source 送进 top-3 |
| 删除后 | 任一已删 Source | 零召回 |

**不**在本文件填写 3K Recall 绝对分数——那要等真实 query/gold 冻结并在 Gate 开跑前写入报告。

## 6. 隐私与目录（`M11-PRIVACY-RETENTION`）

见仓库根 [`data/README.md`](../../../data/README.md) 与 `.gitignore`：

- Git 只收 `data/README.md` 与未来小型 `data/manifests/`
- raw / normalized / candidates / approved 大文件、reports 正文、snapshots 大文件不入库
- 私人学习状态不是 M11 语料
- 报告只留计数、digest、官方 URL

## 7. 本冻结物**不**做什么

- 不批准准入或开工。
- 不提高 chunk 限额。
- 不下载 MIT OCW / OpenDSA / RFC / IANA / Linux docs。
- 不创建 `tests/M11/`。
- 不发明未核验的 3K/10K Recall 绝对分数或事实准确率百分数。
- 不把 Network 自动晋升为 approved。

# M8–M12 规模化范围批准记录 v1

> 状态：`APPROVED / SCOPE_FROZEN`
>
> 本文收敛 M8–M12 的目标、规模单位、阶段边界和部署形态。负责人 `justtodo123` 于 2026-09-10 明确选择：
> M11 以 10K 真实 chunks 为正式退出目标，M12 以可选云端单用户部署为正式边界，并逐项批准 M8 D1–D8。
> 本批准只冻结范围，不批准阶段、后端、实验或执行。M8/M9/M10/M11/M12 继续 `BLOCKED / NOT_STARTED`。

## 1. 决策背景

项目当前默认知识包约 682 chunks；M7 已完成用户源、source lifecycle、1k/3k 合成规模证据和 SQLite/BM25/vector
离线 fail-closed 基础设施。项目下一步需要同时解决两类不同问题：

1. **容量与架构能力**：证明单机离线检索数据面能在 100K chunks 下构建、查询、过滤、增量更新、删除、恢复和回退；
2. **真实数据产品价值**：以许可清晰、可追溯、质量可验证的真实资料逐步扩展生产知识库，而不是用低质量内容机械补量。

专业向量后端只能改善数据面的容量和检索成本，不能替代来源许可、parser、去重、评测、规划、Runner 或部署治理。

## 2. 唯一规模单位

本规划中的规模统一按**可检索 chunk 数量**计量：

- `1K` = 1,000 chunks；
- `10K` = 10,000 chunks；
- `30K` = 30,000 chunks；
- `100K` = 100,000 chunks。

`100K` 不表示 100,000 篇文档、题目、Source 或用户。任何计划、benchmark 和报告必须显式写明 workload 中的
Source/document/chunk 构成，禁止只写“十万级”。

## 3. 统一架构政策

1. **local-first**：本地离线 profile 是默认能力；没有网络、云服务器或专业可选依赖时，默认知识包和既有学习闭环
   必须继续可用。
2. **控制面权威不变**：SQLite/M7 Registry 继续独占 source owner、授权、revision、generation、snapshot、lifecycle、
   tombstone、hard-delete receipt、provenance 和审计历史。
3. **数据面可替换**：专业向量索引只能是从已批准 manifest 可重建的派生物，不能成为权限、删除、学习状态、session 或
   review history 的权威。
4. **分层后端策略**：SQLite linear cosine 保留为 correctness oracle 和 fallback；LanceDB 是 10K–100K 单机嵌入式第一
   评估候选；Qdrant 只在可选云端、常驻服务、多进程或明确并发条件下重新评估；Milvus 当前不采用。
5. **不得预选后端**：候选定位不等于选择。八项 M8 Decision、冻结实证和负责人独立批准未闭合前，不得把 LanceDB、
   Qdrant 或其他后端写成默认或生产依赖。

## 4. Embedding profile 政策

当前基线保持：

- model：`BAAI/bge-small-zh-v1.5`；
- dimension：`512`；
- dtype：`float32`；
- normalization：L2 normalized。

该 profile 是现行基线，不是永久 schema。每个索引 generation 必须绑定 model、model revision、dimension、dtype、
normalization、chunk-policy 与 embedding fingerprint。任一字段变化必须生成新 generation 并重新构建，禁止在同一索引
混用不同 profile。

是否升级模型或维度只能由冻结的真实检索评测决定，不能根据 chunk 数量自动提高维度。评测至少覆盖中文→中文、中文→英文、
中英文技术术语、缩写/全称、代码/协议编号、hard negative、no-hit 与 metadata filter。

## 5. M8 目标：可扩展检索数据面

M8 的唯一目标为：

> 在保持 SQLite/M7 Registry 控制面权威和默认离线能力的前提下，建立可替换、可重建、可回退的检索数据面，验证
> 单机 100K chunks 的容量与生命周期能力，并经负责人决定本地专业后端是否值得采用。

M8 的规模层级：

- `1k-correctness`：正确性、生命周期和 SQLite oracle parity；
- `10k-single-user`：本地单用户真实负载能力；
- `100k-capacity`：固定 synthetic/半合成容量、资源与恢复证据；
- `100k-filtered`：owner/source/generation/snapshot/tombstone 等过滤与隔离；
- `100k-concurrent`：仅在负责人确认需要并发证据时执行，用于判断是否触发服务型后端评估。

M8 不交付 100K 真实生产语料，不部署云服务器，不实现多用户，不批准 Qdrant server，也不以 synthetic capacity
证据声称真实检索质量或产品落地。

## 6. M9 目标：规模感知的目标规划

M9 保留目标驱动学习计划和 mastery 的原有定位，但必须适配 100K 容量：Planner 只读取目录、topic graph、Source 摘要、
版本和 mastery；正文通过受限检索按需取得。M9 不扫描或注入全部 chunks，不负责索引构建、后端选择、数据扩展或云部署。

## 7. M10 目标：可恢复的自主 Runner

M10 保留受控自主 Runner、写授权、checkpoint、幂等、EffectLedger 和恢复边界；新增 ingestion、embedding、reindex、
evaluation 等长任务的异步、取消、进度、资源预算和恢复要求。模型不得直接写向量数据库，批量任务不得阻塞正式学习会话。

## 8. M11 目标：10K 高质量真实数据

M11 为拟议的新阶段，正式退出目标是：

> 发布并验证 10,000 个许可清晰、来源可追溯、质量可验证的真实 approved chunks。

执行 Gate 为当前基线 → 3K → 10K。30K 和 100K 只作为后续扩展 Gate，不阻塞 M11 完成。每级必须覆盖来源与许可、
revision、parser、chunk provenance、去重、领域分布、事实准确率抽样、人工审核、真实 query/gold、Recall/MRR、no-hit、
hard-negative、跨语言与删除传播。

100K synthetic capacity 不能替代 M11 的真实数据质量证据；不得通过重复切块、低质量抓取或未审内容补量。

## 9. M12 目标：可选云端单用户部署

M12 为拟议的新阶段，正式退出目标是：

> 在保留本地离线默认 profile 的同时，在负责人提供的云服务器上完成可复现、可撤销、可备份恢复的单用户云端部署。

M12 可包含 HTTPS/认证、secret 管理、后台 ingestion worker、资源/成本预算、备份恢复、可观测性和条件式 Qdrant
评估。用户本地私人资料默认不上传，上传、导出、删除和数据驻留必须显式授权。

M12 不包含多租户、团队共享、百万级规模或集群编排；这些能力如未来需要，必须进入新的阶段和决策集。

## 10. 阶段依赖

拟议依赖顺序为：

```text
M8 可扩展检索数据面
  → M9 规模感知目标规划
    → M10 可恢复自主 Runner
      → M11 10K 高质量真实数据
        → M12 可选云端单用户部署
```

该顺序可在后续阶段准入设计中进一步拆分事实型前置，但不得让 M11/M12 反向改变 M7 控制面权威或本地离线默认。

## 11. 复核与撤销条件

需要复核本范围决策的条件：

- 真实数据增长超过 30K 或 100K；
- 出现多用户、团队共享、跨设备同步或持续高并发需求；
- 当前 embedding profile 在冻结真实评测集上未达标；
- 单机 100K 的 RSS、磁盘、延迟、构建或恢复超过批准预算；
- 云服务器配置、安全或成本边界发生实质变化；
- 数据来源、许可证或隐私政策变化。

必须撤销或缩小已批准范围的条件：

- 无法维持 M7 control-plane 权威和删除/授权语义；
- 专业后端成为不可重建的唯一权威；
- 本地离线默认被强制云依赖破坏；
- 真实数据无法满足许可、来源或质量 Gate；
- 云端部署泄露用户正文、凭据、绝对路径或未授权数据。

## 12. 负责人批准记录

以下字段必须由负责人明确填写或引用独立批准记录后，本文才可从草案转为批准范围：

- 决策版本：`m8-m12-scope-decision-v1`
- 责任人：`justtodo123`
- 决定日期：`2026-09-10`
- 独立批准人：`justtodo123`
- 独立批准日期：`2026-09-10`
- 批准引用：`本会话对 M11 10K 真实 chunks、M12 可选云端单用户边界及 M8 D1–D8 的逐项明确批准`
- 最终状态：`APPROVED / SCOPE_FROZEN`

该批准只允许同步规划与门禁，不构成 `ADMITTED` 或 `AUTHORIZED`。禁止创建旧 V13 根、运行 V13、安装候选后端、
启动 Qdrant 服务或开始 M8–M12 生产实现。

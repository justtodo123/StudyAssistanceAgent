# M11 决策闭合记录 v1

> 当前地位：本文件记录准入前十项 Decision 的闭合过程，正文中的 `BLOCKED` 与非授权语句均为历史时态；
> M11 计划 §8.1/§8.2 与登记表后续已批准 `ADMITTED / IN_PROGRESS`、开工以及 v1.1 A1/A2/A3。
> 真实外部下载和正式发布仍需单次确认。

> 状态：**批次 ①②③ 均已获 owner 批准**。M11 十项 Decision 在 `stage-admission-gates.json` 中**全部 `RESOLVED`**。
> 本文件是闭合面：令牌串与十项必备内容。**决策闭合不等于准入**——`admission_status` 仍为 `BLOCKED`，
> `approval` 五字段仍为空。不得下载、抓取、导入、解析、embedding、建索引或发布任何语料。
>
> 三项前置已于 2026-09-23 `SATISFIED`（`M11-M8-EXIT` 维持现状），这**不构成**准入。

## 0. 用法与推进方式

- **分批推进**：① `SCALE-GATES` + `SOURCE-ALLOWLIST` + `LICENSE-PROVENANCE` + `PRIVACY-RETENTION`；
  ② `PARSER-QUALITY` + `CHUNK-POLICY` + `PUBLICATION` + `INCREMENTAL-SYNC`；
  ③ `QUALITY-EVALUATION` + `RETRIEVAL-EVALUATION`。
- 每批在本文件追加一节。**只有 owner 批准过的批次**，其 Decision 才可由 `OPEN` 改为 `RESOLVED`。
- 与 `docs/PLAN.md` 或 M11 计划冲突时以后者为准。

## 1. 批次 ①：量什么、从哪来、许可与隐私

### 1.1 `M11-SCALE-GATES`

**拟定 `value`**：

```text
BASELINE_DEFAULT_PACK_ONLY__3K_FIRST_REAL_GATE__10K_EXIT__30K_100K_OUT_OF_SCOPE__LIMITS_MUST_BE_RAISED_AFTER_ADMISSION_NOT_BEFORE
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 计量单位是**可检索 approved chunks**。Baseline = 当前默认知识包（OS/DS/CO；Network 仍 candidate，不进默认索引）。3K 是首个真实扩展 Gate，不是完成。10K 是 M11 退出目标。30K/100K 不阻塞完成。 |
| **形成时硬上限（2026-09-23，必须写准）** | `platform/app/source_config.py` 的 `SourceLimits.max_chunks_total` 默认 **1200**，当时环境变量硬顶 **2000**。M6a 计划禁止在未获批时提高该限制；本决策冻结分级，不在该批偷偷改限额。后续 v1.1 A2 已获批准将硬顶提高到 **4000**，默认仍为 1200，见 M11 live plan §8.2。 |
| **停止条件** | Baseline：默认包 identity/provenance/90 题回归稳定。3K：3,000 真实 approved chunks，禁止纯 synthetic 计数。10K：10,000 真实 approved chunks + 增量同步 + 质量/检索/lifecycle 联合验收。任一 Gate 许可不明、静默丢解析、或默认 90 题退化即停止。 |
| **默认与覆盖** | 默认不扩展。覆盖只能收紧（更少来源、更低占比、更严许可），不能把 Network candidate 或未审 dump 算进 Gate。 |
| **校验与失败** | Gate 报告必须同时给出 document 数、chunk 数、source 数；缺任一计量即 fail closed。synthetic/半合成不得计入 3K/10K。 |
| **隐私** | 计量报告不含正文、宿主路径、凭据。 |
| **兼容** | 不改默认 90 题包；不把 Network 自动晋升为 approved。 |
| **量化阈值** | Baseline 不退化；3K/10K 计数 = 真实 approved chunks；精确重复不得用切块膨胀凑数。 |
| **证据** | 本文件 + M11 计划 §5；实施后拟 `tests/M11/` 的计量护栏。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 1.2 `M11-SOURCE-ALLOWLIST`

**拟定 `value`**：

```text
P0_PROJECT_PACK_AND_LICENSE_CLEAR_OPEN_COURSES_ONLY_AT_3K__NETWORK_AND_STACKEXCHANGE_NOT_IN_FIRST_GATE__DOMAIN_QUOTAS_FROZEN_PER_GATE
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 3K 只允许 P0：项目人工知识包与原创评测集、许可明确的 MIT OCW 子集、OpenDSA 经确认教材内容、RFC Editor approved subset、IANA registries。Linux Kernel Documentation 为 P1，不进 3K。Stack Exchange 为 P2，3K/10K 默认关闭。 |
| **排除** | Network 31 篇保持 `review / candidate / unresolved`，**不算** M11 approved。未授权题库、付费墙、登录墙、robots 禁止页、全量 SE dump 一律排除。 |
| **领域配额** | 每个 Gate 执行前冻结领域最大占比，防止 RFC/Linux 淹没 DS/CO/DB 教学领域。权威规范层、教学解释层、评测层分开统计。 |
| **默认与覆盖** | 默认白名单外的来源不可导入。新增来源必须改本决策并重新批准。 |
| **校验与失败** | 不在白名单的 source_id 不得进入 candidate pipeline；发现即拒绝该 Source，不部分发布。 |
| **隐私** | 白名单记录官方 URL 与许可标识，不含私人路径。 |
| **兼容** | 沿用 `data-expansion-runbook.md` 作**非权威**参考；每个来源仍须重新做许可/revision 核验。 |
| **量化阈值** | 3K 中非白名单 chunks = 0；单一来源不得超过预冻结占比。 |
| **证据** | 本文件 + runbook §3；实施后拟来源 inventory 报告。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 1.3 `M11-LICENSE-PROVENANCE`

**拟定 `value`**：

```text
EVERY_APPROVED_DOCUMENT_HAS_CANONICAL_URL_OR_PROJECT_AUTHORED__LICENSE_APPROVED__DIGEST_REVISION_CAPTURE_TIME__UNRESOLVED_STAYS_CANDIDATE
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 每个 approved document 必须有：canonical URL **或** 核验过的 `project_authored=true`（二选一）、许可标识、许可状态 `approved`、revision、抓取/导入时间、内容 digest。每个 chunk 必须追溯到 document、Source revision、chunk policy、embedding generation、发布 snapshot。 |
| **权威** | 文档级来源与许可的 P0 登记仍是 `docs/reference/document-mapping.json`；运行时权威仍是 M7 Source Registry。映射表**不**自动晋升 runtime approved。 |
| **失败** | `license_status=unresolved`、缺 canonical URL 且非项目原创、第三方材料未剥离 → 保持 `candidate`，不得进入 published view。撤销许可必须传播到 BM25/vector/cache/provenance/plan grounding。 |
| **默认与覆盖** | 默认 fail closed。不得用“后续补许可”把候选算进 3K/10K。 |
| **隐私** | provenance 记录不含私人正文；审计只留 digest 与官方 URL。 |
| **兼容** | 不改 Network 的 `unresolved` 状态。 |
| **量化阈值** | approved 集合中许可不明 = 0；无 canonical URL 且非项目原创 = 0。 |
| **证据** | 本文件 + `document-mapping.json` 政策段；实施后拟 provenance 报告。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 1.4 `M11-PRIVACY-RETENTION`

**拟定 `value`**：

```text
NO_PRIVATE_USER_CORPUS_IN_APPROVED_VIEW__RAW_OUTSIDE_GIT__REPORTS_DIGEST_ONLY__DELETE_PROPAGATES__RETENTION_BOUNDED
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 私人学习状态、会话、复习、plan、Runner ledger **不是** M11 语料。M11 approved view 只含许可清晰的教学/规范文档。raw/normalized 大文件放仓库外；Git 只存 manifest、脚本、审核结果、小型 fixture。 |
| **目录** | 沿用 runbook 的 `data/{manifests,raw,normalized,candidates,approved,rejected,reports,snapshots}`；`rejected/` 只保存原因和身份，不复制违规正文。 |
| **保留** | 报告与 snapshot manifest 保留与 Source revision 一致；过期 raw 可删但必须能从官方 URL + revision 重建。用户数据保留仍由学习状态库策略管理，M11 不延长、不复制。 |
| **删除** | Source 删除、许可撤销、revision 替换必须传播到检索面与计划 grounding；删除后零召回。 |
| **默认与覆盖** | 默认不收录用户私人笔记。覆盖不能把仓库外的只读原始资料根原样入库。 |
| **校验与失败** | 报告/日志/manifest 出现宿主绝对路径或凭据即 fail closed。 |
| **兼容** | 不 bump 学习状态 `SCHEMA_VERSION`；不把用户源自动并入默认 90 题。 |
| **量化阈值** | approved 中私人用户语料 = 0；Git 中无原始大文件；路径泄漏 = 0。 |
| **证据** | 本文件 + runbook §2；实施后拟隐私扫描与路径护栏。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 1.5 本批**不做**什么

- 不把十项 Decision 标 `RESOLVED`。
- 不提高 `max_chunks_total` 硬上限。
- 不下载 MIT OCW / OpenDSA / RFC / IANA / Linux docs。
- 不创建 `tests/M11/`、不改生产检索路径、不发布 candidate。
- 不批准 M11 准入或开工。

## 2. 批准记录

| 批次 | Decision | 裁定 | 批准人 | 批准时间 | 批准引用 |
| --- | --- | --- | --- | --- | --- |
| ① | `M11-SCALE-GATES` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下「批次 ① 批准依据」 |
| ① | `M11-SOURCE-ALLOWLIST` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下「批次 ① 批准依据」 |
| ① | `M11-LICENSE-PROVENANCE` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下「批次 ① 批准依据」 |
| ① | `M11-PRIVACY-RETENTION` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下「批次 ① 批准依据」 |

### 批次 ① 批准依据

| 批准字段 | 值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-23 |
| approval_reference | User instruction: 「继续」——回应「请批准批次 ①。批准后我会把这四项标 `RESOLVED`，再写批次 ②」。按本仓既有惯例逐字引用原话并说明解读：未提出修改，故 §1.1–§1.4 的 `value` 与十项必备内容逐字生效 |

**本批批准做什么**：把登记表中上述四项由 `OPEN` 改为 `RESOLVED`，`value` 取 §1 令牌串。

**本批批准不做什么**：不批准 M11 准入或开工；不提高 chunk 限额；不下载语料；不创建 `tests/M11/`；不改写 M8；其余六项 Decision 仍 `OPEN`。

## 3. 批次 ②：parser / chunk / publication / incremental sync

四项彼此耦合（语料如何切、如何发布、如何增量），故同批裁定。全部以批次 ① 的白名单、许可 fail-closed 和「提额在准入后」为前提。

### 3.1 `M11-PARSER-QUALITY`

**拟定 `value`**：

```text
MARKDOWN_IS_3K_PRODUCTION_TEXT__M7_FIVE_FORMAT_FAIL_CLOSED__NO_SILENT_DROP__TIMEOUT_TIGHTEN_ONLY__TXT_UNAVAILABLE_ON_313_IS_CONTRACT
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 3K 生产正文以 Markdown 为主。PDF/PPTX/DOCX/TXT 沿用 M7 五格式 freeze 与 fail-closed 合同：失败、乱码、空文档、结构丢失均不得静默丢弃，不得计入 approved。 |
| **超时** | `PARSE_TIMEOUT_SECONDS` 默认 30，只能收紧；超时稳定码 `SOURCE_PARSE_TIMEOUT`。 |
| **TXT 合同** | 当前 Python 3.13.3 上 TXT 按精确 `cpython-textio==3.11.9` 合同为 `PARSER_UNAVAILABLE` fail-closed；M11 **不**为凑数放宽该合同。 |
| **人工复核** | parser 失败进入 `rejected/`（只留原因与身份）；不得用“大体能读”把失败文档算进 Gate。 |
| **默认与覆盖** | 默认 fail closed。覆盖不能新增未冻结 parser 或升级承重 pin 而不改 Decision。 |
| **校验与失败** | 静默丢文件 = 0；失败文档出现在 approved = 0。 |
| **隐私** | 失败记录不含正文、路径、凭据。 |
| **兼容** | 不改 M7 parser matrix 身份与 normalized document 形状。 |
| **量化阈值** | parser 静默丢失 = 0；approved 中无 `PARSE_FAILED` / `PARSER_UNAVAILABLE` 产物。 |
| **证据** | 本文件 + `parser_matrix.py` / `tests/M7/`；实施后拟 M11 parser 报告。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.2 `M11-CHUNK-POLICY`

**拟定 `value`**：

```text
DEFAULT_PACK_MARKDOWN_H2_V1__USER_SOURCE_M7_NORMALIZED_UNITS__NO_OVERLAP_INFLATION__IDENTITY_FROM_DOCUMENT_KEY_SCHEMA
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 默认知识包继续 `sa.chunk.markdown-h2.v1`（按 H2 切）。用户源走 M7 normalized units，不另造第四套 chunk 身份。 |
| **身份** | `chunk_id` 由 `document_id + chunk_key + chunk_schema` 派生；logical URI 与 document_id 必须可复算，伪造身份 fail closed（M10 pack manifest 已证明该纪律）。 |
| **去重** | 按 content digest；精确重复不得进入 approved。禁止用 overlap / 重复切块膨胀凑 3K/10K。 |
| **边界** | 标题、代码块、表格、公式尽量不在块中切开；切不开时允许单块超容量，但不得为此改计量口径。 |
| **默认与覆盖** | schema 变更必须改本决策。覆盖只能更严（更少 overlap、更强去重）。 |
| **校验与失败** | 身份冲突、digest 碰撞未裁决、schema 未知 → 该文档不得发布。 |
| **隐私** | chunk 元数据不含宿主路径。 |
| **兼容** | 不 churn 既有默认包 `plan_id` / mastery 语义。 |
| **量化阈值** | 精确重复 approved = 0；Gate 计数不可用切块膨胀解释。 |
| **证据** | 本文件 + `markdown_pack.py` / `normalized_document.py`；实施后拟 chunk policy 报告。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.3 `M11-PUBLICATION`

**拟定 `value`**：

```text
CANDIDATE_THEN_APPROVED_THEN_GENERATION_GATE__READER_REVALIDATES__ATOMIC_POINTER__NO_HALF_PUBLISHED__NO_GATE_WITHOUT_APPROVAL
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 发布链固定为 candidate → approved → generation publication。generation id 由 manifest 摘要派生；`visible()` 读取方复验；半写目录不可见；指针用 temp + fsync + `os.replace`。 |
| **复用** | 复用 M10 `GenerationGate` 与 M7 CURRENT/PREVIOUS / last-good，不另造发布身份。 |
| **rollback** | 失败回退到 last-good generation；candidate 不得被检索面看见。 |
| **receipt** | 每次发布留下 digest、计数、来源集合；不含正文。 |
| **默认与覆盖** | 无独立完成/Gate 批准，不得把 candidate 算进 3K/10K。 |
| **校验与失败** | 半发布可见 = 0；指针与 manifest 不一致则不可见。 |
| **隐私** | receipt / 指针不含路径与凭据。 |
| **兼容** | 不把 Network candidate 发布进默认索引。 |
| **量化阈值** | 半发布 generation = 0；未批准 candidate 进入 published view = 0。 |
| **证据** | 本文件 + `generation_publication.py` / M7 snapshot 发布；实施后拟 publication receipt。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.4 `M11-INCREMENTAL-SYNC`

**拟定 `value`**：

```text
FINGERPRINT_INCREMENTAL_UPSERT_DELETE_IS_THE_DEFAULT__REPLACE_ALL_FORBIDDEN_AS_ROUTINE__RETRY_IDEMPOTENT__DELETE_PROPAGATES
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 常规同步是 fingerprint 驱动的 INCREMENTAL upsert/delete。全库 `replace_all()` **禁止作为常规路径**（仅允许在获批的灾难恢复/schema 迁移中显式一次性使用）。 |
| **幂等** | 失败重试必须使用稳定幂等键；重复应用不新增 chunk、不重复发布 generation。 |
| **传播** | 删除、许可撤销、revision 替换必须传播到 BM25、vector、cache、provenance、plan grounding；删除后零召回。 |
| **默认与覆盖** | 默认 INCREMENTAL。覆盖不能把 FULL replace 重新变成日常。 |
| **校验与失败** | 常规路径出现 `replace_all` = 失败；删除后仍召回 = 失败。 |
| **隐私** | sync 日志只留 digest 与计数。 |
| **兼容** | 学习状态库不被 sync 触碰。 |
| **量化阈值** | 常规 sync 的 `replace_all` 次数 = 0；删除后召回 = 0；重试不产生重复 approved 身份。 |
| **证据** | 本文件 + `user_source_sync.py` / M7 INCREMENTAL；实施后拟 sync 报告。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 3.5 本批**不做**什么

- 不把剩余两项评测 Decision 标 `RESOLVED`。
- 不提高 chunk 限额、不下载语料、不创建 `tests/M11/`。
- 不批准 M11 准入或开工。

## 4. 批次 ② 批准记录

| 批次 | Decision | 裁定 | 批准人 | 批准时间 | 批准引用 |
| --- | --- | --- | --- | --- | --- |
| ② | `M11-PARSER-QUALITY` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下 |
| ② | `M11-CHUNK-POLICY` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下 |
| ② | `M11-PUBLICATION` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下 |
| ② | `M11-INCREMENTAL-SYNC` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下 |

### 批次 ② 批准依据

| 批准字段 | 值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-23 |
| approval_reference | User instruction: 「继续」——回应「请把批次 ② 视为已批准并继续；若有异议再说。接下来我会把这四项标 `RESOLVED`，并写批次 ③」。未提出修改，故 §3.1–§3.4 逐字生效 |

**本批批准不做什么**：不批准准入/开工；不下载；不提额；评测两项仍 `OPEN`。

## 5. 批次 ③：质量与检索评测

### 5.1 `M11-QUALITY-EVALUATION`

**拟定 `value`**：

```text
REAL_CORPUS_ONLY__LICENSE_URL_DIGEST_COMPLETE__NO_SILENT_PARSE_DROP__NO_EXACT_DUPES__NO_PRIVATE_CORPUS__DOMAIN_QUOTAS_PRE_FROZEN
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 3K/10K 门禁度量真实 approved 语料质量，不用 synthetic/半合成容量冒充。每个 Gate 执行前冻结并写入报告：许可/canonical URL 或项目原创/digest/revision 完整率、静默丢解析、精确重复、私人语料、领域配额、人工抽样事实准确率。 |
| **计入规则** | 只有 `license_status=approved` 且（canonical URL 或 `project_authored=true`）的 document 及其 chunk 可计入。Network candidate、未审 dump、parser 失败产物不计。 |
| **人工抽样** | 每个 Gate 至少按领域分层抽样；事实错误超过预冻结阈值则 Gate 失败，不得靠扩量稀释。 |
| **默认与覆盖** | 默认 fail closed。覆盖只能更严。 |
| **校验与失败** | 完整率 < 100%、静默丢失 > 0、精确重复 > 0、私人语料 > 0 → Gate 失败。 |
| **隐私** | 质量报告只留计数、digest、官方 URL，不含正文。 |
| **兼容** | 不把质量 PASS 解释为 M8 容量 PASS。 |
| **量化阈值** | 许可/URL/digest 完整 = 100%；静默丢解析 = 0；精确重复 = 0；私人语料 = 0。事实准确率阈值在每个 Gate 开跑前写入报告，本决策冻结**必须有阈值**，不在本批发明未核验的百分数。 |
| **证据** | 本文件；实施后拟 `tests/M11/` 质量报告护栏。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 5.2 `M11-RETRIEVAL-EVALUATION`

**拟定 `value`**：

```text
DEFAULT_90_QUESTION_BASELINE_PROTECTED__3K_10K_USE_SEPARATE_REAL_QUERY_GOLD__SYNTHETIC_100K_NOT_QUALITY_PASS__PLANNER_INPUT_STAYS_BOUNDED
```

| 必备项 | 内容 |
| --- | --- |
| **政策** | 默认 OS/DS/CO 90 题是**保护基线**，M11 扩展不得使其 Recall@3 低于当前冻结复测（OS 1.000 / DS 0.929 / CO 1.000，加权 0.978）。3K/10K 另冻结真实 query/gold，报告 Recall@3、Recall@5、MRR、no-hit、hard-negative、删除后零召回。 |
| **证据分离** | 100K synthetic 只能复用工程资源门槛（延迟/RSS/磁盘），**不得**当作真实质量或检索 PASS。 |
| **Planner** | 10K 下 Planner 仍只消费有界目录/摘要，不得把全书或 10K chunks 塞进上下文（继承 `M9-EXTERNAL-AI` 最小披露）。 |
| **默认与覆盖** | Network 30 题仍为显式扩展集，不自动并入默认 90 题。 |
| **校验与失败** | 默认 90 题退化、删除后仍召回、Gate 报告缺计量 → 失败。 |
| **隐私** | 评测报告不含 query 原文中的私人数据、路径、凭据。 |
| **兼容** | 不改默认评测发现规则。 |
| **量化阈值** | 默认 90 题 Recall@3 不低于 2026-08-31 冻结值；删除 Source 后召回 = 0。3K/10K 的 Recall 绝对值在每个 Gate 开跑前冻结，本决策冻结**必须有独立 query/gold**，不把 90 题冒充 10K 质量。 |
| **证据** | 本文件 + `docs/baselines.md` + `tests/regression/test_rag_quality.py`；实施后拟 M11 retrieval 报告。 |
| **责任人 / 日期** | justtodo123 / 待本批批准 |

### 5.3 本批**不做**什么

- 不发明未核验的 3K/10K Recall 绝对分数（那要等真实 query/gold 冻结）。
- 不下载语料、不提额、不创建 `tests/M11/`。
- 不批准 M11 准入或开工。

## 6. 批次 ③ 批准记录

| 批次 | Decision | 裁定 | 批准人 | 批准时间 | 批准引用 |
| --- | --- | --- | --- | --- | --- |
| ③ | `M11-QUALITY-EVALUATION` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下 |
| ③ | `M11-RETRIEVAL-EVALUATION` | `RESOLVED` | justtodo123 | 2026-09-23 | 见下 |

### 批次 ③ 批准依据

| 批准字段 | 值 |
| --- | --- |
| approved_by | justtodo123 |
| approved_at | 2026-09-23 |
| approval_reference | User instruction: 「允许」——回应「请把批次 ③ 视为已批准并继续。批准后十项 Decision 全部 `RESOLVED`，下一步才是写 Baseline/3K 冻结物和测试方案」。未提出修改，故 §5.1–§5.2 逐字生效 |

**至此十项强制 Decision 全部 `RESOLVED`。** 这仍**不构成** M11 准入：检查表还差 Baseline/3K 冻结物、数据目录/隐私边界可验证物、以及独立 admission + 开工批准。

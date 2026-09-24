# M11 测试方案 v1（历史准入准备物）

> 当前地位：本文件形成于准入前，保留当时的非授权时态作为审计记录；M11 计划 §8.1/§8.2 与登记表后续已批准
> `ADMITTED / IN_PROGRESS`、开工以及 v1.1 A1/A2/A3。正文中的“现在不创建/不提额/不下载”只描述形成时点，
> 不覆盖后续授权。真实外部下载和正式发布仍需单次确认。
>
> 状态：**准入准备物**。本文件回答「**怎么测**」。权威决策见 [`m11-decision-closure-v1.md`](m11-decision-closure-v1.md)；
> 冻结值见 [`m11-baseline-3k-freeze-v1.md`](m11-baseline-3k-freeze-v1.md)。
>
> **不**批准 M11 准入或开工，**不**创建 `tests/M11/`，**不**写任何生产物件，**不**下载语料，**不**提额。

## 0. 本文覆盖什么、不覆盖什么

| 决策 | 本文给出的可执行方案 |
| --- | --- |
| `M11-SCALE-GATES` | §2 计量护栏：document / chunk / source 三计数；synthetic 不计 |
| `M11-SOURCE-ALLOWLIST` | §3 白名单与领域配额 |
| `M11-LICENSE-PROVENANCE` | §4 provenance 完整率 |
| `M11-PARSER-QUALITY` | §5 parser fail-closed 与超时 |
| `M11-CHUNK-POLICY` | §6 身份、去重、禁止 overlap 膨胀 |
| `M11-PUBLICATION` | §7 半发布不可见、指针原子性 |
| `M11-INCREMENTAL-SYNC` | §8 fingerprint upsert/delete、禁止常规 `replace_all` |
| `M11-QUALITY-EVALUATION` | §9 质量报告形状与人工抽样接缝 |
| `M11-RETRIEVAL-EVALUATION` | §10 默认 90 题保护 + 独立 query/gold 形状 |
| `M11-PRIVACY-RETENTION` | §11 路径 / 凭据 / 私人语料扫描 |

**不覆盖**：真实 3K 语料下载与评测执行（那是准入后的实施）；M8 100K synthetic capacity；M12 云端。

## 1. 测试树、marker 与前置约束

- 新增 `tests/M11/`，`pytestmark = pytest.mark.m11`；**不修改**任何存量阶段测试。
- 测试树**现在不创建**：本文件是方案，不是测试。M11 获准入后按 M11 计划 §7 顺序落地。
- 所有用例使用 `tmp_path` 下的独立数据树与 SQLite；**绝不触碰** `platform/.cache/learning_state.sqlite3`。
- 默认离线：不联网。需要真实下载的用例必须 `online` + skip 门控且**非门禁**，且仍须独立下载授权——本方案本身不授予。
- 每条断言必须能**失败**：实施时逐条做变异（关掉被断言的行为），记录「恰好 N 项判红」。
- 非空性：任何「全部 X 都满足 Y」的断言都要先断言扫描集合**非空**。

## 2. 计量护栏（`M11-SCALE-GATES`）

| 用例 | 断言 |
| --- | --- |
| Gate 报告缺 document 数 | fail closed |
| Gate 报告缺 chunk 数 | fail closed |
| Gate 报告缺 source 数 | fail closed |
| 把 synthetic fixture 计入 3K | 计数拒绝；Gate 失败 |
| 用 overlap / 重复切块把 2,000 真实块报成 3,000 | 精确重复 > 0 ⇒ Gate 失败 |
| v1.1 硬上限 | `max_chunks_total` 默认仍为 1200，hard max 4000；2000/3000/4000 通过，4001 拒绝；per-source 和额外来源数量不变 |
| 隐私 | 报告序列化后不含宿主绝对路径、凭据、正文片段 |

Baseline 用例：默认包 identity 稳定（document_id 可复算）、90 题不退化。不把 682 写成可变常量——从默认包实际切块计数读取并断言与冻结参考一致。

## 3. 白名单与配额（`M11-SOURCE-ALLOWLIST`）

| 用例 | 断言 |
| --- | --- |
| 不在冻结白名单的 `source_id` 进入 candidate pipeline | 拒绝该 Source，不部分发布 |
| Network 31 篇出现在 approved 计数 | Gate 失败 |
| Stack Exchange dump 在 3K | 拒绝 |
| 单一来源超过预冻结占比 | Gate 失败 |
| 权威规范层（RFC+IANA）合计 > 25% | Gate 失败 |
| 覆盖把白名单放宽 | 源码 / 冻结物比对失败（覆盖只能收紧） |

白名单集合**动态枚举**冻结物表格，并断言扫描集合非空——不写死一份可被绕过的短名单。

## 4. Provenance（`M11-LICENSE-PROVENANCE`）

| 用例 | 断言 |
| --- | --- |
| `license_status=unresolved` 进入 approved | 拒绝 |
| 无 canonical URL 且 `project_authored` 不为 true | 拒绝 |
| chunk 无法追溯到 document / revision / chunk schema | 该文档不得发布 |
| 撤销许可后仍被检索 | 零召回失败 |
| mapping 表把 Network 标成可发布 | 运行时仍保持 candidate（映射表不自动晋升） |

## 5. Parser fail-closed（`M11-PARSER-QUALITY`）

| 用例 | 断言 |
| --- | --- |
| 解析失败 / 乱码 / 空文档 | 不得进入 approved；进入 `rejected/` 只留原因与身份 |
| 静默丢文件 | 丢失计数 = 0 |
| 超时 | 稳定码 `SOURCE_PARSE_TIMEOUT`；`timeout_seconds` 不得超过 30 |
| TXT 在 3.13.3 | 仍为 `PARSER_UNAVAILABLE`；M11 测试**不得**把它改写成 PASS |
| 新增未冻结 parser | Decision 未改则拒绝 |

沿用 `tests/M7/` 的五格式合同，不复制其用例；M11 只断言「失败产物不进 approved」。

## 6. Chunk 身份与去重（`M11-CHUNK-POLICY`）

| 用例 | 断言 |
| --- | --- |
| `chunk_id` 与 `sha256(document_id + chunk_key + chunk_schema)` 不符 | fail closed |
| 伪造 logical URI / document_id | 拒绝 |
| 精确重复 content digest | 不得进入 approved |
| overlap 膨胀使计数上升但 digest 集合不变 | Gate 计数失败 |
| schema 未知 | 该文档不得发布 |

用户源走 M7 normalized units，不另造第四套 chunk 身份——源码级断言枚举 `chunk_schema` 取值集合。

## 7. Publication（`M11-PUBLICATION`）

复用 M10 `GenerationGate` 与 M7 CURRENT/PREVIOUS，不另造发布身份。

| 用例 | 断言 |
| --- | --- |
| 半写目录 | `visible()` 不可见 |
| 指针指向 manifest 不符的 generation | 不可见（读取方复验） |
| 指针切换 | temp + fsync + `os.replace` |
| candidate 被检索面看见 | 0 |
| 无 Gate 批准把 candidate 算进 3K | 计数失败 |
| 失败回退 | last-good 仍可见；新 generation 不可见 |

crash 点沿用 M10 测试方案已覆盖的发布矩阵；M11 只加「未批准 candidate 不计 Gate」一条。

## 8. Incremental sync（`M11-INCREMENTAL-SYNC`）

| 用例 | 断言 |
| --- | --- |
| 常规路径调用 `replace_all` | 失败 |
| 同键重试 | 不新增 chunk、不重复发布 generation |
| 删除 / 许可撤销 / revision 替换 | BM25 / vector / cache / provenance / plan grounding 零召回 |
| 学习状态库 | sync 不触碰；整库逐字节不变 |

## 9. 质量报告（`M11-QUALITY-EVALUATION`）

| 用例 | 断言 |
| --- | --- |
| 完整率 < 100% | Gate 失败 |
| 静默丢失 > 0 | Gate 失败 |
| 精确重复 > 0 | Gate 失败 |
| 私人语料 > 0 | Gate 失败 |
| Gate 报告缺「本 Gate 事实准确率阈值」字段 | 失败（钉住**必须有阈值**，不在方案里发明百分数） |
| 质量 PASS 被写成 M8 容量 PASS | 源码 / 报告扫描禁止该表述 |

人工抽样：每个 Gate 按领域分层；实施时物化抽样清单。本方案不规定抽多少篇——那写入该 Gate 开跑前的报告。

## 10. 检索评测（`M11-RETRIEVAL-EVALUATION`）

| 用例 | 断言 |
| --- | --- |
| 默认 90 题 Recall@3 低于 2026-08-31 冻结值 | 失败 |
| Network 30 题被自动并入默认发现 | 失败（发现规则不变） |
| 3K/10K 报告用 90 题冒充独立 query/gold | 失败 |
| 删除 Source 后召回 | 0 |
| 100K synthetic 出现在质量 PASS 字段 | 失败 |
| Planner 输入超过有界目录 / 摘要 | 失败（继承 `M9-EXTERNAL-AI` 最小披露） |

3K query/gold 的**类别**见冻结物 §5.2；实施时物化并钉死摘要，改任务集必须显式更新摘要否则判红。

## 11. 隐私（`M11-PRIVACY-RETENTION`）

| 用例 | 断言 |
| --- | --- |
| `data/README.md` 存在且声明 Git 边界 | 通过 |
| `.gitignore` 含 `data/raw/` 等七层 | 通过；名单非空 |
| Git 跟踪的 `data/` 下出现 raw / pdf / zip | 失败 |
| 报告 / manifest / 日志出现宿主绝对路径或凭据 | fail closed |
| 私人 session / review / plan / ledger 进入 approved | 0 |

路径扫描沿用 `tests/regression/test_path_privacy.py` 的形态：**描述**路径，不粘贴宿主绝对路径。治理文档若需提及外部资料根，只写「仓库外只读资料根」。

## 12. 非空转与变异要求

- 每条新用例都要能失败。
- 「无法用判红表达」的结果必须写明（例如完全移除 parser 墙钟上界会让测试挂起而不是判红——沿用 M7 记录）。
- 源码级守卫必须**动态枚举**并断言扫描集合非空。

## 13. 本方案**不**做什么

- 不创建 `tests/M11/`、不写任何生产代码或 schema。
- 不批准 M11 准入或开工；不改变任何 `RESOLVED` 决策值。
- 不下载语料、不提额、不发明 3K Recall 绝对分数。
- 不产生任何容量或性能声明。

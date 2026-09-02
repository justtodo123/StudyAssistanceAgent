# M7 P0 语料治理报告（2026-08-31）

> 状态：`INCOMPLETE / STOP FOR HUMAN REVIEW`
> 范围：既有 `knowledge/network/` 与 `knowledge/interview/` 正文的文档级治理；不包含 M7 runtime 实现，
> 也不因 M7 基础设施已准入而自动闭合。
> 映射：[`document-mapping.json`](../reference/document-mapping.json)
> SHA-256：`d1bb072da917154a95705c7386b432aeba16af46c08a4fb76cd7d5c419a96fbe`

## 1. 结论

已为 82 篇正文建立一对一 document mapping，并把稳定 `source_id`、`logical_uri`、`document_id`、来源、格式、审核、
入库、注册方式和许可证状态写入逐文档 frontmatter。治理测试证明 mapping 数量、身份和 frontmatter 一致，且 candidate
不会进入现行索引。

P0 **尚未完成**。31 篇 Network 文档只有课程级“网络爬取 + LLM 精炼”记录，没有逐篇可核验原始 URL 或足以声明
项目原创的证据，也没有许可证批准证据。它们全部保持 fail-closed candidate。不得把此状态写成已满足“URL 或项目原创”
门禁，也不得以补写虚构 URL、目录继承或 `study_document` 分类绕过。

51 篇 Interview 文档在仓库提交 `821fdf4` 中作为仓库内容创建，文件自身没有宣称外部来源。P0 据此显式声明为
`project_authored_ai_assisted`，以 repository contributor 署名并按仓库 MIT 许可证登记为 approved。该判断仍应由项目
负责人复核；mapping 没有把 git 历史表述成比现有证据更强的外部作者证明。

## 2. 逐组状态

| 语料组 | 文档数 | provenance | review | ingest | license | 发布结论 |
| --- | ---: | --- | --- | --- | --- | --- |
| Network | 31 | `web_derived_ai_assisted` | `review` | `candidate` | `unresolved` | 不可发布、不可索引 |
| Interview | 51 | `project_authored_ai_assisted` | `approved` | `approved` | `approved` / `MIT` | P0 登记为可发布，待负责人复核声明 |

31 篇未解决 Network 条目：

- `application-layer.md`、`architecture.md`、`arp-icmp.md`、`channel-capacity.md`、`csma-cd.md`；
- `data-link-layer.md`、`dns.md`、`encoding.md`、`encryption.md`、`error-control.md`、`ethernet.md`；
- `exam-review.md`、`firewall-vpn.md`、`flow-control.md`、`ftp-smtp.md`、`http.md`、`ip-protocol.md`；
- `nat.md`、`network-layer.md`、`overview.md`、`performance.md`、`physical-layer.md`、`routing.md`；
- `security-overview.md`、`socket.md`、`subnetting.md`、`tcp-congestion.md`、`tcp-connection.md`；
- `tcp-reliable.md`、`transport-layer.md`、`udp.md`。

每篇的稳定 identity、完整仓库相对路径和相同拒绝原因见 mapping；报告不保存宿主绝对路径或正文。

## 3. 治理契约

- `canonical_url` 与经过核验的 `project_authored: true` 必须二选一；二者皆无时保持 candidate。
- `source_type`、`format`、`review_status`、`ingest_status`、`registration_method`、`license_status` 分别记录，不能互相推导。
- 只有 `review_status=approved`、`ingest_status=approved`、`license_status=approved`，并有 URL 或项目原创声明的记录才可发布。
- `tools/source_inventory.py` 的 `study_document` 是候选发现分类，不是 Source 类型、审核结果、入库许可或许可证决定。
- 本 mapping 是 P0 治理登记，不是未来 `sa.source.provenance.v1` 的 `ProvenanceRecord`；M7 基础设施准入也不改变
  mapping 的逐文档治理结论。

## 4. 验证证据

| 检查 | 结果 |
| --- | --- |
| 文档治理契约 | 8 passed |
| M3c + M3d + M4 + 文档/治理聚焦套件 | 51 passed |
| regression 非 slow | 57 passed、3 deselected |
| `platform/tests/` | 40 passed |
| `git diff --check` | passed |
| 根级 `tests/` 完整套件 | 554 collected；553 passed；1 skipped（显式 online crawler smoke） |
| 根级 + 受保护平台合并口径 | 594 collected；593 passed；1 skipped |
| 默认 OS/DS/CO 90 题 BM25 | Recall@1/3/5 `0.672 / 0.978 / 0.989`；命令成功 |
| 显式 Network 30 题评测 | Recall@1/3/5 均为 `0.000`，符合 31 篇 candidate 不进入索引的 fail-closed 结果 |

默认检索与评测继续使用历史可信 `knowledge-pack` 政策：缺失 `source_type` / `ingest_status` 的既有 OS/DS/CO
笔记保留兼容默认值，但非法显式值会被拒绝，显式 `candidate` 也不会被提升。Network 已逐篇显式声明
`ingest_status=candidate`，因此不会进入默认索引。Network 评测必须通过
`--test-set tools/evaluations/network.json` 显式运行；`--course network` 不是受支持参数，且默认评测仍只包含
OS/DS/CO。受保护平台功能套件 40 项全通过，未发现 quiz、检索、复习计划、调度或 study-assistant 功能回归。

## 5. 停止条件与人工待办

M7 权威登记现为：

- `admission_status: ADMITTED`；
- `delivery_status: IN_PROGRESS`；
- 批准 scope 仅包含基础设施，并明确排除 Network 文档晋升与 P0 语料治理闭环；
- `implementation_start: AUTHORIZED`；M7 已形成并冻结 Source Registry、manifest/parser、normalized document、source-local FULL/INCREMENTAL sync 与 delete/isolation 局部合同，但不影响本报告的 P0 停止状态。

该批准不关闭本报告的 `INCOMPLETE / STOP FOR HUMAN REVIEW`，不批准任何 Network 文档，也不改变以下人工停止条件：

1. 为 31 篇 Network 逐篇找到可核验原始 URL、publisher 和许可证证据；若确有独立原创证据，则逐篇改作项目原创，
   不能按目录批量推断。
2. 复核 51 篇 Interview 的 repository-authored / AI-assisted / MIT 声明是否符合项目负责人对历史内容的认定。
3. 完成 Network 来源与许可审核后，重新生成 mapping digest 并重跑治理、检索、回归和默认 90 题门禁。
4. P0 闭合后另行决定 Network 文档是否逐篇晋升；M7 基础设施批准不能替代该决定。当前 M7 局部合同不修改
   `SourceChunk`、`RetrievalChunk`、API、正式检索、同步、删除或 benchmark 生产路径；后续增量仍需按授权范围实施。

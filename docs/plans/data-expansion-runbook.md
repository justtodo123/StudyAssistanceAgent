# 数据扩展运行手册

> 状态：DRAFT / FUTURE REFERENCE / NON-AUTHORITATIVE
> 仅保留为 M7 候选数据扩展运行手册；不构成 M7 准入、生产实施授权、验收通过或负责人批准。
> 当前 M7 基础设施范围为 `ADMITTED / IN_PROGRESS`，`implementation_start=AUTHORIZED`，但本手册仍未获数据扩展执行授权；十二项强制决策与
> `M7-PROTECTED-BASELINE` 的登记不因本文产生语料批准，Network 语料也不在批准范围内；
> 最终状态以 [`docs/PLAN.md`](../PLAN.md) 和阶段准入门禁为准。
> 进入任何数据扩展阶段前仍须取得明确范围授权并完成文末 Gate 0。Gate 0 只核验单个 Source 的合规与发布条件，
> 不能替代 M7 阶段准入或人工批准。
> 适用项目：StudyAssistanceAgent
> 候选目标规模：首批 3,000 chunks，第二阶段 10,000 chunks
> 最后核验日期：2026-08-27

## 1. 目的与边界

本文用于在项目进入数据扩展阶段后直接启动工作，统一规定：

- 首批允许接入的数据源；
- 下载入口、下载方式和版本固定方法；
- 原始文件、转换文件、审核文件和生产知识包的目录；
- Source / Document / Chunk 身份与 manifest；
- 清洗、转换、去重、切块、审核和发布流程；
- 许可证、署名、删除、同步和验收要求；
- 3k/10k 数据扩展顺序与停止条件。

本文不授权绕过网站条款、登录、验证码、付费墙、robots 策略或访问频率限制。即使来源出现在白名单中，每次首次下载或许可证发生变化时仍须执行 Gate 0。

### 1.1 “可直接使用”的定义

本文中的“可直接使用”表示：

1. 来源为官方组织、原作者或官方项目仓库；
2. 存在可核验的许可或使用条款；
3. 项目能保存作者、来源 URL、许可证、版本和抓取时间；
4. 数据先进入候选区，经自动校验和人工审核后才能发布；
5. 不代表可以省略署名、相同方式共享、非商业限制或第三方材料检查。

### 1.2 当前系统事实

当前生产知识链路的规范输入仍是 Markdown。PDF、PPTX、DOCX、视频和扫描图片尚没有稳定 parser，不应在首批扩展中直接进入生产索引。

当前约有 682 个 chunks；现行默认 Source 上限为 750，能够容纳当前默认包，但总上限 1200 无法容纳首批 3k 或后续 10k 数据。扩展前必须重新设计并 benchmark 容量门禁；仅更换向量数据库不能自动获得 3k/10k 数据能力。

---

## 2. 数据分层与目录

不得把下载文件直接写入 `knowledge/`。建议在仓库外或 Git 忽略的数据目录建立以下结构：

```text
data/
├── manifests/                 # Source manifest；可提交 Git
│   ├── sources/
│   └── licenses/
├── raw/                       # 原始下载；只读、不可人工修改
│   └── <source_id>/<revision>/
├── normalized/                # 统一编码和结构后的文档
│   └── <source_id>/<revision>/
├── candidates/                # 待审核 Markdown
│   └── <source_id>/<revision>/
├── approved/                  # 审核通过的数据
│   └── <source_id>/<revision>/
├── rejected/                  # 拒绝记录，只保存原因和身份，不复制违规正文
├── reports/                   # 质量、许可、去重、benchmark 报告
└── snapshots/                 # 发布快照清单，不重复保存原始文件
```

生产发布路径：

```text
approved snapshot
  → Source adapter
  → SourceSnapshot
  → RetrievalIndex
  → BM25 + VectorStore
```

目录规则：

- `raw/` 下载完成后只读；
- 原始文件不得在转换时被覆盖；
- 所有转换产物都能由 raw + manifest 重新生成；
- 二进制大文件、数据 dump、数据库文件不得提交 Git；
- Git 中只保存 manifest、转换脚本、审核结果和小型 fixture；
- 每次发布生成不可变 snapshot manifest。

---

## 3. 首批白名单

### 3.1 概览

| ID | 来源 | 领域 | 首批动作 | 生产正文许可策略 | 推荐优先级 |
|---|---|---|---|---|---|
| `mit-ocw-6-004-2017` | MIT OCW 6.004 | 计算机组成 | 下载课程包或许可范围内页面 | CC BY-NC-SA，逐文件排除第三方材料 | P0 |
| `opendsa-main` | OpenDSA 官方仓库 | 数据结构与算法 | Git clone 固定 commit | 以仓库 LICENSE/内容声明为准，代码与内容分开记录 | P0 |
| `rfc-editor-index` | RFC Editor | 计算机网络 | 下载 RFC index/XML，按批准清单取 HTML/TXT | 遵守 IETF Trust Legal Provisions；保留法律声明 | P0 |
| `iana-registries` | IANA Registries | 网络结构化事实 | 按注册表 CSV/XML 下载 | 每个 registry 保存条款、URL、更新时间 | P0 |
| `linux-kernel-docs` | Linux Kernel Documentation | 操作系统工程实现 | Git sparse checkout `Documentation/` | 按内核 LICENSE/SPDX；保留版本和路径 | P1 |
| `mit-ocw-6-006` | MIT OCW 6.006 | 算法 | 课程级下载，排除第三方材料 | CC BY-NC-SA，逐文件复核 | P1 |
| `stackexchange-curated` | Stack Exchange 官方 dump | 工程问答和误区 | 第二阶段只抽取审核子集 | 按内容日期记录 CC BY-SA 版本、作者和链接 | P2 |
| `project-authored-evals` | 项目原创评测集 | 全领域 | 团队原创、双人审核 | 项目自有许可 | P0 |

> 首批 3k 不使用 Stack Exchange 全量 dump。它只在课程数据稳定、署名生成器和删除流程完成后进入第二阶段。

---

## 4. Source 运行卡

## 4.1 MIT OpenCourseWare 6.004

### 官方入口

- 课程：https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/
- 使用条款：https://ocw.mit.edu/pages/privacy-and-terms-of-use/

### 用途

- 数字逻辑；
- 组合和时序电路；
- CPU、ISA、存储层次；
- 计算机系统结构。

### 下载方式

优先使用课程页面提供的官方 Download Course 按钮或官方课程包。不要自行递归抓取整个 `ocw.mit.edu`。

若官方页面提供 ZIP 下载链接：

```bash
mkdir -p "data/raw/mit-ocw-6-004-2017/<revision>"
curl -L --fail --retry 3 \
  -o "data/raw/mit-ocw-6-004-2017/<revision>/course.zip" \
  "<从课程页人工确认的官方 ZIP URL>"
sha256sum "data/raw/mit-ocw-6-004-2017/<revision>/course.zip" \
  > "data/raw/mit-ocw-6-004-2017/<revision>/SHA256SUMS"
```

不要在脚本中永久写死未核验的临时下载 URL。manifest 保存课程落地页，下载任务在执行当天解析或人工填入官方 URL。

### 许可和排除

- 默认按 MIT OCW 页面声明的 CC BY-NC-SA 使用；
- 必须保留 MIT、课程名、教师、课程 URL 和许可链接；
- 排除标注为 third-party、all rights reserved 或另有许可的文件；
- 排除学生姓名、提交物和非课程授权内容；
- 非商业和 ShareAlike 限制必须进入发布报告；
- 若项目未来商业化，该 Source 必须单独下线或重新获权。

### 转换

```text
HTML/PDF/讲义
  → 资产清单
  → 许可过滤
  → HTML 主体提取；PDF 暂不自动入生产
  → 标题层级恢复
  → Markdown candidate
  → 人工审核
```

首批只接入 HTML 和可稳定提取的文本讲义。PDF 可保存 raw，但在 PDF parser 正式通过 Gate 前不得发布。

---

## 4.2 OpenDSA

### 官方入口

- 官网：https://opendsa-server.cs.vt.edu/
- 仓库：https://github.com/OpenDSA/OpenDSA

### 用途

- 数组、链表、栈、队列；
- 树、图、排序、查找；
- 算法分析；
- 数据结构练习和概念解释。

### 下载方式

推荐 Git 固定 commit：

```bash
git clone --filter=blob:none --no-checkout \
  https://github.com/OpenDSA/OpenDSA.git \
  "data/raw/opendsa-main/repository"

cd "data/raw/opendsa-main/repository"
git checkout <approved_commit_sha>
git rev-parse HEAD > ../REVISION
```

首次勘察后再配置 sparse checkout，只取教材源文件、必要元数据和许可证，不下载构建产物：

```bash
git sparse-checkout init --cone
git sparse-checkout set <approved-content-directories> LICENSE README.md
```

具体内容目录不得凭猜测填写；首次执行人必须检查当前仓库结构和 LICENSE。

### 许可和排除

- 代码许可证不自动覆盖教材文字、图片、题目和第三方资源；
- manifest 分别记录 `code_license`、`content_license`、`asset_license`；
- 没有明确内容许可的文件不得进入 approved；
- 排除构建依赖、生成页面、第三方图片和测试噪声；
- 每次同步保存 commit SHA，不使用浮动 `main` 作为 revision。

### 转换

优先解析仓库中的结构化教材源文件，而非抓取渲染网页：

```text
结构化源文件
  → 章节/小节 AST
  → 删除导航和构建指令
  → 保留代码块、公式和练习类型
  → Markdown candidate
```

互动组件不能直接变成正文。应转换为描述性占位符，例如：

```markdown
> 交互资源：二叉搜索树插入可视化。原始组件：<logical_uri>
```

---

## 4.3 RFC Editor

### 官方入口

- RFC Editor：https://www.rfc-editor.org/
- 批量检索入口：https://www.rfc-editor.org/retrieve/bulk/
- IETF Trust Legal Provisions：https://trustee.ietf.org/documents/trust-legal-provisions/
- RFC Editor 批量页面中的 Copyright notice：执行当天随页面再次核验

### 用途

- TCP/IP、UDP、DNS、HTTP、TLS、QUIC；
- 协议规范、状态和更新关系；
- 网络事实核验。

### 下载方式

先下载 RFC 索引，再由批准列表选择 RFC，不做全量正文摄取：

```bash
mkdir -p "data/raw/rfc-editor-index/<revision>"
curl -L --fail --retry 3 \
  -o "data/raw/rfc-editor-index/<revision>/rfc-index.xml" \
  "https://www.rfc-editor.org/rfc-index.xml"
sha256sum "data/raw/rfc-editor-index/<revision>/rfc-index.xml" \
  > "data/raw/rfc-editor-index/<revision>/SHA256SUMS"
```

批准列表建议保存为：

```yaml
rfcs:
  - number: 8200
    topic: ipv6
  - number: 9293
    topic: tcp
  - number: 9110
    topic: http-semantics
```

按清单下载 HTML/TXT：

```bash
curl -L --fail --retry 3 \
  -o "data/raw/rfc-editor-index/<revision>/rfc9293.html" \
  "https://www.rfc-editor.org/rfc/rfc9293.html"
```

### 许可和排除

- RFC 文本不是“无条件公共领域”；
- 保存 RFC 编号、作者、发布日期、类别、状态和法律声明；
- 不删除或改写版权声明；
- 提取代码组件前单独核验 Code Components 条款；
- 被废止 RFC 不删除，但标记 `obsoleted`，普通检索默认降权；
- 回答标准事实时优先最新有效 RFC，同时保留更新链。

### 转换

RFC 必须解析：

- RFC number；
- title；
- authors；
- publication date；
- status/category；
- updates/obsoletes/updated-by/obsoleted-by；
- section number 和 section title；
- normative language（MUST、SHOULD、MAY）不得意译丢失。

推荐 `chunk_key`：

```text
section:<section-number>
```

RFC 作为“标准证据层”，普通教学查询默认权重低于人工教学文档；规范性问题再提高权重。

---

## 4.4 IANA Protocol Registries

### 官方入口

- 协议注册表总入口：https://www.iana.org/protocols

首批建议注册表：

- Service Name and Transport Protocol Port Number Registry；
- Protocol Numbers；
- Media Types；
- TLS Parameters；
- DNS Parameters。

### 下载方式

每个 registry 必须从其官方页面人工确认 CSV/XML 下载 URL。示例模板：

```bash
mkdir -p "data/raw/iana-registries/<revision>/<registry_id>"
curl -L --fail --retry 3 \
  -o "data/raw/iana-registries/<revision>/<registry_id>/registry.csv" \
  "<官方 registry 页面给出的 CSV URL>"
sha256sum "data/raw/iana-registries/<revision>/<registry_id>/registry.csv" \
  > "data/raw/iana-registries/<revision>/<registry_id>/SHA256SUMS"
```

### 数据角色

IANA 不是教材正文，应标记：

```yaml
data_role: reference_registry
```

保留结构化行，不先拼成大段 Markdown。检索层可生成短事实 chunk：

```text
HTTPS 的服务名为 https，传输协议 TCP，注册端口 443；来源为 IANA registry。
```

### 校验

- CSV/XML schema 变更检测；
- 主键重复检测；
- 更新时间和 Last-Modified；
- 空值、保留值、未分配值不得丢失；
- 不把“Registered”误写成“强制使用”。

---

## 4.5 Linux Kernel Documentation

### 官方入口

- 当前文档：https://docs.kernel.org/
- Git：https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git

### 用途

- 调度、内存、锁、文件系统；
- Linux 内核接口；
- OS 理论对应的工程实现。

### 下载方式

优先 Git 固定 tag/commit，并只取文档和许可证：

```bash
git clone --filter=blob:none --no-checkout \
  https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git \
  "data/raw/linux-kernel-docs/repository"

cd "data/raw/linux-kernel-docs/repository"
git sparse-checkout init --cone
git sparse-checkout set Documentation LICENSES COPYING

git checkout <approved_tag_or_commit>
git rev-parse HEAD > ../REVISION
```

### 许可和处理

- 保存 tag、commit、文件路径、SPDX 声明；
- 文档和引用代码分别记录许可；
- 不抓取 `docs.kernel.org/latest` 后丢失版本；
- 首批主题只选 `scheduler`、`locking`、`mm`、`filesystems` 的教学相关文档；
- API 自动生成表、构建内部文件和无正文索引页排除；
- 作为“工程证据层”，不要代替入门教学层。

---

## 4.6 项目原创评测集

### 目标

建立不受第三方题库版权限制的检索、问答和学习评测数据。

### 生成原则

- 题目由项目团队原创；
- 题目答案只能基于 approved 文档；
- 每题至少绑定 1 个稳定 `document_id`，推荐绑定 `chunk_id`；
- 每题由第二位审核者确认；
- 不改写 LeetCode、牛客、商业教材或付费题库题面；
- 不让 LLM 生成内容未经审核直接进入 gold set。

### 推荐 schema

```json
{
  "schema_version": "evaluation-case-1",
  "question_id": "os-deadlock-001",
  "course": "os",
  "topics": ["deadlock"],
  "question_type": "short_answer",
  "difficulty": "medium",
  "prompt": "死锁产生的四个必要条件是什么？",
  "expected_concepts": [
    "mutual_exclusion",
    "hold_and_wait",
    "no_preemption",
    "circular_wait"
  ],
  "evidence": [
    {
      "source_id": "knowledge-pack",
      "document_id": "...",
      "chunk_id": "..."
    }
  ],
  "license": "project-authored",
  "review_status": "approved",
  "reviewers": ["reviewer-id"]
}
```

数据拆分按主题分层，避免同一文档的近重复问题同时进入 train/dev/test。

---

## 4.7 Stack Exchange 官方 Data Dump（第二阶段）

### 官方入口

- Dump：https://archive.org/details/stackexchange
- 许可说明：https://stackoverflow.com/help/licensing

### 启用前置条件

以下条件全部满足后才可下载：

1. attribution renderer 已实现；
2. 能按帖子创建时间选择相应 CC BY-SA 版本；
3. 能保存作者、原 URL、帖子 ID、创建和修改时间；
4. 支持删除和重建一个 Source；
5. 内容审核器能排除隐私、日志、密钥和低质量回答；
6. 项目已确认 ShareAlike 对发布产物的影响。

### 处理范围

不要导入整个 Stack Overflow。先选官方 dump 中相关站点和标签，抽取：

- 已接受回答；
- 正评分；
- 主题匹配；
- 非关闭、非删除、非明显过时；
- 无隐私和凭据；
- 由人工审核。

生产入库时必须把问题和回答分成独立 document，保留关系，不把作者署名隐藏在不可见 JSON 中。

---

## 5. 明确禁止直接下载全文的来源

以下来源可以保存元数据和官方链接，也可以由团队写原创摘要，但不得默认批量下载全文进入生产知识库：

| 来源 | 原因 | 允许动作 |
|---|---|---|
| OSTEP | 免费阅读不等同于开放再分发许可 | 保存目录、链接；人工原创摘要；必要短引文 |
| Nand2Tetris 书籍/课程正文 | 工具、书籍和课程材料许可可能不同 | 分项核验；仅使用明确授权部分 |
| ARM/Intel 商业文档 | 使用条款不等同开放教材许可 | 元数据、链接、人工摘要和事实核验 |
| LeetCode/牛客题库 | 题面和付费内容版权风险 | 保存题号、URL、用户自己的错题摘要 |
| CSDN/知乎/博客转载 | 原始来源和许可不稳定 | 仅作线索，回溯到官方原文 |
| 网盘教材/扫描 PDF | 版权、恶意文件和 OCR 风险 | 不接入 |
| 无 LICENSE 的 GitHub 仓库 | 公开可见不等于允许复用 | 不复制正文或数据 |

---

## 6. Source Manifest

每个 Source 必须有 manifest，建议路径：

```text
data/manifests/sources/<source_id>.yaml
```

最低 schema：

```yaml
schema_version: source-manifest-1

source_id: rfc-editor-index
display_name: RFC Editor approved RFC set
connector_type: web_collection
data_role: standard_document
provenance: standards_body
owner_scope: system_default

publisher: RFC Editor
course: network
language: en
formats:
  - text/html
  - application/xml

license:
  identifier: IETF-Trust-Legal-Provisions
  url: https://trustee.ietf.org/documents/trust-legal-provisions/
  verified_at: "2026-08-27"
  attribution_required: true
  share_alike: unknown
  commercial_use: review_required
  notes: "Code Components and older RFCs require separate checks."

origin:
  entry_url: https://www.rfc-editor.org/
  download_method: approved-list

sync:
  mode: manual_reviewed
  revision_strategy: source-metadata-and-sha256
  refresh_interval_days: 90

ingest:
  status: candidate
  require_human_review: true
  allowed_mime_types:
    - text/html
    - application/xml
  preserve_original_url: true
  preserve_attribution: true

limits:
  max_documents: 100
  max_raw_bytes: 200000000
  max_chunks: 2000
```

manifest 必须通过 JSON Schema 或 Pydantic 校验。未经 schema 校验的 Source 不得下载。

---

## 7. Document 与 Chunk schema

## 7.1 Document

```yaml
schema_version: document-1
source_id: rfc-editor-index
document_id: <sha256(source_id + logical_uri)>
logical_uri: rfc/rfc9293.html
canonical_url: https://www.rfc-editor.org/rfc/rfc9293.html
title: Transmission Control Protocol
course: network
topics: [tcp, transport-layer]
language: en
mime_type: text/html
provenance: standards_body
license_id: IETF-Trust-Legal-Provisions
source_revision: <revision>
content_sha256: <sha256>
retrieved_at: <ISO-8601>
review_status: approved
attribution:
  publisher: RFC Editor
  authors: []
  source_url: https://www.rfc-editor.org/rfc/rfc9293.html
```

## 7.2 Chunk

```yaml
schema_version: chunk-2
source_id: rfc-editor-index
document_id: <document_id>
chunk_id: <sha256(document_id + chunk_key + chunk_schema)>
chunk_key: section:3.5
chunk_schema: section-v2
title: Closing a Connection
course: network
topics: [tcp, connection-close]
source_type: standard_document
review_status: approved
license_id: IETF-Trust-Legal-Provisions
source_revision: <revision>
content: |
  ...
```

`RetrievalChunk` 和 VectorStore 必须保留 `source_id`、`document_id`、`chunk_id`、`license_id`、`source_revision`，不能仅保留文件路径。

---

## 8. 通用处理流水线

```text
DISCOVER
  → LICENSE_REVIEW
  → MANIFEST_VALIDATE
  → DOWNLOAD_RAW
  → HASH_AND_INVENTORY
  → NORMALIZE
  → EXTRACT
  → DEDUPLICATE
  → CHUNK
  → AUTO_QUALITY_GATE
  → HUMAN_REVIEW
  → APPROVE
  → BUILD_SNAPSHOT
  → INDEX_BM25
  → INDEX_VECTOR
  → EVALUATE
  → PUBLISH
```

### 8.1 下载

下载器必须：

- 有明确 User-Agent；
- 遵守访问频率和网站条款；
- 只访问 manifest 白名单 URL；
- 限制最大文件数、单文件大小和总字节数；
- 设置连接和读取超时；
- 失败重试最多 3 次，指数退避；
- 不绕过验证码、登录、付费墙或 robots；
- 下载到临时文件，校验后原子重命名；
- 保存 HTTP 状态、ETag、Last-Modified、Content-Type；
- 计算 SHA-256。

### 8.2 安全检查

- 不执行下载的脚本、宏、二进制或文档附件；
- 解压必须阻止 Zip Slip；
- 限制压缩展开比例和最大展开体积；
- 拒绝符号链接逃逸；
- HTML 禁止执行 JavaScript；
- 移除 API key、token、邮箱、电话号码等非必要敏感信息；
- 记录恶意或异常文件，不换方式绕过。

### 8.3 文本规范化

- UTF-8，无 BOM；
- Unicode NFC；
- 换行统一为 LF；
- 保留代码块、公式、表格语义；
- 删除导航、页脚、Cookie banner、广告和重复目录；
- 不擅自改写 MUST/SHOULD/MAY；
- 原文和中文翻译分开保存，翻译不能覆盖原文；
- 机器翻译必须标记 `translation_method: machine` 并人工抽检。

### 8.4 去重

分三层：

1. 原始文件：SHA-256 精确去重；
2. 规范化文档：normalized content hash；
3. 近重复：MinHash/SimHash，仅生成候选，不自动删除。

重复处理原则：

- 同一官方文档多个格式：选 HTML/TXT 作为主版本，PDF 作为资产；
- 官方原文优先于转载；
- 新有效标准优先于被废止标准；
- 近重复不能只因相似度高就删除，需人工确认。

### 8.5 切块

首批沿用标题结构切块，但升级为 `section-v2`：

- 优先按语义章节；
- 目标 300–800 中文字或约 200–600 tokens；
- 最大约 1,000 tokens；
- 过长章节按段落二次切分；
- 保留父标题链；
- 代码块和表格不从中间截断；
- 每个 chunk 能反向定位到原文 section；
- 切块规则变化必须升级 `chunk_schema`，不得静默复用旧 `chunk_id`。

### 8.6 自动质量门禁

拒绝或转人工复核：

- 空正文；
- 缺 source/license/canonical URL；
- 乱码比例超过阈值；
- 导航或模板文本占比过高；
- 大量重复行；
- 标题与正文主题不一致；
- 单文档异常大；
- 识别到密钥、私人邮箱、电话号码；
- 许可状态不是 approved；
- parser 版本未知。

### 8.7 人工审核

每个 Source 上线前至少审核：

- 全部许可证和第三方排除项；
- 所有 parser 异常文档；
- 每个主题至少 5 个随机文档；
- 每种格式至少 10 个样本；
- 所有敏感信息命中；
- 所有近重复冲突；
- 所有机器翻译抽样；
- RFC 的规范词和更新关系。

审核记录只使用 reviewer ID，不保存不必要的个人信息。

---

## 9. 增量同步与删除

每次同步比较：

```text
source revision
+ logical_uri
+ content_sha256
+ parser_version
+ chunk_schema
+ embedding_model
```

变更分类：

- 新 document：insert；
- 内容变更：重建该 document chunks；
- metadata 变更：更新 metadata，必要时重建；
- 路径变更但 canonical identity 不变：保留 document_id；
- 删除：生成 tombstone，并从 BM25、VectorStore、cache 删除；
- license 撤回或变更：立即停止发布，保留审计记录，不继续提供正文。

VectorStore 需要支持：

```python
upsert(chunks, vectors)
delete_ids(chunk_ids)
delete_source(source_id)
get_fingerprints(source_id)
```

禁止 10k 阶段仍以全库 `replace_all()` 作为常规同步方式。

---

## 10. 署名与回答展示

所有第三方来源的检索结果必须能生成：

```text
标题 — 作者/发布机构 — 来源 URL — 许可 — 版本/日期
```

回答引用不能只显示本地 `knowledge/...` 路径。至少返回：

- `source_id`；
- `document_id`；
- 标题；
- canonical URL；
- publisher/author；
- license；
- section；
- source revision。

如果来源要求 ShareAlike 或非商业使用，应能按 Source 生成许可报告。

---

## 11. 首批 3k 执行计划

### Stage A：扩展前修复

- [ ] `RetrievalChunk` 保留 Source/Document 身份；
- [ ] VectorStore 支持增量 upsert/delete；
- [ ] 基于 3k benchmark 调整现行默认 Source 750、额外 Source 600、总量 1200 的容量门禁；
- [ ] manifest schema 和 validator 完成；
- [ ] raw/candidate/approved 目录不进入 Git；
- [ ] attribution renderer 完成；
- [ ] Source 删除传播测试通过；
- [ ] 建立 3k benchmark 数据生成和结果模板。

### Stage B：建议数据配额

| 来源 | 目标 chunks | 用途 |
|---|---:|---|
| 当前项目人工知识包 | 682 左右 | 中文教学主层 |
| OpenDSA | 600–800 | DS/算法 |
| MIT OCW 6.004 | 350–500 | CO |
| RFC approved set | 350–500 | 网络标准层 |
| IANA registries | 100–200 | 网络事实层 |
| Linux Kernel Docs | 300–450 | OS 工程层 |
| 项目原创评测与解释 | 200–300 | 评测/中文桥接 |

目标总量约 2,600–3,400，不为凑数放宽质量门禁。

### Stage C：发布顺序

1. 项目原创评测；
2. OpenDSA；
3. MIT OCW 6.004；
4. RFC approved set；
5. IANA；
6. Linux Kernel Docs。

每个 Source 独立发布和回滚，不一次合并全部来源。

---

## 12. 10k 扩展计划

只有 3k Gate 全部通过后才能开始：

- 扩展更多 MIT OCW 明确许可课程；
- 扩展 RFC approved list；
- 增加 Linux 文档主题；
- 完成署名和许可链后评估 Stack Exchange 子集；
- 增加数据库、编译原理、分布式系统；
- benchmark 当前 SQLite；未来专业服务后端仅在 M8 独立决策与批准后讨论。Milvus Lite 仅为历史调查中的非权威提及，
  未选定、未批准、未接入，也不构成实现方向。

10k 阶段不得通过抓取博客或题库快速补量。

---

## 13. 验收指标

### 13.1 数据质量

- 100% approved document 有 source/license/canonical URL；
- 100% chunk 可追溯到 document 和 raw asset；
- 未授权第三方内容：0；
- 明文密钥和私人凭据：0；
- parser 失败不得静默丢弃；
- 精确重复率低于 1%；
- 乱码文档：0；
- 抽样事实准确率不低于 95%。

### 13.2 检索质量

按课程和来源分层评估：

- Recall@3；
- Recall@5；
- MRR；
- 来源过滤正确率；
- 被删除 Source 零召回；
- 被废止 RFC 默认不压过有效 RFC；
- 中文问题能召回英文权威材料和中文解释层；
- 负例查询不得强行给出不相关证据。

阈值必须在 benchmark 前冻结，不在看到结果后修改。

### 13.3 性能

分别记录纯 BM25、SQLite hybrid 和候选向量后端：

- 冷启动时间；
- 全量构建时间；
- 增量同步时间；
- 查询 p50/p95；
- 10/50 并发；
- RSS 内存峰值；
- 磁盘占用；
- 单 Source 删除传播时间。

---

## 14. Gate 0：每次新 Source 的必做检查

下载前逐项确认：

- [ ] URL 属于官方组织、原作者或官方仓库；
- [ ] 当前许可页面已实际打开并保存 URL/日期；
- [ ] 许可允许项目计划中的保存、转换和展示方式；
- [ ] 商业使用、衍生、署名、ShareAlike 条件已记录；
- [ ] 第三方内容能识别并排除；
- [ ] robots、使用条款和访问频率允许下载方式；
- [ ] manifest 已通过 schema；
- [ ] 文件数、字节数和 chunk 上限已配置；
- [ ] parser 有 fixture 和失败门禁；
- [ ] 删除与回滚路径已定义；
- [ ] 许可证变化时能够停止发布；
- [ ] reviewer 已签署审核结果。

任何一项为否，Source 保持 `reference_only` 或 `candidate`，不得进入生产索引。

---

## 15. 建议脚本布局

进入实现阶段后建议创建：

```text
tools/data_pipeline/
├── schemas/
│   ├── source-manifest.schema.json
│   ├── document.schema.json
│   └── evaluation-case.schema.json
├── connectors/
│   ├── git_source.py
│   ├── approved_url_source.py
│   ├── rfc_source.py
│   └── iana_registry_source.py
├── parsers/
│   ├── html_parser.py
│   ├── rst_parser.py
│   ├── xml_registry_parser.py
│   └── markdown_parser.py
├── quality/
│   ├── license_gate.py
│   ├── pii_scan.py
│   ├── duplicate_check.py
│   └── content_quality.py
├── commands/
│   ├── discover.py
│   ├── download.py
│   ├── normalize.py
│   ├── review.py
│   ├── publish.py
│   └── rollback.py
└── tests/
```

命令必须支持 dry-run：

```bash
python -m tools.data_pipeline.commands.download \
  --manifest data/manifests/sources/rfc-editor-index.yaml \
  --dry-run
```

正式下载前输出：URL 数、预计文件数、预计字节数、目标绝对路径和许可摘要。

---

## 16. 官方来源索引

以下页面是本文执行时的首要核验入口：

1. MIT OpenCourseWare Terms：https://ocw.mit.edu/pages/privacy-and-terms-of-use/
2. MIT OCW 6.004：https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/
3. OpenDSA：https://opendsa-server.cs.vt.edu/
4. OpenDSA GitHub：https://github.com/OpenDSA/OpenDSA
5. RFC Editor：https://www.rfc-editor.org/
6. RFC bulk retrieval：https://www.rfc-editor.org/retrieve/bulk/
7. IETF Trust Legal Provisions：https://trustee.ietf.org/documents/trust-legal-provisions/
8. IANA Protocol Registries：https://www.iana.org/protocols
9. Linux Kernel Documentation：https://docs.kernel.org/
10. Linux Kernel Git：https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
11. Stack Exchange licensing：https://stackoverflow.com/help/licensing
12. Stack Exchange Data Dump：https://archive.org/details/stackexchange

> 外部许可和下载入口可能变化。本文记录的是核验入口，不以历史结论替代执行当天的官方页面复核。

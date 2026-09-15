# M8 1K 最小安全 dry-run 协议 `v3`

> 状态：`DRAFT_FOR_INDEPENDENT_S0 / NOT_EXECUTION_AUTHORIZED`。
> 授权：[实现级验证路线决定与 v3 起草授权](m8-minimal-1k-v3-implementation-validation-authorization-20260914.md)。
> v1、v2 及其 `PROTOCOL_REJECTED / stop` 审计保持冻结；本文不是 draft-0.11 P4。

## 1. 范围与权限边界

本协议只比较 `sqlite-linear-exact` 与 `lancedb-embedded-exact-flat`。SQLite 是 correctness oracle/fallback，LanceDB
是唯一候选。两者必须读取同一份 1,000 chunk synthetic 预编码向量、query、gold 和 metadata filter。

冻结输入为 512 维、L2-normalized、`float32`、seed `20260914`。只评价 correctness、filter/no-hit、close/reopen、隔离、
observer 和清理。排除 Qdrant、ANN、10K/100K、真实资料、生产 adapter、迁移/cutover、默认后端选择和 M8 admission。
S3 接受 1K evidence 后仍为 `stop`，不自动形成任何后续权限。

S0 接受前不得创建真实 identity、实验根、venv、依赖环境或 1K 输入，也不得运行 SQLite/LanceDB。仓库内的微型 fixture
只验证 graph validator，不是 dry-run evidence，不构成 S1/S2。

## 2. 验证职责分层

- JSON Schema：`schemas/m8-minimal-1k-artifacts-v3.schema.json`，只定义 envelope、REF、member 和 observer summary 的
  字段形状、局部枚举及 closed primitive；它不声称能读取引用目标。
- Graph validator：`tools/m8_validate_minimal_1k_graph_v3.py`，必须读取调用方指定的持久 artifact directory，解析真实文件，
  复算摘要、字节数、JSONL 记录数、事件聚合、角色映射和 gate authority。
- Fixture generator：`tools/m8_generate_minimal_1k_v3_fixtures.py`，只生成微型 synthetic validator fixtures；不导入
  LanceDB，不访问网络，不读取真实资料，不创建仓库外实验根。

跨文件 bytes、目录集合或聚合语义由 graph validator 负责；单文件局部结构由 schema/validator 共同负责。任何约束只写在
自然语言而未在 graph validator 或 S1 前置检查中实现，不得作为“已机械闭合”申报。

## 3. Artifact directory 与 canonical bytes

待验证目录固定含：

```text
<graph>/
  artifacts/{identity,input-manifest,run-report,validation-report,cleanup-receipt,s0,s1,s2,s3}.json
  input/{chunks.jsonl,vectors.bin,queries.jsonl,gold.jsonl}
  events/{network,write,process,redaction}.jsonl
```

九个 JSON artifact 使用排序键、无空格、UTF-8 无 BOM、恰一个 LF 的 `sa-json-c14n-v1`。每个 envelope 的 logical name
唯一为 `minimal-1k/<experiment_id>/<role>.json`。目录中缺少角色、增加未知 JSON artifact、非 canonical bytes 或跨 artifact
experiment ID 不一致均为 invalid graph。

真实执行的 artifact directory 位于 S1 冻结的仓库外 evidence directory；S0 fixtures 位于仓库内 references/fixtures，必须
标注 `validator-micro-fixture-not-real-1k`。

## 4. Typed REF 与实际 bytes

REF 必须包含 `logical_name,role,schema_id,sha256,byte_count`。Graph validator 以 role 定位唯一目标 artifact，并机械验证：

1. role 与目标文件名一致；
2. schema ID 与 role 的冻结映射一致；
3. logical name 与目标 envelope 完全一致；
4. SHA-256 与目标实际 bytes 一致；
5. byte count 与目标实际 bytes 一致。

不得依靠 logical-name 或 schema-ID 的宽泛正则推断类型安全。断链、错型、错摘要、错字节数均 invalid，不能转化为有效失败图。

## 5. Gate 唯一映射与 authority

| Gate | Actor role | 成功 decision/action | 失败 decision/action |
| --- | --- | --- | --- |
| S0 | independent-reviewer | `PROTOCOL_ACCEPTED/request-s1` | `PROTOCOL_REJECTED/stop` |
| S1 | owner | `DRY_RUN_AUTHORIZED/run-s2` | `NOT_AUTHORIZED/stop` |
| S2 | executor | `EVIDENCE_READY/request-s3` | `DRY_RUN_FAILED/stop` |
| S3 | independent-reviewer | `ACCEPT_1K_EVIDENCE/stop` | `REJECT_1K_EVIDENCE/stop` |

S1 必须引用 S0。S2 必须按固定顺序引用 S1、run report、cleanup receipt 和 validation report。只有 validation `PASS` 且
cleanup `CLEANED` 时，S2 才能为 `EVIDENCE_READY/request-s3`；否则必须 `DRY_RUN_FAILED/stop`。S3 必须引用 S2；只有
S2 evidence ready 时才允许接受 1K evidence。S0 reviewer 不得是起草方；S3 reviewer 不得是 S2 executor。actor 名称与独立性
披露由真实 S0/S3 记录冻结，fixture 只验证 role 映射，不虚构独立性。

## 6. S1 必须冻结的可重放配置

S1 identity 必须使用全新 experiment ID，并在签发前由 S1 validator 额外冻结：clean 40-hex commit、clean status bytes 与
SHA-256、CPython 精确版本、NumPy/LanceDB/PyArrow/psutil 精确版本、wheel/安装 inventory、隔离 temporary root 与 evidence
directory 的 canonical Windows 路径和 parent identity、observer 配置文件 bytes、允许写入根集合及 production/repository
pre-inventory digest。

Identity 的核心 workload 常量固定为：1000 chunks、512 dimensions、`float32` little-endian、L2、seed `20260914`、
`top_k=[1,3,5]`、两个固定 backend 和 generator `sa-m8-synthetic-unit-v3`。S0 fixture identity 只覆盖这些核心常量；它不能
代替未来 S1 对机器环境与绝对路径的冻结。

## 7. Deterministic 1K workload

真实 S1 输入生成器必须在独立落盘的 generator specification 中冻结以下算法并由 graph validator 复算 manifest：

- NumPy 精确版本和 `PCG64(seed)`；一次调用生成 C-order `(1000,512)` float64，再显式转换为 little-endian `<f4`；
- 拒绝零范数、NaN 和 Inf；以 float64 求 L2 norm，除法后转 `<f4`，再次验证有限且范数误差在冻结容差内；
- chunk ID `m8-s00-00000`～`m8-s00-00999`，按 UTF-8 byte value 升序；
- exact 目标 0..24；perturbed 目标 25..49，使用 `PCG64(seed+1)` 一次生成 `(25,512)`、逐行缩放至 L2 `0.001` 后相加并归一化；
- metadata-filter 目标 50..74；wrong-owner-no-hit 目标 75..99；负向对象 100 tombstone、101 unpublished、102 generation
  mismatch、103 snapshot mismatch；
- score 降序，tie 以 chunk ID UTF-8 byte value 升序；top-k set agreement 分母固定为所有 104 query × 3 个 k，空 gold/no-hit
  也计入；要求 agreement `1.0`；
- JSONL 每行 canonical JSON + LF；vectors.bin 为 1000×512 连续 `<f4` C-order bytes，不含 header。

在 generator specification 与实现落盘并经独立 S0 接受前，不得签发 S1。本 v3 不生成真实 1K 输入。

## 8. Observer closed events

四类 ledger 的每行均为 closed event：`detail,kind,sequence,status`。sequence 从 0 连续递增；首事件必须
`observer-start`，末事件必须 `observer-stop`。summary 必须复算实际 ledger SHA-256、bytes、event count 和聚合 status；任一
事件 FAIL 则 summary FAIL。

允许 kind：

- network：`observer-start,observer-stop,outbound-connection`；measured phase 出现 outbound 即 FAIL；
- write：`observer-start,observer-stop,allowed-write,denied-write`；出现 denied-write 即 FAIL；
- process：`observer-start,observer-stop,child-count,unexpected-child`；出现 unexpected-child 即 FAIL；
- redaction：`observer-start,observer-stop,utf8-scan,sensitive-match`；出现 sensitive-match 即 FAIL。

真实 observer 的 API、Windows path/reparse/race 处理、进程树采集和 redaction registry bytes 必须在 S1 配置中冻结。observer
启动、读取、解码或扫描失败必须形成 FAIL event，不能缺省为 PASS。

## 9. 成功图与合法失败图

完整成功图要求：两个 backend status PASS、四类 observer PASS、cleanup `CLEANED`、validation 四项 check 全 true、最终
validation `PASS`、S2 evidence ready、S3 accept。

合法失败图必须保留相同的完整九 artifact 集合和可解析引用，但按事实闭合：

- cleanup failure：receipt `FAIL` 且说明残留事实，validation FAIL，S2 failed，S3 reject；
- observer failure：对应 ledger 含 FAIL event、summary FAIL，validation FAIL，S2 failed，S3 reject；
- runtime failure：run FAIL 且 errors 非空，validation FAIL，S2 failed，S3 reject；
- validation failure：至少一个 validation check false，verdict FAIL，S2 failed，S3 reject。

失败事实与失败 authority 一致的图是 `VALID_FAILURE_GRAPH`；篡改摘要、删除证据、把失败包装为 PASS 或让 S2 越权均是
invalid graph。失败记录不可就地改写；真实重跑使用新 experiment ID。

## 10. S0 fixture 与负例要求

S0 package 至少包含 `success`、`failure-cleanup`、`failure-observer`、`failure-runtime`、`failure-validation` 五个持久图，并
证明 graph validator 可逐目录重放。还必须通过复制到临时工作目录后实施的负例矩阵，至少覆盖：目标 bytes 被改、REF role/
schema 错配、logical name 错、digest/count 错、非法 gate actor/decision/action、S2 缺 PASS validation/cleanup authority、
observer summary 与 ledger 不一致、非法 event sequence/kind、失败事实伪装为成功、未知或缺失 artifact、路径 escape。

当前修订测试 harness 包含 5 个持久图和 20 个 fail-closed mutation；其中新增 non-canonical event JSONL 与 input JSONL 两类负例。数量本身不是通过条件，独立 S0 应核对每个 mutation 对应的阻断类别与实际拒绝输出。

负例副本不是治理记录，可在验证结束后由测试 harness 自行回收；冻结的 v1/v2 和 v3 正式材料不得改写。

## 11. S0、S1 与后续边界

独立 S0 只判断协议、schema、graph validator、fixture generator 与正负例是否闭合，不接受任何真实 1K evidence。S0 通过
只允许 owner 另行决定是否签发 S1。S1 签发前仍需补齐第 6、7、8 节要求的机器环境、generator implementation 和 observer
配置冻结。

S3 即使接受，也只证明该 experiment 的 1K evidence 满足本协议；不批准 10K、backend selection、生产修改或 M8 admission。

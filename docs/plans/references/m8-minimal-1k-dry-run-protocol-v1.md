# M8 1K 最小安全 dry-run 协议 `v1`

> 性质：仅覆盖一次 SQLite/LanceDB 1K 隔离实验的规范文本。
> 状态：`DRAFT_FOR_S0_REVIEW / NOT_EXECUTION_AUTHORIZED`。
> 路线依据：[M8 分层 dry-run 治理路线变更决定](m8-minimal-dry-run-route-decision-20260914.md)。
> 与旧链关系：不是 `draft-0.11` 的修订或 P4；不得复用其 identity、binding 或 gate。

## 1. 目标和非目标

目标是使用相同的 canonical synthetic input 比较：

- `sqlite-linear-exact`：correctness oracle 和 fallback；
- `lancedb-embedded-exact-flat`：唯一候选。

本次只验证 1K correctness、filter/no-hit、基本观测、close/reopen 和隔离清理。性能只记录，不自动选择后端。
不包含 Qdrant、ANN、10K/100K、真实资料、生产 adapter、迁移、cutover、默认后端切换或 M8 admission。

## 2. 四步门禁

| Gate | Actor | 接受结果 | 拒绝结果 | 权限 |
| --- | --- | --- | --- | --- |
| S0 | independent reviewer | `PROTOCOL_ACCEPTED / request-s1` | `PROTOCOL_REJECTED / stop` | 只接受文字 |
| S1 | owner | `DRY_RUN_AUTHORIZED / run-s2` | `NOT_AUTHORIZED / stop` | 只授权一个全新 1K experiment |
| S2 | executor + validator | `EVIDENCE_READY / request-s3` | `DRY_RUN_FAILED / stop` | 只执行和验证已冻结配置 |
| S3 | independent reviewer | `ACCEPT_1K_EVIDENCE / stop` | `REJECT_1K_EVIDENCE / stop` | 只裁定 1K 证据 |

S0 reviewer 不得是协议起草方。S3 reviewer 不得是 S2 executor。主体分离以记录中的 actor name 逐字比较并诚实披露，
不虚构密码学独立性证明。失败记录不得改写；重跑必须使用新的 experiment ID。

## 3. S1 冻结配置

S1 必须在执行前冻结以下字段：

```text
experiment_id, protocol_sha256, repository_commit, python_version,
seed, chunk_count=1000, dimension=512, dtype=float32,
normalization=l2, backends=[sqlite-linear-exact,lancedb-embedded-exact-flat],
query_counts, top_k=[1,3,5], measured_run_network=false,
temporary_root_policy=isolated-disposable, dependency_versions
```

输入采用固定 seed 的预编码 synthetic unit vectors。metadata 只允许 synthetic `chunk_id`、`owner_id`、`source_id`、
`generation`、`snapshot`、`published`、`tombstone` 和 synthetic filter label，不得包含真实路径、资料、URI、凭据或用户内容。

## 4. 1K workload

- 1 个 synthetic owner、1 个 synthetic source、1,000 个 stable chunk ID；
- 每个向量为确定性生成的 512 维 `float32` L2-normalized unit vector；
- query 集包含 exact、perturbed、metadata-filter、wrong-owner/no-hit 四类；各类数量由 S1 明确冻结；
- SQLite 与 LanceDB 必须读取字节相同的 input manifest、vector blob 和 query/gold manifest；
- `top_k` 为 1、3、5；同分时按 stable chunk ID 升序归一化；
- LanceDB 必须使用 embedded local mode、显式 Arrow schema、exact/flat search，不创建 ANN index。

首次 dry-run 不设置复杂性能准入线。只记录 build/query/reopen elapsed time、peak RSS 和 index bytes，供后续决定 10K schema。

## 5. 允许和禁止

S1 接受后只允许在一个仓库外隔离临时根内：

- 创建临时 venv、依赖缓存、synthetic input、SQLite DB、LanceDB directory、raw report 和日志；
- 在 acquisition 阶段按冻结版本获取 LanceDB 依赖；
- 执行本协议规定的 build、query、filter、close/reopen、验证和清理。

禁止读取 `D:\111_Others_Subjects` 或真实用户资料；禁止写生产数据、修改默认后端、启动服务、打开 listener；
measured run 禁止网络。禁止自动准备或运行 10K，禁止后端选择和 M8 admission。

## 6. 最小 canonical artifact

所有 JSON 使用 UTF-8 无 BOM、排序键、无额外空格、恰一个 LF 结尾；envelope 字段固定为：

```text
schema_id, schema_version=1, canonicalization_id=sa-json-c14n-v1,
logical_name, payload
```

### 6.1 `sa.m8.minimal.experiment-identity.v1`

Payload：S1 冻结配置的全部字段，加 `created_at`、`owner_actor` 和随机 64 位小写十六进制 nonce。

### 6.2 `sa.m8.minimal.input-manifest.v1`

Payload：`experiment_id`、config digest、chunk/vector/query/gold 的 logical name、SHA-256、byte count、record count，
以及 synthetic-only 声明。manifest 不内嵌 1,000 个向量。

### 6.3 `sa.m8.minimal.run-report.v1`

Payload：environment、dependency versions、input manifest REF、两个 backend result。每个 result 只含 build/query/reopen
观测、count、identity-set digest、每类 query 的 normalized result digest、filter/no-hit counters、unexpected errors 和
backend-native/harness-enforced 边界说明。

### 6.4 `sa.m8.minimal.validation-report.v1`

Payload：input equality、count/identity equality、top-k parity、filter/no-hit、reopen、network、write-boundary、redaction、
cleanup-precondition 检查，以及 `PASS` 或 `FAIL`。每项只有 `id`、`passed`、`evidence_digest` 和短说明。

### 6.5 `sa.m8.minimal.cleanup-receipt.v1`

Payload：`experiment_id`、隔离根的脱敏 logical label、清理前后条目计数、清理结果、失败原因、timestamp。不得记录主机绝对路径。

### 6.6 S0–S3 decision record

Payload 固定为：`record_id`、`gate_id`、`actor`、`timestamp`、`decision`、`allowed_next_action`、`reason`、
`protocol_sha256`、`experiment_id`（S0 可为 `none`）、`read_refs`。decision record 不包含未来 gate 的预置裁定。

## 7. 硬失败条件

以下任一成立，S2 必须 `DRY_RUN_FAILED / stop`，S3 不得接受：

1. 两个 backend 的 input digest 不同；
2. count 或 identity-set 不一致；
3. wrong-owner、tombstone、unpublished 或不匹配 generation/snapshot 产生命中；
4. 预期 no-hit 返回非空；
5. exact/flat normalized top-k 集合超出 S1 冻结容差；
6. close/reopen 后结果不一致；
7. measured run 出现网络或越界写入；
8. 报告含主机绝对路径、真实资料、凭据或源内容；
9. cleanup 失败；
10. unexpected error 非空。

## 8. 执行顺序和停止点

1. S0 独立接受协议；
2. S1 owner 冻结全新 identity、commit、依赖和 input config；
3. acquisition 与隔离环境准备；
4. 生成 canonical synthetic input；
5. 执行 SQLite 与 LanceDB；
6. 生成 run/validation report；
7. 生成脱敏摘要后清理隔离根并形成 receipt；
8. S3 独立裁定；
9. 无论接受或拒绝均停止，请 owner 另行决定是否准备 10K。

1K 接受仅表示 `1K_EVIDENCE_ACCEPTED`。M8 继续 `BLOCKED / NOT_STARTED`。

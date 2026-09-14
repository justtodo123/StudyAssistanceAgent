# M8 1K 最小安全 dry-run 协议 `v2`

> 状态：`DRAFT_FOR_INDEPENDENT_S0 / NOT_EXECUTION_AUTHORIZED`。
> 授权：[v2 修订授权](m8-minimal-1k-protocol-v2-authorization-20260914.md)。
> v1 与其 `PROTOCOL_REJECTED / stop` 审计保持冻结；本文不是 draft-0.11 P4。

## 1. 唯一范围

比较 `sqlite-linear-exact` 与 `lancedb-embedded-exact-flat`，使用同一份 1,000 chunk synthetic 预编码向量输入。
只评价 1K correctness、filter/no-hit、close/reopen、隔离和清理。排除 Qdrant、ANN、10K/100K、真实资料、生产实现、
迁移/cutover、后端选择和 M8 admission。1K 接受后仍 `stop`，10K 必须另行授权。

## 2. 四步 gate

- S0 independent reviewer：`PROTOCOL_ACCEPTED/request-s1` 或 `PROTOCOL_REJECTED/stop`；
- S1 owner：`DRY_RUN_AUTHORIZED/run-s2` 或 `NOT_AUTHORIZED/stop`；
- S2 executor：仅当最终 validation `PASS` 且 cleanup receipt `CLEANED` 时为 `EVIDENCE_READY/request-s3`，否则
  `DRY_RUN_FAILED/stop`；
- S3 independent reviewer：`ACCEPT_1K_EVIDENCE/stop` 或 `REJECT_1K_EVIDENCE/stop`。

S0 reviewer 不得是 drafting party `ai-assistant`；S3 reviewer 不得是 S2 executor。失败记录不可改写，重跑使用新
experiment ID。

## 3. 双 commit 绑定

S0 materials 分别记录：

- `reviewed_object_commit`：首次同时包含 v2 protocol、schema、validator 的 clean commit；
- `review_package_commit`：包含 S0 materials/worksheet 的 clean commit。

Reviewer 必须证明后者是前者的后代，并验证三个被审对象在两 commit 中字节相同。S1 再绑定其签发时的 clean commit，
不得混用上述 commit 含义。

## 4. S1 closed config

Identity 必须冻结：全新 experiment ID、protocol digest、40-hex repository commit、clean-status digest、CPython
`3.11.9`、seed `20260914`、1000 chunks、512 dimensions、`float32`、L2、两个固定 backend、四类 query 各 25 条、
`top_k=[1,3,5]`、exact top-k set agreement `1.0`、LanceDB 精确版本、acquisition network allowed、measured network
forbidden、隔离根 label、根外 evidence label、observer 配置、生成算法 ID 和 HEX64 nonce。开放版本或占位符非法。

## 5. Deterministic workload

算法 ID 为 `sa-m8-synthetic-unit-v2`。使用 NumPy `PCG64(seed)` 按 chunk ordinal 生成 1000×512 `float32`，逐行
L2 normalize；chunk ID 为 `m8-s00-00000` 至 `m8-s00-00999`。正常 owner/source 为 `owner-00/source-00`，不存在的
owner 为 `owner-missing`。generation/snapshot 固定为 `generation-01/snapshot-01`。

四类 query 各 25 条且 ID 固定：

- exact：目标 ordinal 0..24，向量等于目标向量，gold 为目标 ID；
- perturbed：目标 25..49，加由 `PCG64(seed+1)` 生成、L2 norm 为 `0.001` 的噪声后归一化，gold 为目标 ID；
- metadata-filter：目标 50..74，filter 要求正常 owner/source、published=true、tombstone=false、正确 generation/snapshot；
- wrong-owner-no-hit：目标 75..99，但 filter owner=`owner-missing`，gold 为空。

另有四个固定负向 fixture，ordinal 100 tombstone、101 unpublished、102 generation mismatch、103 snapshot mismatch；
其 query 使用对象自身向量与对应不匹配 filter，gold 均为空。所有 manifest 使用稳定 ID 升序和 canonical JSONL。

## 6. Phase 与 observer

Acquisition phase 仅允许 S1 冻结的 Python 包下载；结束标志为 dependency inventory 写入 evidence directory。Measured
phase 从 input digest 复验开始，到 run report 原始 bytes 摘要完成为止，进程树为 executor PID 及其 descendants。

- Network observer：measured phase 前后以 `GetExtendedTcpTable` 捕获进程树连接，并由 harness 记录所有 socket API
  调用；observer 启动/读取失败即 FAIL；事件非空即 FAIL。
- Write observer：所有创建/修改目标先 canonicalize，拒绝 symlink/junction/reparse escape；允许集合仅为隔离临时根与
  根外 evidence directory。仓库根和 production roots 的 pre/post inventory digest 必须相同。
- Redaction observer：扫描所有持久 evidence UTF-8 bytes，拒绝 Windows absolute path、URI credential、token/private-key
  marker、`D:\111_Others_Subjects` 和非 synthetic content marker；解码或扫描失败即 FAIL。

Observer 结果使用 closed schema；无法观测与观测到违规同样 fail closed。

## 7. Evidence 生命周期

S1 为每个 experiment 预留两个仓库外同 parent 的目录：`temporary_root` 和 `evidence_directory`；两者不得互为 descendant，
也不得位于仓库或 production roots。Raw input、DB/index 和临时日志只在 temporary root。脱敏 run report、validation draft、
摘要与最终 cleanup receipt 写入 evidence directory。

顺序固定：运行 → 写 run report → 写 validation draft（不含最终 verdict）→ 删除 temporary root → 写 cleanup receipt →
复验 receipt 与 evidence → 写最终 validation report → 写 S2 decision。Cleanup 失败也必须在 evidence directory 写 receipt，
最终 validation 只能 FAIL，S2 只能 `DRY_RUN_FAILED/stop`。S3 只读取 evidence directory 中的持久 artifact。

## 8. 六类 closed artifact

规范 schema 为 `schemas/m8-minimal-1k-artifacts-v2.schema.json`。它以 schema ID 的 `oneOf` 分支关闭六类 payload，
规定 logical-name grammar、typed REF、actor、timestamp、digest、计数、资源、observer 与 error 字段。所有 object 均拒绝
额外字段。Canonical JSON 为排序键、无空格、UTF-8 无 BOM、单 LF。

Logical name 唯一派生为：

```text
minimal-1k/<experiment_id>/<role>.json
```

role 只能为 `identity,input-manifest,run-report,validation-report,cleanup-receipt,s0,s1,s2,s3`。S0 的 experiment ID 为
`protocol-v2`。REF 必须携带匹配目标的 logical name、schema ID 和 SHA-256。

## 9. 硬失败

Input digest、count/identity、全部 exact/perturbed top-k set、filter/no-hit、四个负向 fixture、reopen、network、write-set、
redaction、unexpected errors 与 cleanup 任一失败，最终 validation 必须 FAIL。LanceDB 必须证明 embedded exact/flat 且没有
ANN index；SQLite 为 oracle。性能仅记录非负整数纳秒、peak RSS 和 index bytes，不产生选择结论。

本协议通过 S0 也不授权 S1；通过 S3 也不授权 10K、backend selection 或 M8 admission。

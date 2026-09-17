# M8 最小 1K v3 deterministic generator specification

> 状态：`S1_PREREQUISITE_CONTRACT / NOT_EXECUTION_AUTHORIZED`。
> 本文只冻结未来真实 1K synthetic input generator 的可重放合同；不生成输入、不创建 experiment identity 或根目录，
> 不安装依赖、不运行 SQLite/LanceDB，也不构成 `PROTOCOL_ACCEPTED`、S1、backend selection 或 M8 admission。

## 1. 权威边界

本文实现 [`m8-minimal-1k-dry-run-protocol-v3.md`](m8-minimal-1k-dry-run-protocol-v3.md) 第 6、7 节要求。
未来 generator implementation、其精确 bytes 和本文精确 bytes 必须先由独立 S0 接受；Owner 随后仍须另行签发 S1。
模板中的占位符、fixture generator 和仓库内 micro-fixture 均不是实现、真实输入或授权。

Generator identifier 固定为 `sa-m8-synthetic-unit-v3`。实现不得读取真实资料、用户内容、生产索引、
`D:\111_Others_Subjects` 或网络；输出只能位于未来 S1 冻结的仓库外 temporary root。

## 2. 冻结常量

| 项目 | 固定值 |
| --- | --- |
| PRNG | `numpy.random.Generator(numpy.random.PCG64(seed))` |
| seed | `20260914` |
| chunk count | `1000` |
| dimension | `512` |
| stored dtype / byte order | IEEE-754 binary32 / little-endian `<f4` |
| generation working dtype | NumPy `float64` |
| array order | C-order |
| normalization | L2 |
| chunk IDs | `m8-s00-00000`～`m8-s00-00999` |
| query count | `104` |
| top-k | `[1,3,5]` |
| required set agreement | `1.0` |
| canonical JSON | `sa-json-c14n-v1` |
| backends | `sqlite-linear-exact`, `lancedb-embedded-exact-flat` |

S1 config 必须冻结精确 NumPy 版本和正的有限 `normalization_tolerance`；实现不得自行选择版本或容差。
所有 ordinal、ID、path 和 record 顺序均按 UTF-8 byte value 升序比较，不使用 locale collation。

## 3. Canonical serialization

`chunks.jsonl`、`queries.jsonl` 和 `gold.jsonl` 的每条记录必须为 closed JSON object，并逐条使用：

1. UTF-8，无 BOM；
2. object key 递归按 Unicode code point 排序；本合同中的 ASCII keys 因而等同 UTF-8 byte 顺序；
3. separators 固定为 `,` 与 `:`，无 insignificant whitespace；
4. JSON literals 仅使用小写 `true`、`false`、`null`；
5. 禁止 NaN、Infinity、重复 key 和未配对 surrogate；
6. 每条记录后恰一个 LF (`0x0a`)，包括最后一条；禁止 CR。

向量不以 JSON decimal array 表达。Query record 的 `vector_f32_le_base64` 是对应 512 个连续 `<f4` bytes 的 RFC 4648
standard base64，必须有规范 padding，禁止空白。这样 query bytes 不依赖浮点十进制格式化。

`vectors.bin` 固定为按 chunk ordinal 0..999 连续拼接的 `1000 × 512 × 4 = 2048000` bytes，无 header、padding、
record delimiter 或 trailer。每行向量先成为 C-contiguous `<f4`，再按 `ndarray.tobytes(order="C")` 拼接。

## 4. Chunk vector 生成

实现必须执行以下单一路径，不得分批、逐 chunk 重置 PRNG 或替换 bit generator：

1. 创建 `Generator(PCG64(20260914))`。
2. 以一次 `standard_normal(size=(1000,512), dtype=float64)` 调用得到 C-order float64 matrix `raw`。
3. 若 `raw` 非 C-contiguous，立即 FAIL；不得隐式复制后继续。
4. 若任一元素不是 finite，或任一行的 float64 L2 norm 为 0 或非 finite，立即 FAIL。
5. L2 norm 使用 float64 的 `sqrt(sum(raw * raw, axis=1, dtype=float64))`；按行执行 float64 division。
6. 将归一化结果一次显式转换为 C-contiguous little-endian `<f4` matrix `stored`。
7. 再验证 `stored` 全部 finite，并以 `stored.astype(float64)` 复算每行 norm；每行
   `abs(norm - 1.0) <= normalization_tolerance`，否则 FAIL。
8. `stored` 的 C-order bytes 原样形成 `vectors.bin`。

任何 FAIL 都不得发布 partial manifest、补零、重抽样、跳过行或更换 seed。

## 5. Chunk metadata

每个 `chunks.jsonl` record 必须且只能含以下 keys：

```text
chunk_id,filter_label,generation,ordinal,owner_id,published,snapshot,source_id,tombstone,vector_byte_length,vector_byte_offset
```

共同值与派生规则：

- `chunk_id = "m8-s00-" + zero_pad_5(ordinal)`；
- `filter_label = "label-" + zero_pad_5(ordinal)`；
- `owner_id="owner-00"`，`source_id="source-00"`；
- 正常值为 `generation="generation-01"`、`snapshot="snapshot-01"`、`published=true`、`tombstone=false`；
- `vector_byte_offset = ordinal * 2048`，`vector_byte_length=2048`；
- ordinal 100：`tombstone=true`；
- ordinal 101：`published=false`；
- ordinal 102：`generation="generation-mismatch"`；
- ordinal 103：`snapshot="snapshot-mismatch"`；
- 除 100..103 的上述单项差异外，其他字段均使用正常值。

文件必须含 ordinal 0..999 各一次且仅一次，并按 `chunk_id` UTF-8 bytes 严格升序。

## 6. Query vector 与 filter 生成

Query IDs、类型、目标和顺序固定如下：

| 顺序 | query ID | type | target ordinal |
| --- | --- | --- | ---: |
| 0..24 | `m8-q-exact-000`～`m8-q-exact-024` | `exact` | 0..24 |
| 25..49 | `m8-q-perturbed-000`～`m8-q-perturbed-024` | `perturbed` | 25..49 |
| 50..74 | `m8-q-metadata-filter-000`～`m8-q-metadata-filter-024` | `metadata-filter` | 50..74 |
| 75..99 | `m8-q-wrong-owner-no-hit-000`～`m8-q-wrong-owner-no-hit-024` | `wrong-owner-no-hit` | 75..99 |
| 100..103 | `m8-q-negative-100`～`m8-q-negative-103` | `negative-fixture` | 100..103 |

每个 `queries.jsonl` record 必须且只能含：

```text
filter,query_id,query_type,target_chunk_id,vector_f32_le_base64
```

`filter` 是 closed object，且只能含
`filter_label,generation,owner_id,published,snapshot,source_id,tombstone`。规则如下：

- exact、perturbed：使用 `filter_label="*"`，其余六项也为字符串 `"*"`，表示无 metadata predicate；
- metadata-filter：使用目标的唯一 `filter_label` 和全部正常 metadata 值；
- wrong-owner-no-hit：使用目标的唯一 `filter_label`、正常 metadata，但 `owner_id="owner-missing"`；
- negative 100..103：使用目标的唯一 `filter_label` 和全部正常 metadata；目标分别因 tombstone、unpublished、generation
  mismatch、snapshot mismatch 被排除，因此 candidate set 为空。

`"*"` 只在本节定义的 query filter 内表示 omitted predicate，不得作为 chunk metadata 或 S1 template placeholder。

### 6.1 Exact、filter 与 no-hit vectors

Exact、metadata-filter、wrong-owner-no-hit 和四条 negative query 的 query vector，均为目标 chunk 在 `stored` 中的 2048
bytes 原样复制，再按第 3 节 base64 编码。

### 6.2 Perturbed vectors

Perturbed query 必须使用独立 `Generator(PCG64(seed+1))`：

1. 以一次 `standard_normal(size=(25,512), dtype=float64)` 调用生成 C-order float64 noise matrix；
2. 对每行用第 4 节相同的 finite/zero-norm规则复核；
3. 以 float64 将每行缩放到精确目标 L2 norm `0.001`；
4. 将 ordinal 25..49 的 stored chunk rows 转为 float64，与相应 noise row 相加；
5. 以 float64 重新 L2 normalize，拒绝 zero、NaN、Inf；
6. 一次显式转换为 C-contiguous `<f4`，复算 finite 与 S1 容差；
7. 每行 2048 bytes 分别进行规范 base64 编码。

不得复用 chunk PRNG 状态、逐行重新 seed 或对转换后的 query 再作随机修正。

## 7. Gold 与 ranking oracle

Gold 由 generator 内的 exact linear oracle 从已落盘并复读的 `vectors.bin` 与 canonical `queries.jsonl` 计算；不得使用
SQLite/LanceDB 输出反向生成 gold。

1. 将候选 `<f4` 和 query `<f4` 显式转换为 float64。
2. 只保留满足 query filter 的 chunks。
3. score 为 float64 dot product；任一非 finite score 立即 FAIL。
4. 排序 key 为 `(-score, chunk_id_utf8_bytes)`；score 降序，同分以 chunk ID UTF-8 bytes 升序。
5. 对 k=1、3、5 取 `min(k,candidate_count)` 个 ID；candidate set 为空时三个集合均为空。

每个 `gold.jsonl` record 必须且只能含：

```text
gold_by_k,query_id
```

`gold_by_k` 必须且只能含字符串 keys `"1"`,`"3"`,`"5"`，值为依 ranking 顺序排列的 chunk-ID array。Gold records 与
query records 一一对应并使用相同顺序。

Backend agreement 对全部 104 queries 和三个 k 分别计一个 set comparison，固定分母为 `104 × 3 = 312`；空 gold/no-hit
同样计入。每项比较忽略结果内部顺序但不忽略重复项；backend result 含重复 ID、超出 k、非法 ID 或 filter-ineligible ID 时该项
FAIL。成功要求 `312/312 = 1.0`。

## 8. Manifest 重算与 fail-closed

未来 implementation 必须在写入后重新打开四个成员，以 binary mode 复算 path、SHA-256、byte count 和 record count；manifest
不得信任内存中预期值。固定成员和 record count 为：

- `input/chunks.jsonl`：1000；
- `input/gold.jsonl`：104；
- `input/queries.jsonl`：104；
- `input/vectors.bin`：1000 logical vector records，2048000 bytes。

Graph validator 必须从实际 bytes 复算 manifest、canonical JSONL、ID/ordinal 集合、vector offsets、query/gold 对应关系和 gold。
Digest、count、canonicalization、finite/norm、ordering、filter、ranking 或 agreement 任一不一致均 fail closed。

## 9. S1 前置检查

签发 S1 前至少必须证明：本文和 implementation bytes 已由独立 S0 接受；S1 config 对其 path、SHA-256、byte count、精确
CPython/NumPy 版本和 normalization tolerance 完整绑定；implementation 的 deterministic self-test 在两个全新空 output root
产生逐 path、逐 byte 相同的四成员树。该 self-test 只能生成 synthetic candidate input，不产生 S1 或执行权限。

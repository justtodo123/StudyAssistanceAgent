# M8 最小 1K dry-run 协议 v2 独立 S0 技术审查记录

- reviewer：`s0-independent-reviewer-20260914`
- reviewed object commit：`1f1d147deb9fd9b28338851f00f9cbbbc5c26614`
- review package commit：`e763002c340e78f29b2b43dd925116ca31375ef3`
- decision：`PROTOCOL_REJECTED`
- allowed_next_action：`stop`
- 状态：`S0_V2_REJECTED / S1_NOT_AUTHORIZED / M8_BLOCKED`

## 独立性披露

Reviewer 名称与 drafting party `ai-assistant` 逐字节不同。Reviewer 声明未修改被审对象，未参与 v2 protocol、schema
或 validator 起草；审查依据冻结 bytes、静态分析、仓库外内存正负例设计和 validator 代码审阅。现有材料不能密码学
证明 reviewer 从未参与历史起草；名称分离只是最低机械条件。

## 冻结对象

| 对象 | SHA-256 | bytes | LF |
| --- | --- | ---: | ---: |
| protocol | `1a6be348b8d0396ecf44943b582e94bee2a80dcbe0277a16fcd86141adc9aeda` | 6379 | 102 |
| schema | `d29d368083c2a62b1f9687aa8fd870a1c8f22df655ffc185a17095c4da3af14e` | 17214 | 1 |
| validator | `879b7b3b74d50bb6807269af2a03be541636a9575c8ae3f595bcf053a0245077` | 6383 | 25 |

Review package 是 reviewed object commit 的后代，三个对象在两 commit 及工作区中 byte-identical。审查环境缺少
`jsonschema`，reviewer 遵守禁止安装依赖的限制，未把 validator 无法运行误判为协议通过；其余结论来自静态和内存分析。

## Findings

### `m8-v2-s0-001` — 六类 payload 在 artifact graph 层仍开放

字段层使用 `oneOf` 和 `additionalProperties=false`，但 REF、logical name、schema ID、payload experiment ID 与实际
artifact bytes 的关系未闭合，故不能视为完整 closed artifact schema。

### `m8-v2-s0-002` — Typed REF 不具类型安全

REF 的 logical name 和 schema ID 分别满足宽泛规则即可，可将 input-manifest logical name 与 run-report schema ID
组合；SHA-256 也未解析到实际目标 bytes。

### `m8-v2-s0-003` — Logical name 未与 payload 和 schema role 绑定

Envelope 路径中的 experiment ID 未强制等于 payload experiment ID，role 也未通过通用跨字段验证绑定到 schema ID。

### `m8-v2-s0-004` — Gate、actor、decision、action 未闭合映射

Decision schema 允许四个 gate、三种 role、八个 decision 和四个 action 的非法笛卡尔组合，未机械限定 S0～S3 的唯一映射。

### `m8-v2-s0-005` — 协议要求的失败 artifact 无法表达

Cleanup schema 只允许 `CLEANED/none/after_count=0`；validation 只允许 PASS；run report 只允许 observer PASS 和空 errors。
因此 cleanup/observer/runtime 失败无法形成协议要求的持久失败证据链。

### `m8-v2-s0-006` — S2 未机械依赖 PASS validation 与 CLEANED receipt

S2 `read_refs` 只是通用 REF 数组，可为空或指向错误对象；schema 和通用 validator 未解析并强制
`EVIDENCE_READY/request-s3` 读取 PASS validation 与 CLEANED cleanup receipt。

### `m8-v2-s0-007` — Digest、计数和资源只是格式声明

REF digest、manifest byte/record count、identity/result/observer digest、clean status 和 metrics 未与实际 bytes、JSONL 行数、
事件或仓库状态复算绑定；两个 backend 的 identity/result digest 也无通用一致性校验。

### `m8-v2-s0-008` — S1 仍未冻结可重放的精确配置

Dependency 仅限制 semver 形状，不固定具体值；clean-status digest 输入未定义；observer ID 无配置 bytes；目录只有 label；
agreement 分母/空集合处理和 LanceDB exact/flat 运行证据未闭合。

### `m8-v2-s0-009` — Deterministic workload/gold 仍不保证 byte-identical

缺少精确 NumPy 版本值、PCG64 调用/reshape/字节序、零向量/NaN/Inf、perturbation 伪代码、top-k tie-break、完整 query/gold
record schema、float serialization 与 JSONL canonicalization，两个独立 executor 仍可生成不同 bytes。

### `m8-v2-s0-010` — Observer 设计仍不可独立重放审计

Network ledger、短连接和 native/child 覆盖，Windows canonical path/reparse/race/write ledger，以及 redaction pattern registry、
Unicode/encoding/扫描清单均未形成 closed algorithm 和 event schema；三字段 observer 摘要不能证明实际执行。

### `m8-v2-s0-011` — 未证明完整合法 S0→S3 实例

Validator 只构造 identity、manifest、run、cleanup、validation 和示例 S2，未构造完整四 gate，也未解析持久 artifact graph。
结构上可接受非法 transition，而协议要求的失败 transition 又无法由 schema 表达。

### `m8-v2-s0-012` — v1 关键负例仍存在 fail-open 类别

Logical/schema 错配、错误 REF/bytes、非法 gate 组合、S2 缺 PASS/cleanup authority、任意 observer digest、任意 semver 与任意
clean digest 仍未被通用验证器拒绝。部分单字段负例通过不足以关闭 v1 findings。

### `m8-v2-s0-013` — 新的组合不可满足问题

协议要求失败闭环而 schema 只允许成功对象；要求 typed REF 而只实现字段格式；要求 gate 映射而允许任意组合；要求
observer 可验证而没有事件 schema。这些是组合层阻断，不是单个字段遗漏。

## 通过项与边界

双 commit 绑定语义得到闭合；v2 没有越出授权范围，仍只覆盖 SQLite/LanceDB 1K synthetic，不包含 Qdrant、ANN、
10K/100K、真实资料、生产迁移、后端选择或 M8 admission，也未创建 draft-0.11 P4。

## 最终裁定

```text
decision: PROTOCOL_REJECTED
allowed_next_action: stop
finding_ids:
  - m8-v2-s0-001
  - m8-v2-s0-002
  - m8-v2-s0-003
  - m8-v2-s0-004
  - m8-v2-s0-005
  - m8-v2-s0-006
  - m8-v2-s0-007
  - m8-v2-s0-008
  - m8-v2-s0-009
  - m8-v2-s0-010
  - m8-v2-s0-011
  - m8-v2-s0-012
  - m8-v2-s0-013
```

不得签发 S1、创建实验环境、安装依赖、生成 1K 输入、执行 SQLite/LanceDB dry-run，或创建 draft-0.11 P4。
M8 继续 `BLOCKED / NOT_STARTED`。v2 及本拒绝记录冻结，不得就地改写。

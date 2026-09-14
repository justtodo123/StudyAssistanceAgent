# M8 最小 1K 实现级验证路线决定与 v3 起草授权

- 日期：2026-09-14
- owner：`justtodo123`
- 状态：`AUTHORIZED_FOR_V3_IMPLEMENTATION_LEVEL_VALIDATION_DRAFTING / NOT_S0_ACCEPTED / NOT_EXECUTION_AUTHORIZED`
- 前版：`m8-minimal-1k-dry-run-protocol-v2.md`
- 前版 S0：`PROTOCOL_REJECTED / stop`
- 路线：`MINIMAL_SAFETY_BOUNDARY / IMPLEMENTATION_LEVEL_GRAPH_VALIDATOR / SYNTHETIC_FIXTURES`

## 1. Owner 决定

Owner `justtodo123` 选择“实现级验证”路线：协议只冻结首次 1K dry-run 的安全边界、权限状态、必须存在的证据角色和不可越权条件；跨 artifact 的引用解析、摘要复算、计数复算、状态转换、成功/失败证据图和 observer 事件一致性，交由读取真实 artifact directory 的实现级 graph validator 机械验证。

本决定终止继续要求单对象 JSON Schema 在不读取引用目标 bytes 的前提下自证完整 artifact graph。该变化是验证职责分层，不是降低以下安全边界，也不推翻 v1/v2 的独立审查结论。

## 2. 历史冻结

以下对象及其审查记录继续保持原字节，不得就地改写：

- `m8-minimal-1k-dry-run-protocol-v1.md` 及 v1 schema、validator、S0 materials、worksheet 和拒绝记录；
- `m8-minimal-1k-dry-run-protocol-v2.md` 及 v2 schema、validator、S0 materials、worksheet 和拒绝记录；
- `draft-0.1` 至 `draft-0.11` 的全部协议、门禁、授权、identity、binding、audit 和失败记录。

v2 继续为 `S0_V2_REJECTED / S1_NOT_AUTHORIZED`。新路线不得解释为 v2 已通过、draft-0.11 P4，或对历史 finding 的撤销。

## 3. 获准起草的 v3 范围

允许另行创建新的 v3 协议、artifact role schema、graph validator、fixture generator、正负 fixture 和独立 S0 审查材料。v3 必须：

1. 冻结 SQLite linear exact 为 correctness oracle/fallback，LanceDB embedded exact/flat 为唯一候选；
2. 只覆盖 1,000 个 synthetic chunks、512 维 L2-normalized `float32` 预编码向量和固定 seed；
3. 冻结 S0、S1、S2、S3 的 actor、decision、allowed action 和前驱映射；
4. 让 graph validator 从显式 artifact directory 读取持久文件，不得只校验进程内自构造对象；
5. 解析 typed REF 到实际目标文件，复算 SHA-256、bytes、JSONL record count 和被引用对象角色；
6. 分别表达并验证合法成功图与 cleanup、observer、runtime、validation 失败图；
7. 强制 S2 `EVIDENCE_READY / request-s3` 引用 PASS validation 和 CLEANED cleanup receipt；
8. 使用 closed observer event schema 验证 network、write/process/redaction 事件与摘要；
9. 固定 deterministic workload、query/gold、排序、浮点序列化和 canonical JSONL 算法；
10. 提供完整 S0→S3 fixture 以及覆盖 v2 十三项 finding 的 fail-closed 负例。

JSON Schema 只负责单文件结构、枚举和局部约束；凡依赖其他文件 bytes、目录集合或事件聚合的约束，必须在协议中明确归属于 graph validator，并由持久 fixture 证明。

## 4. S0 接受标准

独立 S0 reviewer 应分别审查：

- 协议中的安全边界是否闭合且无组合不可满足；
- 单文件 schema 与 graph validator 的职责边界是否明确；
- graph validator 是否读取真实目录并拒绝断链、错型、错摘要、错计数、非法 gate、缺失 authority 和非法失败闭环；
- fixture 是否包含至少一条完整成功图，以及 cleanup、observer、runtime、validation 四类失败图；
- validator 的正负例结果是否可在不安装 LanceDB、不生成真实 1K 输入、不创建实验根的条件下重放。

S0 只评审协议、schema、validator 和 synthetic fixture harness，不接受或拒绝任何真实 SQLite/LanceDB 运行结果。

## 5. 继续禁止的事项

在独立 S0 接受且 owner 另行签发 S1 前，仍不得：

- 创建真实 experiment identity、实验临时根或 venv；
- 获取或安装 LanceDB；
- 生成真实 1K corpus、向量、query 或 gold；
- 执行 SQLite 或 LanceDB dry-run；
- 准备或执行 10K/100K；
- 引入 Qdrant、ANN、真实资料、生产 adapter、迁移或 cutover；
- 选择默认后端、修改生产路径或批准 M8 admission。

用于验证 validator 自身的微型 synthetic fixture 必须位于仓库测试材料范围内，不得伪装成真实 1K evidence，不得包含真实资料，也不得产生 S1 或 S2 权限。

M8 继续 `BLOCKED / NOT_STARTED`。

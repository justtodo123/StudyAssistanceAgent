# M8 分层 dry-run 治理路线变更决定

- 日期：2026-09-14
- 决策人：`justtodo123`（owner）
- 状态：`APPROVED_FOR_MINIMAL_PROTOCOL_DRAFTING / NOT_EXECUTION_AUTHORIZED`
- 旧链：`draft-0.11 P3 REJECTED / stop / NEVER_EXECUTED`
- 新路线：`MINIMAL_SAFETY_PROTOCOL / 1K_DRY_RUN / PROGRESSIVE_SCHEMA_FREEZE`

## 1. Owner 决定

Owner `justtodo123` 决定停止追求“一次性完全形式化 P0→P9”，改为：

1. 起草仅覆盖首次 1K dry-run 的最小安全协议；
2. 以 `sqlite-linear-exact` 为 correctness oracle 和 fallback；
3. 以 `lancedb-embedded-exact-flat` 为唯一候选；
4. 两者使用同一份 1K synthetic corpus、预编码向量、query、gold 与 filter；
5. 根据 1K 真实产物逐层冻结后续 schema，而不是预定义 10K/100K 的完整 evidence universe。

本决定吸收 owner 的两项明确选择：

- 首次 1K 使用固定 seed 的合成预编码向量；
- 1K 成功只形成证据，不自动授权准备或执行 10K。

## 2. 冻结旧链

`draft-0.1` 至 `draft-0.11` 及其 authorization、gate、identity、binding、audit 和校验记录继续作为不可改写历史。
`draft-0.11` 的最终结论保持 `P3 REJECTED / stop`，不得创建或解释为其 P4，也不得复用其 experiment identity、
P1/P2/P3 或 repository binding。

路线变更不推翻旧审计 findings，不把旧链改判为通过，也不允许通过别名、补充说明或新校验器绕过冻结阻断。

## 3. 最小安全协议边界

获准起草的新协议只能覆盖：

- 1,000 个 synthetic chunks；
- 512 维 `float32`、L2-normalized、固定 seed 预编码向量；
- SQLite linear exact 与 LanceDB embedded exact/flat；
- 同一 canonical input manifest；
- build、query、filter、no-hit、close/reopen、结果机械比较和隔离清理；
- 全新 experiment identity、clean commit、依赖版本、隔离临时根和 measured-run 无网络；
- input manifest、run report、validation report、cleanup receipt 与四步 S0–S3 决策记录。

明确排除：Qdrant、ANN、10K/100K、真实资料、生产 adapter、迁移/cutover、默认后端切换、M8 admission、M9/M10。

## 4. 四步门禁

- `S0`：独立 reviewer 接受最小协议文字；
- `S1`：owner 冻结全新 identity、commit、配置与仅限 1K 的执行权限；
- `S2`：执行并机械验证 SQLite/LanceDB 1K dry-run；
- `S3`：独立 reviewer 接受或拒绝 1K evidence。

任一步失败即停止当前 experiment。纠正必须使用新的 experiment ID 和并行记录，不得改写失败记录。

## 5. 当前授权与禁止

本决定只授权起草最小安全协议、对应 schema、实例生成器、正负例 validator 和 S0 空白审查材料。

在独立 S0 接受且 owner 另行签发 S1 前，不得：

- 创建实验临时根或 venv；
- 获取或安装 LanceDB 依赖；
- 生成 1K corpus、向量、query 或 gold；
- 运行 SQLite/LanceDB dry-run；
- 自动准备或执行 10K；
- 选择后端、修改生产代码、改变默认路径或准入 M8。

M8 继续为 `BLOCKED / NOT_STARTED`。

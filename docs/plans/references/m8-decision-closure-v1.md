# M8 八项 Decision 单一政策批准记录 v1

> 状态：`APPROVED / EIGHT_DECISIONS_RESOLVED`
>
> 范围依据：[`m8-m12-scope-decision-v1.md`](m8-m12-scope-decision-v1.md)。本文提供八项 Decision 的逐项审阅材料，
> 本文记录负责人于 2026-09-10 对 D1–D8 的逐项明确批准。该批准关闭八项 Decision，但不选择后端，
> 不授权 V13、M8 admission 或生产实现；权威状态须按本文同步到阶段计划与门禁。

## 0. 共同不变量

1. SQLite/M7 Registry 是 source owner、授权、revision、generation、snapshot、lifecycle、tombstone、hard-delete receipt、provenance 和审计历史的唯一权威。
2. 专业后端仅为从已批准 immutable manifest 可重建的数据面；不得成为学习状态、session、review history 或授权权威。
3. 默认本地离线 profile 必须在无网络、无云端、无专业可选依赖时继续启动并保留既有学习闭环。
4. 当前 embedding 基线为 `BAAI/bge-small-zh-v1.5 / 512 / float32 / L2 normalized`；每个 generation 必须绑定 model revision、dimension、dtype、normalization、chunk policy 与 fingerprint。
5. `100K` 指 100,000 个可检索 chunks。M8 的 100K 是 synthetic/半合成容量证据，不是 100K 真实语料质量声明。
6. SQLite linear cosine 保留为 correctness oracle/fallback；LanceDB 仅为单机第一评估候选；Qdrant 仅为云端/常驻服务条件候选；Milvus 当前不采用。
7. 所有 Decision 在负责人和独立批准人填写完整字段前保持 `OPEN`。

---

## D1 — `M8-CONTROL-SCHEMA`

- **当前状态**：`RESOLVED / APPROVED`
- **支撑证据**：`docs/PLAN.md` M7/M8 边界；`m7-source-lifecycle-plan.md` 的 registry、generation、delete 与 provenance 合同；本文件共同不变量。
- **唯一政策值**：`SQLITE_M7_AUTHORITATIVE_CONTROL_PLANE__REBUILDABLE_SPECIALIZED_DATA_PLANE`
- **政策内容**：SQLite/M7 Registry 独占控制面写入；候选索引仅接受版本化不可变发布包。索引绑定 `source-set + revision + generation + snapshot + identity-set digest + schema version + embedding fingerprint`；缺失或不匹配即拒绝加载/查询。candidate 在隔离目录构建并通过 count、identity、metadata、integrity、deletion 校验后才能原子发布。
- **默认值与覆盖**：默认 SQLite/BM25 + SQLite linear；仅经 M8 批准的 opt-in profile 可切换数据面，不允许请求级任意覆盖。
- **复核条件**：control schema、embedding profile、授权模型、删除语义或多用户需求变化。
- **撤销条件**：专业索引成为唯一权威；无法从 manifest 重建；无法证明 owner/generation/deletion；出现 stale/cross-owner 结果。
- **责任人**：`justtodo123`
- **决定日期**：`2026-09-10`
- **独立批准人/日期/引用**：`justtodo123 / 2026-09-10 / 本会话对 D1–D8 的逐项明确批准`

## D2 — `M8-MIGRATION`

- **当前状态**：`RESOLVED / APPROVED`
- **支撑证据**：M7 immutable revision/generation/last-good 合同；V8–V12 失败治理中对 partial、rollback、receipt 的要求。
- **唯一政策值**：`FROZEN_EXPORT__ISOLATED_BUILD__VALIDATE__SHADOW_READ__MANUAL_CUTOVER`
- **政策内容**：迁移仅按“冻结导出 → 独立构建 → 完整校验 → shadow read → 人工 cutover”执行，禁止原地 destructive migration。cutover 只指向已发布 candidate，并记录 receipt、旧 last-good 与回滚点；失败保持 last-good 或 fail closed。
- **默认值与覆盖**：默认不迁移；只有负责人批准的 generation 可进入 shadow/cutover。
- **复核条件**：后端、schema、embedding profile、数据规模层或部署 profile 改变。
- **撤销条件**：无完整 manifest/identity 校验；无法原子切换；回滚依赖损坏索引；出现 partial visibility。
- **责任人**：`justtodo123`
- **决定日期**：`2026-09-10`
- **独立批准人/日期/引用**：`justtodo123 / 2026-09-10 / 本会话对 D1–D8 的逐项明确批准`

## D3 — `M8-LANCEDB-CRITERIA`

- **当前状态**：`RESOLVED / APPROVED`
- **支撑证据**：local-first 产品约束；当前 8C/16T、15.19 GiB RAM、D 盘约 117.9 GiB 可用的单机事实；M8 既有 1K/3K/10K benchmark 设计与新 100K capacity 目标。
- **唯一政策值**：`PRIMARY_LOCAL_SPECIALIZED_CANDIDATE__OPT_IN_ONLY_AFTER_ALL_HARD_GATES`
- **政策内容**：LanceDB 是 10K–100K 单机嵌入式第一评估候选，但不是预选后端。必须通过 Windows/离线安装、版本和许可证、1K correctness、10K single-user、100K capacity/filter、parity、lifecycle、reopen/corruption、rollback、fallback、RSS/磁盘/延迟全部硬门槛，并由负责人单独书面采纳后，才可成为 opt-in 数据面。
- **默认值与覆盖**：默认仍为 SQLite 路径；任一硬门槛失败即“不采用”，不得用综合平均分抵销。
- **复核条件**：LanceDB 版本/许可证/ABI、CPython、Windows 支持、100K 预算或 embedding profile 变化。
- **撤销条件**：破坏离线默认；无法稳定安装/恢复/删除；资源超预算；parity 或生命周期失败。
- **责任人**：`justtodo123`
- **决定日期**：`2026-09-10`
- **独立批准人/日期/引用**：`justtodo123 / 2026-09-10 / 本会话对 D1–D8 的逐项明确批准`

## D4 — `M8-QDRANT-CRITERIA`

- **当前状态**：`RESOLVED / APPROVED`
- **支撑证据**：当前单机离线默认；拟议 M12 可选云端单用户 profile；Qdrant 服务模式需要常驻进程、网络和运维边界。
- **唯一政策值**：`NOT_A_LOCAL_DEFAULT__CLOUD_OR_SERVICE_TRIGGERED_CANDIDATE_ONLY`
- **政策内容**：M8 不选择 Qdrant 作为本地默认，也不启动 Qdrant server/container/listener。只有进入 M12 可选云端 profile，或出现常驻服务、多进程共享、明确并发/远程需求并经新决策批准后，才评估 Qdrant；local client 证据不能自动批准 server 部署。
- **默认值与覆盖**：本地默认禁用；不得因 benchmark 更快自动启用。
- **复核条件**：批准云端部署、多进程共享、持续并发、远程访问或 100K+ 实际规模。
- **撤销条件**：服务不可达破坏学习路径；持久化/恢复/安全/成本不达标；本地私人资料被默认上传。
- **责任人**：`justtodo123`
- **决定日期**：`2026-09-10`
- **独立批准人/日期/引用**：`justtodo123 / 2026-09-10 / 本会话对 D1–D8 的逐项明确批准`

## D5 — `M8-BACKEND-PARITY`

- **当前状态**：`RESOLVED / APPROVED`
- **支撑证据**：M7 RetrievalIndex、owner/source/generation/delete 合同；V12 FAIL 对 tombstone/hard-delete before/after 机械证据的要求。
- **唯一政策值**：`ZERO_TOLERANCE_IDENTITY_AUTH_LIFECYCLE__FROZEN_SCORE_ORDER_TOLERANCE`
- **政策内容**：SQLite oracle 与候选后端在 owner/source、generation/snapshot、identity-set、filter、tombstone、hard-delete、publish/reopen、错误 taxonomy 上零容差一致。score/排序只能在预先冻结容差内差异，并用稳定 chunk ID 消除未定义 tie。删除测试必须有 before/after oracle 和 reopen 证据。
- **默认值与覆盖**：无法证明等价的后端不可用，不允许功能降级掩盖 parity 失败。
- **复核条件**：查询协议、filter、score normalization、schema、后端或 embedding profile 变化。
- **撤销条件**：跨 owner、stale generation、已删除结果、partial candidate 或错误映射不一致。
- **责任人**：`justtodo123`
- **决定日期**：`2026-09-10`
- **独立批准人/日期/引用**：`justtodo123 / 2026-09-10 / 本会话对 D1–D8 的逐项明确批准`

## D6 — `M8-FALLBACK`

- **当前状态**：`RESOLVED / APPROVED`
- **支撑证据**：M0–M7 默认离线与 fail-closed 基线；M7 user-source 授权和删除语义。
- **唯一政策值**：`DEFAULT_PACK_SQLITE_BM25_FALLBACK__USER_SOURCE_FAIL_CLOSED`
- **政策内容**：可选依赖缺失、索引损坏、manifest 不匹配、迁移未完成或服务不可达时，默认知识包回退 SQLite/BM25；user-source 若无法证明授权、generation、snapshot、identity-set 或删除状态则拒绝，不返回 stale 数据。恢复只从 SQLite 当前权威 manifest 重建。
- **默认值与覆盖**：禁止把 user-source 静默回退到旧索引；错误不得泄露路径、正文、凭据或后端原始错误。
- **复核条件**：默认 pack/user-source 边界、授权、缓存、云端 profile 或后端错误模型变化。
- **撤销条件**：fallback 返回 stale/cross-owner 数据；损坏索引反向修复控制面；无网络时默认知识包不可用。
- **责任人**：`justtodo123`
- **决定日期**：`2026-09-10`
- **独立批准人/日期/引用**：`justtodo123 / 2026-09-10 / 本会话对 D1–D8 的逐项明确批准`

## D7 — `M8-DEPENDENCY-PACKAGING`

- **当前状态**：`RESOLVED / APPROVED`
- **支撑证据**：默认安装零专业后端依赖；M7 精确 CPython/依赖冻结经验；拟议 local/cloud profile 分离。
- **唯一政策值**：`ISOLATED_OPTIONAL_EXTRAS__NO_MANDATORY_SERVICE_OR_NETWORK`
- **政策内容**：LanceDB 作为独立 optional extra，精确锁版本并提供许可证、Windows/CPython、离线 wheel/cache、升级/卸载说明；默认安装不新增强制依赖。Qdrant server 不进入本地默认安装，只能在未来 M12 云端 profile 单独打包。
- **默认值与覆盖**：依赖缺失、ABI 冲突、升级失败或服务不可达不得半启用，触发 D6。
- **复核条件**：CPython、OS、后端版本/许可证、安装包体积、云服务器环境或供应链政策变化。
- **撤销条件**：默认安装必须联网/常驻服务；依赖冲突污染核心环境；无法锁定或审计许可证。
- **责任人**：`justtodo123`
- **决定日期**：`2026-09-10`
- **独立批准人/日期/引用**：`justtodo123 / 2026-09-10 / 本会话对 D1–D8 的逐项明确批准`

## D8 — `M8-BENCHMARK`

- **当前状态**：`RESOLVED / APPROVED`
- **支撑证据**：`docs/baselines.md` 当前 682/1K 基线；`data-expansion-runbook.md` 3K/10K 目标；M8 历史 benchmark 设计；范围决策中的 100K capacity 与 M11 10K production 分离。
- **唯一政策值**：`1K_CORRECTNESS__10K_SINGLE_USER__100K_CAPACITY_FILTERED__OPTIONAL_CONCURRENCY`
- **政策内容**：
  - `1k-correctness`：SQLite oracle、完整 lifecycle/parity；
  - `10k-single-user`：本地单用户 build/incremental/query/reopen/delete 和资源；
  - `100k-capacity`：固定 seed synthetic/半合成容量、资源、恢复；
  - `100k-filtered`：owner/source/generation/snapshot/tombstone 分布与 filter；
  - `100k-concurrent`：仅负责人确认需要判断服务化时才执行。
  固定 corpus/seed/query/gold/top-k/filter/profile/environment；至少记录 Recall@3/5、MRR、no-hit、identity/filter correctness、p50/p95/p99、build/rebuild/incremental/reopen、RSS、磁盘、删除传播、recovery 和 fallback。硬门槛失败即候选不采用；benchmark 只形成决策输入，不自动选后端。
- **默认值与覆盖**：100K synthetic 不能声称真实语料质量；M11 的 10K production 必须使用独立真实数据 Gate。
- **复核条件**：目标规模、硬件、embedding profile、并发需求、候选后端或真实语料分布变化。
- **撤销条件**：阈值看结果后修改；库存/摘要/环境不可重现；synthetic 冒充生产质量；网络/路径/cleanup/terminal 证据不可验证。
- **责任人**：`justtodo123`
- **决定日期**：`2026-09-10`
- **独立批准人/日期/引用**：`justtodo123 / 2026-09-10 / 本会话对 D1–D8 的逐项明确批准`

---

## 9. 逐项负责人审批表

| Decision | 唯一政策值 | 负责人结论 | 责任人 | 日期 | 独立批准信息 | 最终状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `M8-CONTROL-SCHEMA` | `SQLITE_M7_AUTHORITATIVE_CONTROL_PLANE__REBUILDABLE_SPECIALIZED_DATA_PLANE` | `APPROVED` | `justtodo123` | `2026-09-10` | `justtodo123 / 2026-09-10 / 本会话逐项批准` | `RESOLVED` |
| `M8-MIGRATION` | `FROZEN_EXPORT__ISOLATED_BUILD__VALIDATE__SHADOW_READ__MANUAL_CUTOVER` | `APPROVED` | `justtodo123` | `2026-09-10` | `justtodo123 / 2026-09-10 / 本会话逐项批准` | `RESOLVED` |
| `M8-LANCEDB-CRITERIA` | `PRIMARY_LOCAL_SPECIALIZED_CANDIDATE__OPT_IN_ONLY_AFTER_ALL_HARD_GATES` | `APPROVED` | `justtodo123` | `2026-09-10` | `justtodo123 / 2026-09-10 / 本会话逐项批准` | `RESOLVED` |
| `M8-QDRANT-CRITERIA` | `NOT_A_LOCAL_DEFAULT__CLOUD_OR_SERVICE_TRIGGERED_CANDIDATE_ONLY` | `APPROVED` | `justtodo123` | `2026-09-10` | `justtodo123 / 2026-09-10 / 本会话逐项批准` | `RESOLVED` |
| `M8-BACKEND-PARITY` | `ZERO_TOLERANCE_IDENTITY_AUTH_LIFECYCLE__FROZEN_SCORE_ORDER_TOLERANCE` | `APPROVED` | `justtodo123` | `2026-09-10` | `justtodo123 / 2026-09-10 / 本会话逐项批准` | `RESOLVED` |
| `M8-FALLBACK` | `DEFAULT_PACK_SQLITE_BM25_FALLBACK__USER_SOURCE_FAIL_CLOSED` | `APPROVED` | `justtodo123` | `2026-09-10` | `justtodo123 / 2026-09-10 / 本会话逐项批准` | `RESOLVED` |
| `M8-DEPENDENCY-PACKAGING` | `ISOLATED_OPTIONAL_EXTRAS__NO_MANDATORY_SERVICE_OR_NETWORK` | `APPROVED` | `justtodo123` | `2026-09-10` | `justtodo123 / 2026-09-10 / 本会话逐项批准` | `RESOLVED` |
| `M8-BENCHMARK` | `1K_CORRECTNESS__10K_SINGLE_USER__100K_CAPACITY_FILTERED__OPTIONAL_CONCURRENCY` | `APPROVED` | `justtodo123` | `2026-09-10` | `justtodo123 / 2026-09-10 / 本会话逐项批准` | `RESOLVED` |

## 10. 批准结果与剩余边界

负责人 `justtodo123` 已于 2026-09-10 对 D1–D8 逐项明确批准；独立批准人同为 `justtodo123`，批准引用为
“本会话对 D1–D8 的逐项明确批准”。八项 Decision 均为 `RESOLVED`。

该批准仅关闭政策 Decision，剩余边界不变：

- M8：继续 `BLOCKED / NOT_STARTED`，尚未取得阶段 admission；
- backend selection：未选择；LanceDB 只是第一评估候选，Qdrant 只是条件候选；
- V13：已处置为 `SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`，不得恢复；
- M11/M12：拟议阶段，未准入；
- 不授权创建旧 V13 根、安装候选依赖、运行 benchmark 或开始生产实现。

八项政策已同步到 `m8-specialized-storage-plan.md`、`stage-admission-gates.json` 和 `docs/PLAN.md`；同步本身仍不构成
M8 admission。后续若需实证，须使用全新协议身份并另行取得分阶段授权。

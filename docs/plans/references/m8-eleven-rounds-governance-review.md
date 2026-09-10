# M8 十一轮治理复盘（V1–V11）

> 记录日期：2026-09-09
> 适用范围：`docs/plans/m8-specialized-storage-plan.md` 中 `sa.m8.admission-evidence.v1` 至 `.v11` 的准入治理过程
> 地位：**辅助复盘，不是计划依据，也不构成任何阶段授权**。最终依据是 [`docs/PLAN.md`](../../PLAN.md) 与
> [`docs/plans/m8-specialized-storage-plan.md`](../m8-specialized-storage-plan.md)。
> 结论只针对 V1–V11 已记录的失败处置；V12 仅作为报告形成时的后继状态附注，不计入本复盘的十一轮结论。
> 文中的 Decision `OPEN` 均是截至 2026-09-09 本报告形成时的历史状态；2026-09-10 后续状态见第 6.1 节。

## 1. 背景与总览

M8 的目标是在 SQLite linear baseline 之外评估 LanceDB embedded 与 Qdrant Client local mode，
形成 `M8-BENCHMARK` 等八项强制决策的人工 decision input。治理过程通过**逐轮递增的
admission-protocol** 推进，各轮均有独立 experiment ID 及不同程度的治理记录，但独立静态审阅、书面授权和终态
标签并非每轮完全相同：V9 与 V10 的记录明确为 `NOT_AUTHORIZED`，V4 使用 `ABORTED/INVALID`、V5 使用
`INVALID/GATE_FAILED` 等复合历史标签。因此，下文按各轮实际记录描述，不将这些共性或概括性模式视为统一授权、
统一审计或严格唯一终态，也不构成任何阶段授权。

**总体状态（截至本报告形成时）**：V1–V12 全部以失败终态关闭；V11 已处置为
`PRE_SOURCE_PROVENANCE_INVALID`。后继 V12 完成阶段 1 source freeze 后，独立静态审计于
`2026-09-09T12:12:34Z` 判定 `FAIL`，V12 已以 `INDEPENDENT_STATIC_AUDIT_FAILED` 永久封口且不可复用。
本报告形成时 M8 始终保持 `BLOCKED / NOT_STARTED`，八项 Decision 全部 `OPEN`，无后端选择、无准入、无生产授权。

失败性质呈现清晰的三阶段演进：

- **V1–V2：结果/数值层面**（corpus 结构、统计口径、环境版本）
- **V3–V6：运行健壮性与资源/语义层面**（报告写出、采样协议、磁盘占用、磁盘预算建模）
- **V7–V11：流程纪律与源码完整性层面**（执行顺序、自引用公式、provenance、实现质量、治理纪律）

## 2. 逐轮失败原因总表

| 轮次 | 协议 | 终态 | 失败原因 | 是否克服上一轮 | 本轮新错误 |
|---|---|---|---|---|---|
| V1 | `precommit-v1` | `INVALID` | ① corpus 结构错误：`source_for()` 把 1k/10k 都压成 3 namespace，偏离冻结的 `1×1000` / `10×1000`；② no-hit 计入 overlap，致 SQLite 自身 aggregate overlap 仅 `0.75`，parity 机械失败；③ fault probe 未完整实现 | — | 定义不精确 + 实现未对齐冻结配置 |
| V2 | — | `INVALID` | 报告环境为 CPython **3.13.3**，偏离冻结的 3.11.9 | 是（修正 corpus、empty-result parity、harness 级 fault probes） | 环境版本漂移：用了错误解释器 |
| V3 | `precommit-v3` | `INVALID` | 错误读取 `qdrant_client.__version__`，写出报告前崩溃、无 raw report；未实现 `5+20` 采样；probe 与 gate 未实际执行 | 是（回到 3.11.9，依赖版本一致） | 健壮性差（靠包 `__version__`）+ 协议只实现到“能跑完 loop” |
| V4 | `precommit-v4` | `ABORTED`/`INVALID` | 未产出 report/publication；lifecycle 未逐样本删实例致临时根涨到 ~7 GiB 被人工停止；stale_generation/snapshot 实际全被判定为 `stale_manifest`；tombstone/hard-delete 用“不存在的 owner”空结果冒充真实语义 | 是（精确 Recall/overlap/lifecycle 口径；版本改从安装元数据读取） | 资源控制缺失（无 per-sample 清理）；probe 分类不精确 |
| V5 | `precommit-v5` | `INVALID/GATE_FAILED` | latency 16/24、lifecycle 6/18、median_drift 33/36，`overall_pass=false`；根因是 smoke 极小样本下固定开销相对 SQLite 亚毫秒基线占主导 | 是（per-sample 清理、11 个可判别 fixture、真实 tombstone/hard-delete、两阶段唯一终态 publication；66/66 probe 通过） | 性能门禁统计口径在缩减样本下不合理（后被 3.20 人工校准修正） |
| V6 | `precommit-v6` | `ABORTED` | preflight 阶段 `DISK_PREFLIGHT_FAILED`；固定 512 MiB reserve 反推 root cap 仅 786.9 MiB，venv/package footprint 即超预算 | 是（3.20 校准：smoke 不再裁决相对性能门禁） | 磁盘预算建模错误：512 MiB reserve 过小，未给包解压留足余量 |
| V7 | `precommit-v7` | `INVALID` | ① 执行顺序颠倒：harness 独立静态 PASS **前**已建 venv 并开始 acquisition；② 依赖门禁 `package_footprint_cap = measured+64MiB` 是自引用公式，机械恒真、无法失败 | 是（双门禁磁盘模型，reserve 扩到 ~1.8–2.3 GiB，解决 V6 根因） | 流程纪律失控（该等审计却先装依赖）+ 公式逻辑缺陷 |
| V8 | `precommit-v8` | `INVALID` | 独立审计前临时根出现 CPython **3.12** bytecode（`acquisition-preflight.cpython-312.pyc`）；三个源码 SHA-256 随后变化，inventory/gate 失去 freshness；gate 未签名、auditor 字段为空；同身份下另有两个不完整根 | 是（去自引用 `PACKAGE_FOOTPRINT_CAP=1GiB` 绝对常量；执行顺序固化为不可颠倒 hard gate；协议静态审阅 `PASS`） | **source-only provenance 失败**：bytecode 污染 + 源文件被改动 |
| V9 | `precommit-v9` | `PRE_FREEZE_STATIC_AUDIT_FAILED` | source freeze 前作者侧只读复核发现 8+ 类阻断缺陷：非 canonical LF JSON、目录创建顺序不安全、inventory 缺相对路径/file type/byte size、gate 先于 audit record、containment 检查不全、DNS guard 不全、fixture 物理语义未成 success gate、cleanup receipt 缺绑定与 self-digest、serializer 未拒 NaN/Infinity、V8 digest 合同定义不完整 | 部分（草案纳入 source-only manifest/inventory 要求，针对 V8 provenance） | **实现质量缺陷**：协议要求与实际 harness 源码存在鸿沟，靠作者侧复核拦截 |
| V10 | `precommit-v10` | `PRE_SOURCE_GOVERNANCE_INVALID` | 治理记录明确禁止建根期间仍错误建根；`root-provenance.json` 的 `allowed_artifact_prefixes` 只含自身、未允许未来 source artifact | 是（§4 把 V9 各类缺陷固化为硬门禁：canonical JSON、O_EXCL、containment、fail-closed 等） | **治理纪律失守**：未获授权先建根 + marker allowlist 设计不完整 |
| V11 | `precommit-v11` | `PRE_SOURCE_PROVENANCE_INVALID` | 阶段 1 授权后写入的首个 marker 初始 allowlist 遗漏 source manifest 与 source-generation inventory，且 marker 无末尾 LF；source 写入前永久封口 | 部分：书面授权、随机根与 marker-first 顺序已落实，但 marker 自身未覆盖完整九文件身份且不满足 canonical LF 合同 | **首个证据身份即失效**：allowlist 不完整 + canonical bytes 不合格 |

## 3. 逐轮失败原因详述

### V1 — 无效（`INVALID`）

- `source_for()` 将 `1k-single` 与 `10k-capacity` 都限制为三个 source namespace，分别偏离冻结的
  `1 × 1,000` 与 `10 × 1,000` 结构；
- top-5 overlap 把 50 个预期为空的 no-hit query 计为零，导致即使 SQLite canonical baseline 的 aggregate
  overlap 也仅 `0.75`，所有 parity gate 机械失败；
- harness 未实现冻结表中全部 required-metadata、stale generation/snapshot、partial/unpublished、reopen、
  last-good/rollback fault probe。

### V2 — 无效（`INVALID`）

随后一次修正 corpus、empty-result parity 与 harness 级 fault probes 的临时尝试，九个组合虽完成且无
workload error，但报告环境实际为 CPython **3.13.3**，偏离预定的 3.11.9，故整体无效。

### V3 — 无效（`INVALID`）

在获准 acquisition、唯一系统临时目录、CPython 3.11.9、冻结依赖版本一致的前提下启动；但 harness 在完成
measured backend loops 后因错误读取 `qdrant_client.__version__` 而在写出结构化报告前失败，未产生可审阅的
raw report。静态复核确认其未实现 `5 warmup + 20 measured` 的 build/rebuild/import/reopen 样本，也未实际
执行完整 fault probe 与 gate calculation。

### V4 — 中止且无效（`ABORTED`/`INVALID`）

完整 frozen run 未生成 `report.json` / `publication.json`。临时 harness 将每个 workload 的五类 lifecycle
各保留 `5+20` 个完整索引实例，且 `rebuild` 同时保留旧实例与 replacement，运行推进到 3k Qdrant query 前
临时根已增长到 ~7.0 GiB，偏离“样本结束即删除”要求，被人工停止。静态复核还发现 `stale_generation` /
`stale_snapshot` probe 只改 manifest 却没同步改 published pointer 的 manifest digest，实际拒绝原因是
`stale_manifest`；`tombstone` / `hard_delete` 复用了不存在 owner 的空结果，未对真实 tombstoned/deleted
identity 执行删除屏障验证。

### V5 — 证据有效但门禁未通过（`INVALID/GATE_FAILED`）

正确性与十一类 probe 全部通过（`66/66`），网络、清理、residual 均为 0；但 `latency` 16/24、
`lifecycle_latency` 6/18、`median_drift` 33/36，`overall_pass=false`。根因是极小 workload 与缩减采样的
smoke 中，固定启动、提交与 wrapper 开销相对 SQLite 亚毫秒基线占主导，不能反映候选质量或作为性能排名。

### V6 — 中止（`ABORTED`）

preflight 阶段 `DISK_PREFLIGHT_FAILED`。根因经 §3.21.11 归因：固定 `512 MiB` reserve 公式反推 root cap
仅 `786.9 MiB`，acquisition 后 venv/package 解压 footprint 已超预算，preflight 无法通过。

### V7 — 无效（`INVALID`）

两项独立根因（§3.21.13）：

1. **执行顺序违规**：冻结顺序要求“全新 harness → 独立静态审计 → 磁盘预算预检 → venv/acquisition → 版本
   自校验 → scaled smoke”；实际在取得独立静态 `PASS` 前已创建 venv 并开始依赖 acquisition，顺序颠倒破坏
   运行前置边界，不能事后补审恢复。
2. **自引用磁盘门禁**：`package_footprint_cap = measured_package_footprint + 64 MiB` 中被 gate 变量同时
   决定自身上限，非负 reserve 下 `measured ≤ cap` 机械恒真，不能形成可失败的预算门禁。

### V8 — 无效（`INVALID`，source-only provenance 失败）

实际临时根在独立 harness 静态审计完成前出现 CPython **3.12** bytecode（`__pycache__/acquisition-preflight
.cpython-312.pyc`），不再满足 source-only provenance；随后三个源码文件 SHA-256 变化，原 inventory 与
execution gate 未随源文件变化重新生成、失去 freshness，不能作为当前根的完整性证明。execution gate 同时为
`signed=false`、`static_audit_pass=false`、`auditor_independent=false`；同身份下另有两个不完整临时根。

### V9 — pre-freeze static-audit failure（不可复用）

source freeze 之前作者侧只读复核发现多类足以阻断 provenance / execution safety / evidence integrity /
correctness gate 的实质缺陷，包括：`frozen-config.json` 非 canonical LF JSON、`query_sample()` 目录创建
顺序不安全、source inventory 缺规范化相对路径/file type/byte size、gate 未绑定独立 audit record 与 release
authorization、root-wide symlink/reparse/containment 检查不完整、network guard 未覆盖全部 DNS/name-lookup
helper、invalid fixture 的 mutation rejection / last-good rollback / tombstone / hard-delete 物理语义未成为
success gate、cleanup receipt 缺完整绑定与 self-digest、failure publication 可能静默吞错、serializer 未显式
拒绝 NaN/Infinity、loaded evidence 缺统一递归 absolute-path rejection，以及 V8 predecessor digest 合同定义
不完整（未冻结 canonical payload 与 digest 值）。

### V10 — pre-source governance failure（不可复用）

临时根在治理记录仍明确禁止建根期间被错误创建；首个 `root-provenance.json` 的 `allowed_artifact_prefixes`
仅允许自身、未允许未来 source artifact。根内除首个 provenance marker 外未写入 source，未执行生成 Python、
preflight、venv、依赖获取、acquisition、smoke、full 或 benchmark，但已违反治理顺序，以唯一治理处置
`PRE_SOURCE_GOVERNANCE_INVALID` 封口。

### V11 — pre-source provenance failure（不可复用）

V11 曾取得仅限 root-provenance / source-authoring 的阶段 1 书面授权，并排他创建全新随机临时根。首个
`root-provenance.json` 的初始 `allowed_artifact_prefixes` 只覆盖 marker 与六个 source，遗漏阶段 1 必需的
`source-manifest.json` 与 `source-generation-inventory.json`；marker 原始 bytes 同时没有末尾 LF。该根在任何
source 写入前停止，未执行 generated Python、preflight、venv、依赖获取、acquisition、smoke、full 或 benchmark，
并以唯一终态 `PRE_SOURCE_PROVENANCE_INVALID` 永久封口。V11 的身份、根、source、hash、inventory 与其他
artifact 均不得修复、恢复、补审、重跑或复用。

## 4. 下一轮是否克服了上一轮失败

逐轮看，后继轮次**通常会在设计层尝试修正上一轮已识别的失败根因**，且常先做“失败归因”（如 §3.21.11 对
V6、§3.21.13 对 V7），再把修正映射进下一轮协议；但总表中的“是/部分”及各轮新增错误表明，这不是每轮均已
完整克服的绝对结论。V11 曾把 V9 的 8 类缺陷（§5.1–5.8）、V10 的 2 类违规（§3 顺序、§4 allowlist）与 V9 的
digest 合同缺陷（§5.10）显式列为规避项，但其首个 marker 又暴露出阶段 1 完整文件集合未从初始身份中一次性冻结的问题。

V12 已在设计与作者侧阶段修正 V11 根因：全新 marker 的初始 allowlist 一次覆盖阶段 1 全部九个文件，并在任何
source 写入前立即验证无 BOM/CR、唯一末尾 LF、canonical-byte equality、self-digest、根仍仅含 marker，以及无
reparse/link。六个 source 随后重新实现并 source freeze。但独立静态审计最终判定 `FAIL`：tombstone/hard-delete
证据缺 before/after 对照、运行期缺 hard-link/ADS 门禁、失败路径缺机械可证明的 ABORTED/INVALID 终态（详见计划
§3.21.20）。V12 已永久封口且不可复用，从未进入 preflight 或执行。

## 5. 出现新错误的系统性原因

1. **治理深度逐层加深**。修复成功让检查下探到更底层、更严格的约束（数值正确性 → 运行健壮性 → 资源/语义
   → 流程纪律 → 源码完整性与实现规范）。约束更严，自然暴露前一约束层看不到的新问题。
2. **修复动作引入新复杂度，且新增机制自身不完善**。如 V7 为修 V6 磁盘预算引入的依赖门禁是自引用公式、
   自身不可失败；V10 的 `allowed_artifact_prefixes` marker 机制自身设计不完整。
3. **协议与执行/实现脱节（纪律问题）**。V7（审计前即 acquisition）、V8（审计前出现 bytecode、源文件被改）、
   V10（禁止建根却建根）与 V11（首个 marker 未满足自身冻结合同）均表明：协议文本与实际操作之间仍可能出现
   偏差。这是最反复出现的一类失败，说明必须把顺序、字节与完整文件集合都转为写入后立即验证的机械门禁。
4. **环境与 provenance 不可控**。V2（3.13.3 vs 3.11.9）、V8（`cpython-312.pyc`）暴露环境隔离与
   source-only provenance 未被彻底贯彻，旧解释器缓存、字节码、源文件改动污染了证据链。
5. **实现质量与协议要求存在固有差距**。V9 集中体现：协议把“应然”写得很严格，实际 harness 源码达不到要求，
   只能靠作者侧复核在 freeze 前拦截。V11 尝试把 V9 的每一项缺陷转为必须真实实现、可供独立审计的对象；V12
   修正了 V11 的证据身份缺陷，但独立静态审计又暴露四项机械门禁证据不足，V12 亦告失败。

## 6. 结论

- **12 轮全部未通过准入**（V1–V12）；截至本报告形成时，M8 仍 `BLOCKED / NOT_STARTED`，八项 Decision 保持 `OPEN`。
- 后继轮次通常会**在设计层尝试修正上一轮已识别的根因**，但逐轮结果包含“部分”克服及新增缺陷，不能概括为
  每轮均已完整克服。
- 执行或证据层持续暴露更深层的新错误，错误由“数值/结果”逐步上升到“过程纪律与源码完整性”，说明治理在
  向更高可信度标准收敛，而非原地打转。
- V11 已因 marker allowlist 与 canonical bytes 缺陷永久封口；V12 完成阶段 1 source freeze 后，独立静态审计
  判定 `FAIL`（四项机械门禁证据缺陷），V12 亦已永久封口且不可复用；无 preflight 或执行授权，任何后继实验
  须由负责人另行书面授权。

## 6.1 2026-09-10 后续状态

2026-09-10 后续治理快照将 M8 八项 Decision 逐项闭合为 `RESOLVED`，但 M8 仍为
`BLOCKED / NOT_STARTED`；未选择后端，未批准 admission，未授权生产实现。V12 的最终状态仍为
`INDEPENDENT_STATIC_AUDIT_FAILED`，V13 则为
`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`。本节仅说明后续状态，不改写本报告形成时的历史事实。

## 7. 引用来源

- [`docs/plans/m8-specialized-storage-plan.md`](../m8-specialized-storage-plan.md)（§3.10–§3.21.20 各轮冻结与处置）
- [`docs/plans/references/m8-v7-admission-protocol.md`](m8-v7-admission-protocol.md)
- [`docs/plans/references/m8-v8-admission-protocol.md`](m8-v8-admission-protocol.md)
- [`docs/plans/references/m8-v9-admission-protocol.md`](m8-v9-admission-protocol.md)
- [`docs/plans/references/m8-v10-admission-protocol.md`](m8-v10-admission-protocol.md)
- [`docs/plans/references/m8-v11-admission-protocol.md`](m8-v11-admission-protocol.md)
- [`docs/plans/references/m8-v12-admission-protocol.md`](m8-v12-admission-protocol.md)
- `docs/plans/references/` 下 V7–V12 authorization 记录（V7–V11 历史授权均已消费/失效；V12 仅阶段 1
  授权已消费）

---

> 说明：本报告的逐轮结论仅覆盖 V1–V11。V12 截至本报告形成时的后继状态仅用于避免把历史复盘误读为
> 现行授权；其独立审计与任何后续处置以主计划及 V12 专属记录为准。2026-09-10 后续状态见第 6.1 节。

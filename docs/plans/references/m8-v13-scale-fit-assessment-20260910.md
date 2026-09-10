# M8 V13 对 100K 新目标的适配评估

- 评估日期：2026-09-10
- 评估对象：`sa.m8.admission-evidence.v13` / `precommit-v13`
- 评估时状态：`DRAFT / NOT_AUTHORIZED / UNBOUND_DRAFT`（历史快照）
- 评估类型：只读协议适配分析；不是审计、binding、授权或执行
- 结论：**`NOT_FIT_AS_COMPLETE_M8_EVIDENCE_PROTOCOL`**

## 1. 结论摘要

现有 V13 的目标是修复 V12 的四项机械证据缺陷：tombstone before/after、hard-delete continuity、运行期
hard-link/ADS 门禁和失败终态/cleanup 闭合。其 S/A/G/E 分离治理拓扑可继续作为参考，但协议没有冻结重构后 M8
所需的 `1k-correctness`、`10k-single-user`、`100k-capacity`、`100k-filtered` workload，也没有冻结质量、资源、
构建、增量、恢复或可选并发的数值预算。

因此，V13 不能直接支持新的 `M8-BENCHMARK` 唯一政策值
`1K_CORRECTNESS__10K_SINGLE_USER__100K_CAPACITY_FILTERED__OPTIONAL_CONCURRENCY`，也不能作为完整 M8 实证协议。

## 2. 可保留内容

以下设计仍与新范围一致，可作为后继协议参考：

- repository binding 只绑定 immutable Git blob bytes；
- `S freeze → A independent audit PASS → release authorization → G gate → execution authorization → E` 分离授权；
- source/audit/gate/execution 四根隔离与单向 digest binding；
- canonical JSON、排他写入、exact set、link/reparse/hard-link/ADS 和 containment 门禁；
- tombstone 删除前可见性和删除后物理保留/逻辑不可见证据；
- hard-delete 删除前 oracle 和删除后连续性证据；
- 失败终态、cleanup、residual scan 和 fallback 机械闭合；
- synthetic-only、离线、禁止读取外部真实资料的证据边界。

## 3. 不适配项

1. **Decision 状态过时**：V13 写明八项 Decision `OPEN`；当前权威状态已是 2026-09-10 全部 `RESOLVED`。
2. **workload 缺失**：没有冻结 1K/10K/100K 的 Source/document/chunk 构成、query/gold、filter 分布和重复次数。
3. **100K 容量证据缺失**：没有 100K build/rebuild/incremental/reopen、RSS、磁盘、cleanup 与运行时间预算。
4. **100K filter 证据缺失**：没有 owner/source/generation/snapshot/tombstone 的规模分布和 filter correctness 门槛。
5. **质量协议缺失**：没有 Recall@3/5、MRR、no-hit、hard-negative、跨语言或 SQLite oracle 非劣性阈值。
6. **候选政策过时**：仍把 `qdrant-client-local` 与 LanceDB 并列为本地候选；新政策规定 Qdrant 非本地默认，仅为云端/
   服务化触发后的条件候选。
7. **embedding binding 不完整**：固定 512/float32/L2，但没有完整冻结 model revision、chunk-policy 和 embedding
   fingerprint，也未定义 profile 变化必须新 generation。
8. **实证职责混杂风险**：当前 V13 更适合验证 harness 机械完整性，不能同时自动承担完整 100K benchmark 和后端选择。

## 4. 建议处置

### 推荐方案

**不直接绑定或执行当前 V13。** 保持其 `DRAFT / NOT_AUTHORIZED / UNBOUND_DRAFT`，将其定位为“四项机械门禁修复
参考草案”。若负责人确认 M8 需要新实证，应先重写完整协议，再做文本审查和 repository binding。

由于新目标改变了 workload、候选范围、资源预算、embedding binding 和证据职责，建议启用**新的协议身份**，而不是
在未来授权时仍沿用 `precommit-v13`。新协议可继承 V13 的 S/A/G/E 治理设计，但必须重新冻结：

- 1K correctness、10K single-user、100K capacity/filter；
- SQLite oracle + LanceDB 第一候选；Qdrant 不参与本地默认选择；
- model/revision/dimension/dtype/normalization/chunk-policy/fingerprint；
- quality、resource、lifecycle、recovery、cleanup 和 terminal 门槛；
- smoke 与 full/capacity 的职责分离；
- 100K synthetic 不能产生真实语料质量结论；
- benchmark 只产生人工后端采纳输入，不自动选择或批准 M8。

### 不推荐方案

- 直接把现有 V13 commit/bind 后运行；
- 仅补一个 `100K` 常量而不重写 workload 和资源合同；
- 用 Qdrant local fixture 结果批准未来 Qdrant server；
- 把四项机械门禁 smoke 当成完整 100K benchmark；
- 一次性授权 S/A/G/E 全链。

## 5. 负责人待决事项

负责人需在以下两项中明确选择：

1. **需要新的 M8 实证协议**：永久停止当前 V13 的 binding/执行方向，创建全新协议身份，按新 100K 政策重写并重新接受
   文本审查、binding 和 S/A/G/E 分离授权；
2. **当前仅关闭政策 Decision，不立即做实证**：V13 保持未授权，M8 继续 `BLOCKED / NOT_STARTED`，后续在需要实际
   选择 LanceDB 时再启动新协议。

无论选择哪项，当前 V13 均不得创建根、安装依赖、运行 source、执行 preflight 或产生 M8 admission。

## 6. 2026-09-10 最终后续处置

负责人后续选择永久停止 V13 的 binding 和执行方向。V13 最终状态为
[`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`](m8-v13-disposition-20260910.md)：从未建立 repository
binding，从未创建 S/A/G/E 根，从未 author 或 freeze source，也从未运行 preflight、venv、dependency
acquisition、smoke、full 或 benchmark。第 4–5 节保留评估时的建议与待决选项，不再构成当前待办；任何后续 M8
实证只能使用全新协议身份。

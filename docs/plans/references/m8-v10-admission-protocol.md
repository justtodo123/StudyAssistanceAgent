# `precommit-v10` 新实验协议（治理准备，独立静态审计前停止）

- experiment ID：`sa.m8.admission-evidence.v10`
- protocol：`precommit-v10`
- 状态：**`PRE_SOURCE_GOVERNANCE_INVALID`；首次根创建违反治理顺序，根不可复用；未授权执行**
- 本文件是治理协议，不构成 preflight、acquisition、smoke、full 或 benchmark 授权。

## 1. 身份与前置处置

V8 已因 source-only provenance 失败以 `INVALID` 永久封口；V9 已在 source freeze 前的作者侧只读复核中
发现阻断缺陷，根同样永久冻结且不可复用。V10 只能引用仓库中的去敏处置 digest 作为 predecessor context，
不得读取、复制或复用 V8/V9 的 harness、venv、source、sample、index、report、inventory、receipt、publication、
bytecode、统计结果或任何临时根。V9 作者侧复核不是独立审计，也不产生可继承的 `PASS`。V10 predecessor
只允许绑定 V9 去敏处置 digest
`f0590baaf24a187db010539f8d5e2ebfbf19616cfc3cae43dd431202a8a16eb6`，不得绑定或继承 V9 root artifact。

## 2. 严格范围与禁止事项

- 仅允许合成预编码向量：`synthetic-unit-vector-v1`，seed `20260906`，512 维，`float32`，L2 归一化。
- 严禁读取、复制或索引 `D:\111_Others_Subjects`，严禁将其内容导入实验或仓库。
- 候选仅为 `sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`；Qdrant 只能使用本地 `path=`，
  不得启动 server、container、listener、网络服务或持久服务。
- 即使获得后续授权，范围最多为 `smoke-1s-32` 与 `smoke-2s-64` 的 scaled smoke；full、benchmark、性能排名、
  后端选择、Decision 关闭、M8 admission、生产实现、commit、merge、push 均不在本协议授权内。
- `SMOKE_NON_ADMISSION` 仅是原拟 smoke 成功终态，`INVALID` / `ABORTED` 仅是原拟运行失败终态；V10 未进入
  运行阶段，实际治理处置仅为 `PRE_SOURCE_GOVERNANCE_INVALID`，授权状态仅为 `NOT_AUTHORIZED`。

## 3. 已失效的 provenance 与门禁顺序（仅保留为失败上下文）

1. 未来有效尝试只有在形成明确书面阶段授权后，才可在 system-temp 中排他创建全新、不可预测的 V11 根，并首先写入
   canonical `root-provenance.json`；本 V10 根不得继续使用。
2. 从零生成并修复 source tree；首批仅允许协议列明的源码与配置文件。任何 `.pyc`、`.pyo`、`__pycache__`、
   venv、构建缓存、symlink、reparse point、根外路径、重复或未登记文件都立即 `INVALID`，不得清理后继续。
3. source freeze 前由作者侧进行只读复核；通过后独立生成 canonical source manifest/source-generation inventory，
   记录规范化相对路径、file type、byte size、SHA-256、experiment/protocol 和 records digest。
4. 独立审计者在未编写、未修复、未执行 harness 的前提下，独立重算 root/source/tree/harness/config/inventory
   hashes，核对网络、数据、路径、终态与 immutable-write 边界，并排他写入独立 audit record。
5. 只有独立 audit `PASS` 后，才可生成绑定该 audit record 的一次性 closed execution gate，并另行取得明确指向
   后继递增身份（当前为 `precommit-v11`，而非已永久失效的 V10）及 preflight 阶段的负责人书面授权和 release
   artifact；三者同时有效时，才可考虑 standard-library-only preflight。本协议当前不创建 gate 或 release artifact。
6. preflight、venv/acquisition、版本核对、smoke 和 cleanup 各自仍需对应的新增书面授权；独立 PASS 不自动授权任何
   后续阶段。

## 4. 实现与证据硬门禁

该 V10 协议原拟要求 source tree 使用 canonical UTF-8 JSON（LF 结尾、`allow_nan=False`）和
`O_CREAT | O_EXCL` 的排他不可变写入，不得 overwrite、truncate、rename-over-existing 或 check-then-replace。
本节仅保存未执行的设计上下文；不得复制为 V11 source 或将其视为已审计实现。
所有输入、输出和加载的 evidence 均须
递归拒绝 absolute path，并进行 lstat/reparse/resolved-containment 检查。network/DNS guard 必须在任何第三方
import 前安装并覆盖 socket construction、connect helpers 与 name lookup helpers。

每个 invalid fixture 必须在 publication 前被拒绝并保持 last-good generation；tombstone 必须证明物理保留而不可见，
hard delete 必须证明物理移除且剩余检索连续有效。cleanup receipt 必须包含完整上游绑定、峰值、零残留和 self-digest；
任何 cleanup、写入或 publication 失败都必须 fail closed，不得静默吞错或伪造成功终态。诊断 timing 不得参与正确性、
排序、后端选择或准入决定。

## 5. V10 pre-source governance failure disposition

在 V10 治理记录仍明确禁止创建实验根期间，错误创建了唯一临时根，并且首个 `root-provenance.json` 的
`allowed_artifact_prefixes` 仅包含自身，未允许后续 source artifact。该根因此违反治理顺序，且 marker allowlist
不足以支持后续 source authoring；没有证据表明已写入 allowlist 外 artifact。该根不得修复、补审、清理后继续、
重算、重判、恢复、重跑或复用。根内未写入 source，未执行生成 Python、preflight、
venv、依赖获取、acquisition、smoke、full 或 benchmark；该根仅作为失败上下文保留，不能产生任何可采纳证据。

该去敏处置的 canonical payload（无尾随换行）为：

```json
{"experiment_id":"sa.m8.admission-evidence.v10","generated_python_executed":false,"preflight_started":false,"protocol":"precommit-v10","root_reusable":false,"source_authored":false,"status":"PRE_SOURCE_GOVERNANCE_INVALID","violations":["root_created_while_governance_record_forbade_root_creation","root_marker_allowlist_omitted_future_source_artifacts"]}
```

其 SHA-256 为 `1a7043b78e51d293ba5e0d37a7e0bfc409b05f0ba7d0bfb20010dea34aa8d4e9`；该 digest 只绑定治理处置事实，
不是实验、审计、cleanup 或执行证据。V10 authorization 仍为 `NOT_AUTHORIZED`、未消费且不能授权任何后续动作。

下一次有效尝试必须递增为新的 experiment/protocol 身份，使用全新的不可预测系统临时根和全新 source tree，从
root provenance 重新开始。正确顺序是：先取得明确指向 V11 root-provenance/source-authoring 阶段的书面授权，
再创建根并从零生成、冻结 source tree；随后由未编写、未修复、未执行该 harness 的独立会话进行静态审计。
只有独立审计 `PASS` 后，才可另行申请 preflight；不得在此前创建 venv、获取依赖或执行 acquisition、smoke、
full、benchmark。
M8 继续保持 `BLOCKED / NOT_STARTED`，八项 Decision 继续为 `OPEN`。

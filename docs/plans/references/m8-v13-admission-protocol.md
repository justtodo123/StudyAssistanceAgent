# `precommit-v13` 协议：M8 阶段 1 source provenance 与运行证据门禁

- experiment ID：`sa.m8.admission-evidence.v13`
- protocol：`precommit-v13`
- 状态：**`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`（2026-09-10 永久停止）**
- 前置处置：V8、V9、V10、V11 永久封口；V12 因独立静态审计 `FAIL` 永久封口
- 最终状态权威：[`docs/PLAN.md`](../../PLAN.md)

本协议曾是 V12 失败后的后继草案，不是 V12 的修复提交或补审；现已由
[`m8-v13-disposition-20260910.md`](m8-v13-disposition-20260910.md) 永久停止，仅保留为历史、非操作性设计记录。
全文中所有关于未来 binding、授权、建根、source authoring、审计或执行的步骤均已失效，不得据此采取行动。
V12 的 root、nonce、source、manifest、inventory、digest、audit、运行目录和任何 artifact 均不得读取后复用、
复制、清理后继续或重判。V13 不得再取得授权，不得填充占位符、binding、修订、建根、执行生成 Python、
preflight、venv、依赖获取、smoke、full、benchmark、后端选择、M8 admission 或生产实现，也不得复用为后继协议。
任何后续 M8 实证必须使用全新协议身份并重新取得分阶段书面授权。本文件同样不授权 commit、merge 或 push。

## 0. Historical draft-only repository-binding design — permanently non-operational

V13 从未绑定到不可变仓库对象。以下值是必须永久保留的历史占位符，不是待推断或待填写值，也不得由工作区状态、
短 commit 或当前文件摘要替代：

| Binding field | Historical value | Original draft validation contract |
| --- | --- | --- |
| `final_repository_path` | `TBD_UNBOUND` | 最终、规范化、大小写精确的仓库相对 POSIX 路径 |
| `git_commit_revision` | `TBD_UNBOUND` | 包含冻结协议 blob 的完整 40 字符小写 immutable Git commit revision |
| `protocol_content_sha256` | `TBD_UNBOUND` | 指定 commit 中最终路径处原始 Git blob bytes 的 64 字符小写 SHA-256 |
| `binding_status` | `UNBOUND_DRAFT` | 只有独立的 owner-authorized binding record 经验证后才可记为 `BOUND` |

原草案曾规定未来绑定遵守以下规则；这些规则现仅保留为历史设计说明，不得用于绑定 V13：

1. 先把最终协议版本以 `final_repository_path` 写入一个不可变 Git commit；path 不得包含 `.`、`..`、反斜杠、
   绝对路径或大小写归一化后的替代拼写；revision 必须完整解析到唯一 commit，不能使用 branch、tag、`HEAD` 或短 SHA；
2. verifier 必须直接从 `git_commit_revision` 的 tree 读取 `final_repository_path` 对应 Git blob 的原始 bytes，重算
   `protocol_content_sha256`，并验证该 blob 仍声明 experiment ID `sa.m8.admission-evidence.v13`、protocol
   `precommit-v13` 和绑定前允许的非授权状态；不得对 working-tree bytes、checkout 后的 CRLF 转换结果或复制文件求摘要；
3. 真实 path、revision、digest、负责人、批准日期和批准引用只能写入未来单独的 owner-authorized binding record。
   该 record 不属于协议 blob 的 digest 输入，协议摘要也不得回写本文件后继续声称覆盖回写后的整份文件；
4. binding verifier 必须拒绝 path/revision/blob 不存在、tree entry 非 regular blob、字段格式错误、摘要不符、协议身份
   不符或 record 未获负责人明确批准的情况，并保持 `UNBOUND_DRAFT`；
5. 链接修复、Git commit、摘要计算、binding record 或 `BOUND` 都不授权创建 `S/A/G/E`、source authoring、
   preflight、执行、后端选择、Decision 关闭或 M8 admission。处于 `UNBOUND_DRAFT` 时不得创建任何 V13 root；完成
   binding 后仍必须取得后续每一步的独立书面授权。

本节只记录原草案的绑定算法。V13 已在任何授权、建根或 source freeze 前永久停止，不得再按 §6 修订、文本审计
或切换为 `BOUND`；任何后续实质方案都必须使用全新协议身份并重新开始治理链。

## 1. 目标、范围与不可变边界

V13 只建立一条可被独立会话审计的 M8 阶段 1 证据链，目标是修复 V12 报告的四个机械缺口：

1. tombstone 必须有删除前可见性基线，并证明删除后物理保留、逻辑不可见；
2. hard-delete 必须有删除前 oracle，并证明删除后剩余检索连续、完整、排序稳定；
3. 运行期每个文件必须同时通过 symlink/reparse、containment、hard-link 与 NTFS ADS 门禁；
4. 每条失败路径必须机械尝试生成失败终态、cleanup receipt 和 residual scan；任一 writer 失败必须留下协议规定的
   fallback 判定或被外部 verifier 归类为不可验证，且不得发布成功证据。

V13 仍保持 V12 的合成数据与离线边界：只允许 `synthetic-unit-vector-v1`、seed `20260906`、512 维
`float32` L2 归一化向量；严禁读取、复制或索引 `D:\111_Others_Subjects`。候选仍限于
`sqlite-linear`、`lancedb-embedded`、`qdrant-client-local`；Qdrant 只能使用本地 `path=`，不得启动
server、container、listener 或网络服务。M8 继续为 `BLOCKED / NOT_STARTED`；八项 Decision 已于 2026-09-10
`RESOLVED`，但该批准不恢复或授权本 V13 草案。

## 2. 四根拓扑、所有权与跨根绑定

V13 使用四个互不嵌套的全新随机根。四根都位于同一个已验证的 system-temp 父目录下，但 basename、nonce、
marker 和 allowlist 各自独立；任何后根不得写入、移动、删除或补充前根。V12 的目录即使当前为空也不可复用。

| Root ID | 创建者与前置授权 | 初始 marker | 冻结 exact set | 作用 |
| --- | --- | --- | --- | --- |
| `S` source-freeze root | source author；须先取得 root-provenance/source-authoring 授权 | `root-provenance.json` | marker、六个 source、manifest、inventory，共九个文件 | 唯一冻结 source 输入 |
| `A` audit root | 未参与 V13 authoring/repair/execution 的独立审计者；须先取得 audit-root 授权 | `audit-root-provenance.json` | marker + `independent-static-audit.json`，恰好两个文件 | 保存独立静态审计记录 |
| `G` gate root | 负责人授权的 release/gate 生成者；须已有独立 audit `PASS` 和书面 release authorization | `gate-root-provenance.json` | marker + `release-authorization.json` + `execution-gate.json`，恰好三个文件 | 保存唯一 immutable open gate |
| `E` execution root | 获得独立 execution 授权后的 launcher | `execution-root-provenance.json` | 按 §3.2 的阶段化集合变化 | 保存运行、cleanup 与终态证据 |

每个 marker 必须在该根为空时以 `O_CREAT | O_EXCL` 首次写入，完整列出本根所有可能文件名和允许的临时目录
prefix；marker 写入后立即完成 canonical bytes、self-digest、父链/根/文件 link、hard-link、ADS 和 containment
检查。根的绝对路径只允许在执行进程内用于 containment，不得进入跨根 evidence；跨根只记录 basename、nonce、
marker SHA-256 和规范化相对文件摘要。

跨根绑定形成单向无环链：

1. `A/independent-static-audit.json` 绑定 `S` 的 marker、source records、manifest 和 inventory digest；
2. `G/release-authorization.json` 明确引用 V13、`S` 与 `A` 的身份及 audit `PASS` digest；
3. `G` marker 表示 gate 尚未建立；`G/execution-gate.json` 是唯一 immutable open artifact，绑定 `S`、`A`、release
   authorization、自身 gate nonce 和一个预先生成但尚未建根的 `authorized_execution_nonce`。只有匹配该 nonce 的
   一个 `E` 可被采纳；观察到重复 nonce 的多个 execution root 时全部 `INVALID`；
4. `E/execution-root-provenance.json` 绑定 `S`、`A`、`G` 的 marker/record/gate digest 和本次 execution authorization；
5. 后根只能引用前根 digest，前根不得引用尚不存在的后根，也不得把 audit record 或 gate 追加到 `S`。

严格顺序为 `S freeze → A independent audit PASS → release authorization → G gate → execution authorization → E`。
任一步骤越序、跨根绑定缺失或前根 frozen exact set 改变，都使后续根 `INVALID`，不得清理后继续。

## 3. 阶段化 exact set 与字节合同

所有 JSON 均为 canonical UTF-8、`sort_keys=True`、固定 separators、恰好一个 LF、`allow_nan=False`，并递归拒绝
NaN、Infinity、绝对路径和根外路径。所有 evidence writer 均使用排他创建、完整写入循环、flush 和 fsync；已存在
文件不得 overwrite、truncate、rename-over-existing 或 check-then-replace。

### 3.1 Source、audit 与 gate 根

`S` 必须按以下集合单调推进：

- `S0`：空根；
- `S1`：仅 `root-provenance.json`；
- `S2`：`S1` + 六个 source；
- `S3`：`S2` + `source-manifest.json` + `source-generation-inventory.json`，恰好九个 regular files。

六个 source 固定为 `STATIC-AUDIT-CHECKLIST.md`、`acquisition-preflight.py`、`frozen-config.json`、
`precommit_v13_smoke.py`、`requirements.txt`、`run_smoke.py`。`S3` 不得有目录、bytecode、venv、cache、symlink、
reparse point、hard link、ADS 或未登记 artifact。

`A` 只能为 `A0` 空根、`A1` 仅 marker、`A2` marker + audit record；`G` 只能为 `G0` 空根、`G1` 仅 marker、
`G2` marker + release authorization、`G3` marker + release authorization + execution gate。任何跳级、额外文件、
提前出现的 audit/gate 文件或不符合 exact set 的目录都为 `INVALID`。

### 3.2 Execution 根总 allowlist 与阶段集合

`E` marker 的初始 allowlist 必须一次性列出：

- 永久证据文件：`execution-root-provenance.json`、`runtime-inventory.json`、`tombstone-probe.json`、
  `hard-delete-probe.json`、`failure-intent.json`、`residual-scan.json`、`cleanup-receipt.json`、`report.json`、
  `publication.json`、`terminal.json`、`terminal-fallback.json`；
- 临时数据 prefix：`runtime/`、`indexes/`、`cache/`、`venv/`、`logs/`。

总 allowlist 不是阶段许可。每次写文件前后都必须按下列集合验证；临时 prefix 下的实际文件必须与最近一次
runtime tree scan 的 exact set/digest 相等：

| 阶段 | 必须存在 | 必须不存在 |
| --- | --- | --- |
| `E0_PROVENANCE` | execution marker | inventory、probe、failure、cleanup、report、publication、terminal |
| `E1_RUNTIME` | `E0` + runtime inventory；临时数据可存在且被 inventory/scan 覆盖 | probe、failure、cleanup、report、publication、terminal |
| `E2_PROBES` | `E1` + 两个 probe；临时数据仍须 exact-match | failure、cleanup、report、publication、terminal |
| `E3_CLEAN` | `E2` + residual scan + cleanup receipt；临时数据为零 | failure、report、publication、terminal |
| `E4_REPORTED` | `E3` + 已自校验 report | failure、publication、terminal |
| `E5_PUBLICATION_READY` | `E4` + 已自校验 publication envelope | failure、terminal、fallback |
| `E6_SUCCESS` | `E5` + 唯一有效 `terminal.json` | failure-intent、terminal-fallback、全部临时数据 |

`publication.json` 在 `E5` 只是待终态确认的 envelope，不能单独表示成功。成功路径的唯一无环顺序为：

`probes → cleanup → residual scan → cleanup receipt → report → verify report → publication → verify publication → terminal(SMOKE_NON_ADMISSION) → verify terminal → stop`

report 绑定 probes、runtime inventory、residual scan 与 cleanup receipt；publication 绑定 report；terminal 最后绑定
publication 以及全部上游 digest。`terminal.json` 写入成功后不得再写任何文件。只有 exact set 为 `E6_SUCCESS`
且全部绑定重算一致，publication 才可被采纳；这消除了“publication 成功后才能写 publication/report”的循环。

### 3.3 失败阶段

失败可从 `E0`–`E5` 任一阶段进入。`failure-intent.json` 必须记录 `entered_from_stage` 和进入失败前的 exact-set
digest；从该时刻起不得再新建 report 或 publication，但进入失败前已存在的 report/publication 必须保留，且由
failure-intent 和最终 terminal 将其列为 `unaccepted`；不得修改原文件或删除来伪装较早阶段。

- `F1_INTENT`：进入失败前的证据集合 + `failure-intent.json`；
- `F2_CLEANED`：`F1` + `residual-scan.json`，并尝试写入 `cleanup-receipt.json`；全部临时数据应为零；
- `F3_TERMINAL`：`F2` + 唯一有效 primary terminal，或符合 §4.5 的 fallback 组合；不得产生新的成功 artifact。

失败路径 exact set 由 `entered_from_stage` 决定，审计者必须据此重算，不能只检查总 allowlist。

## 4. 四项修复的强制运行证据

### 4.1 Tombstone：before/after 可见性与物理保留

每个 tombstone probe 必须在同一个固定 generation/snapshot 下产生一份不可变 `tombstone_probe` 记录，至少包含：

- `target_chunk_id`、source/owner、query digest、generation、snapshot 和 filter digest；
- 删除前完整 top-k 结果的规范化 `chunk_id`、score、rank、metadata digest 及结果 digest；
- `target_was_visible=true`，且目标必须实际出现在删除前结果中，不能用“删除后不命中”反推；
- tombstone 操作后的完整 top-k 结果及结果 digest；
- `physical_retained=true`、`logical_hidden=true`、`tombstoned=true`，以及保留记录的 identity/content
  fingerprint（不得记录源内容）；
- `non_target_before_after_equal=true`：删除前结果去除目标后的顺序、ID 和 score 在协议容差内与删除后结果一致；
- 至少一次 reopen/重新加载后的重复查询结果，证明缓存或旧 snapshot 没有重新暴露目标。

机械验收必须同时满足：删除前目标可见、删除后目标在全部规定 probe 的结果中不可见、物理记录仍存在且标记为
tombstoned、所有非目标结果符合基线。任一字段缺失、目标删除前不可见或只能由固定常量填充，probe 为 `FAIL`。

### 4.2 Hard-delete：剩余检索的连续性、完整性与排序

hard-delete probe 必须先冻结删除前的 live-record oracle，而不是只记录 count。oracle 至少包含：

- 全部 live chunk ID 的有序 identity-set、count 和 digest；
- 固定 query corpus 的每个 query、filter、top-k、排序 tie policy，以及删除前完整结果；
- 目标 chunk 的物理 fingerprint 和 target rank（如命中）。

删除后必须证明目标物理不存在（含 reopen 后的物理检查），并对同一 query corpus 重跑检索。验收要求：

- `post_identity_set == pre_identity_set - {target}`，count 恰减一；
- 每个 query 的 post 结果等于 oracle 过滤掉 target 后按同一 tie policy 重排的结果，包含 ID、metadata digest、
  score 容差和 top-k 截断；
- 至少一个全量/分页或等价覆盖 probe 证明所有剩余记录仍可检索，不能以“一次非空搜索”替代；
- reopen/reload 后结果与删除后结果一致，且没有 stale cache、已删除 ID 或跨 generation 结果；
- 结果 digest、identity-set digest、oracle digest 和 hard-delete receipt 交叉绑定。

缺少删除前 oracle、只比较非空、只比较 count、排序/完整性不一致或任一 stale hit，均为 `FAIL`，不得发布 report。

### 4.3 运行期 hard-link 与 NTFS ADS 门禁

运行期扫描和 cleanup 必须复用同一个 `inspect_tree(root, phase)`，并在 marker 后、每次 artifact 写入后、runtime
inventory、cleanup 前、cleanup 后和 publication 前调用。对根、父链、目录和每个文件必须检查：

- `lstat` 类型、symlink/reparse point、resolved containment；
- regular file 的 `st_nlink == 1`，目录和文件的 link/reparse 属性不得被忽略；
- Windows 上使用 `FindFirstStreamW`/`FindNextStreamW` 或等价原生 API 枚举 ADS，只允许默认 unnamed `::$DATA`，
  任何命名 stream、枚举失败或非 Windows 无法执行检查都必须 fail closed；
- 扫描结果记录规范化相对路径、file type、size、SHA-256、link count、stream names、phase 和 scan digest，
  不记录宿主机绝对路径。

`tree_bytes` 或 resolved-containment 单独通过不构成门禁。运行期出现 `st_nlink != 1`、任意额外 ADS、扫描异常、
根外解析或扫描与 cleanup exact-set 不一致，必须立即进入 `INVALID`/`ABORTED`，不得删除可疑文件后继续并宣称成功。

### 4.4 失败终态与 cleanup closure

运行器必须将状态建模为 `RUNNING`、`SMOKE_NON_ADMISSION`、`ABORTED`、`INVALID`；成功以外的任意异常都必须
fail closed。异常处理采用以下不可变顺序：

1. 首次异常立即以 `O_CREAT | O_EXCL` 写入 `failure-intent.json`，绑定 root provenance、phase、exception class、
   upstream digests、`entered_from_stage`、进入失败前 exact-set digest、预期 cleanup delete set、retained set 和
   `requested_status`；不得只打印后退出；
2. cleanup 只删除 runtime inventory 中标记为 `ephemeral-runtime` 的 exact set：backend index、合成 corpus/vector
   materialization、cache、venv、临时日志和工作目录。不得删除任何 provenance、inventory、probe 或进入失败前已写入
   的 report/publication，也不得删除 `failure-intent.json`；cleanup 不得跟随 symlink、reparse、hard link、ADS 或
   根外路径；
3. 无论 cleanup 是否抛错，都排他写入 `residual-scan.json`。该文件列出 cleanup 后全部剩余相对路径、file type、
   size、digest、link count、streams 和 scan digest。`zero_residual=true` 只表示 ephemeral-runtime 残留为零，
   不表示 execution root 为空；
4. cleanup 后必须保留并可重新读取的 exact set 为：execution marker、已生成的 runtime inventory/probe、
   `failure-intent.json`、进入失败前已存在且标为 `unaccepted` 的 report/publication、`residual-scan.json`，随后再加入
   cleanup receipt 和 terminal witness。任何未登记文件或缺失的必保留文件都使 closure 为 `INVALID`；
5. 排他写入 `cleanup-receipt.json`，记录 attempted/deleted/retained exact set、cleanup exception（脱敏）、
   residual scan digest、`zero_residual`、link/ADS scan digest、四根 provenance 绑定和 self-digest。receipt 必须留在
   `E` 中供独立审计重算，不能只把 digest 留在内存；
6. receipt 成功且 `zero_residual=true` 时，失败终态可为 `ABORTED`；cleanup、residual scan、receipt 或边界任一失败
   只能为 `INVALID`。receipt 写入失败时不得伪造 receipt 或 digest，terminal 必须记录
   `cleanup_closed=false`、`cleanup_receipt_digest=null` 和稳定 closure failure code。

成功路径同样只删除 `ephemeral-runtime` exact set，并永久保留 execution marker、inventory、两个 probe、
`residual-scan.json`、`cleanup-receipt.json`、report、publication 和唯一 success terminal。独立审计必须能够从这些
原文件重新计算整条链，不能依赖进程内对象、stdout 或退出码。

### 4.5 `terminal.json` 与 `terminal-fallback.json` 的排他规则

1. primary writer 必须先以 `O_CREAT | O_EXCL` 尝试写入、fsync、回读并校验 `terminal.json`。primary 完整有效时，
   `terminal-fallback.json` 必须不存在；两者都为有效 canonical terminal 时，整体判为 `INVALID_DUAL_TERMINAL`；
2. 只有 primary 的 create/write/fsync/read-back/canonical/self-digest 任一步失败，才允许排他创建 fallback。fallback
   的 status 永远只能为 `INVALID`，必须记录 primary 是否已创建、稳定失败阶段/错误码，以及可读取时 primary 的 size
   和 SHA-256；fallback 不能声明 `SMOKE_NON_ADMISSION` 或 `ABORTED`；
3. primary 无效或不完整且 fallback 有效时，fallback 只负责机械证明该 run 为 `INVALID`。若残留了 partial
   `terminal.json`，两文件必须同时保留供审计；这不是 dual-valid 情形；
4. primary 有效但 fallback 也存在、fallback 无授权提前出现、fallback 未绑定 failure-intent/cleanup 状态，均为
   `INVALID`；
5. primary 和 fallback 均缺失或均无法验证时，任何 verifier 必须仅由文件拓扑输出
   `UNVERIFIABLE_TERMINAL`，使用保留退出码 `97`，并拒绝 report/publication。runner 可同时输出固定 stderr token
   `V13_TERMINAL_UNVERIFIABLE`，但 stdout/stderr 不构成证据；
6. 成功路径只能有一个有效 `terminal.json`，其 status 为 `SMOKE_NON_ADMISSION`，并且 exact set 必须为
   `E6_SUCCESS`。失败路径的 normal terminal 为 `ABORTED`/`INVALID`，fallback 只能为 `INVALID`。

故障注入必须覆盖 runtime inventory、cleanup 删除、residual scan、receipt 写入、report 写入、publication 写入、
primary terminal 的 create/write/fsync/read-back 以及 fallback 写入失败。每个注入点都必须验证：非零退出、按本节
得到唯一可判定结果、无可采纳 success publication、retained exact set 可重算、无未登记残留，并验证重复执行不会
覆盖旧 intent/receipt/terminal。

## 5. 库存、审计与停止规则

V13 继续分别记录 fixture `11`、probe-query `10`、smoke fixture `66/66`、full fixture `495/495`、smoke
probe-query `660/660`、full probe-query `4,950/4,950`，不得以总数替代分项库存。独立审计必须逐项重算四根
provenance、source/tree/config/manifest/inventory、两个 before/after probe、阶段 exact set、运行期 link/ADS scan、
failure matrix、residual scan、cleanup receipt、report、publication 和 terminal witness digest；作者会话不得自判
`PASS`。

任一字节合同、路径/链接/ADS、tombstone before/after、hard-delete oracle、失败终态、cleanup closure 或库存不符，
唯一允许终态为 `INVALID` 或 `ABORTED`。V13 也不得因此自动关闭 M8 Decision、选择后端或进入生产实现。

## 6. V13 退出条件与不可复用规则

V13 已在任何 root-creation/source-authoring 授权、建根或 source freeze 前永久停止。原草案关于在同一 V13 身份内
修订、文本审计、binding 或获得 `SMOKE_NON_ADMISSION` 的退出路径均已失效；不得补充勘误后恢复，也不得递增本文件
中的 V14 叙述来绕过处置。任何后续 M8 实证必须采用全新协议身份，重新完成 source freeze、独立静态审计 `PASS`、
后续 release/gate/execution 授权和全部运行期 hard gates。V13 的协议、占位符、root、source、receipt、audit、report
或 publication 均不得用于该新身份。

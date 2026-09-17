# M8 最小 1K v3 observer specification

> 状态：`S1_PREREQUISITE_CONTRACT / NOT_EXECUTION_AUTHORIZED`。
> 本文只冻结未来真实 1K dry-run 的 observer 合同；不探测当前机器、不创建 identity/root、不安装依赖、不运行 backend，
> 也不构成 `PROTOCOL_ACCEPTED`、S1、backend selection 或 M8 admission。

## 1. 权威边界

本文实现 [`m8-minimal-1k-dry-run-protocol-v3.md`](m8-minimal-1k-dry-run-protocol-v3.md) 第 6、8 节要求。
真实 observer implementation、configuration、redaction registry 和本文精确 bytes 必须先由独立 S0 接受；未来 Owner 仍须
在 S1 config 中绑定其 path、SHA-256 和 byte count，并冻结真实 Windows API、race/reparse 处理、process-tree 采集和允许根。
模板占位符与仓库内 micro-fixture 不是 observer 配置、运行证据或授权。

Observer 不得读取真实资料正文；除未来 S1 冻结的系统观察 API、temporary root、evidence directory、repository root 和
production roots 外，不得扫描任意文件系统。Persistent evidence 只写入 S1 冻结的 evidence directory。

## 2. Phase、主体与时钟

执行生命周期固定为：

1. `observer-bootstrap`：四个 ledger writer 和底层 collector 全部初始化；
2. `acquisition`：仅取得 S1 冻结的依赖，网络是否允许完全由 S1 config 决定；
3. `measured`：从 input member digest 复验开始，到 canonical run-report 原始 bytes 的 SHA-256 完成为止；
4. `redaction-and-seal`：扫描全部拟持久化 evidence，重算 ledger summary；
5. `cleanup`：删除 temporary root，形成 cleanup receipt；
6. `observer-finalize`：四个 ledger 写入终止事件并以 binary mode 复读、验证和摘要。

本合同的 network 禁止只适用于 `measured`；listener 在全部 phase 均禁止。Measured process tree 的 root 是 executor PID，成员是
其在 phase 内出现的全部 descendants。PID 必须与 process creation time 组成 identity，禁止仅按可复用 PID 关联。

所有排序和比较使用原始 UTF-8 bytes 或冻结的 canonical Windows comparison key，不使用 locale。时间值仅可作为 detail 中的
诊断字段，不能替代 `sequence`、产生 authority 或参与 canonical verdict。

## 3. Ledger framing 与 closed event

固定四个 ledger：

```text
events/network.jsonl
events/write.jsonl
events/process.jsonl
events/redaction.jsonl
```

每行必须是 `sa-json-c14n-v1` JSON：UTF-8 无 BOM、递归排序 key、无 insignificant whitespace、恰一个 LF，禁止 CR、重复 key、
NaN、Infinity 和未配对 surrogate。每个 event 必须且只能含四个 top-level keys：

```text
detail,kind,sequence,status
```

- `detail`：closed object；只允许本文相应 event branch 声明的 keys；
- `kind`：第 4～7 节相应 ledger 的固定枚举；
- `sequence`：integer，从 0 开始，逐行严格加 1，无重复、跳号或回绕；
- `status`：`PASS` 或 `FAIL`。

每个 ledger 至少两条事件。sequence 0 必须是 `observer-start`；最后一条必须是 `observer-stop`。启动失败仍由独立 supervisor
writer 写 `observer-start/FAIL` 和 `observer-stop/FAIL`；不得因 collector 未启动而省略 ledger。运行期读取、解码、枚举、扫描、
持久化或 seal 失败必须写本节或后续章节指定的 FAIL event；无法观察等同观察失败，禁止默认 PASS。

仓库内 synthetic-only orchestrator 还要求每个 injected collector 在采集后、seal 前返回独立 coverage receipt。Receipt
不是 ledger event，也不得持久化为真实 observation evidence；它只供 hermetic Builder test 证明 synthetic collector 明确声明完成了
六个 phase。Receipt 必须是 closed object，且只能含 `complete,observer,phases`：`complete` 必须严格为 `true`，`observer`
必须等于当前四类 observer 之一，`phases` 必须按第 2 节原顺序精确等于完整六项 tuple。缺失、非 object、额外 key、错误 observer、
`false`、缺项、重复、重排或 `coverage()` 抛错都以 `collector-coverage-failed` fail closed。有效 receipt 仍不能替代 event-specific
coverage：process 必须按顺序为每个 phase 提供一条 `child-count`，redaction 必须使 `utf8-scan.path` 集合精确等于预期排序集合；
network/write 无 activity event 只有在 receipt 有效时才可通过。该机制纯属 synthetic、non-authoritative preparation，不证明真实
Windows API coverage，不构成独立审查、S1 authorization 或 dry-run evidence。

所有 detail branch 都必须含 `code` 和 `phase`：

- `code` 为小写 kebab-case ASCII，成功 lifecycle 使用 `none`；
- `phase` 只能为第 2 节六个 phase 名称；
- FAIL 时 `code` 不得为 `none`，且必须是 S1 configuration 冻结的 error-code registry 成员；
- detail 禁止 stack trace、环境变量、command line、credential、主机名、用户名或未脱敏绝对路径。

## 4. Network observer

允许 kind 仅为：

```text
observer-start,observer-stop,outbound-connection
```

S1 configuration 必须冻结实际 collector API 和调用参数；Windows baseline 是 `GetExtendedTcpTable` 的 IPv4/IPv6 TCP 表、
对应 UDP table，以及 harness 对所有 socket-creation/connect API 的 instrumentation ledger。Collector 必须在 measured phase 开始前
和结束后采样，并在 phase 内持续捕获短连接；仅比较前后快照不足以 PASS。

Detail branches：

- `observer-start` / `observer-stop`：只能含 `api_ids,code,phase,root_process_identity`；`api_ids` 为非空、排序且唯一的
  frozen API identifier array；`root_process_identity` 为脱敏 digest；
- `outbound-connection`：只能含 `address_family,code,local_endpoint_digest,phase,process_identity_digest,protocol,
  remote_endpoint_digest`；endpoint 只能记录 canonical endpoint bytes 的 SHA-256，不得记录原始地址。

Measured phase 中任一 outbound attempt 或 established connection 必须为 `outbound-connection/FAIL`。Acquisition 中仅当目标、phase、
process identity 与 S1 allowlist 全部匹配时可为 PASS；其他连接均 FAIL。任何 listener、无法归属到冻结 process tree 的 socket、
API hook gap、table read/size race 超出有界重试、access denied 或 parse failure 均使 lifecycle event FAIL，并使 ledger FAIL。

## 5. Write observer 与 Windows containment

允许 kind 仅为：

```text
observer-start,observer-stop,allowed-write,denied-write
```

Detail branches：

- lifecycle：只能含 `allowed_root_set_sha256,api_ids,code,phase,root_process_identity`；
- write event：只能含 `code,operation,path_digest,phase,process_identity_digest,root_id`；`operation` 来自 S1 冻结的 create、
  modify、rename、delete、metadata-change 枚举；`root_id` 只能指向 S1 config 中的 logical root ID。

允许写入根集合恰为 future S1 冻结的 temporary root 与 evidence directory。Repository root、production roots、其 parent 和所有未知根
均禁止写。允许集合按 directory identity 而不是字符串 prefix 判断；两个允许根必须同 parent、彼此不相等且互不为 descendant，
并位于 repository/production roots 外。

每次可能写入前和打开后都必须执行 no-follow containment：

1. 输入必须是 absolute canonical Windows path；拒绝 relative、drive-relative、UNC/device/extended-prefix alias、ADS、保留设备名、
   trailing-dot/space ambiguity 和未冻结 case-normalization；
2. 从已冻结 parent handle 逐 component 使用 no-follow semantics 打开；检查 reparse attributes/tag，任何未明确允许的 reparse point
   立即 denied；
3. 对每个 handle 读取 final path、volume identity、file ID 和 parent identity；必须位于同一冻结 allowed root identity；
4. 在 mutation 前紧邻复验 parent/component identity，在 mutation 后再次复验 target 和 parent；任一 identity 变化、replace race、
   mount/junction/symlink escape 或无法复验均 fail closed；
5. rename 的 source 与 destination 分别执行完整检查；delete 也不得绕过 containment。

实现使用的 Windows API、flags、reparse allowlist、canonicalization algorithm、重试上限和 identity serialization 必须由 S1 config bytes
精确冻结。每个允许 mutation 写 `allowed-write/PASS`；每个被阻止的 attempt 写 `denied-write/FAIL`。Collector 自身失效以
`observer-stop/FAIL` 记录。Repository 与每个 production root 的 canonical pre-inventory 必须在 measured 前冻结；post-inventory
逐 byte digest 不同、不可读取或集合不完整均为 FAIL。

## 6. Process observer

允许 kind 仅为：

```text
observer-start,observer-stop,child-count,unexpected-child
```

S1 config 必须冻结 process enumeration/event API、poll/event strategy、creation-time identity format、expected executable digests、
command shape digest 和允许 child count。只在 phase 边界拍快照不足以 PASS；必须覆盖 measured phase 中启动后快速退出的 child。

Detail branches：

- lifecycle：只能含 `api_ids,code,phase,root_process_identity`；
- `child-count`：只能含 `code,count,phase,tree_digest`；count 为非负 integer，tree digest 绑定按 process identity 排序的完整集合；
- `unexpected-child`：只能含 `code,executable_digest,parent_identity_digest,phase,process_identity_digest`。

Root executor 本身不计 child。每个 descendant 必须沿 `(pid,creation_time)` parent chain 归属，且 executable bytes digest、父 identity、
启动 phase 与 S1 allowlist 匹配；不得信任 command line 自报身份。每个 phase 至少写一条 `child-count`。任一未知/超额 child、PID
reuse ambiguity、enumeration gap、access denied、identity 或 executable digest 无法读取，均写 FAIL（未知 child 使用
`unexpected-child/FAIL`，collector gap 使用 `child-count/FAIL`）。

## 7. Redaction observer

允许 kind 仅为：

```text
observer-start,observer-stop,utf8-scan,sensitive-match
```

S1 config 必须冻结 canonical redaction registry 的 path、SHA-256、byte count、canonicalization ID 和 registry schema ID。Registry
必须是 closed canonical JSON，至少覆盖：Windows absolute/device/UNC path、URI credential、token/private-key marker、
`D:\111_Others_Subjects`、real-content marker、用户名/主机身份和 S1 指定 secret literals 的 deterministic matcher。禁止运行期新增、
删除、重排或弱化 pattern。

Detail branches：

- lifecycle：只能含 `code,phase,registry_sha256,scanned_set_sha256`；
- `utf8-scan`：只能含 `byte_count,code,path,phase,sha256`；`path` 必须是相对 evidence-directory 的 canonical path；
- `sensitive-match`：只能含 `code,match_count,path,pattern_id,phase`；`path` 同样必须是相对 evidence-directory 的 canonical
  path；不得写入 matched bytes、offset 周围正文或 secret。

Seal 前必须枚举 evidence directory 的全部 regular files，按 relative-path UTF-8 bytes 排序，拒绝 symlink/reparse/unknown object，
并冻结 `scanned_set_sha256`。声明为 UTF-8 JSON/JSONL/Markdown/text 的文件必须使用 strict UTF-8 decode；decode failure 写
`utf8-scan/FAIL`。每个文件至少一条 scan event；漏扫、read race、bytes 在 scan 后 seal 前变化、registry mismatch 或 matcher error
均 FAIL。每个命中写 `sensitive-match/FAIL`；match count 可以记录，matched content 不得持久化。Binary allowlist 必须在 registry 中
按 path/schema 冻结；未知 binary file 直接 FAIL，不能跳过。

## 8. Summary、聚合与下游绑定

每个 ledger summary 必须从已关闭 ledger 的实际 binary bytes 复算，字段与 v3 artifact schema 一致：

```text
path,sha256,byte_count,event_count,status
```

- `path` 必须是对应固定 ledger path；
- `sha256` 和 `byte_count` 绑定完整 bytes，包括最终 LF；
- `event_count` 是实际 canonical JSONL 行数且至少 2；
- 存在任一 event `status=FAIL` 时 summary 必须 `FAIL`，否则只有全部 event PASS 时才可 `PASS`。

Run report 必须绑定四个 summary。任一 ledger 缺失、为空、非 canonical、生命周期/sequence/kind/detail 非法、摘要不符、collector
coverage 不完整或 summary FAIL，observer validation check 必须 false，最终 validation 必须 FAIL，S2 只能
`DRY_RUN_FAILED/stop`，S3 只能 `REJECT_1K_EVIDENCE/stop`。失败证据不得删除或包装为 PASS。

## 9. S1 configuration 必须冻结的 observer material

签发 S1 前，closed config 至少必须绑定：

1. 本文和四类 observer implementation 的 path、SHA-256、byte count；
2. 独立 S0 接受记录的 typed REF；
3. 每类 API IDs、参数/flags、poll interval、bounded retry、timeout 和 coverage strategy；
4. executor root identity、process allowlist 与 executable/command-shape digests；
5. temporary/evidence/repository/production root 的 canonical path、volume/file/parent identity；
6. allowed-write root set、reparse policy、canonicalization algorithm 与 race revalidation algorithm；
7. repository/production pre-inventory members、serialization algorithm 和 digest；
8. redaction registry bytes 及 matcher algorithm；
9. event error-code registry、persistent file allowlist 和 binary classification；
10. observer config 本身的 canonical path、schema ID、SHA-256 和 byte count。

占位符、空 digest、开放版本、仅 label 的路径、未绑定 registry 或“best effort” collector 均不满足 S1。

## 10. S0/S1 前置验证

独立 S0 至少必须以 synthetic temp roots 验证：正常 lifecycle；measured outbound；短连接；denied write；junction/symlink/reparse
escape；rename race；repository/production inventory change；允许和未知 child；PID reuse；UTF-8 decode failure；registry match；漏扫；
ledger final-LF/nonempty/canonicalization；summary reseal；collector startup/read/seal failure。每项 mutation 必须因目标约束失败，不能由
stale digest/REF 冒充。

这些测试只验证 observer implementation，不得访问真实资料、当前 production roots 或真实 dry-run root，也不产生 S1。只有独立
S0 接受和 Owner 对完整 closed S1 config 的另行签发，才可能允许后续 `run-s2`。

# M8 S1 environment-resolution Owner 决策（2026-09-18 r01）

## 1. Decision identity

- record：`m8-minimal-1k-v3-s1-environment-resolution-20260918-r01`
- record revision：`r01`
- decision timestamp：`2026-09-18T19:33:05+08:00`
- Owner role：`StudyAssistanceAgent M8 Owner`
- decision agent：`Claude Code M8 Owner for this session`
- repository identity：`justtodo123 <2103286227@qq.com>`
- repository path：`D:\Git Demo\StudyAssistanceAgent`
- repository remote：`git@github.com:justtodo123/StudyAssistanceAgent.git`
- branch at decision：`fix/m8-s1-environment-authority-r01`
- target commit：`dbfc53651fd5a3e2084515b3a084e99e880fbd1a`
- target tree：`ee8fe4172cc600774c985a877257a36914a3515c`

```yaml
decision: ENVIRONMENT_RESOLUTION_REMAINS_FAILED_CLOSED
reason: no locally available complete offline closure and no authorized acquisition or import path
environment_authority_outcome: ENVIRONMENT_AUTHORITY_PACKAGE_FAILED_CLOSED
allowed_next_action: stop
```

这是方案 C 的明确决定，不是原则同意、建议尝试或有条件授权。本文不授权网络获取 wheel，
不授权导入外部 wheelhouse，也不授权任何后续 environment-resolution 执行动作。

## 2. Parent records 与 Git-object binding

本决策基于以下已核验记录，不修改、不替代其历史字节：

| 记录 | Git binding | 工作区 SHA-256 | 核验含义 |
| --- | --- | --- | --- |
| parent environment-resolution decision：`docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-environment-resolution-20260918.json` | commit `dbfc53651fd5a3e2084515b3a084e99e880fbd1a`；blob `ddeeb736a97060a6d37034ebd1091c83606cfed3` | `2197c03a3352a873b06175d5e412482ecb50f4a0461e4176910da225d8bb72b7` | 历史 `S1_ENVIRONMENT_RESOLUTION_AUTHORIZED / prepare-environment-authority-package`；禁止网络、下载、正式环境和 S1 retry |
| S1 failure：`docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-failure-20260918-r01.json` | commit `3c98323382b4520d013fef54261f7620acd1a425`；blob `55856de49d16e8fb0125bcaff1161692961ad4dd` | `6ebdce91d1689511065464889c9fbcc429fd00761a366ee5f5ff5c187fa909c1` | `S1_A_FAILED / FAILED_CLOSED`；未建立完整精确离线闭包及完整 frozen inventory/config |
| original S1 Owner decision：`docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-owner-decision-20260918.json` | commit `340e130ec20b430aed5a3328abfa951e4de9ff22`；blob `708ee1635ceda35752fa920ab97b110f23d46b88` | `80f2990a29251cce7da00ef0363149b25a7aec825f81e44af24f17f01ea691bc` | 历史 `S1_AUTHORIZED`；失败后不构成 retry authority |
| current prerequisite freeze：`docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-prereq-freeze-20260918-r01.json` | commit `3c2249d7fd0a7d2cb4363ba9093ff62f09c975b6`；blob `40c74c76db076faad19af2b68bc226051d2fce21` | `6f1315591915a80ae9d463ec85aafa92925d57514ea691180318dc212817a517` | `S1_PREREQUISITE_RECORD_ONLY_NOT_AUTHORIZATION` |
| parent wheelhouse rejection：`docs/plans/references/m8-minimal-1k-v3-s1-wheelhouse-preparation-authorization-20260918-r01.md` | target commit `dbfc53651fd5a3e2084515b3a084e99e880fbd1a`；content-derived blob OID `ed8b1fb9e23efa645ad56df89795d7c585d02187`；not tree-bound at decision time | `4c60be9c2ff050b60e23aadadd629aeb682c90a0003db9c116abb5ffcdf04ff1`；9,578 bytes | `WHEELHOUSE_PREPARATION_REJECTED / request-owner-environment-resolution`；工作区独立记录尚未提交，故不得虚构 introducing commit |

经核验的 committed authority ancestry 为：

```text
6f9cf4617e79462130737eaf78cdb392b02b6664
  -> 3c2249d7fd0a7d2cb4363ba9093ff62f09c975b6
  -> 340e130ec20b430aed5a3328abfa951e4de9ff22
  -> 3c98323382b4520d013fef54261f7620acd1a425
  -> dbfc53651fd5a3e2084515b3a084e99e880fbd1a
```

每个箭头均对应直接 parent commit。当前 wheelhouse rejection 是基于 target commit 的未跟踪工作区记录，
不在上述 committed ancestry 中；本文将其按路径、字节数、SHA-256 和 content-derived blob OID 绑定，
不把尚不存在的 tree/commit binding 写成事实。

## 3. 独立核验的当前状态

- M8：`BLOCKED / NOT_STARTED`
- S1 execution：`FAILED_CLOSED_PENDING_RESOLUTION`
- S1 retry：`NOT_AUTHORIZED`
- S1-B：`NOT_AUTHORIZED`
- S2：`NOT_AUTHORIZED`
- S3：`NOT_AUTHORIZED`
- backend selection：`NOT_AUTHORIZED`
- environment authority package：`ENVIRONMENT_AUTHORITY_PACKAGE_FAILED_CLOSED`
- wheelhouse preparation：`WHEELHOUSE_PREPARATION_REJECTED`
- dependency installation：未发生
- formal venv、identity、experiment root、evidence root：均未创建
- formal synthetic 1K：未生成
- SQLite：未运行
- LanceDB：未运行
- network wheel acquisition：未获授权且未发生
- external wheelhouse import：未获授权且未发生
- origin push：未发生

S1 failure 只冻结了四个 direct archive 的观察证据：`lancedb==0.38.0`、`numpy==2.4.6`、
`psutil==7.2.2`、`pyarrow==25.0.1`。该记录同时明确：四个直接依赖及递归依赖不存在完整、
精确、provenance-verifiable 的本地离线 wheel closure；LanceDB ranges 还存在冲突的本地 satisfier。
因此不能把本地恰好存在的版本、cache 顺序、文件系统顺序或隐式最高版本提升为 Owner authority。

## 4. 三选一决定与理由

### 4.1 方案 A 未获授权

本 Owner 不签发 `NETWORK_WHEEL_ACQUISITION_AUTHORIZED`。当前治理链没有已经冻结并核验的：

- 精确 package repository、index/artifact URL 规则和 source identity；
- host 与 redirect-host allowlist、redirect policy；
- TLS/证书、proxy、mirror 和 authentication policy；
- 非正式 preparation root、persistent file allowlist、partial-file/cleanup policy；
- 单文件、文件数、总字节、timeout、retry 和 concurrency 边界；
- network/write/process/redaction observer 的可执行实现、API IDs 和 implementation digest；
- child-process policy 与对应的 fail-closed error-code contract。

虽然当前机器存在可观察 runtime 值，这些机器观察值不是一套已冻结、独立审查且绑定 acquisition
observer/source policy 的完整 authority。Owner 不得让 Builder、下载工具或 resolver 自行补全这些决定。

### 4.2 方案 B 未获授权

本 Owner 不签发 `EXTERNAL_WHEELHOUSE_IMPORT_AUTHORIZED`。当前没有由 Owner 或受信任提供方交付并冻结的：

- provider identity、提供时间和 source provenance；
- 精确 source root 或 artifact identity；
- transfer mechanism；
- source manifest、manifest SHA-256、wheel count 和 total bytes；
- 逐文件 filename/size/SHA-256 登记；
- 允许读取与复制的精确 roots；
- 等价的 write/process/redaction observer authority。

因此不存在可授权的外部 wheelhouse source。不得扫描未知目录、访问
`D:\111_Others_Subjects`，也不得由执行者临时选择一个 wheelhouse 或复制来源。

### 4.3 方案 C

因为本地没有完整离线闭包，且网络 acquisition 与外部 import 两条路径都缺少可冻结、可验证的
source、write boundary 和 observer authority，本决策选择：

```text
ENVIRONMENT_RESOLUTION_REMAINS_FAILED_CLOSED
```

获取或导入候选 wheel 本来也不等于接受 dependency closure；但本轮连 acquisition/import 前提均未闭合，
故不得进入候选收集、离线 resolver、closure 枚举或 Environment Authority Package 准备。

## 5. Authorized scope

本决策新增的 authorized scope 为：**空集**。

历史 parent records 继续作为不可改写的治理事实保存，但不得把其中先前的只读准备范围解释为本决策之后
仍可继续推进 environment-resolution 的授权。对当前阻断的唯一有效处置是 failed closed；没有网络读取、
文件复制、写入、resolver、安装、执行、正式环境创建或候选验证权限。

## 6. Forbidden scope

本决策明确禁止：

- 下载或复制 wheel，访问 package repository、index、artifact URL、mirror、proxy 或其他网络来源；
- 创建、填充或修改 wheelhouse，包括 partial download 和临时 acquisition/import 文件；
- 扫描未知 external source root，导入未登记文件，或跟随 symlink/junction/path escape；
- 修改任何 source wheelhouse；
- 获取 sdist/source archive/VCS/editable dependency，执行 build isolation、wheel build、源码构建或 `setup.py`；
- 执行、导入、安装、升级或卸载候选包；
- 运行 environment resolver，或选择任何 direct/transitive dependency closure；
- 按最高版本、cache 时间、下载顺序或文件系统顺序作闭包选择；
- 创建正式 venv、identity、experiment root、evidence root 或正式 temporary root；
- 生成正式 synthetic 1K；
- 运行 SQLite 或 LanceDB，创建 backend evidence 或选择 backend；
- retry/run S1，执行 S1-B，签发或执行 S2/S3；
- admit M8，修改 production，或修改历史 decision/review/failure/freeze；
- 读取、扫描或复制 `D:\111_Others_Subjects`；
- push origin。

本轮不实例化 runtime acquisition binding、source allowlist、preparation root、write limits、observer、
wheel inventory 或 transfer contract。“未实例化”表示无权限，不表示执行者可以自行选择。

## 7. Fail-closed conditions

以下任一情况均保持 failed closed，不能自动修复或降级放行：

- 缺少完整本地离线 wheel closure；
- 缺少 Owner 冻结的网络 source 或外部 wheelhouse source identity；
- 缺少精确 runtime、write boundary、observer implementation 或 fail-closed error contract；
- 缺少 wheel filename、size、SHA-256、tag、source、redirect chain 或 provenance；
- 需要网络、外部复制、build、安装、包代码执行或未知 child process 才能继续；
- resolver、工具默认值、cache 或遍历顺序决定版本；
- 零闭包、多个未由 Owner 显式选择的闭包，或 closure evidence 未经独立只读审查；
- 任何 source/manifest/file digest、ZIP/WHEEL/METADATA/RECORD、Requires-Python 或 tag 校验失败。

## 8. 唯一下一步与显式非授权

```yaml
allowed_next_action: stop
```

本决策结束时明确保持：

- `M8 = BLOCKED / NOT_STARTED`
- `S1 retry = NOT_AUTHORIZED`
- `S1-B = NOT_AUTHORIZED`
- `S2 = NOT_AUTHORIZED`
- `S3 = NOT_AUTHORIZED`
- `backend selection = NOT_AUTHORIZED`
- `environment authority package = ENVIRONMENT_AUTHORITY_PACKAGE_FAILED_CLOSED`
- `wheelhouse preparation = WHEELHOUSE_PREPARATION_REJECTED`

本文不构成 network acquisition、external import、S1、S1-B、S2、S3、backend selection 或 M8 admission。
本 Owner 不充当任何后续材料的独立 Reviewer。

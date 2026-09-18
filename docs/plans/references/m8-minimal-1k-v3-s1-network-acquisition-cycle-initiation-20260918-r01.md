# M8 S1 network-acquisition 新周期启动候选（2026-09-18 r01）

## 1. Cycle identity

- cycle ID：`m8-s1-network-acquisition-cycle-20260918-r01`
- record：`m8-minimal-1k-v3-s1-network-acquisition-cycle-initiation-20260918-r01`
- status：`CANDIDATE / NOT_REVIEWED / NOT_ACQUISITION_AUTHORIZED`
- route：`NETWORK_ACQUISITION`
- initiated at：`2026-09-18T19:54:27+08:00`
- repository：`git@github.com:justtodo123/StudyAssistanceAgent.git`
- base commit：`0ee1911c574aee95085b51abf40a0a5d0947b05c`
- base tree：`a5a82b192eed9d72c474c944e09c4c66791aae55`
- preparation branch：`docs/m8-network-acquisition-cycle-r01`
- candidate author role：`network-acquisition authority builder`

```yaml
decision: M8_NETWORK_ACQUISITION_NEW_CYCLE_INITIATED
purpose: PREPARE_AND_REVIEW_NETWORK_ACQUISITION_AUTHORITY_ONLY
selected_source_policy: OFFICIAL_PYPI_STRICT
selected_target_runtime: WINDOWS_AMD64_CPYTHON_3_13_3_CP313
allowed_next_action: prepare-network-acquisition-authority-review-materials
acquisition_status: NOT_AUTHORIZED
s1_retry_status: NOT_AUTHORIZED
s2_status: NOT_AUTHORIZED
s3_status: NOT_AUTHORIZED
m8_status: BLOCKED_NOT_STARTED
```

本记录建立一条与历史 failed-closed 链平行的新治理周期。它不修改、不撤销、不恢复历史
`ENVIRONMENT_RESOLUTION_REMAINS_FAILED_CLOSED / stop`，也不使旧 `S1_AUTHORIZED` 重新生效。

## 2. Immutable parent history

| 历史记录 | Git blob OID | SHA-256 | bytes | 绑定含义 |
| --- | --- | --- | ---: | --- |
| `m8-minimal-1k-v3-s1-environment-resolution-20260918-r01.md` | `acfb8b86e899d3903c49d3176f28dfe4e15080d8` | `6c8f141c4bba4da25db2ca6570ac4557d765df6c6953090dd08149ef40ebc667` | 10697 | 历史链终态为 `ENVIRONMENT_RESOLUTION_REMAINS_FAILED_CLOSED / stop` |
| `m8-minimal-1k-v3-s1-wheelhouse-preparation-authorization-20260918-r01.md` | `ed8b1fb9e23efa645ad56df89795d7c585d02187` | `4c60be9c2ff050b60e23aadadd629aeb682c90a0003db9c116abb5ffcdf04ff1` | 9578 | 历史 wheelhouse 准备被拒绝 |
| `external-artifacts/m8-minimal-1k-v3-s1-failure-20260918-r01.json` | `55856de49d16e8fb0125bcaff1161692961ad4dd` | `6ebdce91d1689511065464889c9fbcc429fd00761a366ee5f5ff5c187fa909c1` | 3715 | 历史 S1-A 环境准备 failed closed |
| `external-artifacts/m8-minimal-1k-v3-s1-prereq-freeze-20260918-r01.json` | `40c74c76db076faad19af2b68bc226051d2fce21` | `6f1315591915a80ae9d463ec85aafa92925d57514ea691180318dc212817a517` | 38095 | prerequisite record only，不是 acquisition authority |

上述对象已包含在 base commit `0ee1911c574aee95085b51abf40a0a5d0947b05c` 的历史中。本周期只引用其事实，不改写旧字节。

## 3. Selected route decisions

### 3.1 Source policy

本候选选择 `OFFICIAL_PYPI_STRICT`：

- 元数据初始 host 仅允许 `pypi.org`；
- wheel 制品最终 host 仅允许 `files.pythonhosted.org`；
- 仅允许 HTTPS；
- TLS 和证书校验必须开启，任何校验错误 fail closed；
- 禁止 mirror、proxy、extra index、认证来源和证书绕过；
- redirect 只能进入已冻结 host allowlist；
- authority package 未独立审查并被 Owner 另行接受前，不得访问上述网络来源。

### 3.2 Target runtime

本候选选择：

```text
OS family: Windows
architecture: AMD64
Python implementation: CPython
CPython exact version: 3.13.3
Python tag: cp313
ABI/SOABI: cp313 / cp313-win_amd64
platform tag: win_amd64
```

只读核验发现 `D:\Python\python.exe` 在 isolated、no-site 模式下报告 CPython 3.13.3、Windows build
`10.0.26200`、AMD64 和 `cp313-win_amd64`。普通 site 初始化受到 WPS Python 3.12 路径污染并发生 SRE mismatch；
因此该观察只用于指出 authority 必须冻结 isolated/no-site 启动与环境清理，不构成 acquisition 执行授权。

pip、packaging、locale、timezone、允许/禁止环境变量及 bytecode policy 必须在后续 authority candidate 中精确冻结；
未冻结字段不得由执行者用 ambient 值补齐。

## 4. Authorized scope of this initiation

本 initiation candidate 只允许：

- 起草 network-acquisition authority candidate；
- 冻结 runtime、官方 PyPI 来源、TLS/redirect、写入根、限额和 provenance schema；
- 实例化四类 observer 候选及 fail-closed error registry；
- 使用 hermetic、无网络 fixtures 做 Builder 自检；
- 从 candidate Git object bytes 生成 freeze 与 handoff-only review package；
- 请求一名未参与起草或修改的独立 Reviewer 进行只读审查。

## 5. Explicitly forbidden scope

本 initiation 不授权：

- 访问 `pypi.org`、`files.pythonhosted.org` 或任何其他网络来源；
- 下载、复制、创建或填充 wheelhouse；
- 运行现有未提交的 `m8_resolve_s1_environment_v3.py` 或任何 environment resolver；
- 获取 sdist、源码、VCS/editable dependency，或执行 build、`setup.py`、候选包代码；
- 安装、升级、卸载或导入候选包；
- 创建正式 venv、identity、experiment root、evidence root 或正式 temporary root；
- 选择直接或递归依赖版本及 dependency closure；
- 生成正式 synthetic 1K，运行 SQLite/LanceDB，创建 backend evidence 或选择 backend；
- retry/run S1、执行 S1-B、签发或执行 S2/S3、admit M8；
- 修改 production、历史 decision/review/failure/freeze，访问 `D:\111_Others_Subjects`，或 push origin。

## 6. Review and decision separation

本候选的起草/修改方不得担任其最终独立 Reviewer。独立审查接受最多只能产生：

```text
NETWORK_ACQUISITION_AUTHORITY_ACCEPTED
allowed_next_action: request-owner-acquisition-decision
```

该接受仍不允许下载。只有独立审查接受后，Owner 才能另行决定是否签发一次性、范围受限且绑定 freeze 的
`NETWORK_WHEEL_ACQUISITION_AUTHORIZED`。

## 7. Current state preserved

```text
M8: BLOCKED / NOT_STARTED
historical environment resolution: REMAINS_FAILED_CLOSED
network acquisition: NOT_AUTHORIZED
wheelhouse creation: NOT_AUTHORIZED
environment resolver: NOT_AUTHORIZED
S1 retry: NOT_AUTHORIZED
S1-B: NOT_AUTHORIZED
S2: NOT_AUTHORIZED
S3: NOT_AUTHORIZED
backend selection: NOT_AUTHORIZED
```

本记录的唯一下一步是准备并审查新周期 authority 材料；不是执行 acquisition。

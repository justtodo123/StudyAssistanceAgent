# M8 `draft-0.10` P2 材料：目标卷实测

- 对象：`draft-0.10` P2 `binding`
- 日期：2026-09-14
- 负责人：`justtodo123`
- 前驱：P0 `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`；P1 `AUTHORIZED / request-p2`
- 状态：`P2_BLOCKED_ON_WORKSPACE_VOLUME / FINDING_RECORDED / NOT_AUTHORIZED`

## 1. 边界

本材料不是 P2 门禁记录，不产生 `repository-binding`、experiment root、执行、发布或准入权限。
它只记录当前工作区目标路径的 read-only parent-binding 实测结果。未生成 P2 binding record，未创建新的运行期对象。

被测目标：`D:/Git Demo/StudyAssistanceAgent`。该路径位于当前工作区所在的 `D:` 卷。

## 2. 前驱与新 identity

- P0：`external-gates/p0/p0-m8-active-execution-draft010-20260913-r01.json`
- P1：`external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json`
- identity：`external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json`
- 协议摘要：`b5bc5088486079971eba28efe5cd2d7ed90c73a1359a87d9bca4722c473caa39`

P1 仅授权创建 identity，虽然其 `allowed_next_action` 为 `request-p2`，但这不等于已授权 P2 binding。

## 3. 实测方法

使用 `tools/m8_parent_binding_validator.py`，该工具只读地：

- 以 `NtCreateFile` 打开卷根；
- 以 `FILE_OPEN_REPARSE_POINT`、完整共享和相对 `RootDirectory` 逐级打开目标组件；
- 通过 `NtQueryInformationFile(FileStreamInformation)` 读取每个已打开句柄的流清单；
- 同时读取文件系统、volume serial、file ID、ACL 摘要和 reparse 状态；
- 不创建、不修改、不删除对象。

执行命令：

```text
python tools/m8_parent_binding_validator.py "D:/Git Demo/StudyAssistanceAgent"
```

结果：退出码 `1`，在卷根/目录流复验处停止：

```text
ValueError: directory exposes unexpected streams: [':sguard:$DATA']
```

这是 `draft-0.10` P2 的 fail-closed 结果。`D:` 卷上的工作区目标不能作为当前 P2 parent binding 通过。

## 4. 对照实测

为区分“目标卷阻断”与“工具或机器整体不可用”，对不属于工作区目标的 `C:` 卷路径执行：

```text
python tools/m8_parent_binding_validator.py "C:/Users/Public"
```

结果退出码 `0`，卷根和目标目录均完成 stream、ID、ACL 等检查。该对照不构成换卷授权，也不能绕过当前工作区目标卷的阻断。

## 5. 结论与禁止事项

1. 当前工作区目标 `D:/Git Demo/StudyAssistanceAgent` 的 P2 实测失败，原因是目录暴露未被当前 P2 内建容许表接受的 `:sguard:$DATA`。
2. 该结果只证明 **D: 工作区目标路径当前不能通过 P2**，不推断整机所有卷均不可用；C: 对照通过。
3. `draft-0.10` 的 A1 已解决“P2 阶段没有可查的容许表”的阶段前置问题，但不保证每个目标卷通过 stream 检查。
4. 不得用 `C:/Users/Public` 或其他卷替换当前目标来规避阻断；环境选择需要负责人另行决定并独立记录。
5. 不得把本材料或这次实测改写为 `P2 AUTHORIZED`、`P2 PASS` 或 `request-p3`。
6. 不得因为对照卷通过而生成 D: 目标的 binding。

## 6. 建议决策（不代替负责人）

负责人需要在以下路径中选择并形成独立记录：

- **保留当前 D: 工作区目标**：记录 `P2_BLOCKED_ON_WORKSPACE_VOLUME`，不生成 binding；
- **明确选择 C: 上的 parent 路径**：先形成环境选择依据和授权，再重新构造、复验并记录新的 parent binding；这会改变 binding 的目标范围，不能默认为当前仓库路径；
- **另行修订协议**：若要改变 `sguard` 判定，必须另行提出协议修订，不得在 P2 记录中绕过。

本材料不选择其中任何一项。

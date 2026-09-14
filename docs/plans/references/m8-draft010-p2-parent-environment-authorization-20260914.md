# M8 `draft-0.10` P2 parent 环境选择与目录创建授权

- 日期：2026-09-14
- 授权人：`justtodo123`（owner）
- 状态：`AUTHORIZED_FOR_PARENT_PREPARATION / NOT_P2_AUTHORIZED / NOT_EXECUTION_AUTHORIZED`
- 协议：`docs/plans/references/m8-active-execution-protocol-draft-0.10.md`
- 协议 SHA-256：`b5bc5088486079971eba28efe5cd2d7ed90c73a1359a87d9bca4722c473caa39`
- P1：`external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1.json`
- identity：`external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1.json`

## 1. 决定

负责人授权在 `C:` 卷创建并使用以下**唯一专用 parent 目录**，作为 `draft-0.10` 的 P2 parent-binding 候选环境：

```text
C:\M8-Parents\sa-m8-active-draft010-20260914-5d10f2a1
```

本决定基于 2026-09-14 的只读实测：当前仓库所在 `D:` 卷目标
`D:/Git Demo/StudyAssistanceAgent` 暴露 `:sguard:$DATA`，P2 fail closed；`C:/Users/Public` 对照完整通过。
对照结果只证明 `C:` 卷具备候选条件，不把公共目录作为实验 parent，也不把 C: 的结果冒充 D: 的结果。

## 2. 允许动作

1. 在 `C:` 卷创建目录 `C:\M8-Parents`（仅当不存在）及其唯一子目录
   `sa-m8-active-draft010-20260914-5d10f2a1`。
2. 对目录链执行 read-only parent-binding 复验：卷根、`M8-Parents`、专用子目录逐级使用相对句柄、
   no-follow、完整共享读取 stream、volume serial、file ID、ACL digest 与 reparse 状态。
3. 将复验输出写入仓库内 P2 材料目录，形成可追溯的 canonical JSON 或材料说明。
4. 若复验全部通过，准备 `sa.m8.parent-binding.v1`、`sa.m8.repository-binding.v1` 与 P2 门禁记录候选，
   但在候选满足协议全部字段、摘要与前驱闭包前不得声明 `AUTHORIZED / request-p3`。
5. 若任一层复验失败，立即停止并形成阻断记录，不自动改用其他 C: 路径试探绕过。

## 3. 明确禁止

本授权不包含：

- 修改、移动或复制 `D:\Git Demo\StudyAssistanceAgent` 仓库；
- 把仓库迁移到 C:；
- 使用 `C:\Users\Public`、Windows 系统目录或其他未指定路径作为 parent；
- 创建 experiment root 下的 source、corpus、query、gold、dependency、environment 或执行产物；
- 获取或安装依赖、创建 venv、下载 wheel；
- 运行 preflight、smoke、benchmark 或任何实证执行；
- 生成 P3 或后续门禁记录；
- 发布证据、准入 M8 或选择专业后端；
- 修改协议以放宽 `sguard` 判定；
- 删除或改写任何既有门禁记录、identity、材料或历史目录。

## 4. 成功与失败条件

只有下列条件同时成立，目录才可作为 P2 parent-binding 候选：

1. 文件系统为协议允许的 NTFS/ReFS；
2. 卷根及每个组件均按协议 no-follow、relative RootDirectory 逐级打开；
3. 每次 open 的 stream 结果满足 `draft-0.10` P2 当前生效的 `BINDING_STREAM_ALLOWLIST`；
4. 无 reparse point；
5. volume serial 全链一致；
6. file ID、ACL SHA-256 与组件序列均被精确记录；
7. identity、P1、协议摘要和当前 Git commit 的引用闭包一致。

目录创建成功本身**不等于** P2 通过；只读复验成功也**不单独等于** P2 授权。P2 的最终决定必须由独立的
机器可读门禁记录表达。

## 5. 授权来源

负责人原始决定：

> 授权在 C: 卷创建并使用专用 parent 目录，作为 draft-0.10 的 P2 binding 环境。

本记录将该决定收敛为唯一路径和最小动作集，不扩张为执行、发布、准入或后端权限。

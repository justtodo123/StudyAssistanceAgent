# M8 `draft-0.11` P2 parent 环境选择与目录创建授权

- 日期：2026-09-14
- 授权人：`justtodo123`（owner）
- 状态：`AUTHORIZED_FOR_PARENT_PREPARATION / NOT_P2_AUTHORIZED / NOT_EXECUTION_AUTHORIZED`
- 协议：`docs/plans/references/m8-active-execution-protocol-draft-0.11.md`
- 协议 SHA-256：`92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d`
- P0：`external-gates/p0/p0-m8-active-execution-draft011-20260914-r01.json`
- P1：`external-gates/p1/p1-m8-active-execution-draft011-940ecec4-r01.json`
- identity：`external-artifacts/identity/sa-m8-active-draft011-20260914-940ecec4.json`

## 1. 决定

负责人授权在 `C:` 卷创建并只读复验以下全新专用 parent 目录，作为 `draft-0.11` identity
`sa-m8-active-draft011-20260914-940ecec4` 的 P2 parent-binding 候选环境：

```text
C:\M8-Parents\sa-m8-active-draft011-20260914-940ecec4
```

该路径与 `draft-0.10` 的专用 parent 不同；不得复用旧目录、旧 parent-binding、旧 repository-binding 或旧 P2。
本授权只选择物理候选环境，不是 canonical parent-binding、repository-binding 或 P2 gate。

## 2. 允许动作

1. 在既有或新建的 `C:\M8-Parents` 下创建唯一子目录
   `sa-m8-active-draft011-20260914-940ecec4`。
2. 对卷根、`M8-Parents` 和专用子目录执行 read-only parent-binding 复验：逐级 relative RootDirectory、
   no-follow、完整共享，读取 stream、volume serial、file ID、ACL digest 和 reparse 状态。
3. 在创建后执行两次独立只读复验；两次结果必须逐字段相同，且复验期间目录保持为空。
4. 将事实输出写入新的 draft-0.11 P2 材料说明，作为后续 binding 候选的可追溯输入。
5. 若任一检查失败，立即停止并记录阻断；不得自动改用其他路径规避失败。

## 3. 明确禁止

本授权不允许：

- 创建或签署任何 canonical parent-binding、repository-binding 或 P2 gate；
- 创建 experiment root 或其 source、corpus、query、gold、dependency、environment、package、receipt；
- 获取或安装依赖、创建 venv、下载 wheel；
- 准备输入、运行 preflight、smoke、benchmark 或任何实证执行；
- 发布证据、请求 P3、选择后端或准入 M8；
- 修改协议以放宽 stream、reparse、identity 或路径检查；
- 修改、删除或复用 draft-0.10 的 parent、binding、gate、identity 或其他历史记录。

## 4. 候选成功条件

目录仅在下列条件全部成立时可进入后续 P2 binding 准备：

1. 文件系统是协议允许的 NTFS/ReFS；
2. 卷根和每个组件均以 no-follow、relative RootDirectory 逐级打开；
3. 每次 open 的 stream 结果满足 draft-0.11 当前 P2 `BINDING_STREAM_ALLOWLIST`；
4. 全链无 reparse point，volume serial 一致；
5. volume root 与 parent 的 file ID、ACL SHA-256 及组件序列被精确记录；
6. 两次复验结果逐字段一致，目标目录为空；
7. protocol、P0、P1 和 identity 的字节与摘要保持不变。

创建成功和只读复验通过均不等于 P2 授权。P2 必须在后续独立步骤中，以满足协议完整引用闭包的机器可读记录表达。

## 5. 授权来源

负责人原始决定：

> owner justtodo123 授权为 draft-0.11 identity sa-m8-active-draft011-20260914-940ecec4 在 C: 卷创建并只读复验一个全新的专用 parent 环境，用于准备 P2 binding 候选。本授权不等于 P2 授权，不允许创建 experiment root、获取依赖、准备输入、执行 benchmark、发布证据、选择后端或准入 M8

本记录仅将该决定收敛为唯一候选路径、最小动作集和 fail-closed 条件，不扩张授权范围。

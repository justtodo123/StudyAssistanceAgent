# M8 `draft-0.11` P2 owner 裁定材料

- 日期：2026-09-14
- 状态：`P2_DECISION_MATERIALS_READY / OWNER_DECISION_REQUIRED / NOT_P2_AUTHORIZED`
- protocol：`docs/plans/references/m8-active-execution-protocol-draft-0.11.md`
- identity：`sa-m8-active-draft011-20260914-940ecec4`
- predecessor P1：`p1-m8-active-execution-draft011-940ecec4-r01`
- 候选 repository commit：`9e80d7e1275a835cdee9fcf5d927f094e2b7d128`

## 1. 已闭合事实

| 对象 | SHA-256 / 结果 |
| --- | --- |
| protocol | `92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d` |
| identity | `44fabea20f36165151b3e5c6bf140efdf348929399b33aa1d478a6cfec6c58a2` |
| P1 | `d60057e5ec81dad67a5706574db8bf51cc6a6fdda03f385a8621421371ad13f6` |
| parent-binding candidate | `3b237c6dfd11fd322b0761ef4b520d7e6d942d3a35ddb0eb41d0a3cec027ff9f` |
| repository-binding candidate | `91af7708a8d73ffe99e185d1cfec8efba8f09ad04768408f2e3bbfc7785bc602` |
| repository snapshot | clean commit `9e80d7e1275a835cdee9fcf5d927f094e2b7d128` |
| parent directory | 空；冻结前复验结果与前两次结果逐字段相同 |

P1 实际决定为 `AUTHORIZED / request-p2`。候选 parent 使用全新路径：

```text
C:\M8-Parents\sa-m8-active-draft011-20260914-940ecec4
```

冻结前只读复验继续得到：NTFS、volume serial `fc30cc0830cbc7ba`、parent file ID
`7ffb040000002c000000000000000000`、parent ACL SHA-256
`0229296849ad851aa453408c453e58c89fa0bcb7c21cd3940bf26b20574fdc40`，并满足 `NtCreateFile`、relative
RootDirectory、no-follow、完整共享、无 reparse point 和无不允许 stream。

## 2. 候选结构

候选 parent-binding 使用 `sa.m8.parent-binding.v1`，components 精确为：

```json
["M8-Parents", "sa-m8-active-draft011-20260914-940ecec4"]
```

候选 repository-binding 使用 `sa.m8.repository-binding.v1`，绑定上述 identity、protocol 和 clean commit；
`experiment_parent_binding` 指向该 parent。五种 publication purpose 按协议 enum 顺序全部存在，并共同引用同一已复验
parent-binding：`package`、`normal-receipt`、`nonpublication-receipt`、`abort-receipt`、`failure-receipt`。
协议要求 purpose 完整覆盖与 REF 一致，不要求五个不同物理 parent。

候选 JSON 当前仅位于仓库外 `D:\面试实习\draft011-p2-candidates-final`，不构成 canonical artifact。仓库内尚无
任何 draft-0.11 parent-binding、repository-binding 或 P2 gate。

## 3. owner 可作出的封闭裁定

### 接受

若 owner 接受上述精确候选，应明确决定：

```text
owner justtodo123 授权 draft-0.11 P2：以 clean commit
9e80d7e1275a835cdee9fcf5d927f094e2b7d128、parent-binding candidate SHA-256
3b237c6dfd11fd322b0761ef4b520d7e6d942d3a35ddb0eb41d0a3cec027ff9f 和 repository-binding candidate SHA-256
91af7708a8d73ffe99e185d1cfec8efba8f09ad04768408f2e3bbfc7785bc602 冻结 binding，并签发
AUTHORIZED / request-p3。授权范围仅为 binding，不授权建根、依赖、输入、执行、发布、后端选择或 M8 admission。
```

接受后仍须在写入前再次复验 parent、确认仓库状态与候选 commit 一致，再把 canonical bindings 和 P2 gate 一次性并行落盘，
运行专用校验器后提交。

### 拒绝

若 owner 不接受，应决定 `NOT_AUTHORIZED / stop` 并说明 finding；不得创建 canonical binding 或继续 P3。

## 4. 独立性与后续边界

P2 是 owner gate，actor 固定为 `justtodo123 / owner`，independence 固定 `false / false`，operation 仅 `["binding"]`。
P2 若接受，下一步 P3 必须由既不是 drafting party `ai-assistant`、也不是 owner `justtodo123` 的独立 reviewer 完成。
本材料不替 owner 作 P2 裁定，也不预置 P3 结论。

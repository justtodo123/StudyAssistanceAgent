# M8 `draft-0.11` P2 专用 parent 目录双次复验结果

- 日期：2026-09-14
- 状态：`PARENT_CANDIDATE_VALIDATED / P2_NOT_YET_ISSUED`
- 授权：`m8-draft011-p2-parent-environment-authorization-20260914.md`
- identity：`sa-m8-active-draft011-20260914-940ecec4`
- 目标：`C:\M8-Parents\sa-m8-active-draft011-20260914-940ecec4`

## 1. 创建结果

授权记录已先独立提交为 Git commit `fe506de`。随后创建全新专用目录：

```text
C:\M8-Parents\sa-m8-active-draft011-20260914-940ecec4
```

创建后及两次复验前后，直接子项数均为 `0`。未创建 experiment root、source、corpus、query、gold、dependency、
environment、package、receipt 或执行数据。

## 2. 两次只读复验

两次均执行：

```text
python tools/m8_parent_binding_validator.py "C:/M8-Parents/sa-m8-active-draft011-20260914-940ecec4"
```

两次退出码均为 `0`，输出 bytes 完全相同；输出文件 SHA-256 均为：

```text
69625632b8e68305ebb6ef353911b1c35400e1ca4751555e1598025e5a56b696
```

精确结果：

```json
{
  "components": [
    "M8-Parents",
    "sa-m8-active-draft011-20260914-940ecec4"
  ],
  "no_follow": true,
  "opened_by": "NtCreateFile",
  "parent": {
    "acl_sha256": "0229296849ad851aa453408c453e58c89fa0bcb7c21cd3940bf26b20574fdc40",
    "file_id": "7ffb040000002c000000000000000000",
    "filesystem": "ntfs",
    "volume_serial": "fc30cc0830cbc7ba"
  },
  "root_directory_relative": true,
  "share_mask": "read-write-delete",
  "volume_root": {
    "acl_sha256": "9883229953ef0673df9d964decd6f2363795c46090c20a397a006c4ff7a8c6ea",
    "file_id": "05000000000005000000000000000000",
    "filesystem": "ntfs",
    "volume_serial": "fc30cc0830cbc7ba"
  },
  "walk": "volume-root-component-walk"
}
```

## 3. 核验结论

- 文件系统为允许的 `ntfs`；
- volume root 与 parent 的 volume serial 均为 `fc30cc0830cbc7ba`；
- 使用 `NtCreateFile`、volume-root component walk、relative RootDirectory、no-follow 与完整共享；
- 卷根与每个目录组件均未遇到 reparse point 或不允许的 stream；
- 两次 parent file ID、ACL SHA-256、volume root identity 与组件序列逐字段相同；
- 专用目录在复验期间保持为空。

## 4. 边界

本记录只证明该物理目录在两次只读复验时满足 parent-binding 候选条件。它不是 canonical
`sa.m8.parent-binding.v1`、`sa.m8.repository-binding.v1` 或 P2 gate，不产生 `AUTHORIZED / request-p3`，也不授权
创建 experiment root、获取依赖、准备输入、执行、发布、选择后端或准入 M8。目录状态若变化，后续冻结前必须重新复验。

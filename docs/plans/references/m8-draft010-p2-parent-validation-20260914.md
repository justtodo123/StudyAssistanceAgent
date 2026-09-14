# M8 `draft-0.10` P2 专用 parent 目录复验结果

- 日期：2026-09-14
- 状态：`PARENT_CANDIDATE_VALIDATED / P2_NOT_YET_ISSUED`
- 授权：`m8-draft010-p2-parent-environment-authorization-20260914.md`
- 目标：`C:\M8-Parents\sa-m8-active-draft010-20260914-5d10f2a1`

## 1. 创建结果

授权记录提交后创建：

```text
C:\M8-Parents\sa-m8-active-draft010-20260914-5d10f2a1
```

创建完成后目录为空（直接子项数为 0），未写入 source、corpus、query、gold、dependency、environment 或执行数据。

## 2. 只读复验

命令：

```text
python tools/m8_parent_binding_validator.py "C:/M8-Parents/sa-m8-active-draft010-20260914-5d10f2a1"
```

退出码：`0`。

精确结果：

```json
{
  "components": ["M8-Parents", "sa-m8-active-draft010-20260914-5d10f2a1"],
  "no_follow": true,
  "opened_by": "NtCreateFile",
  "parent": {
    "acl_sha256": "0229296849ad851aa453408c453e58c89fa0bcb7c21cd3940bf26b20574fdc40",
    "file_id": "24fd05000000e5000000000000000000",
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

卷根与 parent 的 volume serial 相同；文件系统为 NTFS；逐级 relative RootDirectory、no-follow、完整共享均成立；
未遇到 reparse point 或不允许的 stream。

## 3. 链状态更正

本次复验后，在准备 P2 binding 时发现已提交的初版 `draft-0.10` identity/P1 不符合 B1/C2a 后的精确 schema：
`forbidden_history_ids` 为字符串数组而非 `{id,ordinal}` 对象数组，且 nonce 只有 32 个十六进制字符。
该问题见 `m8-draft010-p1-schema-defect-20260914.md`，已通过并行 `-r02` 记录纠正，旧记录未改写。

因此，后续 P2 只能引用：

- `external-gates/p1/p1-m8-active-execution-active-draft010-5d10f2a1-r02.json`
- `external-artifacts/identity/sa-m8-active-draft010-20260914-5d10f2a1-r02.json`

## 4. 边界

本材料只证明该专用目录当前满足 parent identity 的只读复验条件。它不单独构成 repository binding、P2
`AUTHORIZED / request-p3`、experiment root 创建权限或执行权限。目录状态若变化，必须重新复验。

# M8 Metadata Discovery Governance Tests

本目录验证 Metadata Discovery 的离线治理边界，不执行 metadata request、DNS、网络、下载、解析、安装、collector 或其他 M8 stage。

## 范围

- canonical JSON、严格类型、重复键、非有限数字和 surrogate 拒绝；
- committed Git object、blob、字节数和摘要绑定；
- package/tooling/API/dependency/history 证据不被误选为发行包身份；
- exact authorization token 仅作为 predicate，不能开启任何执行；
- current effective limits、execution counts 和 `m8_status` 的 failed-closed 约束；
- reviewer 只能返回 ready-for-external-review，不产生 Owner approval。

## 命令

```bash
python -m pytest tests/M8_metadata_discovery -v
```

测试使用显式当前 Git commit 的 committed objects；不会把 worktree 中的 untracked 文件作为证据。

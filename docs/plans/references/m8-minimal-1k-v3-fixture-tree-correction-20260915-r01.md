# M8 v3 fixture-tree 摘要更正记录

- correction_id：`m8-v3-fixture-tree-correction-20260915-r01`
- 原记录：`m8-minimal-1k-v3-s0-independent-audit-20260915.md`
- 原审查材料：`m8-minimal-1k-v3-s0-review-materials-20260914.md`
- 适用 reviewed object：`50bea24df515f8d2956f619b2b92844f5f6eb194`

## 事实核验

对 reviewed object 与当前工作区执行两条独立读取路径（工作区 `Path.read_bytes()`、Git `ls-tree/show`）后，均得到相同结果：

```text
fixture-tree-v1
SHA-256: 6d4a2d16ba97b90331ec796daf6869356737a7256935130381653ce6c9fb1b8a
files: 90
bytes: 41519
```

两条路径的文件集合相同，逐文件字节差异为 0。因此没有证据表明 reviewer 审查了另一份 fixture tree。

## 更正结论

原审查材料第 21 行记录的摘要：

```text
51d7723caf5a77f90d64baf6210d49e948fa8420be3daab03a5cc58dc39963e2
```

与 reviewed object 的实际 fixture tree 不一致。该记录应视为**起草阶段摘要记录错误或对应未提交版本**，不能表述为 reviewer 审查内容与实际材料不一致。

原拒绝记录保持原字节不动；本文件是并行更正记录，不撤销原 S0 裁定。由于 JSONL canonicalization 缺陷已经由 `m8-v3-s0-002` 独立确认，v3 S0 仍保持 `PROTOCOL_REJECTED / stop`，直到新修订对象重新经过独立 S0。

## 修订后冻结值

修订后的 S0 review package 应使用：

```text
e09c1e45eab38f72e9cc92e128f50d5e3ec4440d0d7d29f113c7617a57cd250a
```

该值对应完成 JSONL canonicalization 修复并重新生成 fixture 后的当前 tree：90 files / 41519 bytes。它不能回写到旧版审查记录，只能用于新的并行 review package。

# M8 active execution protocol `draft-0.1` P0 前技术审查记录

- 审查日期：2026-09-11
- 审查对象：`m8-active-execution-protocol-draft.md` 的 `draft-0.1`
- 审查类型：P0 前只读技术口径审查
- 负责人处置：按审查建议修订
- 最终结论：**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**

## 1. 通过项

`draft-0.1` 与八项已批准 M8 Decision 总体一致：SQLite/M7 是控制面权威，SQLite linear 是 oracle/fallback，
LanceDB 仅为 active candidate，Qdrant/Milvus/并发/云端不在本轮范围；1K/10K/100K、synthetic-only、hard gates、
P0–P9 分离和 M8 `BLOCKED / NOT_STARTED` 边界方向正确。

## 2. 退回原因

1. 100K query manifest 只有 1,000 条，但每 repetition 需要 100 warmup + 1,000 measured，分母和重复规则未定义；
2. raw evidence 在 cleanup 中删除，但 durable sanitized evidence publication 没有独立授权节点，P8/P9 无稳定引用；
3. 冻结 CPython 3.11 launcher digest 虽匹配，但当前继承环境导致 `SRE module mismatch`，缺 launcher health contract；
4. 草案冻结 `%TEMP%` 在 C:，但审查时实际 `%TEMP%` 位于非 C: 卷，实验根和卷门禁自相矛盾；
5. `lancedb-embedded-exact` 只验证 exact/flat，却未明确不能外推 ANN；
6. query/build/lifecycle sample 与 child process 单位、gold 生成预算、canonical input bytes 和 acquisition 网络边界需要明确。

## 3. 处置边界

`draft-0.1` 未被 P0 接受，不创建 experiment/protocol ID，不建立 binding，不建根、不安装依赖、不生成 harness/input、
不执行 benchmark。其原始文本保存在 `m8-active-execution-protocol-draft-0.1-returned.md` 仅作历史追溯，不得用于未来
binding 或授权。

修订版必须保持新的文档修订号，完成上述阻断修复后重新接受 P0 审查。修订不自动批准 P0，也不授权 P1–P9。

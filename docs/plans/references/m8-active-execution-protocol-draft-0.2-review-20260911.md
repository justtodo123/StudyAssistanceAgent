# M8 active execution protocol `draft-0.2` P0 技术口径审查记录

- 审查日期：2026-09-11
- 审查对象：`m8-active-execution-protocol-draft.md` 的 `draft-0.2`
- 封存原文：`m8-active-execution-protocol-draft-0.2-returned.md`
- reviewed/archived SHA-256：`9fe455c9efcca49c2d9120af6ac2d1192b7c396e901d2b92991337e6d21b4923`
- 审查类型：`P0_TECHNICAL_SCOPE_REVIEW`
- 负责人处置：按审查建议形成 `draft-0.3` 后重新执行独立 P0 审查
- 最终结论：**`RETURNED_FOR_REVISION / P0_NOT_ACCEPTED`**

## 1. 已闭合方向

`draft-0.2` 保持了八项已批准 M8 Decision 的方向：SQLite/M7 是控制面权威，SQLite linear exact 是
oracle/fallback，LanceDB 仅是 exact/flat active candidate；Qdrant、Milvus、ANN、并发、云端均不在本轮范围。
1K/10K/100K、synthetic-only、hard gates、P0–P9/P7A 分离和 M8 `BLOCKED / NOT_STARTED` 边界正确。

它也修复了 `draft-0.1` 的 query 分母、独立 evidence publication 节点、launcher health、TEMP 卷假设、
exact/flat 外推和部分 sample/canonical input/acquisition 边界，但尚不足以成为可机械执行和独立核验的协议文本。

## 2. 按优先级排列的退回原因

1. **协议 blob 与外部授权记录未彻底分离**：协议本体仍包含当前状态、null identity/binding 字段和待负责人填写的
   P0–P9/P7A 表。协议字节会随审批事实变化，无法让外部记录稳定绑定一个不可变 reviewed blob。
2. **canonicalization 与 schema 不完整**：仅冻结 machine report 顶层 key，未为所有嵌套对象、输入清单、独立核验、
   durable package、cleanup receipt 和 external gate reference 定义完整类型、required、enum、nullability、唯一性与
   `additionalProperties=false`；也未闭合 duplicate key、有限小数、数组排序和 reserialize-byte-equality。
3. **lifecycle 不是可执行状态机**：现有箭头流程没有 current state、actor、precondition、allowed write set、failure
   transition 与唯一 next state，且 `L5` 与正文链路不一致，无法机械阻止越级、补跑或 evidence splice。
4. **Windows 安全模型仍以 resolved path 为主**：缺少 parent/descendant handle-relative open、no-follow/open-reparse-point、
   打开后 file identity 复验、sharing mode、rename/delete-by-handle 和完整 TOCTOU 失败语义。
5. **query/gold 唯一生成证明不足**：hash preimage 没有长度前缀与完整 domain separation；各 role 的目标选择并非来自
   一次无放回分区，尚不能机械证明 query ID、target identity 和 gold entry 的全局 disjointness/bijection。
6. **fault inventory 不是完整原子枚举**：`corrupt manifest/index` 与 `interrupted publish/cutover` 各自合并了两个不同
   故障，导致 fixture 数、适用范围、injection point、expected code、probe 数和责任边界无法逐项复算。
7. **预算与 deadline 未闭合**：gold、acquisition、preflight、provisioning、child、query、lifecycle、fault、publication、
   verification、cleanup、terminate/kill 以及 file/process/handle/log/report 等预算仍存在缺项或未冻结值。
8. **exact/flat 公平采样与 index provisioning 不完整**：未冻结 counterbalanced backend 顺序、每次从同一 corpus 建立
   独立新 index、cache 边界、provisioning 与 query timing 分离、scalar index 政策及无 ANN 的机械证明。
9. **P7A package 与 cleanup receipt 的最终权威关系不唯一**：现有文本允许 companion receipt 或 package 预留 receipt，
   并在 cleanup 后“finalize package digest”，与 package write-once 冲突；P8/P9 缺少必须同时引用两个不可变 digest 的规则。

## 3. 处置与零授权边界

`draft-0.2` 未被 P0 接受。其精确原文保存于
[`m8-active-execution-protocol-draft-0.2-returned.md`](m8-active-execution-protocol-draft-0.2-returned.md)，
只作历史追溯，不得用于未来 binding 或授权。任何基于该 blob 的 identity、binding、root、source、input、report 或结果
均无效。

本次退回和后续 `draft-0.3` 起草均不创建 experiment ID、executable protocol ID、repository binding、实验根、venv、
wheel cache、source、harness、corpus、query/gold、report、package 或 cleanup artifact；不安装依赖，不执行 benchmark，
不修改 M8 registry，不准入 M8，不授权生产开工，也不选择 LanceDB。

在 `draft-0.3` 取得绑定其精确字节的独立 P0 PASS 前，P1–P9 与 P7A 全部保持 `OPEN`。修订本身不批准 P0；
`draft-0.3` 必须重新接受技术口径审查，且 reviewer 不得在同一审查中修改被审协议。

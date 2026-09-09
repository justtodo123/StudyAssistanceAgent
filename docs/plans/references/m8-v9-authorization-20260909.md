# V9 授权记录：`sa.m8.admission-evidence.v9`

- experiment ID：`sa.m8.admission-evidence.v9`
- protocol：`precommit-v9`
- 日期：2026-09-09
- 状态：**`NOT_AUTHORIZED`**

本文件仅记录 V9 的失败治理身份和未授权状态，不是负责人书面授权，不允许执行任何阶段。V9 source tree 已在
source freeze 前的作者侧只读复核中发现阻断缺陷；该复核不是独立静态审计，未产生 `PASS`，当前 V9 根不得修复、
恢复、补审、重跑或复用。

## 当前边界

- V9 未取得独立静态审计 `PASS`，不能创建或使用执行 gate。
- V9 身份与原根已永久冻结且不可复用；不得为 V9 补发 `PASS`、恢复原根或授予 preflight、venv、依赖获取、
  acquisition、smoke、full、benchmark 等任何后续阶段授权。
- 任何后续尝试必须使用全新的递增身份；当前治理上下文指向 V11，而非 V9。V11 的
  root-provenance/source-authoring 阶段必须先取得明确书面授权；独立静态审计 `PASS` 后，preflight 与后续执行
  阶段仍须另行取得明确书面授权。
- V8 的历史授权已消费并失效，不能授权 V9，也不能授权任何后续实验。
- V9 只能使用合成预编码向量；禁止读取、复制或索引 `D:\111_Others_Subjects`，禁止启动 Qdrant server、
  container、网络服务或持久服务。
- 不产生后端选择、候选排名、Decision 关闭、M8 admission、生产实现、commit、merge 或 push 授权。

## 后续若申请授权必须重新确认

后继授权必须按阶段区分，不能把创建待审 source tree 与审计 `PASS` 写成循环前置：

- 初始 root-provenance/source-authoring 授权至少应明确后继递增 experiment/protocol（当前为
  `sa.m8.admission-evidence.v11` / `precommit-v11`，而非已永久冻结的 V9）、唯一系统临时根、允许生成和冻结的
  source-only 范围、合成数据与路径/网络边界，以及禁止的后续阶段。
- 只有 source tree 冻结并取得独立静态审计 `PASS` 后，后续授权才可明确允许的具体阶段
  （preflight/acquisition/smoke/full）、精确依赖版本、冻结磁盘预算、失败终态、cleanup/residual 要求及禁止的
  生产影响。

上述任一授权都不得恢复或授权 V9；本记录保持 `NOT_AUTHORIZED`。

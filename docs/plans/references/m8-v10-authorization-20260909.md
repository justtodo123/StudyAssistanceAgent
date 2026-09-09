# V10 授权记录：`sa.m8.admission-evidence.v10`

- experiment ID：`sa.m8.admission-evidence.v10`
- protocol：`precommit-v10`
- 日期：2026-09-09
- 状态：**`NOT_AUTHORIZED`**

本文件仅记录 V10 的治理身份和默认拒绝状态，不是负责人书面授权，不允许执行任何阶段。V10 根曾在本记录仍
禁止创建期间被错误创建，现已登记为 `PRE_SOURCE_GOVERNANCE_INVALID`；该根不得修复、补审、清理后继续、
重算、重判、恢复、重跑或复用。根内除首个 `root-provenance.json` 外未写入 source 或其他实验 artifact，且不得
再向其中写入任何内容。

## 必须先满足的条件

- V9 pre-freeze static-audit failure 已永久封口；V8/V9 根、源码、harness、venv、artifact 和授权均不可复用。V10
  只能绑定 V9 去敏处置 digest `f0590baaf24a187db010539f8d5e2ebfbf19616cfc3cae43dd431202a8a16eb6`，不得绑定
  V9 root artifact。
- 未来有效尝试必须递增为 `sa.m8.admission-evidence.v11` / `precommit-v11`，并先取得明确指向 V11
  root-provenance/source-authoring 阶段的负责人书面授权，然后才可从全新不可预测 system-temp root 的 canonical
  root provenance 开始；V10 authorization 不得继承。source-only provenance 和独立静态审计必须分别完成并
  独立记录。
- 独立静态审计取得 `PASS` 前，不得执行 preflight、创建 venv、获取或安装依赖、acquisition、smoke、full 或
  benchmark。独立 `PASS` 也不会自动授权后续阶段。
- 仅允许 synthetic-only、offline、local-path-only 范围；禁止读取、复制或索引 `D:\111_Others_Subjects`，
  禁止 server/container/listener/network service。
- V10 root disposition canonical payload 的 SHA-256 为
  `1a7043b78e51d293ba5e0d37a7e0bfc409b05f0ba7d0bfb20010dea34aa8d4e9`；该 digest 仅绑定去敏治理事实。

初始 V11 授权必须明确新的 experiment/protocol、唯一临时根、root-provenance/source-authoring 范围、合成数据与
路径/网络边界，并禁止 preflight 与执行。只有冻结 source tree 且独立静态审计 `PASS` 后，后续授权才可另行明确
允许的阶段、精确依赖版本、冻结预算、失败终态、cleanup/residual 要求和禁止的生产影响。V10 authorization 仍保持
`NOT_AUTHORIZED`、未消费，不能授权 V10 或任何后继实验的动作。

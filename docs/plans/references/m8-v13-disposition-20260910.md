# M8 V13 草案处置记录

- experiment ID：`sa.m8.admission-evidence.v13`
- protocol：`precommit-v13`
- 处置日期：2026-09-10
- 负责人：`justtodo123`
- 处置依据：本会话在八项 M8 Decision 逐项批准后，对 V13 与 100K 新目标的适配性选择
- 最终状态：**`SUPERSEDED_UNBOUND_DRAFT / NOT_AUTHORIZED / NEVER_EXECUTED`**

## 1. 处置结论

负责人确认停止 V13，并为重构后的 M8 规划全新实证协议身份。V13 永久停留在未绑定草案层：

- repository binding 从未建立；
- 未创建 S/A/G/E 根；
- 未 author/freeze V13 source；
- 未运行 preflight、venv、dependency acquisition、smoke、full 或 benchmark；
- 未选择 LanceDB、Qdrant 或其他后端；
- 未产生 M8 admission 或生产实现授权。

V13 文本及其文本审计可继续作为历史治理参考，但不得在补字段、修订、重新审计、binding 或清理后恢复使用。

## 2. 停止原因

2026-09-10 获批的 M8 范围已从旧的 1K/3K/10K 比较扩展为：

- `1k-correctness`；
- `10k-single-user`；
- `100k-capacity`；
- `100k-filtered`；
- 经负责人确认才执行的 `100k-concurrent`。

现有 V13 只聚焦修复 V12 的四项机械证据缺陷，未冻结上述 workload、100K 资源预算、真实质量指标、完整
embedding profile binding 和新候选政策；它不能作为完整 M8 实证协议。详细分析见
[`m8-v13-scale-fit-assessment-20260910.md`](m8-v13-scale-fit-assessment-20260910.md)。

## 3. 不可复用边界

以下 V13 身份与治理对象不得用于未来实证：

- experiment ID `sa.m8.admission-evidence.v13`；
- protocol ID `precommit-v13`；
- 未来 binding 占位符、revision、digest 或 path；
- 任何以 V13 名义创建的 root、nonce、source、manifest、inventory、audit、gate 或 execution artifact。

截至处置时上述运行对象均不存在；本条只防止未来复用，不声称执行过清理或运行期验证。

## 4. 新协议规划边界

新的 M8 实证协议必须使用全新 experiment/protocol 身份，并重新完成：

1. 冻结最终目标、workload、数值门槛和最终仓库路径；
2. 把协议纳入不可变 Git commit；
3. 对该 commit 中指定路径的原始 Git blob bytes 计算 SHA-256；
4. 创建负责人授权的 repository binding record；
5. 独立验证 path、revision、blob digest 与协议身份；
6. 另行取得仅限 S root/source-freeze 的授权；
7. 按 `S freeze → A independent audit PASS → release authorization → G gate → execution authorization → E`
   分离推进。

新协议至少覆盖 SQLite oracle、LanceDB 第一候选、1K/10K/100K 分层 workload、embedding profile binding、
parity、lifecycle、资源、cleanup 和失败终态。Qdrant 不参与 M8 本地默认选择；100K synthetic evidence 不得冒充
真实生产语料质量。

## 5. 状态边界

本处置不批准新协议文本、协议身份、binding、source authoring、依赖安装、执行、后端选择、M8 admission、生产实现、
commit、merge 或 push。M8 继续 `BLOCKED / NOT_STARTED`；八项 Decision 已 `RESOLVED`，但后端选择和阶段批准仍为空。

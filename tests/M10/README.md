# M10 自主 Runner 与写副作用测试

M10 计划 §5 步骤 1 交付的是**拒绝路径**：写权限、确认令牌、幂等键与副作用台账的
**拒绝面**先落地，接受面存在但生产上**没有任何东西能到达它**——`RUNNER_WRITE_TOOL_ALLOWLIST`
冻结为空，且这些模块**尚未接入 `main.py`**（无路由、无开关、无后台 worker）。

`M10-AUTHORITY` 的边界是结构性的：runner 只拥有 job / checkpoint / ledger 状态，放在**独立**的
SQLite 文件里；它**不 import** 领域仓储，也不引用领域写方法。状态机仍是正式默认。

> **口径（易写错）**：判据是「不触碰**领域**库」，**不是**「不用 `sqlite3`」。
> `M10-CHECKPOINT` 已裁定 runner 状态放独立文件，故 `effect_ledger.py` **必然** import `sqlite3`
> 并自建库——那是它自己的库。把判据写成「不用 sqlite3」会是一条错的守卫。

## 文件

| 文件 | 覆盖 |
|------|------|
| `test_write_authorization.py` | 写权限默认拒绝（生产 allowlist 为空 ⇒ 什么都注册不了）、写 allowlist 与只读 preview allowlist **不相交**、注册期拒绝非幂等/非写工具、执行期拒绝缺写能力 / 无令牌 / 令牌绑定到别的 job 或 tool / **同令牌配不同参数** / 已撤销授权；审计**追加式**且只留参数**摘要**（用例断言参数原文不出现在审计里）；六态跃迁合法性；幂等键派生对四个输入分量都敏感。另含两条**上游契约钉桩**——`ToolSpec` 拒绝 `WRITE + SideEffect.NONE`、以及 preview 名字走不到写注册表——因为那两条在本模块里是**不可达**的，写重复检查只会得到一条永不执行的「守卫」 |
| `test_effect_ledger.py` | 独立文件 + 版本化 `runner_meta`（family + 数值版本，不匹配即 fail closed）、重开幂等、job 唯一、**`pending` 先于领域写入**（崩溃窗口的闭合点）、同键重放**返回已记录 effect 而非再建一条**、同键不同参数判冲突、非法跃迁被拒且历史追加式、checkpoint 每 job 单调且序号冲突被拒、**schema 里没有存放参数/结果原文的列**（隐私是结构性的）、使用台账后学习状态库**逐字节未变** |
| `test_runner_service.py` | 步骤 6 的生产接线：**默认关闭是结构性的**——`SA_RUNNER` 未设时服务不构造、`/api/v1/autonomous-runs` 不在 OpenAPI 文档里（该前缀在 M6a 契约中是保留的 *forbidden* 前缀），且既有状态机路径逐条仍在；反面用例证明开关打开时路由**能**出现。写经领域服务、**同一写两次是重放而非第二次写**（领域调用计数保持 1）、缺写能力或令牌参数不符**都到不了领域**；**kill switch 在效果边界生效**（写前叫停 ⇒ 领域零调用；写中叫停 ⇒ 效果**保持未决**交给 reconcile，不替它编答案；有界 job 中途叫停 ⇒ 报告为 `JOB_KILLED` 停止而**不是** `step-failed`）；回滚 = 关掉开关后既有记录仍可读可分类；状态**不含参数、路径或用户数据**。**注意**：本文件会 import 启用态的 `app.main`，故 `load_main` fixture 每次用完都**放回原模块对象**。**重新 import 不够**——那会造出第二个模块对象：后续阶段要么看到不该有的路由（M6a 的精确公开面契约），要么更隐蔽地让**依赖替换打在另一个对象上而真实服务照跑**（`tests/M5b/` 是模块级 `from app.main import app` + 字符串 `patch("app.main._study_sessions")`）。这个坑实测把全量从 3 failed 变成 6 failed |
| `test_reconcile.py` | reconcile / 补偿 / 人工介入：present ⇒ applied、absent ⇒ failed、**unknown ⇒ defer 而非猜**（既不 applied 也不 failed，仍留在 `pending`）；**第二次 sweep 无事可做**（幂等性以可观测性质表述：`examined == 0` 且台账不增长）；**重复 defer 有界升级**而非死循环；**已升级的 effect 不会被后续 sweep 收敛**（否则升级就只是建议）、`open_interventions()` 是它唯一的出口、**人工裁定是它唯一的移动方式**；补偿把 `applied` 移到 `compensated`，但**对从未 apply 的 failed effect 不谎称已撤销**；台账 **v1 → v2 迁移**（步骤 5 是第一个真正需要迁移的改动）保留数据，且**未来版本仍被拒绝**（迁移的反面） |
| `test_generation_publication.py` | **「无半发布 generation」断言**（前两步刻意没做的那条，到这里才适用）：generation id **由 manifest 摘要派生**（同一输入 ⇒ 同一 generation，顺序无关，reindex 不 churn 身份）；读取方**复验磁盘上的 manifest 能否重现它声称的 id**，故半写目录与「指针指向内容没落地的 generation」都**不可见**而非部分可见；`stage` 拒绝数量或摘要不符的 units；`publish` 拒绝重复发布；`resume` 在输入摘要变化时**丢弃 checkpoint 记录的那个暂存目录**并 fail closed（未变化时仍能继续——反面也钉住）。**每个发布 crash point 都断言**：可见的要么是旧 generation 的**完整**内容、要么什么都没有，且可见 generation 的 manifest 计数与其声明一致 |
| `test_job_envelope.py` | 通用异步 job：**预算三分类**（`ENFORCED_LOCALLY` 由步进循环强制 / `ENFORCED_ELSEWHERE` 由台账 `purge_expired` 强制 / `NOT_ENFORCED_LOCALLY` 明示不强制）——分区断言保证**新增字段无法不被归类**，并对循环强制的每一项做**行为化**验证（真的把 job 停下且提前停下，而不是名字出现在源码里）；`ENFORCED_ELSEWHERE` 的名字必须**能解析到真实可调用对象**。另含：有界 job 完成并报告进度、失败步进不逃逸、**取消在每个步进边界检查**（含「取消优先于预算」的确定性顺序）、并发槽**确实被持有**（非空转）且**失败路径也释放**、预算**只能收紧**、job 状态**不含工作区路径或用户数据** |
| `test_recovery.py` | **十个 crash point** 逐个行使：`proposed`/`authorized`/`mid_checkpoint` 上的崩溃 ⇒ 领域写入**从未发生**、resume 判 `crashed-before-apply` 而**不盲目重放**；`mid_apply` 上的崩溃 ⇒ 台账停在 `pending`，**只由领域对账**判定落没落（absent/present 两侧都测）；`after_apply_before_ledger` ⇒ 写入已落但台账不知，resume 对账而非假设；`after_ledger_before_checkpoint` ⇒ 台账已 `applied`，resume 无事可做。另含：**磁盘满 / provider 超时**经领域写入抛出而 fail closed、**取消意图**先落盘再崩溃故 resume 必须拒绝、**撤销**在崩溃窗口内到达则拒绝、revalidation 拒绝、**重放返回已记录 effect 且领域写入次数保持 1**、poison 阈值（三个**不同** effect 失败才触发；同一个 effect 重试**不会**累积——并把这个反面也钉成用例）、不可补偿失败是**独立终态**而非可重试的 failed |
| `test_authority_boundary.py` | 源码级**动态枚举** `platform/app/` 全部 `*.py`：写 `study_sessions` / `answer_attempts` 的模块**恰好**是 `learning_store.py`；导入领域仓储的模块**恰好**是已知集合（runner 模块不在其中）；runner 模块不引用领域写方法名；台账模块不读 `LEARNING_STORE_PATH`。含检测器正反对照与**非空性**断言。闭包由 `tests/M9/test_mastery_write_authority.py` 承担，本文件钉住那条护栏仍然存在 |

## 关键约定

- **默认关闭是恒等操作**：这些模块未接入任何路由或开关。接入属 §5 后续步骤，且须先有
  `M10-ROLLOUT` 的 kill switch 语义。
- **拒绝优先**：本步骤交付的每一条路径都是「拒绝」，接受面只有测试通过**注入**的 allowlist 才可达。
- **只留摘要**：台账与审计**只**保存 `argument_digest` / `result_digest`，不保存参数或结果原文。
- **独立库的代价已计入**：跨库事务不可用 ⇒ outbox + reconcile 是**必需项**，故 `pending_effects()`
  是台账的对外接口之一，而不是可选优化。

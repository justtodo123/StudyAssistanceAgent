# M8 Reviewer-Fixer 双阶段审查模式决定

- decision_id：`m8-reviewer-fixer-two-stage-20260915`
- owner：`justtodo123`
- status：`ADOPTED_FOR_NEXT_CYCLE / NOT_S1_AUTHORIZATION`
- predecessor：`m8-minimal-1k-v3-s0-rereview-audit-20260915-r02.md`

## 决定

从 r02 之后的下一轮开始，M8 最小 1K 协议采用 Reviewer-Fixer 双阶段模式，不再为修复阶段发现的每一个小问题分别创建完整 S0 拒绝—打包—复审循环。

### 阶段 A：Reviewer-Fixer

Reviewer A 可以独立读取当前候选对象、发现问题并自行修改代码、测试和材料，持续执行“发现—修复—回归—自查”，直至其认为不存在已知阻断。

Reviewer A 第一次修改候选对象后，角色立即转为：

```text
reviewer-fixer / remediation author
```

其最终输出只能是：

```text
REMEDIATION_COMPLETE
SELF_CHECK_PASS
allowed_next_action: request-independent-s0
```

Reviewer A 不得对自己修改后的候选对象签署 `PROTOCOL_ACCEPTED`。

### 阶段 B：最终独立 Reviewer

Reviewer B 必须未参与候选对象修改，只读审查 Reviewer A 冻结的最终 commit。Reviewer B 才能作出：

```text
PROTOCOL_ACCEPTED / request-s1
```

或：

```text
PROTOCOL_REJECTED / stop
```

若 Reviewer B 自行修改对象，其身份也立即转为 fixer；该修订对象必须交给 Reviewer C 或其他未参与修改者终审。

## 当前修复批次

Reviewer A 应至少闭合 r02 的两个 finding：

1. `m8-v3-r02-s0-001`：从最终候选 commit 的 Git object bytes 自动生成并核验全部完整摘要；不得手工复用旧摘要或截短摘要；
2. `m8-v3-r02-s0-002`：harness 的 `missing-final-lf` 与 `empty-observer` 必须同步 observer summary、run-report、validation-report、S2、S3 的全部受影响 REF，并断言拒绝原因来自非空/最终 LF 约束，而不是 stale digest、byte count、event count 或 REF。

Reviewer A 可在同一修复周期内处理其新发现的同类缺陷，无需每项另建正式 S0 拒绝记录，但必须在修复日志中记录发现、修改、测试和剩余风险。

## 候选冻结要求

Reviewer A 完成后必须：

1. 先冻结最终候选代码 commit；
2. 从该 commit 的 Git object bytes 自动生成对象摘要和 fixture-tree 摘要；
3. 在干净临时副本中运行五个持久 graph 与完整 mutation harness；
4. 对关键 mutation 检查具体目标错误消息，并确认没有 stale digest/REF 错误；
5. 生成独立修复报告和最终 S0 材料；
6. 材料提交不得修改被审对象；若对象发生变化，旧材料自动失效；
7. 明确所有已知限制和延期到 S1 的配置；
8. 请求 Reviewer B 只读终审。

## 停止条件和审查重点

修复阶段达到以下条件后停止扩张并交终审：

- r02 已知 findings 已闭合；
- 五个持久 graph 行为符合预期；
- mutation 因目标约束而失败，而非仅因陈旧引用；
- 干净临时副本可重放；
- 摘要与 Git object bytes 一致；
- 未发现能把失败事实伪装为成功证据的 fail-open；
- 非安全关键的格式、命名、文档美观问题不阻断交审。

最终独立 S0 重点阻断安全边界失效、证据伪造、不可重放和组合不可满足；不以不影响结论的纯格式瑕疵无限延长循环。

## 不变边界

- 历史授权、拒绝和审查记录不得就地改写；
- 当前 r02 仍为 `PROTOCOL_REJECTED / stop`；
- 本决定不签发 S1；
- 不允许创建真实 experiment identity、实验根或 venv；
- 不允许安装 LanceDB、生成真实 1K 输入或运行 SQLite/LanceDB；
- Reviewer-Fixer 的自查通过不自动授权 1K、10K、后端选择、生产修改或 M8 admission；
- 最终 Reviewer B 接受后也仅可向 Owner 请求 S1。

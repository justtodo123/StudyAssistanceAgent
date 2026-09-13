# M8 active execution protocol `draft-0.10` P0 材料说明

- 说明对象：`draft-0.10` 的独立 P0 技术口径审查所需材料
- 说明日期：2026-09-13
- 负责人：`justtodo123`
- 上游依据：同日的 `draft-0.10` 修订授权
  [`m8-active-execution-protocol-draft-0.10-authorization-20260913.md`](m8-active-execution-protocol-draft-0.10-authorization-20260913.md)
  与协议修订提案 [`m8-protocol-revision-proposal-20260913.md`](m8-protocol-revision-proposal-20260913.md)
- 材料状态：`MATERIALS_PREPARED / P0_PENDING_INDEPENDENT_REVIEW / NOT_AUTHORIZED`

## 0. 治理事实声明（必读）

1. 本说明**不是**审查记录，**不是**门禁记录，**不是**授权，也**不**修改协议正文。
2. 本说明**不预置** `draft-0.10` 的 P0 结论。凡涉及"是否接受"的判断，本说明一律不予回答，只在
   §4 列出该判断**所依据的可复验事实**，供 reviewer 自行裁定。
3. **起草方（AI 助手）已参与 `draft-0.10` 的起草**：四项修订的实施、其字节归档、以及本说明所引各项
   事实的测算脚本，均由起草方产出。因此**起草方不能担任 `draft-0.10` 的 P0 reviewer**，
   其任何自检结论在本轮中只能作为**参考输入**，不构成独立性证据。
4. 本说明的受众是负责人 `justtodo123`，其已于 2026-09-13 被指定为 `draft-0.10` 的独立 P0 reviewer。
5. `draft-0.10` 目前处于 `DRAFTED / PENDING_P0_REVIEW / UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`。

## 1. 被审对象（精确字节）

| 项 | 值 |
| --- | --- |
| 路径 | `docs/plans/references/m8-active-execution-protocol-draft-0.10.md` |
| 字节数 | **186129** |
| SHA-256 | **`b5bc5088486079971eba28efe5cd2d7ed90c73a1359a87d9bca4722c473caa39`** |
| 行尾 | 纯 LF（受 `.gitattributes` 逐文件规则保护，见 §3 D1a） |
| 工作区与仓库是否一致 | **一致**（D1a 生效后不再有 CRLF 检出差异） |

**上表是本次 P0 审查的唯一被审对象。** `draft-0.9` 与 `draft-0.5` 不是本次被审对象，其字节见 §3 D1a。

## 2. 独立性基础（供 reviewer 自行确认）

按协议要求，P0 的 `independence` 为 `{required:true, satisfied:true}`，其成立依赖**主体分离**而非工具：

| 主体 | 是否参与 `draft-0.10` 准备 | 说明 |
| --- | --- | --- |
| 负责人 `justtodo123` | **否** | 批准了修订授权，但未起草协议文本、未编写任何修订或核验脚本、未产出本说明 |
| 起草方（AI 助手） | **是** | 实施四项修订、形成字节归档、编写全部核验脚本与本说明 |

"批准授权"与"审查协议文本"是两项不同的行为。`draft-0.5` 与 `draft-0.9` 的既有 P0 先例均采用
"负责人以 `independent-reviewer` 署名"的同一安排。

**reviewer 须自行判断该项是否成立，并在记录中写明依据。** 若判定不成立，应如实记为
`P0_NOT_ACCEPTED`——`draft-0.9` 的 `-r01` 正是这样一条记录，先例表明这在本仓库是可接受的结果。

## 3. 四项修订的可复验事实

以下事实由 `tools/m8_verify_proposal_claims.py`（19 项）与 `tools/m8_verify_authorization_claims.py`（含
D1a 后状态断言）机械复验，两项脚本均全部通过。**reviewer 应独立重跑**，不采信本说明的转述。

### A1 —— P2 的 stream 复验在阶段顺序上不可满足

修订前的事实（缺陷本体，已由提案与授权记录记载）：

- §7 的 per-open stream 复验要求按 `allowed_system_streams` 判定本次 scope 的 `observation`；
- `allowed_system_streams` 属于 `sa.m8.child-allowlist.v1.payload`，即 **P5** 的产物；
- P2 早于 P5，故 P2 时该表**不存在**，任何输入都无法满足该判定 → **P2 在任何卷上都必然 fail closed**。

`draft-0.10` 的改动：

| 项 | 内容 | 位置 |
| --- | --- | --- |
| 新增 | `BINDING_STREAM_ALLOWLIST`：P2 阶段的内建容许表，由协议直接规定，不引用任何 artifact | 第 116 行起 |
| 新增 | §7 阶段选择规则：两条互斥且穷尽的规则，P2 用内建表、P5 及其后用 artifact，选择是机械的 | 第 990–997 行 |
| 统一 | §2 与 §7 的引用由"具名某一来源"改为"**当前生效的容许表**" | 第 275、989–998、1008 行 |

（行号口径：以下所有行号均为 **`draft-0.10` 自身**的行号。`draft-0.10` 较 `draft-0.9` 在前部新增了 A1
内容，故两版行号整体相差约 41 行，**不得**沿用在 `draft-0.9` 上取得的行号。）

A1 的三条取值均为 `absent-if-empty`。**取值理由须由 reviewer 独立复核**：该项在此前的起草过程中一度
被误选为 `present-and-reverified`，后因 `C:` 卷不暴露 `sguard` 会因此在 P2 失败而改为 `absent-if-empty`。
reviewer 需判断该取值在 P2 语义下是否成立，而非采信起草方说明。

授权记录 §1.1 对 A1 设有限制：若 A1 的实施必然要求改动 `allowed_system_streams` 的**类型定义**
（而非仅新增 P2 专用规则），必须停止并另行取得授权。**该限制是否被遵守，属 reviewer 的核查项。**

### B1 —— `forbidden_history_ids` 的类型标注

- 第 85 行定义 `ID` 为 `[a-z0-9][a-z0-9-]{0,127}`，**不允许点号**；
- 第 86 行定义 `SCHEMA_ID` 为 `[a-z0-9][a-z0-9.-]{0,127}`，`SCHEMA_ID` 是 `ID` 的**超集**；
- 该字段的 **13 个取值全部含点号**，因此**全部匹配 `SCHEMA_ID`、全部不匹配 `ID`**。

`draft-0.10` 把两处标注由 `ID` 改为 `SCHEMA_ID`（第 198、377 行），**未改动任何取值**。

需 reviewer 注意的一项边界：`SCHEMA_ID` 是 `ID` 的超集，因此"改标注"与"改取值"两种修法**都能**消除
矛盾。脚本只能证明**矛盾存在**，不能判定**哪一侧应改**。本项目采用了改标注的方案（授权记录的 B1），
reviewer 需判断该选择是否可接受。第 85–86 行的**类型定义本身未被改动**，属授权 §3 冻结项。

### C2a —— `forbidden_history_ids` 的排序

- 第 167 行定义 `order=value`：对 `ASCII/ID/CODE/HEX/SCHEMA_ID/LOGICAL_NAME` 按 **UTF-8 bytes** 排序；
- 按该定义算得的顺序为 `v1, v10, v11, …, v2, …`；
- 而 `draft-0.5` 与 `draft-0.9` 两代记录中该字段的实际排列为**数字序**（13 项按 `ordinal` 递增）。

`draft-0.10` 把两处改为携带显式顺序要素的对象数组：

```
A<{id:SCHEMA_ID,ordinal:INT[0,12]};13..13;order=key(ordinal);unique=key(id)>
```

该式复用协议**已有**的 `order=key(...)` 机制（同章节内既有定义），未新增 comparator 种类。

**`order=value` 的比较器定义本体未被改动**（授权 §3 冻结项）：全协议 `order=value` 出现 **29 处 / 27 行**，
本项只改该字段的 schema。

### D1a —— 协议本体的行尾锁定

修订前：`git check-attr` 对协议本体报 `text/eol: unspecified`；`draft-0.9` 工作区为 CRLF
`162c9047…` / 182575 bytes，仓库为 LF `6ccebc47…` / 181209 bytes，**5 条 draft-0.9 记录绑定的是前者**。
故在 LF 检出环境（Linux，或 `autocrlf=false`）下这些记录**会停止验证**。

`draft-0.10` 的改动：

| 文件 | 规则 | 说明 |
| --- | --- | --- |
| `.gitattributes` | `docs/plans/references/m8-active-execution-protocol-draft-0.9.md text eol=lf` | 逐文件，**非通配** |
| `.gitattributes` | `docs/plans/references/m8-active-execution-protocol-draft-0.10.md text eol=lf` | 同上 |
| `draft-0.9.md` | 重写为 LF 字节 | 181209 bytes / `6ccebc47…` |

**`draft-0.5` 未被触及**（D1b 已被否决）：其协议文本仍为工作区 CRLF `ac907b83…` / 171830 bytes、
仓库 LF `4ab35a66…` / 170550 bytes，差 1280 = CRLF 对数；其 3 条记录仍绑 `ac907b83…`。
该差异**不是本次修订造成的**，是先前既存状态，已在 README 记载。

需 reviewer 注意：`draft-0.9` 的字节在本轮修订中**曾一度被就地改写**（在起草过程中误将修订应用到
`draft-0.9` 上，使其变为 184174 bytes），随后已恢复为 181209 bytes / `6ccebc47…`，修订另存为
`draft-0.10.md`。当前 `draft-0.9` 的字节与仓库历史提交一致，**可独立复验**。起草方主动披露该过程，
供 reviewer 决定其是否影响对"逐版独立"惯例的信任。

## 4. 待 reviewer 独立裁定的问题（本说明不作答）

1. `draft-0.10`（186129 bytes / `b5bc5088…`）的**技术文字**是否可接受？
2. 四项修订（A1 / B1 / C2a / D1a）是否**逐项**落在授权记录 §1 的范围内？
3. 授权记录 §3 的**冻结字节不变量**是否全部保持？特别核查：
   - `sa.m8.status-map.v1.payload` 的 72 行映射表（第 1110–1112 行）行数、取值、行序、两项 72 基数；
   - `order=value` 比较器定义本体（第 167 行）；
   - `SCHEMA_ID` 与 `ID` 的字符类定义（第 85–86 行）；
   - §7 的 per-open stream 复验语义（第 976–1008 行）；
   - `TECH_GATE_ID` 闭合枚举恰为 **26 项**（第 137 行）与第 832、848 行的 `26..26` 基数；
   - `draft-0.5` 协议文本与 3 条记录。
4. 授权记录 §4 的各项**明确禁止**是否均未被触碰？
5. §2 所列**独立性基础**是否成立？
6. 是否存在本说明未列出、但 reviewer 认为应记入 P0 记录的发现？

## 5. 本次审查的边界

1. 本审查只针对 `draft-0.10` 的**技术口径文字**，不产生任何执行权限。
2. 即使判定接受，`draft-0.10` 仍为 `UNBOUND / NOT_AUTHORIZED / NEVER_EXECUTED`。
3. 本审查**不**处理 §3 D1a 遗留的记录重算问题。`draft-0.9` 的 **5 条记录仍绑定修订前摘要 `162c9047…`**；
   按负责人决定，重算留待 `draft-0.10` 取得独立 P0 **之后**进行，使重算只发生一次。现行校验器接受
   "当前值或修订前值"并以显式 NOTE 报告该待办状态，**不静默通过**。
4. 本审查**不**授予 `draft-0.10` 的 binding、P1 或任何后续门禁。

## 6. 审查产物的允许形态（由 reviewer 决定）

reviewer 可产出以下任一结果，均须以独立记录落盘、**不改写任何既有记录**：

| 结果 | 含义 | 对链的影响 |
| --- | --- | --- |
| `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY` | 技术文字被接受 | 链可推进至 P1（另行取得授权后） |
| `P0_NOT_ACCEPTED` | 不予接受 | 链停在 P0；记录须写明具体缺陷 |

如需 `-r02` 以区别于先例记录，命名建议沿用既有惯例
`p0-m8-active-execution-draft010-20260913-r01.json`（首次即 `-r01`，因 `draft-0.10` 尚无 P0 记录）。

**本说明不指定 reviewer 的决定，也不建议其倾向。**

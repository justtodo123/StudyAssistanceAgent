# M8 active execution protocol 修订提案（四项遗留缺陷）

> **状态：`PROPOSAL_ONLY / NOT_AN_AUTHORIZATION / NOT_A_REVISION`**
>
> 本文件是一份**提案**，不是授权记录，不是审查记录，也不修改协议正文。它列举四项已核实的协议缺陷、
> 各自的候选修法、以及修订会造成的失效范围，供负责人裁定。**在本文件被负责人明确批准之前，
> 不得据以修改协议正文，也不得据以推进任何门禁。**
>
> 起草方：本次会话（AI 助手）。本文件**未经独立审查**，不构成独立性证据。

- 提案日期：2026-09-13
- 目标协议：`docs/plans/references/m8-active-execution-protocol-draft-0.9.md`
- 当前协议摘要：`162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4`（工作区 CRLF，182575 bytes）
  - 仓库内同文件为 `6ccebc477dd54df4415998c8…`（LF，181209 bytes）——**两者内容逐字节相同，仅行尾不同**，
    该双口径本身就是缺陷 D（§4）的对象
- 负责人：`justtodo123`
- 上游依据：本提案四项缺陷的事实来源见 §1–§4 各自的"证据"行；全部可用仓库内工具独立复跑

## 0. 为什么建议合并为一次修订

协议正文的任何字节变化都会改变 `protocol_blob_sha256`。按协议头部声明，绑定旧摘要的 P0/P1/P2 记录
**全部失效**，必须在新摘要上重新形成。

因此每启动一次独立修订，就要付出一次完整重走的成本。当前实测的失效范围（详见 §5.1/§5.2）为：

| 记录集 | 绑定摘要 | 失效成因 | 数量 |
| --- | --- | --- | --- |
| `external-gates/p0/…draft09…-r01.json` | `162c9047…` | A/B/C/D 均致失效 | 1 |
| `external-gates/p0/…draft09…-r02.json` | `162c9047…` | 同上 | 1 |
| `external-gates/p1/…draft09…-r02.json` | `162c9047…` | 同上 | 1 |
| `external-gates/p1/…（旧版）.json` | `162c9047…` | 同上 | 1 |
| `external-artifacts/identity/…draft09…json` | `162c9047…` | 同上 | 1 |
| `external-gates/p0/…draft05…-r01.json` | `ac907b83…` | **仅 D1b 致失效** | 1 |
| `external-gates/p1/…draft05….json` | `ac907b83…` | **仅 D1b 致失效** | 1 |
| `external-artifacts/identity/…draft05….json` | `ac907b83…` | **仅 D1b 致失效** | 1 |
| **合计** | | | **8** |

即：只做 A/B/C 或只做 D1a → 失效 5 条；若做 D1b（一并锁定两份协议）→ 失效 **8 条**。

四项缺陷若分四次修订，则需四次重走；合并为一次，只需一次。**本提案据此建议合并**，但不替负责人作此决定。

尤其注意 **D 与 A/B/C 天然同属一次修订**：D 会把工作区协议字节从 `162c9047…` 变为 `6ccebc47…`，
这本身就会使 draft-0.9 的记录失效；若不同时处理，就会在“刚重算完记录”之后立刻再因行尾重算一次。

## 1. 缺陷 A：P2 在任何卷上都必然 fail closed（**阻断级**）

### 证据

| 项 | 内容 |
| --- | --- |
| 规则位置 | §2.1 第 96 行；§7 第 958–966 行；`sa.m8.child-allowlist.v1.payload` 第 180、188 行 |
| 规则内容 | `SYSTEM_RESERVED_STREAM`（当前唯一成员 `sguard`，对应 Windows `:sguard:$DATA`）"每个成员都必须按 `STREAM_SCOPE` 显式列入 `sa.m8.child-allowlist.v1.payload.allowed_system_streams` 才被允许"；"未在该 scope 行中列出的 `SYSTEM_RESERVED_STREAM` 与任何其他 named stream 一律视为 ADS" |
| 复验强制范围 | §7 第 946–949 行：该复验"对全部十六个 `FILE_OPERATION` 都是强制的"，每个 operation 的 `stream_reverify` 必须恰为 `"required"` |
| P2 是否触发 | 第 364 行：`P2=[binding]`；`sa.m8.parent-binding.v1.payload`（第 174 行）要求从 `volume_root` 按 `components` 复走得到 `parent` identity，走查必然产生 per-open 复验 |
| allowlist 产出时机 | 第 188 行：`allowed_system_streams` 属 `sa.m8.child-allowlist.v1.payload`；该 artifact 在第 349 行仅作为 **P5** 的 `child_allowlist:REF` 输入出现，P6 才消费其中的 `child_allowlist_ref` |

### 结论

**P2 执行时 `allowed_system_streams` 尚不存在，因此 P2 的 stream 复验无表可查，只能 fail closed。**
这不是环境问题，是**协议自身的阶段顺序矛盾**：§7 要求查一张要到 P5 才产出的表，而 P2 在 P5 之前。

**因此：`D:` 卷不可用只是表象；换到 `C:` 卷（已实测可通过 stream 复验）同样无解。**
任何"换卷/换机"的处置都不能解除本项阻断。

### 候选修法

| 方案 | 内容 | 评价 |
| --- | --- | --- |
| A1 | 为 P2 阶段的 `parent-walk` 定义一份**独立的、闭合的、可机械复验的**最小容许集合（例如：允许 `sguard` 在 `volume-root` 与 `directory` 两个 scope 上以 `present-and-reverified` 出现），与 P5 的 `child_allowlist` 各自独立 | **推荐方向**。改动局部、不牵连 P5 语义。需同时规定 P2 阶段该判定的观测方式（`NtQueryInformationFile(FileStreamInformation)`）与失败 CODE |
| A2 | 把 `allowed_system_streams` 的产出**前移**到 P2 | 不推荐。会把 P5 的产物语义拆散，且 P2 时还没有 `dependency_lock` 等 P5 输入 |
| A3 | 在 P2 阶段豁免 stream 复验 | 不推荐。等于在 binding 冻结环节放弃完整性检查，缺陷会沿链传染到 P3 |
| A4 | 由负责人特许"allowlist 尚未生成时 P2 可先行冻结" | 不推荐。属用授权掩盖缺陷：P3 需由独立 reviewer 按 §7 复验，必然失败，届时须推翻 P2 或连 P3 一并豁免 |

## 2. 缺陷 B：`forbidden_history_ids` 标注为 `ID`，但取值含点号

### 证据

| 项 | 内容 |
| --- | --- |
| `ID` 定义 | 第 68 行：`ASCII[1,128]`，匹配 `[a-z0-9][a-z0-9-]{0,127}`——**不含点号** |
| `SCHEMA_ID` 定义 | 第 69 行：`ASCII[1,128]`，匹配 `[a-z0-9][a-z0-9.-]{0,127}`，且不得连续 `..`、以 `.` 结尾——**含点号** |
| 标注位置 | 第 168 行与第 346 行：`forbidden_history_ids:A<ID;13..13;order=value;unique=value>` |
| 实际取值 | `sa.m8.admission-evidence.v1` … `v13`（13 个），**全部含点号** |

### 复验方式

```
python tools/m8_verify_protocol_inconsistencies.py
  → 16 项全通过，其中：
    OK  none of the 13 values match ID
    OK  all 13 values match SCHEMA_ID
    OK  no value contains '..' or ends with '.'
```

### 结论

**矛盾确定存在**：这 13 个值不匹配 `ID`。

**但修法不唯一**。`SCHEMA_ID` 的字符类恰是 `ID` 的超集（仅多允许点号），故下列两种改法都能消除矛盾：

| 方案 | 内容 | 代价 |
| --- | --- | --- |
| B1 | 把两处标注的 `ID` 改为 `SCHEMA_ID` | 只动两个词，**不动任何数据** |
| B2 | 保留 `ID` 标注，改写那 13 个值为不含点号的形式 | 需改 **所有** 含该字段的记录（P1 与 identity），且会改变既有记录语义 |

**推荐 B1**，理由：`sa.m8.experiment-identity.v1`、`sa.m8.parent-binding.v1` 等 schema 命名本身就是点号分段形态，
`SCHEMA_ID` 正是为此类标识符定义的类型；这 13 个值是有意设计的遗产 ID 清单，不应为迁就一个标注而改写。
**但本提案不判定这一点，最终须由负责人按协议本意裁定**——脚本只能证明矛盾存在。

## 3. 缺陷 C：`order=value` 的排序结果与实际记录冲突

### 证据

| 项 | 内容 |
| --- | --- |
| 定义位置 | 第 137–138 行 |
| 定义内容 | "原子值按类型全序；整数按数值，BOOL 按 `false < true`，`ASCII/ID/CODE/HEX/SCHEMA_ID/LOGICAL_NAME` 按 UTF-8 bytes，enum 按 schema 声明顺序。object 不得使用 `value`。" |
| 冲突字段 | 第 168、346 行的 `forbidden_history_ids:A<ID;13..13;order=value;unique=value>` |
| 协议规定的顺序 | 按 UTF-8 bytes → `v1, v10, v11, v12, v13, v2, v3, …, v9` |
| 实际记录的顺序 | **数字序** `v1…v13`（draft-0.5 与 draft-0.9 `-r02` 两代记录一致） |

### 复验方式

```
python tools/m8_verify_protocol_inconsistencies.py
  → 16 项全通过，其中：
    OK  order=value sorts these types by UTF-8 bytes
    OK  the stored order is not the order the protocol prescribes
    OK  the stored order is numeric order
    OK  the draft-0.5 record uses the same numeric order
```

### 结论

**`order=value` 的定义本身完整、封闭、可机械执行，不存在"语义未明确"。**
真正的问题是：**按该定义算出的顺序，与仓库两代记录实际存储的顺序不一致**。二者必有一侧与现行文本不符。

### 候选修法

| 方案 | 内容 | 评价 |
| --- | --- | --- |
| C1 | 按协议重排那 13 个值为字典序 | 改动纯机械，但会使"历史版本清单"呈 `v1, v10, v11…` 形态，**语义上反直觉** |
| C2 | 为该字段换一个能表达数字序的 comparator | **推荐方向**。需注意**不可直接改动 `order=value` 的定义**——该 comparator 在全协议中被 **29 个字段**使用（分布于 27 行；`grep -o "order=value" | wc -l` 可复验），改定义会波及全协议 |
| C3 | 维持现状、不修 | 不推荐。矛盾留在协议内，会在下一个 P1 记录上重现 |

**C2 的两种具体做法**（需协议作者择一）：

- C2a：把该字段改为携带显式顺序要素的 object 数组，例如 `A<{id:ID,ordinal:INT;13..13;order=key(ordinal);unique=key(id)}>`
  —— 与协议既有做法一致（第 143 行附近已要求"若语义要求固定顺序，object 必须自带相应 enum 字段并使用 `key(...)`"）。
- C2b：为该字段单独注册一个专用 comparator（协议第 141 行禁止未注册的说明词，故须正式登记）。

**推荐 C2a**：它复用协议**已有的**机制（`order=key(...)`），不新增 comparator 种类，改动面最小。

## 4. 缺陷 D：协议本体的行尾未锁定，使全部记录依赖检出环境（**结构级**）

### 证据

| 项 | 内容 |
| --- | --- |
| 协议路径 | `docs/plans/references/m8-active-execution-protocol-draft-0.9.md` |
| 工作区字节（CRLF） | `162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4`，182575 bytes |
| 仓库字节（LF） | `6ccebc477dd54df4415998c8…`，181209 bytes |
| 差值 | 1366 bytes，恰为 1366 个 CRLF 行尾，**内容逐字节相同** |
| 行尾保护 | `git check-attr text eol` → **`text: unspecified`、`eol: unspecified`**（未受 `.gitattributes` 保护） |
| 记录绑定的值 | **全部 5 条** draft-0.9 记录的 `reviewed_protocol_sha256` 均为 `162c9047…`，即**工作区 CRLF 摘要** |

涉及记录：`p0/…-r01.json`、`p0/…-r02.json`、`p1/…-r02.json`、`p1/…（旧版）.json`、
`external-artifacts/identity/…draft09…json`。

**同类缺陷也存在于 `draft-0.5` 协议**（起草过程中一并核实）：

| 项 | `m8-active-execution-protocol-draft.md` |
| --- | --- |
| 行尾保护 | `text: unspecified`、`eol: unspecified`（同样未受保护） |
| 工作区（CRLF） | `ac907b83f11d9d8827798ba2ee19ec8b203c5560ecdff0137d619ddefcb9fbc9`，171830 bytes |
| 仓库（LF） | `4ab35a66b2786cc1c0f18338b46c739ec8d88b9f375d02ffaaf2ba4b13d9cf71`，170550 bytes |
| 差值 | 1280 bytes = 1280 个 CRLF |
| 记录绑定值 | `ac907b83…`（**同样是工作区 CRLF 摘要**），涉及 3 条记录 |

即：**若把两份协议都锁定为 LF，总失效面为 8 条记录（而非 5 条）**；若只锁定 `draft-0.9`，则为 5 条。
该取舍见下述 D1a/D1b。

### 结论

协议摘要 **`162c9047…` 是在 Windows + `core.autocrlf=true` 的检出条件下得到的**，而仓库内存储的是 LF 版
（`6ccebc47…`）。因此：

> **在任何 LF 检出环境（如 Linux、或 `autocrlf=false` 的机器）上克隆该仓库，协议摘要会是 `6ccebc47…`，
> 与全部 5 条 draft-0.9 记录不符，这些记录会因此全部失效。**
>
> `draft-0.5` 同样如此（摘要会从 `ac907b83…` 变为 `4ab35a66…`，涉及其 3 条记录）。
> 换言之，**当前仓库内全部 8 条外部门禁记录的摘要，都只在 Windows + `autocrlf=true` 的检出条件下成立。**

这与 2026-09-13 已修复的门禁 JSON 行尾缺陷**同源**（参见提交 `ec749cb`），但影响面更大：
已修复的是门禁 JSON 与 identity 工件，**协议本体作为整条链的摘要根，尚未修复**。

**这是结构级缺陷，不是环境偶然**：只要协议本体不受行尾保护，链根的摘要就随检出环境漂移。

### 候选修法

| 方案 | 内容 | 评价 |
| --- | --- | --- |
| D1a | **只锁定 `draft-0.9`**：为 `m8-active-execution-protocol-draft-0.9.md` 单列 LF 规则，在 LF 口径上重算 `reviewed_protocol_sha256`，重新形成其 5 条记录 | **推荐**。与已采用的修复（`ec749cb`）同构，代价最小；`draft-0.5` 作为已冻结历史保持原状 |
| D1b | **一并锁定两份协议**（如 `docs/plans/references/*.md text eol=lf`），重算全部 8 条记录 | 彻底固定链根，但 `draft-0.5` 是已冻结的历史版本，重算其记录等于**改动历史门禁记录**，与“历史不得就地改写”的纪律张力较大 |
| D2 | 维持现状，不修 | 不推荐。链根摘要继续依赖检出环境，任何非 Windows 验证者都会得出“记录失效”的结论 |
| D3 | 只修协议、不动记录 | 不可行。锁定 LF 后工作区字节变为 `6ccebc47…`，与全部 5 条记录的 `162c9047…` 不符，必须重算记录 |

**注意**：D1 与缺陷 A/B/C 的修订**天然合并**——反正都要重走 P0/P1，行尾口径应与本轮修订一并定下，避免“刚重算完又因行尾再改一次”。

## 5. 修订的影响范围（无论采用哪些方案）

### 5.1 必然失效的记录

协议字节一经改动，下列 4 条记录按协议头部声明**全部失效**，须在新摘要上重新形成：

| 记录 | 当前摘要依据 |
| --- | --- |
| `external-gates/p0/p0-m8-active-execution-draft09-20260913-r01.json` | `protocol_blob_sha256 = 162c9047…` |
| `external-gates/p0/p0-m8-active-execution-draft09-20260913-r02.json` | 同上 |
| `external-gates/p1/p1-m8-active-execution-active-draft09-21aaa3818bd761b63543-r02.json` | 同上 |
| `external-artifacts/identity/sa-m8-active-draft09-21aaa3818bd761b63543.json` | 同上 |

**历史记录不删除**：按仓库惯例，旧记录以 `-r01`/`-r02` 后缀并行保留，字节不动（配套校验器断言历史字节未变）。

### 5.2 `draft-0.5` 记录：不因 A/B/C 失效，但**因 D 而失效**

起初本条写作“`draft-0.5` 的两条记录不因本次修订失效”（且条数本身也少算，实为三条），**该判断不完整**，现更正如下。

须区分两种失效成因：

| 成因 | 对 `draft-0.5`（绑定 `ac907b83…`）的影响 |
| --- | --- |
| 缺陷 A/B/C 的修订（改动 `draft-0.9` 正文） | **不影响**。`draft-0.5` 绑定的是另一份协议文件（`m8-active-execution-protocol-draft.md`） |
| 缺陷 D 的修复（将协议 `.md` 锁定 LF） | **会使其失效**。因为 `ac907b83…` 同样是**工作区 CRLF 摘要** |

实测证据：

| 项 | `draft-0.5` 协议（`m8-active-execution-protocol-draft.md`） |
| --- | --- |
| 工作区（CRLF） | `ac907b83f11d9d8827798ba2ee19ec8b203c5560ecdff0137d619ddefcb9fbc9`，171830 bytes |
| 仓库（LF） | `4ab35a66b2786cc1c0f18338b46c739ec8d88b9f375d02ffaaf2ba4b13d9cf71`，170550 bytes |
| 差值 | 1280 bytes，恰为 1280 个 CRLF 行尾 |
| 记录绑定值 | `ac907b83…`（即**工作区 CRLF 摘要**） |

因此：**`draft-0.5` 的三条记录（`external-gates/p0/…draft05…`、`p1/…draft05…`、
`external-artifacts/identity/…draft05…`）在 `draft-0.5` 协议被锁定为 LF 后同样失效。**

若 D 的锁定范围写作 `docs/plans/references/*.md`（包含两份协议），则本次修订的**总失效面为 8 条记录**，
而非五条。这一点应在上报前明确，因为它显著改变了修订的代价。

可选做法：D1 只锁定 `draft-0.9`（最小面），或一并锁定两份协议（彻底固定，但 `draft-0.5` 记录也需重算）。
该取舍列在 §4 的 D1a/D1b，由负责人裁定。

### 5.3 需要重新履行的治理动作

1. 新协议正文的独立 P0 技术审查（**须由未参与起草者签署**）
2. 新摘要上的 P0 → P1（含 identity 是否重新铸造的裁定）
3. 缺陷 A 的修复若生效，P2 方可首次尝试

**注意**：缺陷 A 只解决"sguard 无表可查"；`D:` 卷本身仍暴露 `:sguard:$DATA`，故 P2 的父目录选在暴露该流的卷上时，
仍须满足 A1 所定义的容许规则。**P2 不因此自动变为可在任意卷上执行。**

## 6. 建议的执行顺序（供负责人裁定）

1. 负责人审阅本提案，对 A/B/C/D 各自选定方案（A 建议 A1；B 建议 B1；C 建议 C2a；D 建议 **D1a**）
   - **D 应优先于 A/B/C 定案**：它决定协议在哪个行尾口径上被固定，而 A/B/C 的修订文本还要在此基础上落地并摘要
2. 起草**授权记录**（独立落盘），明确批准哪一项、按哪个方案
3. 按授权执行协议正文修订（正文改动本身应可机械复算，并归档旧版字节）
4. 修订后重走 P0 → P1；届时再评估 P2

**本提案不代作上述任何一步。**

## 7. 边界声明

- 本文件是**提案**，不构成授权、不解除任何禁令、不推进任何门禁、不使任何记录失效或生效。
- 四项缺陷的事实均可用 §1–§4 所列命令在仓库内独立复跑。
- 本文件**只证明矛盾/阻断存在**，不判定 A/B/C/D 应选哪个方案；方案选择属协议作者与负责人的裁量。
- 本文件由 AI 起草，**未经独立审查**，不得作为独立性证据。
- 当前有效链仍为：P0 `-r02` 已接受、P1 `-r02` `AUTHORIZED / request-p2`、**P2 未生成**；
  M8 仍为 `BLOCKED / NOT_STARTED`。

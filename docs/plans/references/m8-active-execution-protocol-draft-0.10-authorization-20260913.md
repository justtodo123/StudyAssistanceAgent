# M8 active execution protocol `draft-0.10` 修订授权记录

- 授权对象：`docs/plans/references/m8-active-execution-protocol-draft-0.9.md` 的新修订 `draft-0.10`
- 授权日期：2026-09-13
- 负责人：`justtodo123`
- 上游依据：本记录依据同日的修订提案
  [`m8-protocol-revision-proposal-20260913.md`](m8-protocol-revision-proposal-20260913.md)（状态 `PROPOSAL_ONLY`）
  与其可复验事实核验脚本 `tools/m8_verify_proposal_claims.py`（17 项，全部通过）
- 授权决议：负责人于 2026-09-13 明确指示"现在起草授权记录，尽快推进 M8"，即**批准该提案的四项方案**
  （A1 / B1 / C2a / D1a），并授权据此形成 `draft-0.10` 文本修订
- 修订后状态：授权时 **`DRAFTED / PENDING_P0_REVIEW`**。本授权**不**预先宣告 `PASS`

## 0. 治理事实声明（必读）

1. 本记录是**授权**，不是审查记录，不是门禁记录，也不修改协议正文。它授权的是**一次定点文本修订**，
   不产生任何执行权限。
2. 本记录的四项缺陷事实**来自提案，并经独立脚本复验**（`tools/m8_verify_proposal_claims.py`，17 项全通过）。
   复验内容涵盖：两份协议的工作区/仓库双口径摘要与字节数、CRLF 差值、`162c9047…`/`ac907b83…` 的记录归属
   计数（5 + 3）、`order=value` 的字段计数（29 处、27 行）、以及两份协议均未受 `.gitattributes` 保护的事实。
3. **提案的受理方是负责人，批准方也是负责人**；起草方（AI 助手）未参与批准。这与本仓库既有的
   "起草方与审查方分离"纪律一致，但**本授权本身不构成 `draft-0.10` 的独立性证据**——
   `draft-0.10` 的 P0 仍须由未参与起草者独立审查。
4. 本授权取代 `draft-0.9` 授权记录中"不自动产生 `draft-0.10`"的适用；该限制的原意是禁止**未获批准的续版**，
   不禁止**经负责人明确批准的定点修订**。

## 1. 授权内容

本授权只批准一件事：把 active execution protocol 推进到 `draft-0.10`，即由负责人主动发起的下一轮**定点**文本
修订。该修订**仅**用于处理下列四项已核实缺陷，且只按下列已裁定的方案执行：

| 编号 | 缺陷 | 采用方案 | 改动要点 |
| --- | --- | --- | --- |
| A | **P2 在任何卷上都必然 fail closed**：§7 要求查 `allowed_system_streams`，而该表属 P5 的 `sa.m8.child-allowlist.v1.payload`，P2 时不存在——阶段顺序矛盾 | **A1** | 为 P2 阶段的 `parent-walk` stream 复验定义一份**独立、闭合、可机械复验**的最小容许规则；须同时规定其观测方式（`NtQueryInformationFile(FileStreamInformation)` 于 `opened-file-handle`）与失败 CODE。**不**前移 P5 的 `child_allowlist`（否决 A2），**不**豁免 P2 复验（否决 A3） |
| B | `forbidden_history_ids` 标注为 `ID`（第 68 行：`[a-z0-9][a-z0-9-]{0,127}`，不许点号），但 13 个取值全部含点号 | **B1** | 把该字段的**两处**标注由 `ID` 改为 `SCHEMA_ID`：协议第 168 行（`sa.m8.experiment-identity.v1.payload`）与第 346 行（P1 门禁表）。**只动标注，不改动任何取值**；否决 B2（改写 13 个值） |
| C | `order=value` 规定 `ASCII/ID/CODE/HEX/SCHEMA_ID/LOGICAL_NAME` 按 UTF-8 bytes 排序（第 137–138 行），算得 `v1, v10, v11, …, v2, …`；而 `forbidden_history_ids` 的实际记录用数字序 | **C2a** | 把第 168 与 346 行的该字段改为自带显式顺序要素的 object 数组（如 `A<{id:ID,ordinal:INT;13..13;order=key(ordinal);unique=key(id)}>`），复用协议**已有**的 `order=key(...)` 机制（第 139–141 行）。**不得改动 `order=value` 自身的定义**——该 comparator 被 29 个字段使用 |
| D | **协议本体未受行尾保护**：`git check-attr` 报 `text/eol: unspecified`；工作区摘要 `162c9047…`（CRLF）/仓库 `6ccebc47…`（LF），5 条 draft-0.9 记录绑定前者 | **D1a** | **只**为 `draft-0.9`（及其后续 `draft-0.10`）单列 LF 规则，在 **LF 口径**上重算 `reviewed_protocol_sha256` 并重新形成其 5 条记录。**否决 D1b**（一并锁定 `draft-0.5`）——后者会要求重算已冻结的历史记录，与"历史不得就地改写"冲突；**否决 D2**（不修） |

`draft-0.10` 是文档修订号，不是 experiment ID，也不是 executable protocol ID。本次修订不产生新身份、不取代任何
历史记录、不改变 M8 的阶段状态。

### 1.1 对 A1 的额外约束（防止过度扩张）

A1 是本授权中唯一会**新增规范内容**的一项。为免其演变为重新设计，特设约束：

- 新增规则**只**适用于 P2 阶段的 `parent-binding` 生成与复验路径；**不**得改动 P5–P9 的 `child_allowlist` 语义；
- 规则必须**闭合**：允许集合中的每一行须指明 `scope`、`stream` 与 `observation` 三要素，且判定方式与 §7 既有
  的 per-open 语义保持一致；
- 规则必须**可机械复验**：不得引入任何依赖人类判断的条款；
- 若 A1 的实施被发现必然要求改动 `allowed_system_streams` 的**类型定义**（而非仅新增 P2 专用规则），
  **必须停止并另行取得授权**——那已越出本授权范围。

## 2. 允许动作

1. 在 `docs/plans/references/m8-active-execution-protocol-draft-0.9.md` 的基础上形成 `draft-0.10` 文本修订，
   范围**严格限于**上表四项（A1 / B1 / C2a / D1a）。
2. 同步更新文档头部版本号与相应日期、修订依据说明（记录本记录为授权来源）。
3. 形成 `draft-0.10` 的精确字节归档，使后续审查记录中的 SHA-256 与被审字节一致。
4. 在 `.gitattributes` 中为协议本体增加 LF 锁定规则（D1a 范围：**只**覆盖 `draft-0.9` 与 `draft-0.10`）。
5. 在 **LF 口径**上重算 `reviewed_protocol_sha256`，并**并行**重新形成 draft-0.9 的 5 条记录
   （`-r01`/`-r02` 后缀或新版本后缀），**不改写**任何旧记录的字节。
6. 形成本授权记录。

`draft-0.10` 进入 `DRAFTED / PENDING_P0_REVIEW`：草案已写出，等待未参与起草的独立 reviewer 完成 P0 技术口径
审查。**审查结论只能由该独立审查产生，不能由本记录或起草方预先写入。**

## 3. 修订边界（冻结字节不变量）

本次修订**不得**改动下列内容；如任一改动成为必需，必须停止并另行取得授权：

- `sa.m8.status-map.v1.payload` 的 **72 行映射表**（协议第 1069–1071 行，`entries:A<STATUS_MAP_ENTRY;72..72;…>`
  与 `required_stable_codes:A<STABLE_CODE;72..72;…>`）：行数、每行取值、行序与两项 72 基数均保持逐字不变。
  A/B/C/D 均不触及该表。
- **`order=value` 的比较器定义本体**（第 137–138 行）：C2a 只改**该字段的 schema**，不改比较器定义。
- **`SCHEMA_ID` 与 `ID` 的字符类定义**（第 68–69 行）：B1 只改字段的**类型标注**，不改类型定义本身。
- **§7 的 per-open stream 复验语义**（第 946–966 行）：A1 只为其新增 P2 专用容许规则，不改 §7 现有判定流程。
- **`draft-0.5` 协议文本与其 3 条记录**：D1a 明确不触及。
- `draft-0.6` 起引入并经 `draft-0.7`–`draft-0.9` 保持的系统保留流设计骨架（`SYSTEM_RESERVED_STREAM` 闭合枚举、
  `STREAM_SCOPE` 三值闭合枚举、`allowed_system_streams` 及其 `observation` 消费逻辑）：A1 只**新增** P2 专用
  容许规则，不推翻该设计。
- 其余全部既有 schema、枚举、谓词、数量、deadline 与状态机转移。
- **26 项技术门禁**：`TECH_GATE_ID` 闭合枚举（协议第 107 行）必须恰为 26 项，且第 801、817 行的
  `A<TECH_GATE_RESULT;26..26;…>` 基数不变。

本次修订是定点文字修订，不是重新设计。

## 4. 明确禁止

本授权不包含、也不得被解释为包含以下任何一项：

- 创建 experiment ID、executable protocol ID、repository binding、experiment root、nonce 或任何 S/A/G/E 根；
- 安装或获取依赖、创建 venv、获取 wheel 或任何 input digest；
- 生成 source、corpus、query 或 gold；
- 运行 preflight、smoke、full、benchmark 或任何实证执行；
- 发布证据、形成 package/receipt、执行 cleanup 或写入任何运行期 artifact；
- 改写 M8 registry、stage-admission 登记表、批准字段或阶段状态；
- 准入 M8、批准开工、选择 LanceDB/Qdrant/Milvus 或任何专业后端；
- 复用 V8–V13 或 `draft-0.1`–`draft-0.10` 的任何身份、绑定、根、source、manifest、digest 或 artifact；
- 追溯性补认 `draft-0.6`–`draft-0.9` 或使它们免于审查；
- 预先写入 P0 审查结论或 `PASS`；
- **据 D1a 改动 `draft-0.5` 的协议文本或记录**（D1b 已被否决）；
- **借 A1 之名改动 P5 的 `child_allowlist` 语义或 `allowed_system_streams` 的类型定义**；
- 借本次修订夹带处理上表四项以外的任何改动，或引入任何未在上表列出的改动。

`draft-0.5` 是被 `PLAN.md` 正式引用的既有 PASS 记录，本授权不改写它；`draft-0.6`–`draft-0.9` 正文仍只作历史追溯，
不得 binding、授权或作为 `draft-0.10` 的等价替代。

## 5. 本次修订的失效范围（如实披露）

按协议头部声明，绑定旧摘要的 P0/P1/P2 记录在协议字节变化后**全部失效**。本次修订的失效范围实测为：

| 记录集 | 原绑定摘要 | 是否失效 | 数量 |
| --- | --- | --- | --- |
| `external-gates/p0/…draft09…-r01.json` | `162c9047…` | 是（A/B/C/D 均致失效） | 1 |
| `external-gates/p0/…draft09…-r02.json` | `162c9047…` | 是 | 1 |
| `external-gates/p1/…draft09…-r02.json` | `162c9047…` | 是 | 1 |
| `external-gates/p1/…draft09…（旧版）.json` | `162c9047…` | 是 | 1 |
| `external-artifacts/identity/…draft09…json` | `162c9047…` | 是 | 1 |
| `external-gates/p0/…draft05…-r01.json` | `ac907b83…` | **否**（D1b 已否决） | 1 |
| `external-gates/p1/…draft05….json` | `ac907b83…` | **否** | 1 |
| `external-artifacts/identity/…draft05….json` | `ac907b83…` | **否** | 1 |

即：**本次修订使 5 条 draft-0.9 记录失效，`draft-0.5` 的 3 条记录保持原状。**

**历史记录不删除**：按仓库惯例，旧记录以 `-r01`/`-r02` 后缀**并行保留，字节不动**；配套校验器须断言历史字节未变。

## 6. 后续前置关系

`draft-0.10` 即使取得独立 P0 `PASS`，也只表示技术口径被接受，**不产生任何执行权限**。其后仍须依次形成：

1. `draft-0.10` 的独立 P0 技术审查（**须由未参与起草者签署**）；
2. 新 LF 摘要上的 P0 → P1（含 identity 是否重新铸造的裁定）；
3. **A1 修复生效后，P2 方可首次尝试**。届时须注意：`D:` 卷本身仍暴露 `:sguard:$DATA`，A1 只解决"无表可查"，
   不使 P2 在任意卷上自动可行；
4. P3 及后续门禁。

**本授权只覆盖文本修订，不覆盖上述任何一步。**

## 7. 状态边界

- 本记录是**授权**，不构成审查、不构成门禁、不推进任何门禁。
- 本记录只授权 §1 表列四项（A1 / B1 / C2a / D1a）的文本修订。
- 本授权**不**预先宣告 `draft-0.10` 会通过 P0 审查。
- 本授权**不**解除任何执行禁令，**不**构成 M8 准入或开工许可。
- 当前有效链在本次修订前为：P0 `-r02` 已接受、P1 `-r02` `AUTHORIZED / request-p2`、**P2 未生成**；
  M8 仍为 `BLOCKED / NOT_STARTED`。该链在 `draft-0.10` 取得独立 P0 前不因本授权改变。

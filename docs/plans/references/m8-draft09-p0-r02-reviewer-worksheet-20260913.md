# M8 `draft-0.9` P0 独立复核工作单（供 `-r02` 使用）

> **文档性质：复核工作单（`REVIEW_WORKSHEET`），不是门禁记录，不构成任何授权。**
>
> 本文件为一位**未参与 draft-0.9 起草与本轮机械核验**的独立 reviewer 提供可逐项核验的事实清单。签署者据此
> 自行判断是否接受 `draft-0.9` 的 P0 技术文字，并据此签发 `p0-m8-active-execution-draft09-20260913-r02.json`。
>
> 本工作单**不预置结论**。`-r01` 记录的 `P0_NOT_ACCEPTED` 是对"同一主体不能自证独立性"的如实记录，不是对
> draft-0.9 技术文字的否定；两者是不同问题，请分别判断。

## 0. 为什么需要 `-r02`

协议状态机规定 `UNBOUND_DRAFT` 的 actor/record 为 **`independent reviewer`/P0**，并规定 P0 要求
`independence={required:true,satisfied:true}`。`-r01` 记录的起草与核验由同一主体完成，无法满足该要求，故
`-r01` 如实落盘为 `P0_NOT_ACCEPTED / independence.satisfied=false / allowed_next_action=stop`，其唯一后继 P1
随之落为 `NOT_AUTHORIZED`。

按协议，修复方式不是修改 `-r01`，而是由**未参与本轮**的审查者另行签发 `-r02`。`-r01` 应作为历史保留。

## 1. 待复核对象（精确字节）

| 项 | 值 |
| --- | --- |
| 被审文件 | `docs/plans/references/m8-active-execution-protocol-draft-0.9.md` |
| 工作区磁盘字节数 | `182575` |
| 工作区磁盘 SHA-256（**即登记值**） | `162c9047ddeaceda59d7da79f8dfbf45234a89e2b00fd271e72473bbc6cca5b4` |
| 仓库（LF 归一化）字节数 | `181209` |
| 仓库（LF 归一化）SHA-256 | `6ccebc477dd54df4415998c8c03ffff3215d523cf2a42af128a8ff6a36e244a9` |
| 行数 | `1366` |

**行尾披露（重要）**：工作区为 CRLF，仓库为 LF，1366 行恰好对应 1366 字节差，故**除行尾外内容逐字节相同**。
登记值 `162c9047…` 对应**工作区磁盘字节**。此与仓库既有惯例一致：`draft-0.5` 先例同为"入库转 LF、记录登记
磁盘 CRLF 哈希"（工作区 `171830`/`ac907b83…` vs 仓库 `170550`/`4ab35a66…`）。请审查者确认是否接受该惯例；
若要求登记值对应仓库 LF 字节，则需改为登记 `6ccebc47…`，并使所有记录与新摘要重新绑定。

复核命令（请自行执行，不要采信本文件结论）：

```bash
cd "<repo>"
sha256sum docs/plans/references/m8-active-execution-protocol-draft-0.9.md   # 期望 162c9047...
wc -c < docs/plans/references/m8-active-execution-protocol-draft-0.9.md     # 期望 182575
git show HEAD:docs/plans/references/m8-active-execution-protocol-draft-0.9.md | sha256sum  # 期望 6ccebc47...
git status --short docs/plans/references/m8-active-execution-protocol-draft-0.9.md  # 期望为空（已提交、未改动）
```

## 2. 复核范围（P0 仅是技术文字）

P0 的 `review_kind` 恰为 `P0_TECHNICAL_SCOPE_REVIEW`。请只判断**技术文字的机械闭合性**。P0 不判断——
也不得被解释为判断——以下任何一项：

- 不创建 experiment identity、repository binding、experiment root；
- 不授权依赖获取/安装、source/corpus/query/gold 生成、preflight、benchmark 执行；
- 不授权证据发布、M8 registry 变更、M8 admission、后端选择、生产实现；
- 即使 P0 被接受，P1–P9/P7A 仍须各自另行形成满足前置关系的外部记录。

## 3. 核验清单（逐项请自行复跑并打勾）

### 3.1 基础完整性

| # | 核验项 | 期望值 | 结果 |
| --- | --- | --- | --- |
| 3.1.1 | 字节数 | `182575` | ☐ |
| 3.1.2 | SHA-256（工作区） | `162c9047…cca5b4` | ☐ |
| 3.1.3 | 无 BOM | 文件不以 `EF BB BF` 开头 | ☐ |
| 3.1.4 | UTF-8 可解码 | 是 | ☐ |
| 3.1.5 | 行数 | `1366` | ☐ |
| 3.1.6 | 工作区相对 HEAD 无改动 | `git status` 为空 | ☐ |

### 3.2 状态表（72 行映射表）

| # | 核验项 | 期望值 | 结果 |
| --- | --- | --- | --- |
| 3.2.1 | 状态表数据行数 | `72`（等于 draft-0.5 基线，非减少） | ☐ |
| 3.2.2 | 状态表逐字节等于 draft-0.5 基线 | 相同 | ☐ |

### 3.3 声称修复项（draft-0.8 的三项阻断缺陷 + 两项清理）

| # | 核验项 | 期望值 | 结果 |
| --- | --- | --- | --- |
| 3.3.1 | 缺陷 A：`STREAM_SCOPE` 为 per-open，由每次 open 实际获得的对象决定 | 已修复 | ☐ |
| 3.3.2 | 缺陷 A：profile 不再携带 `opens_volume_root` | 字段已移除 | ☐ |
| 3.3.3 | 缺陷 A：walk 在开始时先冻结 volume-root identity | 已修复 | ☐ |
| 3.3.4 | 缺陷 B：`stream_scope_per_open` 取代标量派生字段 | 已修复 | ☐ |
| 3.3.5 | 缺陷 C：`stream_query_source` 仅承认 `opened-file-handle` | 已修复 | ☐ |
| 3.3.6 | 清理 D-1：装饰字段 `allowed_system_streams_closed` 已从 schema 移除 | 除修订说明外不再出现（全文仅 1 处，在第 18 行“已删除”叙述中） | ☐ |
| 3.3.7 | 清理 D-2：不可达枚举值 `stream_reverify=not-applicable` 已移除 | 该**枚举成员**已移除；`stream_reverify` **字段本身保留**，在 `FILE_OPERATION` 中恒为 `"required"`（见下） | ☐ |

> **对 3.3.7 的精确说明（请勿误读）**：`stream_reverify` 字段**没有**被删除。它是 `FILE_OPERATION` 的常量，在
> 第 256、284、946 行均以 `"required"` 出现，且对全部十六个 `FILE_OPERATION` 强制。被删除的只是 draft-0.8 中
> 那个不可达的枚举成员 `not-applicable`。复核命令：
>
> ```bash
> grep -n 'allowed_system_streams_closed' <protocol>  # 期望仅 1 处，且在第 18 行修订说明中
> grep -o 'stream_reverify[^,;}]*' <protocol> | sort -u
> #   期望可见 stream_reverify:"required"；不应再出现 not-applicable
> ```

### 3.4 整条链的保留不变量（必须全部成立）

下表“已核实位置”列是本工作单编写时实测的具体行号/取值，仅供复核者比对，**不代替复核者自行验证**。

| # | 核验项 | 期望值 | 已核实位置 | 结果 |
| --- | --- | --- | --- | --- |
| 3.4.1 | `scope` 枚举保持三值 | `scope:enum[query,build,lifecycle]` | 全文唯一 | ☐ |
| 3.4.2 | `SYSTEM_RESERVED_STREAM` 恰定义一次 | 定义唯一（全文提及 7 处，仅 1 处为定义） | §2.1 第 95 行 | ☐ |
| 3.4.3 | allowlist 基数为派生常量 `3..3` | `allowed_system_streams:A<{...};3..3;...>` | 第 189 行 | ☐ |
| 3.4.4 | observation 在 §7 被消费 | 逐条判定规则 + fail-closed 映射 | §7（第 925–980 行区间） | ☐ |
| 3.4.5 | `FileStreamInformation` 查询是 stream 来源 | 全文 7 处 | §7 第 25 行等 | ☐ |
| 3.4.6 | interposition ADS 豁免保留 | `SYSTEM_RESERVED_STREAM` 明确列入 allowlist 者不算 ADS | 第 247 行 | ☐ |
| 3.4.7 | volume-root identity 经 `FileIdInformation` 四字段比对 | `volume_serial`、`filesystem`、`file_id`、`acl_sha256` | §7 第 30 行 | ☐ |

复核命令：

```bash
P=<protocol>
grep -o 'scope:enum\[[^]]*\]' "$P" | sort -u            # 期望 scope:enum[query,build,lifecycle]
grep -n 'SYSTEM_RESERVED_STREAM' "$P"                    # 观察定义处唯一
grep -n 'allowed_system_streams:A<' "$P"                # 期望基数 3..3
awk '/^## 7/,/^## 8/' "$P" | grep -n 'observation'       # 期望有多条消费规则
awk '/^## 7/,/^## 8/' "$P" | grep -n 'acl_sha256'        # 期望在四字段比对中
```

### 3.5 独立复跑（推荐）

仓库内有 `tools/m8_draft_reviewer.py`，但不导入任何起草脚本、全部事实从 blob 重新推导：

```bash
python tools/m8_draft_reviewer.py
```

期望：`draft-0.9: PASS / P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY`（0.6/0.7/0.8 为 `RETURNED_FOR_REVISION`）。
请自行判断是否接受一个由起草方所在工作区提供的工具作为辅助证据；**该工具的输出不能替代您的独立判断**。

## 4. 必须由审查者独立判断的问题（工作单不给答案）

1. **技术文字是否闭合**：§3.3 的修复与 §3.4 的不变量是否成立，是否存在新的机械缺陷。
2. **行尾惯例是否可接受**：登记 `162c9047…`（工作区 CRLF）而非 `6ccebc47…`（仓库 LF）是否可接受。
3. **审查充分性**：`-r01` 的机械核验结论可复现，但由起草方产出；是否足以支撑您的签署。
4. **是否接受**：若接受，签发 `-r02` 并填 `P0_TECHNICAL_SCOPE_WORDING_ACCEPTED_ONLY / request-p1`；
   若不接受，签发 `P0_NOT_ACCEPTED / stop` 并在 `payload.finding_ids` 列出缺陷。

## 5. 签署后我将执行的机械动作（供审查者预知）

审查者完成判断后，以下动作可由我机械执行，且**不涉及任何执行权限**：

1. 按 `-r02` 的 decision 生成 `p0-m8-active-execution-draft09-20260913-r02.json`：
   `actor.role=independent-reviewer`、`actor.name` 由审查者指定、`independence={required:true,satisfied:true}`（若接受）；
   `predecessors=[]`；`scope.operations=["review"]`；绑定协议摘要。
2. 若 `-r02` 为接受，重建 P1 为 `AUTHORIZED / request-p2`，绑定 `-r02` 摘要；`-r01` 与其 `NOT_AUTHORIZED` P1
   作为历史保留，不改写。
3. 重跑校验并更新 README 与材料说明。

**P2 起才涉及 binding 与仓库 commit**；本轮不触及。

## 6. 边界声明

本工作单由参与 draft-0.9 起草的一方编写，因此**它不是独立证据**，不得被引用为审查结论、授权或阶段状态。
它的唯一用途是把可核验事实摆到审查者面前，降低复核成本。审查者的结论只由其签署的 `-r02` 记录承载。

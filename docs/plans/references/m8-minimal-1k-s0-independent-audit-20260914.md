# M8 最小 1K dry-run 协议独立 S0 技术审计记录

- reviewer：`s0-audit-reviewer-20260914`
- reviewed commit：`bee135f8ac3a2f23b5ea1784747dc83e63bd73fb`
- decision：`PROTOCOL_REJECTED`
- allowed_next_action：`stop`
- timestamp：`2026-09-14T11:44:39Z`
- 状态：`S0_REJECTED / S1_NOT_AUTHORIZED / M8_BLOCKED`

## 独立性 basis

Reviewer name 与 drafting party `ai-assistant` 逐字节不同。本裁定基于冻结文件的只读复算、协议/schema/validator
独立分析及仓库外内存负例测试；未修改任何被审对象，也未执行实验。现有证据只能证明名称分离和本次分析过程的
独立性，不能密码学证明该 reviewer 从未参与过历史起草。

## 冻结对象复算

- protocol：`2312509a17d5cacbce61c56dfad53dfde3e498fd332443f0bdbca6f87d0910e3`，6594 bytes，132 LF；
- schema：`498a9cb4d8f695e7e5d0a4b04e548c286477fff36770ce29b5c85c6e0d4a58ed`；
- validator：`5000e5eb2b4f675f868abe25080bc59315c9dba74ae3bb876235e9b0f71ee700`；
- 审查开始和结束时工作区均干净；未发现 draft-0.11 P4。

## Findings

### `m8-s0-001` — HIGH — 冻结审查 commit 绑定不一致

用户指定 reviewed commit 为 `bee135f8…`，但 S0 materials 与 worksheet 指向 `306f826…`。核心对象字节虽相同，
审查 package 的权威 commit 范围不唯一。应分别冻结 `reviewed_object_commit` 与 `review_package_commit`，或统一目标。

### `m8-s0-002` — CRITICAL — 六类 artifact payload 没有机械 schema

当前 JSON Schema 只关闭 envelope，payload 仅为任意 object。六类 payload 没有 required、类型、枚举、唯一性、顺序或
`additionalProperties=false`，无法机械判断 identity、manifest、run/validation report、cleanup receipt 与 decision record。

### `m8-s0-003` — CRITICAL — Validator 对五类 artifact fail open

Validator 只部分检查 identity，未实际验证其他五类 payload。独立负例证明 dependency placeholder、logical-name/type
错配、空 backend run-report、cleanup failure + PASS validation 以及未知 actor role 均可被接受。

### `m8-s0-004` — CRITICAL — S1 关键配置未在观察前闭合

`query_counts` 开放；parity tolerance 未列入 S1；dependency versions 可使用占位符；repository commit 没有格式和 clean
worktree proof。结果出现后仍可能自由选择关键解释，identity 不可重放。

### `m8-s0-005` — HIGH — Workload、负向 fixture 与 gold 生成不确定

Wrong-owner、tombstone、unpublished、generation/snapshot mismatch 及四类 query 没有确定性 fixture、ID、派生算法、
比例或 gold 来源。不同 executor 可生成不同的“合法”输入。

### `m8-s0-006` — CRITICAL — 网络、越界写和 redaction 无机械观测规范

协议只有禁止结果，没有冻结 observer、进程树作用域、phase boundary、事件格式、canonical containment、junction/symlink
处理、redaction scanner 或观测失败的 fail-closed 行为。

### `m8-s0-007` — HIGH — Logical name、REF、actor 与 primitive format 未闭合

Logical name 无唯一派生规则；REF schema ID 为自由字符串；decision actor 无 role enum；timestamp、commit、digest、计数和
资源观测缺少完整格式/范围，artifact 可错配或引用错误对象。

### `m8-s0-008` — CRITICAL — Cleanup 与 S3 完整证据生命周期未闭合

Raw report 可位于待删除隔离根，但 S3 在 cleanup 后才审查；“脱敏摘要”无 schema，receipt 的根外持久位置与 cleanup 失败
保留路径未定义，validation PASS 与最终 cleanup failure 没有机械排斥关系。

## 独立负向测试结论

通过拒绝：10K、增加 Qdrant、measured network、identity 额外字段、缺 query counts、非法 nonce、backend 错序、非法 top-k。

未能拒绝：dependency 使用 `latest`、identity logical name 冒充 run-report、run-report 无 backend、cleanup failure 与
validation PASS 并存，以及未知 actor role。

## 最终裁定

```text
decision: PROTOCOL_REJECTED
allowed_next_action: stop
finding_ids:
  - m8-s0-001
  - m8-s0-002
  - m8-s0-003
  - m8-s0-004
  - m8-s0-005
  - m8-s0-006
  - m8-s0-007
  - m8-s0-008
```

没有创建或授权 S1，没有创建实验根或安装依赖，没有运行 SQLite/LanceDB dry-run，也没有创建 draft-0.11 P4。
M8 继续 `BLOCKED / NOT_STARTED`。若修订最小协议，必须形成新协议版本并重新执行独立 S0，不得改写本记录。

# M8 active execution protocol `draft-0.11` 修订实施说明

- 日期：2026-09-14
- 授权：[`draft-0.11` 修订授权记录](m8-active-execution-protocol-draft-0.11-authorization-20260914.md)
- 提案：[`draft-0.11` 修订提案](m8-draft011-revision-proposal-20260914.md)
- 被修订基线：`draft-0.10`，186129 bytes，SHA-256 `b5bc5088486079971eba28efe5cd2d7ed90c73a1359a87d9bca4722c473caa39`
- 产物状态：`DRAFTED / PENDING_INDEPENDENT_P0_REVIEW / UNBOUND / NOT_EXECUTION_AUTHORIZED`

## 1. 修订范围

本次只实施 owner 批准的 A+B+C：

1. **A：closed gate mapping 与主体不重合**
   - 11 个 gate 分别绑定唯一 actor role、independence flags 和 operations；
   - P0 payload 增加 `drafting_party_name`；
   - P0 reviewer 必须不同于 drafting party；P3/P5/P7 独立主体必须不同于链上全部 owner actors；
   - `independence.basis` 不能替代机械映射或主体比较。
2. **B：P8 admission scope literal**
   - `admission_scope:UTF8[1,1024]` 改为唯一 `"protocol-p8-decision-only"`；
   - 明确 P8 只表示协议内部决定，不代表项目级 M8 准入、实现授权或 backend selection。
3. **C：canonical text-audit 与 P3/package 闭环**
   - 新增 closed `sa.m8.text-audit.v1.payload`，含 `audit_id`、protocol identity、repository binding、verdict、findings 和恰两个 object bindings；
   - logical name 由 `audit_id` 唯一派生为 `external-artifacts/text-audits/<audit_id>.json`；
   - P3 read refs、binding、verdict/decision/next-action 全部机械闭合；
   - durable package 新增独立 `text_audit_member`，原 gate/input arrays 仍保持 9/19。

## 2. 差异规模

相对 `draft-0.10`：60 行新增、10 行删除（版本头部与 A/B/C 的规范文字）。未重排全文，未格式化无关段落。

实施后精确字节由提交前工具计算并填写在本节附表；协议使用纯 LF，受 `.gitattributes` 逐文件规则保护。

| 项 | 值 |
| --- | --- |
| 文件 | `m8-active-execution-protocol-draft-0.11.md` |
| 字节数 | `191290` |
| LF 行数 | `1457` |
| SHA-256 | `92e28958eb3e5d938e8646704fa22a297430bfede3d53f04ba941181c9b8d40d` |

## 3. 冻结边界核验

`tools/m8_validate_draft011_revision.py` 覆盖正向与负向案例，并逐字比较冻结锚点：

- `ID`、`SCHEMA_ID`、`TECH_GATE_ID`；
- `order=value`、`order=key(...)`；
- `BINDING_STREAM_ALLOWLIST`；
- 完整 status-map section（72 行与两项 72..72）；
- gate 顺序；
- 不存在 draft-0.11 gate/artifact。

`tools/m8_verify_draft011_authorization.py` 继续核验授权边界、7 条 draft-0.10 binding surface、冻结对象摘要和 M8 阻断状态。

## 4. 明确未执行

- 未创建 draft-0.11 P0/P1/P2/P3 或任何 gate；
- 未创建 identity、binding、canonical text-audit 或运行期 artifact；
- 未复用或修改 draft-0.10 frozen chain；
- 未创建 experiment root、获取依赖、准备输入或运行实验；
- 未请求 P4、发布证据、准入 M8 或选择后端；
- 未改变 M8 `BLOCKED / NOT_STARTED`。

## 5. 下一状态

修订正文完成后只能等待未参与起草的独立 reviewer 进行 P0：

```text
draft-0.11: DRAFTED / PENDING_INDEPENDENT_P0_REVIEW / UNBOUND
draft-0.10: P3 REJECTED / stop（历史冻结链）
M8: BLOCKED / NOT_STARTED
```

本说明不预告 P0 或 P3 会通过。

# M8 最小 1K dry-run 协议 v2 修订授权记录

- 日期：2026-09-14
- owner：`justtodo123`
- 状态：`AUTHORIZED_FOR_V2_REVISION / NOT_S0_ACCEPTED / NOT_EXECUTION_AUTHORIZED`
- 前版：`m8-minimal-1k-dry-run-protocol-v1.md`
- 前版 S0：`PROTOCOL_REJECTED / stop`
- finding IDs：`m8-s0-001`～`m8-s0-008`

## 1. 授权决定

Owner `justtodo123` 授权创建新的最小协议 v2，只针对独立 S0 记录中的八项 finding 做闭合修订，并在完成后重新申请
独立 S0。v1、v1 schema、v1 validator、S0 materials、worksheet 与拒绝审计均保持原字节，不得就地改写。

## 2. 精确修订范围

1. `m8-s0-001`：区分并冻结 `reviewed_object_commit` 与 `review_package_commit`；
2. `m8-s0-002`：为 identity、input manifest、run report、validation report、cleanup receipt、decision record
   六类 payload 建立按 schema ID 分支的闭合 JSON Schema；
3. `m8-s0-003`：validator 必须实际调用完整 schema 校验，并验证 logical name、REF、跨 artifact 映射及全部负例；
4. `m8-s0-004`：闭合 query counts、parity policy、精确依赖版本、commit 格式和 clean-worktree proof；
5. `m8-s0-005`：冻结 deterministic chunk/query/gold/negative fixture 生成算法；
6. `m8-s0-006`：冻结 acquisition/measured phase、进程树范围、network/write/redaction observer 与 fail-closed evidence；
7. `m8-s0-007`：闭合 logical-name 派生、typed REF、actor role、timestamp、digest、计数和资源字段；
8. `m8-s0-008`：建立仓库外但隔离根外的持久 evidence directory，规定 package/cleanup receipt 顺序，并使 cleanup
   成功成为最终 validation PASS 与 S2 `EVIDENCE_READY` 的必要条件。

## 3. 不得扩张

v2 继续只覆盖 SQLite linear exact 与 LanceDB embedded exact/flat 的 1K synthetic dry-run。不得加入 Qdrant、ANN、
10K/100K、真实资料、生产 adapter、迁移/cutover、后端选择或 M8 admission；不得创建 draft-0.11 P4。

本授权不接受 v2 技术文字，不指定 S0 reviewer，不预置 S0 verdict/findings，不授权 S1、环境创建、依赖安装、输入生成或
SQLite/LanceDB 执行。M8 继续 `BLOCKED / NOT_STARTED`。

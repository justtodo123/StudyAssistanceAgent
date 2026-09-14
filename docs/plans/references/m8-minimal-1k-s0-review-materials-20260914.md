# M8 最小 1K 协议 S0 独立审查材料

- 日期：2026-09-14
- 状态：`S0_MATERIALS_READY / INDEPENDENT_REVIEW_REQUIRED / NOT_A_DECISION`
- drafting party：`ai-assistant`
- owner：`justtodo123`
- protocol：`m8-minimal-1k-dry-run-protocol-v1.md`
- protocol SHA-256：`2312509a17d5cacbce61c56dfad53dfde3e498fd332443f0bdbca6f87d0910e3`
- protocol bytes/LF：`6594 / 132`
- envelope schema SHA-256：`498a9cb4d8f695e7e5d0a4b04e548c286477fff36770ce29b5c85c6e0d4a58ed`
- validator SHA-256：`5000e5eb2b4f675f868abe25080bc59315c9dba74ae3bb876235e9b0f71ee700`
- frozen commit：`306f8267fd0bebb517a2a5d7f921c761d0d1180d`

## Reviewer 必查项

1. 协议是否只覆盖 SQLite/LanceDB 1K synthetic dry-run；
2. 是否与 draft-0.11 拒绝链明确分离，且没有创建 P4；
3. S0–S3 的 actor、decision、权限和停止点是否清楚；
4. S1 是否在执行前冻结 identity、commit、输入、依赖、网络和临时根；
5. 两个 backend 是否强制使用同一 input digest；
6. hard failure 是否覆盖 identity、filter/no-hit、reopen、网络、越界写、redaction 和 cleanup；
7. 六类最小 artifact 是否足以记录真实 1K 产物，而未提前定义 10K/100K universe；
8. 1K 接受是否明确不自动授权 10K、backend selection 或 M8 admission；
9. validator 的正例能否实例化，且 10K、第三 backend、measured network 和额外字段负例能否 fail closed；
10. 是否存在其他使完整 S0→S3 合法实例无法构造的文本/schema 矛盾。

## 允许裁定

- `PROTOCOL_ACCEPTED / request-s1`：未发现阻断问题；
- `PROTOCOL_REJECTED / stop`：必须列出 findings。

本材料不预置 reviewer、verdict、findings 或 S1 授权。S0 即使接受，也只允许 owner 准备独立 S1；不得创建实验环境、
安装依赖、生成 1K 输入或运行 dry-run。

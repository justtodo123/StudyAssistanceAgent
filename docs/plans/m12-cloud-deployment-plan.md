# M12 可选云端单用户部署准入准备计划

> 当前状态：设计准备；`BLOCKED / NOT_STARTED`，未获准开工
> 拟议前置：M8–M11 退出证据；本地离线 profile 保持有效
> 范围决策：[`references/m8-m12-scope-decision-v1.md`](references/m8-m12-scope-decision-v1.md)
> 最终状态权威：[`docs/PLAN.md`](../PLAN.md)

## 1. 目标、范围与非目标

M12 的唯一正式退出目标是：

> 在保留本地离线默认 profile 的同时，在负责人提供的云服务器上完成可复现、可撤销、可备份恢复的单用户云端部署，
> 支持显式授权的远程访问和后台数据任务。

云端是 opt-in deployment profile，不替代本地应用。M12 不包含多租户、团队共享、开放注册、计费、百万级规模、
Kubernetes/集群编排或跨区域高可用；这些能力如未来需要，必须进入新的阶段和 Decision 集。

## 2. 不可削弱的不变量

- 本地 profile 在无网络、无服务器、无云端账号时仍可启动并保留默认知识包和学习闭环；
- 云端不能成为本地私人 Source、session、review history 或 mastery 的默认同步目标；
- 上传、导出、删除和数据驻留必须显式授权，默认不上传本地用户资料；
- 应用、控制面、向量数据面和对象/文件存储职责必须分离，权限最小化；
- 专业向量索引仍是可重建数据面，不能成为权限、删除或审计的唯一权威；
- M11 的许可、provenance、generation、tombstone、hard-delete 和 published snapshot 语义在云端保持一致；
- secret、token、正文、凭据和绝对路径不得进入日志、trace、错误或公开 artifact。

拟议阶段前置继续保持未满足，不因本计划或云服务器存在而自动闭合：

| Prerequisite ID | 状态 | 闭合条件 |
| --- | --- | --- |
| `M12-M8-EXIT` | `OPEN` | M8 取得独立完成批准并提供可引用退出证据 |
| `M12-M9-EXIT` | `OPEN` | M9 取得独立完成批准并提供可引用退出证据 |
| `M12-M10-EXIT` | `OPEN` | M10 取得独立完成批准并提供可引用退出证据 |
| `M12-M11-EXIT` | `OPEN` | M11 取得独立完成批准并提供可引用 published snapshot 退出证据 |

## 3. 强制 Decision（准入前全部保持 `OPEN`）

| Decision ID | 状态 | 准入前必须选定并留证的内容 |
| --- | --- | --- |
| `M12-SERVER-BASELINE` | `OPEN` | OS、CPU、RAM、SSD、网络、区域、成本、维护人与支持周期 |
| `M12-DEPLOYMENT-PROFILE` | `OPEN` | 单用户拓扑、进程/容器、端口、域名、HTTPS、启动和升级方式 |
| `M12-IDENTITY-AUTH` | `OPEN` | 单用户认证、凭据生命周期、session、brute-force/lockout 和恢复 |
| `M12-CONTROL-PLANE` | `OPEN` | 云端继续 SQLite 或采用事务数据库的权威、迁移、备份和回滚边界 |
| `M12-VECTOR-DATA-PLANE` | `OPEN` | LanceDB 或 Qdrant 条件评估、持久化、恢复、timeout 和 fallback |
| `M12-INGESTION-WORKER` | `OPEN` | 后台 job、队列/调度、幂等、checkpoint、资源、取消和 poison task |
| `M12-STORAGE-BACKUP` | `OPEN` | 原文/normalized/index/数据库位置、加密、备份、恢复演练和保留 |
| `M12-PRIVACY-RESIDENCY` | `OPEN` | 上传授权、数据区域、日志、导出、删除、留存和服务器运维访问 |
| `M12-OBSERVABILITY` | `OPEN` | 健康、资源、任务、错误、告警、脱敏和审计，不记录正文或 prompt |
| `M12-SECURITY-HARDENING` | `OPEN` | 最小权限、防火墙、HTTPS、更新、依赖/镜像、secret 和漏洞响应 |
| `M12-COST-CAPACITY` | `OPEN` | 10K 真实/100K capacity 的 CPU、RAM、disk、流量、备份和月成本预算 |
| `M12-LOCAL-CLOUD-COMPAT` | `OPEN` | 本地/云端 schema、manifest、export/import、删除和回退兼容性 |
| `M12-ROLLOUT-ROLLBACK` | `OPEN` | 默认关闭、显式启用、canary、kill switch、回滚和本地继续可用 |

每项 Decision 必须包含唯一政策值、证据、责任人、日期、复核/撤销条件和独立批准。服务器存在不等于适合部署；
未提供并验证配置前，`M12-SERVER-BASELINE` 保持 `OPEN`。

## 4. 推荐单用户拓扑（非批准方案）

```text
Client / Browser
  → HTTPS reverse proxy
    → StudyAssistanceAgent API
      ├─ authoritative control plane
      ├─ background ingestion worker
      ├─ optional vector data plane
      └─ approved file/object storage
```

第一版优先单机云服务器、最少进程和可恢复持久卷。是否使用容器、PostgreSQL、Qdrant 或对象存储必须由上述 Decision
和真实服务器资源决定，不因业界常见架构自动采用。

## 5. Qdrant 条件候选政策

Qdrant 只在以下条件经验证后进入云端候选：

- 服务器资源足以同时运行应用、控制面、worker、Qdrant 和备份；
- 常驻服务、远程访问或明确并发需求使嵌入式数据面收益不足；
- payload filter、owner/source/generation、tombstone/delete、snapshot/reopen 与 SQLite oracle parity 通过；
- timeout、服务不可达、损坏、升级和恢复演练通过；
- 版本、许可证、持久卷、备份和成本在冻结边界内；
- 失败不影响本地离线 profile，也不造成未授权数据上传。

Qdrant local/path fixture 或单次 benchmark 不能自动批准 server。若 LanceDB/SQLite 已满足单用户云端目标，允许明确
“不采用 Qdrant”。Milvus 不在 M12 第一版范围内。

## 6. 安全与隐私最低门槛

- 只开放必要 HTTPS 入口；数据库、向量服务和 worker 管理端口不直接暴露公网；
- secret 通过服务器 secret/env 管理，不提交 Git、不进入镜像层或日志；
- 管理账号使用强认证与恢复流程，禁止默认凭据；
- 上传必须显示目标、范围和数据驻留；本地 Source 默认不自动同步；
- 日志只记录 ID、状态、耗时、计数和脱敏错误，禁止正文、prompt、token、凭据和绝对路径；
- 备份加密并执行真实恢复演练；删除同时覆盖主存储、索引、cache、备份保留策略和 receipt；
- 更新和回滚都必须绑定版本、manifest 和 last-good。

## 7. 容量、性能与成本验证

准入前冻结服务器配置和预算；至少验证：

- 10K 真实 published snapshot 的冷启动、查询、增量、删除和备份；
- 100K synthetic capacity 的 build/rebuild、filter、reopen、RSS、disk 和恢复；
- 1/5/10 并发作为单用户多任务基线；更高并发只有真实需求后再扩展；
- ingestion worker 与在线学习请求的资源隔离；
- 网络中断、服务重启、磁盘不足、备份失败和升级回滚；
- 月度服务器、磁盘、备份和流量预算。

云端 benchmark 不得覆盖本地 benchmark，也不得因服务器更快而削弱 correctness、privacy 或 lifecycle 门槛。

## 8. 获准后的拟实施顺序

1. 记录服务器硬件、系统、网络、成本和运维责任，关闭 `M12-SERVER-BASELINE`；
2. 关闭十三项 Decision，冻结单用户拓扑和威胁模型；
3. 在隔离环境部署最小 API + 控制面，不接真实用户数据；
4. 配置 HTTPS、认证、secret、防火墙、脱敏日志和备份；
5. 接入 M10 background job envelope，先用 synthetic fixture 验证恢复；
6. 评估嵌入式数据面；只有触发条件成立才评估 Qdrant server；
7. 导入 M11 经批准的最小 snapshot，验证 export/import、删除和回滚；
8. 执行容量、故障、安全和备份恢复验收；
9. 负责人显式启用单用户云端 profile，并保留本地 kill switch/fallback。

## 9. 准入检查与批准记录

- [ ] M8–M11 真实退出证据有效；
- [ ] 十三项强制 Decision 全部 `RESOLVED`；
- [ ] 服务器 baseline、威胁模型、拓扑、成本与支持责任冻结；
- [ ] 本地数据默认不上传、删除/导出/驻留政策明确；
- [ ] HTTPS、认证、secret、备份恢复和故障演练方案可执行；
- [ ] `docs/PLAN.md`、本计划和机器门禁一致；
- [ ] 负责人完成阶段 admission、生产开工和最终 rollout 的分离批准。

| 批准字段 | 当前值 |
| --- | --- |
| approved_by | — |
| approved_at | — |
| approval_reference | — |
| plan_revision | — |
| decision_set_version | — |

批准为空，M12 必须保持 `BLOCKED / NOT_STARTED`。本文不授权登录服务器、开放端口、安装软件、上传数据、创建账号、
启动服务、运行 benchmark、commit、merge 或 push。

## 10. 撤销与后续边界

服务器、域名/证书、身份认证、控制面、向量后端、隐私/驻留、备份、成本预算或 rollout 范围实质变化时，阶段 admission
必须 `REVOKED`。出现未授权上传、secret 泄露、删除不完整、公开服务暴露、无法恢复备份或本地离线 profile 被破坏时，
立即停止云端 rollout 并回到本地 profile。

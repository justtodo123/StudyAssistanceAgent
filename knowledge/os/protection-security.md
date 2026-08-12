---
title: 保护与安全
course: os
tags: [安全, 保护, 访问控制, 认证, 威胁]
difficulty: 中等
updated: 2026-08-12
source: docs/reference/os.md
---

## 一句话概括

保护 = 控制进程对资源的合法访问（内部机制）；安全 = 抵御外部恶意攻击（防御体系）。OS 负责两件事：谁可以访问什么（访问控制）+ 怎么证明你是谁（认证）。

## 核心概念

### 保护域 (Protection Domain)

- **域** = 一组 (对象, 权限) 对的集合；一个进程在其域内可访问特定资源
- 静态域：进程生命周期域不变
- 动态域：进程可根据需要切换域（如 Unix setuid 临时提权）
- **最小权限原则**：进程只获得完成任务所必须的最小权限

### 访问矩阵 (Access Matrix)

行 = 域/主体，列 = 对象/资源，单元格 = 权限集：

| 域 | File1 | File2 | Printer |
| --- | --- | --- | --- |
| D1 | Read | Read/Write | — |
| D2 | — | Read | Print |

**实现方式**（关键二分）：

| 实现 | 方向 | 说明 |
| --- | --- | --- |
| **访问控制表 ACL** | 按列存储 | 每个对象附带列表：[域1:R, 域2:W, …]；如文件权限位 |
| **能力表 Capability** | 按行存储 | 每个域/进程持有能力列表；如 Linux fd 表项 |

> ACL 是对象视角，Capability 是主体视角。Unix 混合两者：进程打开文件时 fd 相当于临时 capability。

### Unix/Linux 权限模型

```
-rwxr-xr--  1 alice cs  4096 Aug 10 file.txt
│││││││││
│└┬┘└┬┘└┬┘
│ U  G   O (User/Group/Other × rwx)
└─ 文件类型 (- 普通, d 目录, l 符号链接)
```

- 权限检查顺序：若 UID 匹配 → 用 User 权限；否则 GID 匹配 → 用 Group；否则 → Other
- **root (UID=0)** 绕过所有权限检查
- 特殊位：**setuid**（执行时临时提升为文件所有者权限）、**sticky bit**（仅所有者能删除 /tmp 中的共享文件）

### 安全威胁与防御

| 类别 | 攻击方式 | 防御 |
| --- | --- | --- |
| 缓冲区溢出 | 覆盖栈上返回地址执行恶意代码 | ASLR（地址随机化）、NX/XD bit（栈不可执行）、Stack Canary |
| 恶意软件 | 病毒 (寄生)/蠕虫 (自复制)/木马 (伪装) | 沙箱、签名验证、最小权限 |
| 侧信道 | Spectre / Meltdown（推测执行泄露） | 内核页表隔离 KPTI、微码补丁 |
| DoS/DDoS | 大量请求耗尽资源 | 限流、CAPTCHA、IP 过滤 |
| 用户认证攻击 | 字典/暴力/撞库 | 密码盐值+Hash、MFA、锁账号 |

**ASLR 原理**（常见面试题）：每次加载程序时为栈、堆、共享库分配**随机基址**，使攻击者无法硬编码跳转地址。`/proc/sys/kernel/randomize_va_space` 控制。

## 易错点 / 高频考点

- [ ] 保护 ≠ 安全：保护是内部访问控制机制（ACL/Capability），安全是面对外部威胁的防御体系
- [ ] setuid 提升的是**有效 UID**（EUID），不是真实 UID（RUID）——可用 `getuid()` vs `geteuid()` 验证
- [ ] 权限检查只看 EUID，不是以 RUID 为准

## 经典例题

**题干**：简述 Linux 打开文件 `/etc/passwd` 的完整权限检查过程。
**解答**：(1) 路径解析：/→etc/→passwd，每个目录需有 x（搜索）权限；(2) 到 passwd 后检查：若 UID 匹配→取 user 权限；否则 GID 匹配→取 group；否则→other；(3) 进程需有 r 权限才能 open(O_RDONLY)。

## 关联条目

- [[os-interface]] 操作系统接口（setuid 与 shell）
- [[linux-case-study]] Linux 实例
- 外部资料索引：[docs/reference/os.md](../../docs/reference/os.md)

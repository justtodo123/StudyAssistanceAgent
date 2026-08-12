---
title: Linux 操作系统实例
course: os
tags: [Linux, 内核, 进程调度, 内存管理, 文件系统]
difficulty: 中等
updated: 2026-08-12
source: docs/reference/os.md
---

## 一句话概括

以 Linux 为实例串联 OS 各章知识点：它的进程模型、CFS 调度器、伙伴系统内存分配、ext4 文件系统和内核模块机制是课程理论在真实系统中的最经典实践。

## 核心概念

### Linux 进程模型

- **task_struct**（PCB）：存进程状态、pid/tgid、mm_struct（内存）、fs_struct（文件系统）、files_struct（打开的文件）
- **线程实现**：`clone()` 系统调用，与 fork 共用 `do_fork()`，差别是**共享哪些资源**（CLONE_VM / CLONE_FILES / CLONE_SIGHAND 等）
- **进程状态**：TASK_RUNNING（运行/就绪）、TASK_INTERRUPTIBLE（可信号唤醒的阻塞）、TASK_UNINTERRUPTIBLE（不可信号唤醒，如等磁盘 I/O）、TASK_STOPPED、TASK_ZOMBIE

> 僵尸进程：子进程已退出但父进程未 wait，PCB 仍在内核中（`Z` 状态）。无法用 kill，只能杀掉父进程或 wait。

### CFS 调度器 (Completely Fair Scheduler)

- 核心原则：每个进程获得**公平的 CPU 时间比例**
- **vruntime** = 实际运行时间 × (1024 / nice 权重)；nice 值越大权重越小、vruntime 增长越快
- 红黑树排序：**vruntime 最小**的进程在树最左侧，最优先调度
- 调度周期：`sched_period` 内所有可运行进程至少执行一次（默认 ~6ms × nr_running）
- **nice 值**：-20（高优先级）~ +19（低优先级），默认 0

与课程调度算法对比如下：

| 课程概念 | Linux 实现 |
| --- | --- |
| SJF 贪心 | CFS 公平而非贪心——追求公平 |
| 优先级算法 + 老化 | nice 值 + vruntime（动态老化天然存在） |
| 多级反馈队列 | CFS 就一个调度类（SCHED_NORMAL），早被替代 |

### Linux 内存管理：伙伴系统 (Buddy System)

- 物理页框按 2^order (0~10) 组织，分配时找大小刚好（或稍大）的空闲块
- 若找不到 → 分裂大块；释放时若相邻 buddy 也空闲 → 合并
- **优点**：减少外部碎片、分配释放 O(logN)；**缺点**：内部碎片（申请 3 页给 4 页）
- Slab 分配器在上层：为小对象（task_struct, inode, dentry）提供对象缓存，减少伙伴系统碎片

### ext4 文件系统

| 组件 | 作用 |
| --- | --- |
| 超级块 (Superblock) | 文件系统元数据（块大小、inode 数、空闲块数） |
| 块组描述符 (GDT) | 每个块组的元数据 |
| inode 表 | 每个文件的 inode（权限、大小、块指针、时间戳） |
| 数据块 | 文件内容 + 目录项 |
| 日志 (Journal) | 写前先写日志，保证崩溃一致性 |

- **extent 替换间接块**：记录「起始块号 + 连续块数」而非逐块指针，大文件性能碾压旧索引分配
- 延迟分配 (delayed allocation)：数据块到刷盘时才分配物理块，减少碎片

### Linux 内核模块

- **单内核 + 可加载模块 (LKM)**：核心功能编译进内核，驱动/文件系统等做成 `.ko` 模块化
- `lsmod` 列出已加载模块，`insmod`/`modprobe` 加载，`rmmod` 卸载
- 好处：不必重新编译整个内核，驱动开发方便

### VFS（虚拟文件系统）

- 统一文件操作接口：`read()`/`write()`/`open()` 不区分 ext4/xfs/nfs——上层调用相同系统调用
- 四种核心对象：super_block、inode、dentry（目录项缓存）、file（打开文件上下文）

## 易错点 / 高频考点

- [ ] CFS 不是「先来先服务」也不是「短作业优先」，而是**公平份额**调度
- [ ] 伙伴系统分配按 2^order → 有内部碎片（如申请 3 页给 4 页）；Slab 是进一步的优化层
- [ ] ext4 的 extent ≠ 旧的索引块指针；extent 存「起止位置」而非逐块地址
- [ ] 内核模块没有独立的地址空间——它是内核的一部分，模块 bug 会 panic 整个系统

## 经典例题

**题干**：描述 `fork()` 创建进程时 Linux 内核做了什么。
**解答**：(1) 分配新 pid + task_struct；(2) 复制父进程 mm_struct，实际页通过**写时复制 COW** 延迟复制；(3) 复制 files_struct（两个进程共享文件描述符表），fd 引用计数递增；(4) 复制信号处理表、其他数据结构；(5) 子进程返回 0，父进程返回子进程 pid；(6) 调度器决定谁先运行（通常子进程优先级稍低避免 fork 炸弹）。

## 关联条目

- [[os-overview]] 内核体系结构
- [[process-management]] 进程与线程
- [[os-interface]] 系统调用与接口
- [[protection-security]] 权限与安全
- 外部资料索引：[docs/reference/os.md](../../docs/reference/os.md)

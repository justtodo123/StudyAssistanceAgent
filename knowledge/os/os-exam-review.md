---
title: 操作系统期考复盘与高频错题
course: os
tags: [考试, 真题, 错题, 高频考点, 期末]
difficulty: 进阶
updated: 2026-08-12
source: docs/reference/os.md
---

## 一句话概括

本文档按章节统计期末考试高频考点与易错题型，关联对应的知识库条目，便于考前突击与查漏补缺。

## 各章考点权重（粗略）

| 章节 | 分值占比 | 题型 | 关联条目 |
| --- | --- | --- | --- |
| 进程管理 + 调度 | ~20% | 选择/简答/计算 | [[process-management]], [[process-scheduling]] |
| 同步与互斥 | ~20% | PV 伪码大题 | [[synchronization]] |
| 死锁 | ~15% | 银行家计算/判断 | [[deadlock]] |
| 内存管理 + 虚拟内存 | ~20% | 地址转换/置换计算/论述 | [[memory-management]], [[virtual-memory-deep]], [[segmentation-paging]] |
| 文件系统 | ~15% | 选择/磁盘调度计算/索引计算 | [[file-system]], [[disk-storage]] |
| OS 概述 + 接口 | ~5% | 选择/简答 | [[os-overview]], [[os-interface]] |
| I/O + 保护与安全 | ~5% | 选择 | [[io-system]], [[protection-security]] |

## 高频易错清单（按题型）

### 一、选择题陷阱

1. **「并发 = 并行」** ❌ —— 并发是逻辑同时（宏观），并行是物理同时（多核）
2. **「SPOOLing 是缓冲技术」** ❌ —— SPOOLing 是虚拟设备技术
3. **「银行家算法可预防死锁」** ❌ —— 银行家算法是死锁**避免**（预防=破坏必要条件）
4. **「Belady 异例也会发生在 LRU」** ❌ —— Belady 只在 **FIFO** 发生，LRU/OPT 有栈特性不会有
5. **「分页有外部碎片」** ❌ —— 分页有**内部**碎片；**分段**有外部碎片（高频设错）
6. **「TLB 命中后不需要访问内存」** ❌ —— TLB 命中后仍需访问内存取数据（TLB 只完成地址转换）
7. **「SCAN 算法和 LOOK 算法等价」** ❌ —— SCAN 走到磁盘尽头，LOOK 到最后一个请求即回头
8. **「信号量 V 操作可能阻塞」** ❌ —— **V 操作不会阻塞**，P 操作才可能阻塞

### 二、PV 操作大题（失分重灾区）

**常见坑位**：
- **P 操作次序错**：应先 P(资源信号量)，再 P(mutex)。反了可能死锁（经典：生产者消费者中 P(empty) 必须在 P(mutex) 之前）
- **忘了互斥信号量**：缓冲池访问需要 mutex 保护（PV 时位置正确）
- **信号量初值错**：同步用的信号量（如 empty/full）初值不是 1，而是缓冲区满/空的对应值
- **多进程前驱关系**：用初值=0 的信号量数组，前置进程 V，后置进程 P

**模板**：
```
// 前驱依赖：B 必须在 A 后执行
semaphore s = 0;
// A 尾部：V(s)
// B 开头：P(s)
```

### 三、银行家算法（计算题标准步骤）

1. 算 Need = Max - Allocation
2. 算 Available = 总资源 - sum(Allocation)
3. 安全检查循环（可考到找不出安全序列的题型）：
   - 找 Need[i] ≤ Work 的进程
   - Work += Allocation[i]
   - 标记为 Finish
   - 重复直到全 finish（安全）或无进程可满足（不安全）
4. 请求检查：Request ≤ Need 且 ≤ Available → 试分配→查安全→回滚或批准

### 四、缺页率 / 地址转换 计算

**页号 = 逻辑地址 / 页大小（整除）**
**页内偏移 = 逻辑地址 % 页大小**
**物理地址 = 页框号 × 页大小 + 页内偏移**

内存访问时间 EAT = (1-p) × T_mem + p × T_page_fault

注意：
- 十进制和十六进制的混算容易错——建议全部转化为十进制或统一用十六进制
- 缺页中断处理中对置换页「若修改则写回」多一步——计算 EAT 时考虑脏页比例

### 五、磁盘调度（寻道计算）

- 看清：SCAN 还是 LOOK？SCAN 到磁盘尽头（0/199），LOOK 到最远请求
- 方向默认：若没说当前方向，通常假设向小号方向（或明确说明）
- C-SCAN：单向走→跳回另一头→继续单向（不服务跳回的沿途）

## 考前速记口诀

```
调度 FCFS/SJF/RR/优先级/多级
同步 P before V  资源信号量在前
死锁四条件缺一不可要熟背：互斥 / 占有且等待 / 不可剥夺 / 循环等待
置换 OPT(最优) FIFO(Belady) LRU(找最久) CLOCK(访问位)
寻道 SCAN(要到底) LOOK(到最远) SSTF(贪心) C-SCAN(单向循环)
分页无外碎 分段有外碎 — 谁有内部碎？
系统调用 = 陷入 = 用户→内核的合法入口
```

## 关联条目

- [[os-overview]] 操作系统概述
- [[process-management]] → 进程管理
- [[synchronization]] → PV 大题
- [[deadlock]] → 银行家计算
- [[memory-management]], [[virtual-memory-deep]], [[segmentation-paging]] → 内存计算
- [[file-system]], [[disk-storage]] → 文件与磁盘
- 外部资料索引：[docs/reference/os.md](../../docs/reference/os.md)

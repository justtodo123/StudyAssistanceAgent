# 操作系统（os）

> 课程知识库入口。章节目录、重点难点、外部资料指针。

外部原始资料：`D:\111_Others_Subjects\操作系统`｜索引登记：[docs/reference/os.md](../../docs/reference/os.md)

## 章节地图

| 章节 | 条目 | 状态 |
| --- | --- | --- |
| 操作系统概述 | [os-overview.md](os-overview.md) | ✅ |
| 操作系统接口与 Shell | [os-interface.md](os-interface.md) | ✅ |
| 进程与线程 | [process-management.md](process-management.md) | ✅ |
| 进程调度 | [process-scheduling.md](process-scheduling.md) | ✅ |
| 同步与互斥 | [synchronization.md](synchronization.md) | ✅ |
| 死锁 | [deadlock.md](deadlock.md) | ✅ |
| 内存管理（分页/分段） | [memory-management.md](memory-management.md) | ✅ |
| 段页式存储管理 | [segmentation-paging.md](segmentation-paging.md) | ✅ |
| 虚拟内存深入 | [virtual-memory-deep.md](virtual-memory-deep.md) | ✅ |
| 文件系统 | [file-system.md](file-system.md) | ✅ |
| 磁盘存储管理 | [disk-storage.md](disk-storage.md) | ✅ |
| I/O 系统 | [io-system.md](io-system.md) | ✅ |
| 保护与安全 | [protection-security.md](protection-security.md) | ✅ |
| Linux 操作系统实例 | [linux-case-study.md](linux-case-study.md) | ✅ |
| 期考复盘与高频错题 | [os-exam-review.md](os-exam-review.md) | ✅ |

**共 15 篇条目**（含 1 篇期考复盘）

## 重点 / 难点（高频考点速览）

- 进程调度算法（FCFS / SJF / RR / 优先级 / 多级反馈队列 / HRRN）
- 同步与互斥：信号量、生产者消费者、读者写者、哲学家进餐（PV 伪码）
- 死锁四条件 + 银行家算法（安全序列计算）
- 页面置换（OPT / FIFO / LRU / CLOCK）+ Belady 异例
- 分页地址转换计算、页表多级/快表 TLB、段页式三级映射
- 虚拟内存：请求分页、写时复制 COW、工作集模型、抖动防治
- 文件分配方式（连续/链接/索引/XFS extent）+ inode + 位示图
- 磁盘调度（FCFS/SSTF/SCAN/LOOK/C-SCAN）寻道计算
- I/O 控制方式（程序/中断/DMA/通道）+ 缓冲 + SPOOLing
- 操作系统安全：访问矩阵 ACL/Capability、ASLR、缓冲区溢出防御

## 外部资料指针

见 [docs/reference/os.md](../../docs/reference/os.md)（课堂课件：第01-09章、期末真题、课程设计、实验1-4）。

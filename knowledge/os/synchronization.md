---
title: 进程同步与互斥
course: os
tags: [信号量, 互斥, 同步, PV操作, 经典问题]
difficulty: 进阶
updated: 2026-08-10
source: docs/reference/os.md
---

## 一句话概括

多个进程并发访问同一临界资源时，需要**互斥**（同一时刻只有一个进程进入临界区）与**同步**（进程按正确顺序协作）。核心工具是信号量与 PV 操作。

## 核心概念

### 临界区（Critical Section）

- 临界资源：一次仅允许一个进程使用的资源（打印机、共享变量）
- 临界区：访问临界资源的代码段
- 进入临界区要满足：**互斥**、**前进**（不阻塞无关进程）、**有限等待**（不无限等待）

### 同步与互斥辨析

- **互斥**：同一资源同一时刻只能一个进程用——是**间接制约**（不同进程间）
- **同步**：进程间按既定次序协作（如：先取数后处理）——是**直接制约**
- 互斥是同步的一个特例（互只要一个信号量=1；同步至少要两个或语义化安排）

### 信号量与 PV 操作

```
S 为整型信号量（资源数）。
wait(S)  /  P(S)：while S<=0 阻塞；否则 S--
signal(S) / V(S)：S++；若有等待者，唤醒一个
```

- `S>0` 表示可用资源数；`S<0` 表示等待进程数
- **P 操作可能阻塞，V 操作不会阻塞**
- 信号量必须原子实现（关中断/TSL 指令/硬件原子）

### 互斥模板（一个信号量即可）

```
semaphore mutex = 1;
P(mutex); 进入临界区; V(mutex);
```

## 经典同步问题（高频考点，务必会写伪码）

### 1. 生产者消费者（有界缓冲）

```
empty = n（缓冲区空位）；full = 0；mutex = 1
Producer:                    Consumer:
  while(true){                 while(true){
    produce(item);               P(full);
    P(empty);                    P(mutex);
    P(mutex);                    item = buffer[out];
    buffer[in] = item;           V(mutex);
    in = (in+1)%n;               V(empty);
    V(mutex);                    consume(item);
    V(full);                   }
  }
```

> ⚠️ P(empty)/P(full) 必须在 **P(mutex) 之前**，否则可能死锁（缓冲为空时生产者持有 mutex 等 full，消费者无法进临界区放 full）。

### 2. 读者写者问题

- 读者优先：多读者可同时读，但写者必须等读者走完
- ⚠️ 写者可能**饿死**（读者源源不断）

```
rw_mutex = 1; mutex = 1; read_count = 0
Reader:                       Writer:
  P(mutex);                     P(rw_mutex);
  read_count++;                 write();
  if(read_count==1) P(rw_mutex);  V(rw_mutex);
  V(mutex);
  read(); P(mutex);
  read_count--;
  if(read_count==0) V(rw_mutex);
  V(mutex);
```

### 3. 哲学家进餐（防死锁关键）

- 5 个哲学家围桌，每相邻两人间一根筷子
- **错误做法**：每个人都先拿左边再拿右边 → 同时拿起左筷 → **死锁**
- **解决**：① 最多 4 人同时拿筷（加一个计数信号量）；② 一人先拿右筷（打破环路）；③ 用状态划分（思考/饥饿/吃）—信号量数组

## 易错点 / 高频考点

- [ ] P 与 V 的次序：**先 PV 资源信号量，后 PV mutex**
- [ ] V 操作不会阻塞，写「V(mutex) 会阻塞生产者在缓冲区满时」是错的
- [ ] 读者写者中 `read_count` 自身要加 mutex 保护
- [ ] 同步题建模：先确定「前驱/后驱关系」，再决定信号量初始值

## 经典例题

**题干**：三个进程 A、B、C，要求 A 执行完后 B、C 才能执行，用 PV 操作写出。
**解答**：信号量 `Sb=0, Sc=0`。A 尾部 `V(Sb); V(Sc);`；B 开头 `P(Sb)`；C 开头 `P(Sc)`。即后驱关系用「初值 0 的信号量 + 前置进程尾部 V + 后置进程开头 P」。

## 关联条目

- [[process-management]] 进程管理
- [[deadlock]] 死锁（同步设计不当即死锁来源）
- 外部资料索引：[docs/reference/os.md](../../docs/reference/os.md)

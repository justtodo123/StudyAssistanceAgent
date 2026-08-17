---
title: 线性表（顺序表与链表）
course: ds
tags: [线性表, 顺序表, 链表, 算法]
difficulty: 中等
updated: 2026-08-17
source: docs/reference/ds.md
---

## 一句话概括

线性表是 n 个数据元素的有限序列。顺序存储（数组）与链式存储（指针）各有取舍：顺序表随机访问 O(1)，链表插入删除 O(1)（已有前驱指针时）。本章高频考手写链表操作伪码与顺序/链式对比分析。

## 核心概念

### 线性表的定义

- 线性表中的元素具有逻辑上的顺序性（前驱 / 后继关系唯一，首元素无前驱，尾元素无后继）
- 基本运算：InitList、Length、Get、Locate、Insert、Delete、Print

### 顺序表（Sequential List）

- 用一段地址连续的存储单元（数组）依次存储线性表的数据元素
- `Loc(L, i) = Loc(L, 1) + (i-1) × sizeof(元素)` —— 等差地址计算公式
- 插入 / 删除需移动大量元素（平均约 n/2 个）
- 时间复杂度：随机访问 O(1)；插入/删除 O(n)

### 单链表（Singly Linked List）

```c
typedef struct LNode {
    ElemType data;
    struct LNode *next;
} LNode, *LinkList;
```

- 从头指针 L 开始，沿 next 指针顺序访问
- 插入操作（在 p 之后插入 s）：`s->next = p->next; p->next = s;`
- 删除操作（删除 p->next）：`q = p->next; p->next = q->next; free(q);`
- 头结点（哨兵）：链表第一个结点为空结点，便于统一处理（插入/删除无需特殊处理首元素）

### 循环链表与双向链表

| 类型 | 特点 | 典型用途 |
| --- | --- | --- |
| 循环链表 | 尾结点 next 指向头结点，无空指针 | 约瑟夫环问题 |
| 双向链表 | 每个结点有 prior 和 next 两个指针 | 需要双向遍历的场景（如浏览器历史） |

### 顺序表 vs 链表对比

| 维度 | 顺序表 | 链表 |
| --- | --- | --- |
| 存储方式 | 连续地址（预分配） | 离散结点（动态分配） |
| 随机访问 | O(1) | O(n) |
| 插入/删除 | O(n)（移动元素） | O(1)（修改指针，已知前驱） |
| 适用场景 | 频繁查询、表长固定 | 频繁插入删除、表长不确定 |

## 关键原理 / 算法

### 单链表就地逆置（高频算法）

```c
// 头插法就地逆置：遍历原链表，依次用头插法插入新表头
void ReverseList(LinkList L) {
    LNode *p = L->next;
    L->next = NULL;
    while (p != NULL) {
        LNode *next = p->next;   // 暂存后继
        p->next = L->next;       // 头插：将 p 插在头结点之后
        L->next = p;
        p = next;                // 继续处理原下一结点
    }
}
```

### 逆序打印链表（2017 春真题 Q1 变式）

```c
// 不修改链表，递归实现逆序打印
void PrintListReverse(LNode *pListHead) {
    if (pListHead != NULL) {
        PrintListReverse(pListHead->next);  // 先递归到最后
        printf("%d ", pListHead->data);      // 回溯时再打印
    }
}
// 时间 O(n)，空间 O(n)（递归栈深度 n）
```

## 易错点 / 高频考点

- [ ] 删除链表结点时必须先暂存 `q = p->next`，再修改指针，最后 `free(q)`
- [ ] 头结点与头指针区别：头指针是指向第一个结点的指针（无论是否有头结点）
- [ ] 双向链表插入操作四步：`s->prior=p; s->next=p->next; p->next->prior=s; p->next=s;`（顺序敏感！）
- [ ] 逆置操作不要只记模板，理解「头插法的本质是反转链接方向」

## 经典例题

**题干**：已知单链表 L，将其所有元素就地逆置（不借助新数组）。
**解答**：头插法逆置（见上）；或用三个指针 pre=NULL, cur=L->next, next 逐个反转 next 方向。

## 关联条目

- [[ds-intro]] 时间复杂度分析
- [[stack-queue]] 栈（递归逆序打印本质是栈）
- 参考原始资料：`docs/reference/ds.md`（PPT 第二章：线性表）

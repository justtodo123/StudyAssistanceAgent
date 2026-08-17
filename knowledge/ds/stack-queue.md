---
title: 栈与队列
course: ds
tags: [栈, 队列, 线性结构, 递归]
difficulty: 中等
updated: 2026-08-17
source: docs/reference/ds.md
---

## 一句话概括

栈（后进先出 LIFO）与队列（先进先出 FIFO）是两种受限的线性表：栈只能在一端（栈顶）插入和删除，队列只能在队尾插入、队头删除。递归实现本质上依赖栈，循环队列是考试计算高频点。

## 核心概念

### 栈（Stack）

- 栈顶 Top 指示当前可操作元素；入栈前 Top 先增（Top++），出栈后 Top 减（Top--）
- 顺序栈：数组 + Top 指针，`MaxSize` 固定；链栈：链表头作为栈顶（无溢出，动态分配）
- 空栈：`Top = -1`（教材常用约定，考试题以教材约定为准）

### 队列（Queue）

- 队头 Front 出队，队尾 Rear 入队
- **循环队列**（顺序实现，考试重点）：用取模操作把数组首尾相接，避免假溢出
  - 初始：`Front = Rear = 0`
  - 入队：`Rear = (Rear + 1) % MaxSize`；出队：`Front = (Front + 1) % MaxSize`
  - 空队列条件：`Front == Rear`
  - 满队列条件：`(Rear + 1) % MaxSize == Front`（牺牲一个存储单元判满）
  - 队列元素个数：`(Rear - Front + MaxSize) % MaxSize`

### 栈与递归

递归调用时编译器维护「调用栈」：每次函数调用压栈保存返回地址、局部变量，返回时出栈恢复。递归深度 = 栈的最大深度（空间复杂度来源）。

## 关键原理 / 算法

### 循环队列计算示例（易错点）

```
MaxSize = 6，初始 Front = Rear = 0
入队 A,B,C,D → Rear = 4, Front = 0, 元素个数 = (4-0)%6 = 4
出队 A,B     → Rear = 4, Front = 2, 元素个数 = (4-2)%6 = 2
入队 E,F     → Rear = (4+1)%6=5, (5+1)%6=0 (循环!) → Rear = 0
          此时 (0+1)%6=1 == Front(2)? 否，未满，继续
满判条件：Rear 再前进 1 是否撞 Front
```

### 表达式求值（栈的经典应用）

中缀转后缀（调度场算法）：
- 操作数直接输出
- 运算符与栈顶比较优先级：当前优先级 > 栈顶才入栈，否则栈顶出栈后入栈
- 左括号入栈，右括号弹出直到遇左括号

```python
# 后缀表达式求值（操作数入栈，遇运算符弹两个操作数求值）
def eval_rpn(tokens):
    stack = []
    for t in tokens:
        if t.isdigit():
            stack.append(int(t))
        else:
            b, a = stack.pop(), stack.pop()
            if t == '+': stack.append(a + b)
            elif t == '-': stack.append(a - b)
            elif t == '*': stack.append(a * b)
            elif t == '/': stack.append(int(a / b))  # 整除
    return stack[0]

print(eval_rpn(["2", "1", "+", "3", "*"]))  # (2+1)*3 = 9
```

## 易错点 / 高频考点

- [ ] 循环队列「判满」牺牲一个空间，队列最大容量 = MaxSize - 1，不是 MaxSize
- [ ] `元素个数 = (Rear - Front + MaxSize) % MaxSize`，不要漏 `% MaxSize`
- [ ] 链栈没有溢出问题（动态分配），顺序栈有上溢；队列同理
- [ ] 表达式转换（中缀→后缀）考试常见，记清优先级：`* /` > `+ -`，左结合
- [ ] 递归深度直接决定空间复杂度（如 Fibonacci 递归 O(n) 栈空间）

## 经典例题

**题干**：设循环队列 MaxSize=8，经过若干入队出队后 Front=3, Rear=6，问队列中有几个元素？
**解答**：`(6 - 3 + 8) % 8 = 3`，队列有 3 个元素。

## 关联条目

- [[linear-list]] 线性表（栈/队列的存储结构基础）
- [[ds-intro]] 时间/空间复杂度分析
- 参考原始资料：`docs/reference/ds.md`（PPT 第三章：栈队列）

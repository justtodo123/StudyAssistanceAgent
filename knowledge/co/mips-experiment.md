---
title: MIPS CPU 设计实验复盘
course: co
tags: [MIPS, Logisim, CPU设计, 实验]
difficulty: 进阶
updated: 2026-08-17
source: docs/reference/co.md
---

## 一句话概括

MIPS CPU 设计实验通过 Logisim 搭建单周期/多周期 CPU，将指令系统、数据通路、控制器等理论知识落地。本条目记录实验关键设计决策与踩坑点。

## 核心概念

### MIPS 指令格式

| 类型 | 格式 | 示例 |
| --- | --- | --- |
| R 型 | `op(6) rs(5) rt(5) rd(5) shamt(5) funct(6)` | `add $rd, $rs, $rt` |
| I 型 | `op(6) rs(5) rt(5) imm(16)` | `lw $rt, imm($rs)` |
| J 型 | `op(6) addr(26)` | `j target` |

### 单周期 CPU

每条指令在一个时钟周期内完成（时钟周期 = 最慢指令的延迟）。

**数据通路**：
```
取指：PC → 指令存储器 → 指令
译码：指令 → 控制单元 + 寄存器堆读
执行：ALU 运算
访存：数据存储器读写（仅 Load/Store）
写回：结果写入寄存器堆
```

**控制信号**：RegDst、ALUSrc、MemtoReg、RegWrite、MemRead、MemWrite、Branch、ALUOp

### 多周期 CPU

将指令执行分为多个时钟周期（取指 1 + 译码 1 + 执行 1~2 + 访存 1~2 + 写回 1）。
- 每周期完成一个功能阶段
- 复杂指令用更多周期，简单指令用更少
- 时钟周期由最慢的**单步**决定（不是最慢指令）

### Logisim 实验关键点

- **ALU 设计**：支持 ADD、SUB、AND、OR、SLT 等操作
- **控制器**：硬布线方式，根据 opcode/funct 生成控制信号
- **数据通路连接**：注意多路选择器（MUX）的选择信号
- **时钟同步**：所有寄存器共用时钟边沿触发

## 易错点 / 高频考点

- [ ] 单周期 CPU 时钟周期 = **最慢指令**延迟，多周期 = **最慢单步**延迟
- [ ] R 型指令的功能码在 funct 字段，不在 op 字段
- [ ] 分支指令（beq）需要在执行阶段计算目标地址：PC+4+offset×4
- [ ] Logisim 中注意位宽匹配，总线宽度不一致会导致信号截断

## 关联条目

- [[instruction-system]] MIPS 指令格式和寻址方式
- [[cpu-design]] 数据通路、控制器、流水线理论
- [[alu]] ALU 的具体实现
- 参考原始资料：`docs/reference/co.md`（MIPS CPU 设计实验）

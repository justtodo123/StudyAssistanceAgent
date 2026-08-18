# 计算机组成原理（Computer Organization）

> 课程目标：理解计算机硬件系统的工作原理，掌握数据表示、运算器、存储系统、指令系统、CPU 设计、总线与 I/O 等核心知识。
> 本知识库为考试复习与面试备战提供精炼笔记。

## 章节地图

| 章节 | 条目文件 | 关键词 |
| --- | --- | --- |
| 概述 | [co-intro.md](co-intro.md) | 冯诺依曼、层次结构、性能指标 |
| 数据表示 | [data-representation.md](data-representation.md) | 补码、IEEE754、浮点数、校验码 |
| 运算器 | [alu.md](alu.md) | 加法器、乘法、除法、溢出检测 |
| 存储系统 | [memory-system.md](memory-system.md) | Cache、虚拟存储器、替换算法、局部性 |
| 指令系统 | [instruction-system.md](instruction-system.md) | 指令格式、寻址方式、CISC vs RISC |
| CPU 设计 | [cpu-design.md](cpu-design.md) | 数据通路、控制器、流水线、冒险 |
| 总线与 I/O | [bus-io.md](bus-io.md) | 总线仲裁、中断、DMA、I/O 方式 |
| MIPS 实验复盘 | [mips-experiment.md](mips-experiment.md) | Logisim、单周期 CPU、多周期 CPU |
| 浮点数运算（加减 / 乘除 / 舍入 / 溢出处理） | [floating-point-arithmetic.md](floating-point-arithmetic.md) | 浮点加法、对阶、舍入、IEEE754 |
| 期考复盘 | [co-exam-review.md](co-exam-review.md) | 高频考点、真题、易错点 |

| 数制、编码与定点数表示 | [number-systems-codes.md](number-systems-codes.md) | 数制、补码、移码、BCD |
| Booth 有符号乘法 | [booth-multiplication.md](booth-multiplication.md) | Booth、补码乘法、移位 |
| 补码除法与恢复余数算法 | [division-algorithms.md](division-algorithms.md) | 除法、商、余数 |
| Cache 地址映射与命中率 | [cache-mapping.md](cache-mapping.md) | 直接映射、组相联、Tag |
| 虚拟地址转换与 TLB | [virtual-memory-address-translation.md](virtual-memory-address-translation.md) | 页表、TLB、多级页表 |
| 控制器与微程序控制 | [control-unit.md](control-unit.md) | 硬布线、微程序、微指令 |
| 流水线性能与冒险处理 | [pipeline-performance.md](pipeline-performance.md) | CPI、前递、分支预测 |
| 中断系统与中断响应 | [interrupt-system.md](interrupt-system.md) | 中断向量、优先级、异常 |
| 总线仲裁与总线时序 | [bus-arbitration.md](bus-arbitration.md) | 仲裁、同步总线、异步总线 |
| 计算机性能指标与 Amdahl 定律 | [computer-performance.md](computer-performance.md) | CPU 时间、CPI、加速比 |

**共 20 篇条目**（含 1 篇期考复盘）· ✅ M4 规模补齐完成

## 重点与难点

- **数据表示**：补码运算、IEEE754 格式（选择题高频）
- **Cache**：地址映射、替换算法、命中率计算（大题高频）
- **流水线**：加速比、冒险处理（数据冒险 / 控制冒险）
- **I/O 方式**：程序查询 vs 中断 vs DMA 对比

## 外部资料指针

原始课件与实验资料见：[docs/reference/co.md](../../docs/reference/co.md)

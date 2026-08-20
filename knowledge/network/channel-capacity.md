---
title: 信道容量与信道复用
course: network
tags: [奈奎斯特, 香农, 信道复用, WDM, CDMA]
difficulty: 中等
updated: 2026-08-20
---

## 一句话概括（TL;DR）

> 奈奎斯特定理：无噪声最大数据率 = 2W·log₂V。香农定理：有噪声信道容量 = W·log₂(1+S/N)。信道复用四种方式：FDM/TDM/WDM/CDMA。

## 核心概念

### 奈奎斯特定理（无噪声）

- C_max = 2W × log₂V（bit/s），W 为带宽 Hz，V 为电平数

### 香农定理（有噪声）

- C = W × log₂(1+S/N)
- dB 换算：信噪比(dB) = 10·lg(S/N)，30dB → S/N=1000

### 信道复用

- **FDM**：按频率划分
- **TDM**：按时间片轮转
- **WDM**：光的频分复用
- **CDMA**：正交码片序列区分用户

## 易错点 / 高频考点

- [ ] 奈氏：C = 2W·log₂V（注意是 2W）
- [ ] 香农是对数公式，带宽翻倍容量不翻倍
- [ ] CDMA 内积：用户码片互为正交内积为 0

## 经典例题

**题干**：带宽 3.4kHz，信噪比 20dB，求香农信道容量。
**解答**：20dB → S/N=100；C = 3400 × log₂(101) ≈ 3400 × 6.66 ≈ 22.6 kbit/s。

## 关联条目

- [[encoding]]
- [[performance]]
- 参考原始资料索引：`docs/reference/network.md`

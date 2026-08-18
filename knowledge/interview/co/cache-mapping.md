---
title: Cache 映射与一致性
course: interview
tags: [Cache, 映射, 一致性]
difficulty: 进阶
updated: 2026-08-18
---

## 面试问题

Cache 映射与一致性：直接映射简单但冲突多；组相联在冲突和硬件成本之间折中；全相联灵活但比较器成本高。多核系统还需要协议维护各核缓存副本的一致性。

## 回答要点

一致性解决的是多个缓存副本看到的值是否符合协议；一致性不等于同步，也不自动保证高层业务操作的原子性。

## 项目结合点

多线程更新 MetricsRegistry 时，锁保证业务层原子性；仅依赖硬件缓存一致性不能保证复合更新不会丢失。

## 继续追问

MESI 协议中的 Modified、Exclusive、Shared、Invalid 分别表示什么？

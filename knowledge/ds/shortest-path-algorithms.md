---
title: 最短路径算法选型
course: ds
tags: [Dijkstra, Bellman-Ford, Floyd, 最短路径, 负权边]
difficulty: 进阶
updated: 2026-08-18
source: docs/reference/ds.md
---

## 一句话概括（TL;DR）

> 最短路径算法的选择取决于图的方向、边权是否为负、查询是单源还是多源以及图的稠密程度。Dijkstra 不能处理负权边，Bellman-Ford 可以检测负环。

## 核心概念

- Dijkstra 每次确定当前距离最小的未确定顶点，并松弛其出边。
- Bellman-Ford 重复松弛全部边 |V|-1 轮，可处理负权边并检测负环。
- Floyd 使用动态规划在中间顶点集合上逐步扩展，求所有点对最短路。

## 关键原理 / 算法

- 邻接表加二叉堆的 Dijkstra 复杂度常写为 O((V+E)logV)，适合非负稀疏图。
- Floyd 状态转移为 dist[i][j]=min(dist[i][j], dist[i][k]+dist[k][j])。
- 无向图出现负边通常会形成可往返的负环，因此不能直接套用单源算法。

## 易错点 / 高频考点

- [ ] Dijkstra 的贪心正确性依赖所有边权非负。
- [ ] 不可达距离使用 INF 时要先判断相加是否溢出或把 INF 当作真实数值。

## 经典例题

**题干**：若图中存在边 A→B=-2，不能使用 Dijkstra；可以使用 Bellman-Ford，并在第 V 轮仍能松弛时报告存在负环。

**解答**：先明确对象、状态和边界条件，再按条目中的定义逐步推导；计算题应在最后检查单位、符号和复杂度。

## 关联条目

- [[graph]]
- [[topological-critical-path]]
- [[union-find]]
- 参考原始资料：`docs/reference/ds.md`

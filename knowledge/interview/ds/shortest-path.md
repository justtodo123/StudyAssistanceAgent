---
title: Dijkstra、Bellman-Ford 与最短路
course: interview
tags: [最短路, Dijkstra, 图算法]
difficulty: 进阶
updated: 2026-08-18
---

## 面试问题

Dijkstra、Bellman-Ford 与最短路：Dijkstra 适用于边权非负图，每次确定当前距离最小的顶点；Bellman-Ford 可处理负权并检测负环，但复杂度更高；Floyd 适合小规模全源最短路。

## 回答要点

算法选择取决于边权性质、单源还是全源以及图的稀疏程度。使用优先队列实现 Dijkstra 时，旧距离条目需要丢弃或做 decrease-key。

## 项目结合点

检索排序不是图最短路，但多路召回也要把局部排名转换为全局分数；面试时可类比说明不同信号如何融合。

## 继续追问

为什么 Dijkstra 不能处理负权边？

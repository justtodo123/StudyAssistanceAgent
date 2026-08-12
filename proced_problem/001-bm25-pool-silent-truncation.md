---
problem_id: "001"
slug: bm25-pool-silent-truncation
date: 2026-08-12
tags: [retrieval, bm25, recall-regression, silent-failure, config-default]
severity: critical
status: fixed
related_files:
  - platform/app/config.py
  - platform/app/retrieval.py
  - platform/app/main.py
related_pr: "feature/m1a-os-knowledge (commits 8dc1a2f, 3f16498)"
---

# BM25 候选池静默截断导致 Recall@3 从 1.000 跌到 0.650

## 1. 症状（表现形式）

OS 知识库从 6 篇扩到 15 篇后，重跑 hybrid RAG 评测：

| 指标 | 扩容前（6 篇） | 扩容后（15 篇） | 变化 |
| --- | --- | --- | --- |
| Recall@1 | 0.950 | 0.650 | **-31.6%** |
| Recall@3 | 1.000 | 0.650 | **-35.0%** |
| Recall@5 | 1.000 | 0.700 | **-30.0%** |

20 题中有 7 题（35%）top-3 检索完全不命中相关文档——全部是"进程调度"和"同步/互斥"方向的问题。

系统无任何报错或警告。API 正常返回结果，只是结果**不是对的**。

## 2. 复现条件

1. 知识库包含 ≥ 50 个切片（15 篇 MD，每篇约 5-6 个 `##` 小节 → 89 片）
2. `SA_BM25_POOL` 保持默认值 `50`
3. 评测集中的问题所对应的相关文件在**文件路径排序后落在第 50 片以后**
4. 稳定复现——取决于文件路径排序（sorted by `Path.rglob`），非随机

## 3. 定位过程

**Step 1 — 验证不是评测集问题**：
在修复后的代码上跑原 20 题评测集 → Recall@3 回升到 0.950（接近原 1.000）。排除评测集问题。

**Step 2 — 逐题诊断**：
打印每道题 top-3 的命中文档，发现 7 道 MISS 全集中在 process-scheduling.md 和 synchronization.md。而其他条目（如 deadlock、memory-management、file-system）全部命中。

**Step 3 — 怀疑关键词**：
检查 BM25 分词器是否对"调度""同步"类关键词分词异常 → 分词正常，中文 bigram 输出符合预期。

**Step 4 — 确认切片索引分布**：
打印 `knowledge_index.json` 中每个文件的切片序号：
```
knowledge/os/process-scheduling.md: idx 50-55 (6 chunks)  ← 紧贴 50 边界
knowledge/os/synchronization.md:    idx 70-75 (6 chunks)  ← 远超 50
knowledge/os/deadlock.md:           idx 0-4                ← 在池内，全部命中
knowledge/os/memory-management.md:  idx 25-29              ← 在池内，全部命中
```

**Step 5 — 定位根因**：
在 `retrieval.py:44` 发现：
```python
pool = self._chunks[: config.BM25_POOL] or self._chunks
```
`BM25_POOL=50`，只取前 50 片。而且切片是按 `Path.rglob("*.md")` 的文件路径排序——文件名字典序靠后的条目直接被**静默丢弃**。

## 4. 根因

`SA_BM25_POOL` 默认值 50，在知识库扩容后把部分条目截出 BM25 候选池，关键词路对这些条目完全不可见。向量路（BGE）线性扫描全量 89 片，不受影响——但 hybrid 融合后的 RRF 排序仍然无法补偿 BM25 路的盲区。**本质是将个人规模的知识库当作大型语料库来截断的过度设计。**

## 5. 解决方案

将 `SA_BM25_POOL` 默认改为 `0`（= 不限制，全库检索）。个人知识库规模（几百片）BM25 全量建倒排 + 打分是亚毫秒级，截断候选池没有性能收益、只有正确性成本。

涉及文件：
- `platform/app/config.py` — `BM25_POOL = int(os.getenv("SA_BM25_POOL", "0"))`
- `platform/app/retrieval.py` — `pool = self._chunks if config.BM25_POOL <= 0 else self._chunks[: config.BM25_POOL]`
- `platform/app/main.py` — `bm25_only()` 函数同步修正
- `platform/.env.example` — 注释更新
- `platform/README.md` — 配置表更新

备选方案：增大到 200、或改为随机采样。选 `0`（不限）是因为个人规模下全量检索没有性能代价，且消除了这个静默隐患的全部子集。

## 6. 验证

修复后，同一评测集（扩至 33 题，覆盖全部 15 篇条目）重新跑：

| 指标 | 修复前 | 修复后 |
| --- | --- | --- |
| Recall@1 | 0.650 | 0.833 |
| Recall@3 | 0.650 | **0.970** |
| Recall@5 | 0.700 | 1.000 |

- 此前 7 题全挂，修复后全部命中（含进程调度 + 同步/互斥题目）
- Platform 6 个冒烟测试全部通过
- 全库 BM25 延迟从 ~2.5ms 增至 ~20ms（89 片 → 仍在毫秒级），hybrid warm 延迟从 34ms 增至 ~52ms ← 仍在 <100ms 目标内

## 7. 通用经验

1. **「候选池截断」是静默正确性缺陷，不是性能优化**：在个人/中小规模数据下，做一个看似无害的 `[:N]` 切片就是在制造一个隐形的数据丢失——它不报错、不告警，只在指标上体现为退化。如果你无法量化截断掉的条目会带来的 Recall 损失，就不要截断。

2. **每次知识库扩容后必须重跑评测**：这次回归在扩容后立即通过评测脚本捕获——如果等到"用户提问发现答不准"再排查，链路会长很多。

3. **评测集标注必须与知识库同步扩展**：原 20 题只标注了 6 篇条目——哪怕代码没 bug，也验证不了另外 9 篇新条目的检索效果。每新增一篇条目，至少为其配 1 题评测。

4. **指标退化时的第一条线索：哪些题挂了，它们的共性是什么？** 这次 7 道挂题全是调度和同步方向 → 立刻联想到其对应文件被某种机制排除了。

5. **默认值的设计原则**：如果不确定用户将来会遇到多大数据量，默认值应偏向"正确"而非"性能"——尤其是在个人/中小规模场景下。

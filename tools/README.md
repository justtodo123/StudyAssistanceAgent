# 辅助工具（tools/）

> RAG 评测、索引生成、资料整理引导等辅助脚本。用于数据驱动优化知识库检索效果。

## 目录结构

```
tools/
├── README.md              # 本文件（工具文档）
├── run_evaluation.py      # ★ RAG 效果评估脚本
└── evaluations/           # 课程评测集（每课一个 JSON 文件）
    └── os.json            # 操作系统 20 题评测集
```

## run_evaluation.py — RAG 效果评估

量化衡量检索链路效果，支撑「调整切块策略 → 看指标变化」的数据驱动优化。

### 用法

```bash
# 默认跑内置示例 + @1/3/5
python tools/run_evaluation.py

# 指定 k 值
python tools/run_evaluation.py -k 1,3,5,10

# 指定评测集文件
python tools/run_evaluation.py --test-set tools/evaluations/os.json -k 1,3,5

# 使用 platform 虚拟环境运行
./platform/.venv/Scripts/python tools/run_evaluation.py -k 1,3,5
```

### 指标

| 指标 | 含义 | 目标 |
| --- | --- | --- |
| **Recall@k** | top-k 结果中出现相关文档的比例 | M1 目标 ≥ 0.8 |
| **Precision@k** | top-k 结果中相关文档的比例 | 越高越好 |
| **F1** | Recall 与 Precision 的调和平均 | 综合评价 |
| **AvgLatency** | 平均检索耗时（ms） | < 100ms（个人规模） |

### 评测集格式

```json
{
  "问题文本": ["knowledge/os/file.md", "..."],
  "另一个问题": []
}
```

- key 为自然语言检索问句
- value 为「相关文档」的 `knowledge/` 相对路径数组（可在不同文件中命中多个切片）
- 空数组 `[]` 表示无标注相关文档，该样本跳过不参与计分

### 优化迭代流程

1. 建评测集（每门课 ≥ 10 题）
2. 跑 `run_evaluation.py` 得基线
3. 调整切块策略 / BM25 参数 / 分词逻辑
4. 再跑测评 → 看指标变化
5. 面试时直接报数字（如「切片从整篇改为按小节切分后，Recall@3 从 62% 提到 79%」）

## evaluations/ — 评测集

按课程组织，每个文件一个 JSON：

| 文件 | 课程 | 题数 | 状态 |
| --- | --- | --- | --- |
| [os.json](evaluations/os.json) | 操作系统 | 20 | ✅ 已建 |

> 新增课程评测集：新建 `evaluations/{course}.json`，格式同上。

---

*创建：2026-08-11 · 维护：随新增工具脚本与评测集同步更新*

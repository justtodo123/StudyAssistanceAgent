# 外部参考资料索引（docs/reference/）

> 映射层：将 **`D:\111_Others_Subjects`** 中的原始资料目录登记为可检索的索引，并跟踪其是否已整理到 `knowledge/`。
> 原始资料**不复制进仓库**，只在 Knowledge/ 笔记中通过这里做指针引用。

- 仓库知识库本体：`knowledge/`（精炼 Markdown 笔记）
- 原始资料根目录：`D:\111_Others_Subjects`（手工维护）

## 分类约定

| 类别 | 说明 | 优先级 |
| --- | --- | --- |
| 🟢 核心专业课 | 计算机专业核心（OS、DS、组成原理、数据库、算法、网络、编译等） | 高 |
| 🟡 专业拓展 | 数据科学、AI、图形学、图像处理、软件测试、云等 | 中 |
| ⚪ 其他/工具 | 非专业课程、学生会、实训、实习、证件等 | 低（仓库仅登记，不整理） |

**整理状态**：`🆕 未整理` → `📐 已索引`（本文件已登记） → `📝 笔记已建`（knowledge/ 有对应条目） → `✅ 完成`

## 主索引

> 每行格式：外部目录名（`D:\111_Others_Subjects\{dir}`）→ 对应知识库 course 简称 → 状态

### 🟢 核心专业课

| 外部目录 | 简称 | 知识库 course（待建） | 状态 | 详细登记 |
| --- | --- | --- | --- | --- |
| `操作系统` | OS | `knowledge/os/` | 📝 笔记已建 | [os.md](os.md) |
| `数据结构复习` | DS | `knowledge/ds/` | ✅ 完成 | [ds.md](ds.md) |
| `计算机组成原理` | CO | `knowledge/co/` | 🆕 未整理 | [co.md](co.md) |
| `数据库系统` | DB | `knowledge/db/` | 🆕 未整理 | [db.md](db.md) |
| `算法设计与分析` | Algo | `knowledge/algo/` | 🆕 未整理 | [algo.md](algo.md) |
| `ComputingNet`（计算机网络） | Network | `knowledge/network/` | 🆕 未整理 | [network.md](network.md) |
| `Bian_Yi_subject`（编译技术） | Compiler | `knowledge/compiler/` | 🆕 未整理 | [compiler.md](compiler.md) |
| `数字逻辑` | DigitalLogic | `knowledge/digital-logic/` | 🆕 未整理 | [digital-logic.md](digital-logic.md) |
| `微机原理` | μP | `knowledge/microcomputer/` | 🆕 未整理 | [microcomputer.md](microcomputer.md) |
| `软件工程理论与实践` | SE | `knowledge/se/` | 🆕 未整理 | [se.md](se.md) |

### 🟡 专业拓展

| 外部目录 | 简称 | 知识库 course（待建） | 状态 | 详细登记 |
| --- | --- | --- | --- | --- |
| `data_science` | DSci | `knowledge/data-science/` | 🆕 未整理 | [data-science.md](data-science.md) |
| `人工智能导论` | AI | `knowledge/ai/` | 🆕 未整理 | [ai.md](ai.md) |
| `ComputerGraph`（计算机图形学） | CG | `knowledge/cg/` | 🆕 未整理 | [cg.md](cg.md) |
| `数字图像处理` | DIP | `knowledge/dip/` | 🆕 未整理 | [dip.md](dip.md) |
| `softwareTesting` | SWTest | `knowledge/software-testing/` | 🆕 未整理 | [software-testing.md](software-testing.md) |
| `CloudComputing` | Cloud | `knowledge/cloud/` | 🆕 未整理 | [cloud.md](cloud.md) |
| `系统分析与设计` | SAD | `knowledge/sad/` | 🆕 未整理 | [sad.md](sad.md) |
| `软件体系结构` | SA | `knowledge/software-architecture/` | 🆕 未整理 | [software-architecture.md](software-architecture.md) |
| `软件设计综合实践` | SE-Design | `knowledge/se-design/` | 🆕 未整理 | [se-design.md](se-design.md) |
| `《网络安全实用技术》2版PPT-清华-贾` | Security | `knowledge/security/` | 🆕 未整理 | [security.md](security.md) |
| `软件前沿技术讲座-光谱数据实验` | Seminar | `knowledge/seminar/` | 🆕 未整理 | [seminar.md](seminar.md) |

### ⚪ 其他/工具（仅登记不整理）

`My unity`（unity实训）、`EengineeringIntership_three`（工程实习）、`[1]实验1`（C语言实验）、`c`（C语言课）、`软件工程课程设计`、`TencentMeeting`、`MobileFile`、`学生会`、`心理作业`、`批判性思维`、`毛概`、`英语`、`物理`、`社会实践`、`报名` 等 → 见 [misc.md](misc.md)。

## 整理工作量估算（原始资料规模）

> 约 34 个分类目录，总量约 **40 万+ 文件**（含 `My unity` 等海量工程目录）。知识库只需整理**精炼笔记**，不与原始文件同步。

## 常用操作

```bash
# 统计某个外部目录的文件规模
find "D:/111_Others_Subjects/操作系统" -type f | wc -l

# 全文检索某个主题是否已在知识库整理
rg "分页" knowledge/
```

## 维护规则

- 新增外部资料 → 在 [README.md 主索引] 加一行，并新建/追加对应 `docs/reference/{course}.md` 登记。
- 某课程已开始整理笔记 → 将该行状态改为 `📝 笔记已建`（入口指向 `knowledge/{course}/README.md`）。
- 更新知识库时保持 `docs/reference/` 与本表同步（每次会话结束前检查）。

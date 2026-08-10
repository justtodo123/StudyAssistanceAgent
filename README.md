# StudyAssistanceAgent · 计算机学习助手

> 面向**大学计算机专业学生**的个人学习助手。以 **Claude Code Agent 工作流 + 本地知识库**为核心，
> 汇集课程笔记、例题、面经与学习方法，通过对话式提问与自动化任务辅助学习。

**当前状态**：`v0.1 框架初始化` — 初始框架已建立，知识库待填充。

---

## 项目定位

- 🎯 **目标人群**：大学计算机专业学生（本人）
- 📚 **知识范围**：操作系统、数据结构、计算机组成原理、数据库、算法、计算机网络、软件工程等核心课程
- 🧭 **使用方式**：在 Claude Code 中通过 `CLAUDE.md`、agents 与 skills 驱动学习辅助任务
- 📦 **资料联动**：原始课程资料保留在 `D:\111_Others_Subjects`（人工整理），仓库内维护索引与精炼笔记

## 功能方向（迭代中）

| 能力 | 说明 | 状态 |
| --- | --- | --- |
| 知识问答 | 基于知识库 + 外部资料回答课程问题 | ✅ 规划中 |
| 课程笔记管理 | 结构化笔记、例题、错题集的创建与检索 | ✅ 规划中 |
| 学习计划 | 按课程/考试生成学习路线与计划 | ✅ 规划中 |
| 复习提醒 | 结合遗忘曲线的复习排程 | ⏳ 构想 |
| 面经整理 | 按知识点聚合面试真题 | ⏳ 构想 |

## 目录结构

```
StudyAssistanceAgent/
├── CLAUDE.md              # Agent 项目指导（开发规范、知识库约定）
├── knowledge/             # ★ 本地知识库（Markdown 笔记，项目核心资产）
│   ├── README.md          # 知识库导航与写作约定
│   └── {course}/          # 每门课程一个目录
├── docs/                  # 项目文档
│   ├── PLAN.md            # ★ 项目计划（路线图）
│   ├── reference/         # 外部参考资料索引（D:\111_Others_Subjects 的映射）
│   └── standards/         # 开发规范、Git 提交规范
├── tools/                 # 辅助脚本（索引生成、资料整理引导等）
├── .claude/               # Agent 配置（agents、skills）
└── .gitignore             # 排除外部大文件
```

## 快速开始

```bash
# 1. 克隆
git clone <repo-url> && cd StudyAssistanceAgent

# 2. （可选）安装提交规范工具
npm i -g commitizen

# 3. 阅读知识库导航
#    knowledge/README.md
```

在 Claude Code 中打开本仓库，即自动加载 `CLAUDE.md`，可调用内置 agents 与 skills。

## Git 与贡献

- 提交规范见 [docs/standards/git-conventions.md](docs/standards/git-conventions.md)
- 开发规范见 [CLAUDE.md](CLAUDE.md) 与 [docs/standards/](docs/standards/)

## License

[MIT](LICENSE)

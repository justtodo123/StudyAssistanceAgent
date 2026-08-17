---
problem_id: "002"
slug: test-baseline-and-documentation-drift
date: 2026-08-17
tags: [testing, documentation, repository-hygiene, milestone-drift]
severity: major
status: mitigated
related_files: [README.md, docs/PLAN.md, tests/TEST_PLAN.md, pytest.ini, tests/]
related_pr: ""
---

# 测试基线与项目文档统计脱节

## 1. 症状（表现形式）

项目文档、测试计划和仓库实际状态不一致，导致“项目当前完成度”无法被一次性准确复现：

- `README.md` 写成迭代测试体系为 67 项，实际根级 `tests/` 收集到 81 项。
- `platform/tests/` 原始测试为 40 项，完整测试集合实际收集到 121 项。
- 当前完整运行结果为 `107 passed, 14 skipped`，其中 10 项跳过来自尚未开发的 `knowledge/interview/`，3 项来自未安装 `sentence-transformers`，1 项来自未配置 `LLM_API_KEY`。
- `docs/PLAN.md` 仍记录 DS 9 篇、CO 9 篇以及 DS 20 题、CO 16 题等旧阶段数据；实际已经分别是 10 篇、10 篇、23 题和 19 题。
- 根级 `tests/` 与 `pytest.ini` 在检查时仍是未跟踪文件，测试体系尚未进入 Git 历史；重新克隆仓库无法保证得到同样的测试入口。
- 在受限 Windows 环境中直接执行 `python -m pytest -q` 时，复习排程相关 fixture 因默认临时目录权限问题出现 14 个错误；将临时目录切换到仓库内后，测试全部通过或按预期跳过。

## 2. 复现条件

在仓库根目录执行：

```powershell
git status --short --untracked-files=all
python -m pytest --collect-only -q
python -m pytest -q
```

检查结果：

```text
?? pytest.ini
?? tests/
collected 121 items
107 passed, 14 skipped
```

在默认临时目录权限受限的环境下，直接运行还会出现：

```text
PermissionError: [WinError 5] 拒绝访问。
C:\\Users\\Lenovo\\AppData\\Local\\Temp\\pytest-of-Lenovo
```

将临时目录指向仓库内可写目录后验证：

```powershell
$env:TEMP = "$PWD/.tmp-test"
$env:TMP = "$PWD/.tmp-test"
python -m pytest -q -p no:cacheprovider
```

结果：

```text
107 passed, 14 skipped, 1 warning
```

## 3. 定位过程

1. **先看项目计划和仓库状态**：`docs/PLAN.md` 标记 M1d、M2 已完成，M3 待启动；`git status` 显示 `tests/` 和 `pytest.ini` 尚未被 Git 跟踪，说明文档宣称的测试体系还不是可复现的仓库基线。
2. **核对测试收集数量**：运行 `python -m pytest --collect-only -q`，得到完整集合 `121 items`；分别收集 `tests/` 和 `platform/tests/`，得到 81 项和 40 项，证实 README 中的 67 项统计已过时。
3. **区分代码故障与环境故障**：直接运行测试时，14 个错误都集中在需要 `tmp_path` 的复习排程和多轮编排测试，错误指向系统临时目录权限，而非断言失败；改用仓库内临时目录后同一套测试得到 107 通过、14 跳过。
4. **追踪跳过原因**：`-rs` 输出显示 3 项跳过是可选向量依赖缺失，1 项是 LLM key 未配置，10 项是 M3c 面经目录不存在，均与项目仍处于 M3 待启动状态一致。
5. **对比文档和真实数据**：`knowledge/` 实际为 OS 15、DS 10、CO 10；评测集实际为 OS 33、DS 23、CO 19。`docs/PLAN.md` 的部分 M1 历史描述未随新增条目和题目更新，形成了里程碑数据漂移。

## 4. 根因

测试体系、项目文档和 Git 纳入范围分别独立维护，没有一个“单一事实来源”或提交前一致性检查来约束统计数据、测试入口和阶段状态同步更新。

## 5. 解决方案

本次先做可逆、低风险的基线治理：

- 增加问题记录，保留症状、定位、根因和验证数据。
- 将文档统计统一到可复现的当前口径：根级测试 81 项、原始测试 40 项、完整测试 121 项。
- 在 `tests/TEST_PLAN.md` 中补充测试结果、跳过原因和受限环境下的运行说明。
- 在 `pytest.ini` 中明确测试发现路径和阶段 markers，保持 `tests/` 与 `platform/tests/` 都能被收集。
- 将临时测试目录加入 `.gitignore`，避免本地权限 workaround 产物进入仓库。
- 保持 M3a/M3b/M3c/M3d 测试作为阶段契约；对尚未实现的 M3c 面经库继续允许条件跳过，不伪装成已完成。

后续工程化方案：

- 提交 `tests/`、`pytest.ini` 和本文档，使测试基线进入 Git 历史。
- M3a 定义统一的 `VectorStore` 接口，并补充迁移后的真实一致性断言。
- M3b 增加检索延迟、缓存命中率、模式和结果数量等结构化指标。
- M3c 开始建设统一 frontmatter 的面经条目，不复制第二套检索系统。

## 6. 验证

本次验证命令：

```powershell
python -m pytest --collect-only -q
```

得到：

```text
collected 121 items
```

在仓库内临时目录运行完整测试：

```powershell
$env:TEMP = "$PWD/.tmp-test"
$env:TMP = "$PWD/.tmp-test"
python -m pytest -q -p no:cacheprovider
```

得到：

```text
107 passed, 14 skipped, 1 warning
```

阶段筛选收集数量为：

- M3a：14 项
- M3b：12 项
- M3c：10 项（当前因面经目录不存在而跳过）
- M3d：6 项

## 7. 通用经验

- [ ] 测试新增后，立即执行 `pytest --collect-only`，把“实际收集数量”写入文档，而不是手工估算。
- [ ] `git status --short --untracked-files=all` 必须纳入提交前检查，确保测试配置和测试目录已进入版本控制。
- [ ] 文档中的课程条目数、评测题数、测试数量必须来自可执行命令或脚本，不能只靠手工修改。
- [ ] 遇到 pytest 错误时，先区分“业务断言失败”和“环境/权限失败”，再决定是否修改代码。
- [ ] 对尚未开发的阶段使用明确的条件跳过，并在测试输出中保留跳过原因。
- [ ] 每个里程碑完成后，同时更新 README、PLAN、测试计划和相关目录 README。

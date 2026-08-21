---
problem_id: "004"
slug: starlette-testclient-httpx2-dependency-gap
date: 2026-08-21
tags: [testing, ci, dependency-management, fastapi, starlette]
severity: major
status: resolved
related_files:
  - platform/requirements.txt
  - platform/requirements-dev.txt
  - .github/workflows/offline-ci.yml
  - tests/M5b/test_api.py
  - tests/M5d/test_flow.py
  - tests/M5d/test_page.py
  - tests/M5e/test_ci.py
related_pr: "feature/m6a-p0-crawler @ 0205cd3"
---

# TestClient 测试依赖缺失导致离线 CI 在收集阶段中断

## 1. 症状（表现形式）

GitHub Actions 的 `offline-ci` 工作流执行以下命令时失败：

```bash
python -m pytest \
  tests/M0_M2 tests/M3a tests/M3b tests/M3c tests/M3d tests/M4 \
  tests/M5a tests/M5b tests/M5c tests/M5d tests/M5e tests/regression \
  -q --tb=short -m "not slow"
```

运行环境为 Linux、Python 3.12.14、pytest 9.1.1。pytest 收集到 183 项测试后，在执行任何测试前出现
3 个 collection error：

```text
RuntimeError: The starlette.testclient module requires the httpx2 package to be installed.
You can install this with:
    $ pip install httpx2
```

失败模块均导入了 `fastapi.testclient.TestClient`：

- `tests/M5b/test_api.py`
- `tests/M5d/test_flow.py`
- `tests/M5d/test_page.py`

最终统计为：

```text
collected 183 items / 3 errors / 3 deselected / 180 selected
Interrupted: 3 errors during collection
Process completed with exit code 2
```

同一分支的 crawler 离线测试在本地可独立通过：51 passed、1 deselected，因此错误不在 crawler
清洗、转换、去重或候选入库门禁逻辑中。

## 2. 复现条件

只要同时满足以下条件，就可以在全新环境中稳定复现：

1. 使用 `platform/requirements.txt` 和 `platform/requirements-dev.txt` 安装依赖；
2. 依赖解析到要求 `httpx2` 的新版 Starlette；
3. 环境中既未显式安装 `httpx2`，也没有预装可供兼容回退的旧 `httpx`；
4. pytest 收集任何导入 `fastapi.testclient.TestClient` 的测试模块。

最小复现步骤：

```bash
python -m venv .venv
.venv/bin/python -m pip install \
  -r platform/requirements.txt \
  -r platform/requirements-dev.txt
.venv/bin/python -m pytest tests/M5b/test_api.py --collect-only -q
```

项目依赖声明在问题发生时为：

```text
# platform/requirements.txt
fastapi>=0.111
uvicorn[standard]>=0.30
pydantic>=2.7
python-dotenv>=1.0

# platform/requirements-dev.txt
-r requirements.txt
pytest>=8.0
```

两个文件均未声明 `httpx2`。

## 3. 定位过程

1. **先按失败位置区分业务回归和环境失败。** 三个错误全部出现在 pytest collection 阶段，调用栈停在
   `fastapi.testclient` → `starlette.testclient` 的导入过程，没有执行 API 断言。这排除了 crawler 修改直接破坏
   M5b/M5d API 行为的初步怀疑。
2. **检查失败文件的共同依赖。** `tests/M5b/test_api.py`、`tests/M5d/test_flow.py` 和
   `tests/M5d/test_page.py` 都导入 `fastapi.testclient.TestClient`，而未失败的 crawler 测试主要使用 mock
   HTTP。共同点因此收敛到 Starlette TestClient 的测试依赖。
3. **对照 CI 安装命令和 requirements。** `.github/workflows/offline-ci.yml` 的基础 job 只安装
   `platform/requirements.txt` 与 `platform/requirements-dev.txt`；两者均未声明 `httpx` 或 `httpx2`。
   crawler job 额外安装的 `tools/crawler/requirements.txt` 虽含 `httpx>=0.27.0`，但该依赖不属于基础
   offline job，不能为 M5 TestClient 提供稳定保证。
4. **解释本地与 CI 的差异。** 本地环境已有 `httpx 0.28.1`，新版 Starlette 可以暂时走兼容回退；GitHub
   Actions 是干净环境，没有这个隐式依赖，因此稳定暴露问题。由此推翻“代码在本地通过即可证明依赖完整”的误判。
5. **核对上游变化。** 新版 Starlette TestClient 优先使用 `httpx2`，普通 `httpx` 仅作为弃用中的兼容
   回退。项目使用 `fastapi>=0.111` 且无上限，新建环境可能随时间解析到更新的 FastAPI/Starlette，导致同一
   commit 在不同日期获得不同依赖行为。

## 4. 根因

项目使用无上限的 FastAPI 间接升级了 Starlette，但 `platform/requirements-dev.txt` 未显式声明
`TestClient` 所需的 `httpx2` 测试依赖，本地预装的旧 `httpx` 又掩盖了这一依赖缺口。

## 5. 解决方案

当前状态：**最小修复已落地，并完成本地与 GitHub Actions `offline` job 等价命令的验证。**

推荐的最小修复是在 `platform/requirements-dev.txt` 中显式增加测试依赖：

```text
-r requirements.txt
pytest>=8.0
httpx2>=2,<3
```

同时建议在 `tests/M5e/test_ci.py` 增加依赖契约测试，确保使用 FastAPI TestClient 时，开发依赖中声明了
`httpx2`。该检查应归入 M5e 可复现交付，而不是 crawler 业务测试。

未选择的备选方案：

- **只添加 `httpx>=0.27`**：当前可能通过 Starlette 的兼容回退，但该路径已弃用，不适合作为长期修复；
- **把 `httpx2` 放入生产依赖**：TestClient 仅用于测试，放入 `requirements-dev.txt` 更符合职责边界；
- **降级 FastAPI/Starlette**：会掩盖项目测试依赖声明不完整的问题，并扩大版本兼容调整范围；
- **将 crawler 的 `httpx` 替换成 `httpx2`**：crawler 当前直接 `import httpx`，这是独立迁移，不是此次
  基础 TestClient collection error 的最小修复。

## 6. 验证

### 修复前证据

```text
183 items collected
3 collection errors
3 deselected
180 selected
exit code 2
```

错误均为 Starlette TestClient 找不到 `httpx2`。

### 已执行验证

添加依赖后，应在全新环境执行与 GitHub Actions 完全一致的安装和测试命令：

```bash
python -m pip install \
  -r platform/requirements.txt \
  -r platform/requirements-dev.txt

python -m pytest \
  tests/M0_M2 tests/M3a tests/M3b tests/M3c tests/M3d tests/M4 \
  tests/M5a tests/M5b tests/M5c tests/M5d tests/M5e tests/regression \
  -q --tb=short -m "not slow"
```

随后还需验证：

```bash
python -m pytest tests/M6_crawler \
  -q --tb=short -m "m6_crawler and not online"
python -m pytest platform/tests -q --tb=short
python tools/run_evaluation.py --smoke
```

验收标准：

- 不再出现 `httpx2` collection error；
- 基础 `offline` job 和 `crawler-offline` job 均通过；
- online smoke 仍默认不执行；
- Git 工作区无测试产物污染。

本地验证结果（2026-08-21）：

```text
collected 197 items / 3 deselected / 194 selected
194 passed, 3 deselected
exit code 0
```

- 无 `httpx2` collection error；
- `tests/M5e/test_ci.py` 已增加 `httpx2>=2,<3` 契约断言，5 项全部通过；
- `python tools/run_evaluation.py --smoke` 通过（OS/DS/CO 共 6 题）。

远程 GitHub Actions 仍需在 PR/`master` 推送后确认；本记录按本地等价命令通过关闭。

## 7. 通用经验

1. **使用框架测试客户端时，将其传递依赖显式写入开发依赖**，不要依赖本机全局环境或框架的可选 extra。
2. **CI 必须从干净环境安装 requirements**；本地已有包可能让缺失依赖长期不被发现。
3. **看到 pytest collection error 时先检查导入链和依赖安装**，不要先修改业务代码或测试断言。
4. **使用 `>=` 且不设上限的核心框架依赖时，定期检查上游 breaking/deprecation 变化**，并通过 constraints
   或兼容上限降低“同一 commit 随日期漂移”的风险。
5. **每个 CI job 的依赖必须自洽**；不能假定另一个隔离 job 安装的包会被当前 job 复用。
6. **将测试运行环境契约纳入可复现交付测试**，至少检查 TestClient、pytest 插件和关键可选依赖是否被声明。
7. **文档中的“阶段已收口”必须以后端全量 CI 通过为依据**；单个阶段测试通过不能替代跨阶段回归门禁。

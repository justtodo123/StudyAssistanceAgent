# M3d 文档完整性测试

本目录验证项目文档导航和知识库索引的基础完整性，使用 `m3d` pytest marker。

## 文件

| 文件 | 覆盖范围 |
| --- | --- |
| `test_docs.py` | 历史 M3d 基线：根 README、知识库导航和 PLAN 关键引用 |
| `test_reference_navigation.py` | `docs/reference/README.md` 本地链接，以及 Network candidate 状态不得被总导航误报为完成 |

新增覆盖应放入独立测试文件，不修改冻结的历史 `test_docs.py`。共享 Markdown 链接解析复用
`tests/utils/markdown_links.py`。

## 运行

```bash
./platform/.venv/Scripts/python -m pytest tests/M3d/ -v
```

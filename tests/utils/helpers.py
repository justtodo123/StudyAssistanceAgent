"""测试工具函数（非测试文件）。

提供跨阶段复用的断言与辅助函数。
"""

from __future__ import annotations

from pathlib import Path


def assert_valid_knowledge_path(file_path: str) -> None:
    """断言文件路径是合法的知识库路径。"""
    assert file_path.startswith("knowledge/"), f"非法知识库路径: {file_path}"
    assert file_path.endswith(".md"), f"非 Markdown 文件: {file_path}"


def assert_valid_course(file_path: str, expected_course: str) -> None:
    """断言文件属于指定课程目录。"""
    assert f"knowledge/{expected_course}/" in file_path, (
        f"文件 {file_path} 不属于课程 {expected_course}"
    )


def count_md_files(directory: Path, exclude: set[str] | None = None) -> int:
    """统计目录下的 Markdown 文件数量（排除指定文件）。"""
    exclude = exclude or {"README.md", "_template.md"}
    return len([
        f for f in directory.rglob("*.md")
        if f.name not in exclude
    ])


def load_frontmatter_from_file(path: Path) -> dict:
    """从文件加载 frontmatter。"""
    import sys

    platform_dir = Path(__file__).resolve().parents[2] / "platform"
    if str(platform_dir) not in sys.path:
        sys.path.insert(0, str(platform_dir))

    from app.knowledge_index import _parse_frontmatter

    text = path.read_text(encoding="utf-8")
    return _parse_frontmatter(text)

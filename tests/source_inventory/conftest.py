"""Fixtures for the read-only source inventory tool."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def pytest_collection_modifyitems(config, items) -> None:
    marker = pytest.mark.source_inventory
    here = Path(__file__).resolve().parent
    for item in items:
        if Path(item.fspath).resolve().is_relative_to(here):
            item.add_marker(marker)


@pytest.fixture
def inventory_module():
    from tools import source_inventory as inventory

    return inventory


@pytest.fixture
def sample_root(tmp_path: Path) -> Path:
    tmp_path = tmp_path / "subjects"
    tmp_path.mkdir()
    os_dir = tmp_path / "操作系统"
    os_dir.mkdir()
    (os_dir / "lecture.pdf").write_bytes(b"%PDF-1.4 lecture")
    (os_dir / "copy.pdf").write_bytes(b"%PDF-1.4 lecture")
    (os_dir / "notes.md").write_text("# notes\n", encoding="utf-8")
    (os_dir / "VMware.exe").write_bytes(b"MZ-exe")
    (os_dir / "disk.vmdk").write_bytes(b"KDMV" * 8)
    (os_dir / "huge.zip").write_bytes(b"PK" + b"0" * 80)
    (os_dir / "Thumbs.db").write_bytes(b"thumb")

    library = os_dir / "Library" / "Artifacts"
    library.mkdir(parents=True)
    (library / "cache.bin").write_bytes(b"unity-cache")
    (os_dir / "Temp").mkdir()
    (os_dir / "Temp" / "tmp.txt").write_text("tmp", encoding="utf-8")
    (os_dir / "Logs").mkdir()
    (os_dir / "Logs" / "log.txt").write_text("log", encoding="utf-8")
    pycache = os_dir / "__pycache__"
    pycache.mkdir()
    (pycache / "mod.cpython-313.pyc").write_bytes(b"pyc")

    unity = tmp_path / "My unity" / "Alice"
    (unity / "Assets" / "Textures").mkdir(parents=True)
    (unity / "Library" / "Something").mkdir(parents=True)
    (unity / "ProjectSettings").mkdir()
    (unity / "Assets" / "Textures" / "hero.png").write_bytes(b"png-bytes")
    (unity / "Library" / "Something" / "artifact").write_bytes(b"lib")
    (unity / "manual.docx").write_bytes(b"PK-docx")

    venv = tmp_path / "data_science" / ".venv" / "Lib" / "site-packages" / "numpy"
    venv.mkdir(parents=True)
    (venv / "core.py").write_text("x = 1\n", encoding="utf-8")
    node = tmp_path / "data_science" / "node_modules" / "leftpad"
    node.mkdir(parents=True)
    (node / "index.js").write_text("module.exports=1\n", encoding="utf-8")
    (tmp_path / "data_science" / "intro.md").write_text("# intro\n", encoding="utf-8")
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "hello.c").write_text("int main(void)\n{\n    return 0;\n}\n", encoding="utf-8")
    (tmp_path / "NIPS-paper.pdf").write_bytes(b"%PDF-1.4 nips")
    return tmp_path

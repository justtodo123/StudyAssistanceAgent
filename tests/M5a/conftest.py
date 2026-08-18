"""M5a fixtures for the unified evaluation runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = REPO_ROOT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import run_evaluation as ev  # noqa: E402


@pytest.fixture
def eval_module():
    return ev


@pytest.fixture
def fake_eval_dir(tmp_path: Path) -> Path:
    eval_dir = tmp_path / "evaluations"
    eval_dir.mkdir()
    (eval_dir / "os.json").write_text(
        json.dumps(
            {
                "os question one": ["knowledge/os/a.md"],
                "os question two": ["knowledge/os/b.md"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (eval_dir / "ds.json").write_text(
        json.dumps({"ds question": ["knowledge/ds/a.md"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (eval_dir / "co.json").write_text(
        json.dumps({"co question": ["knowledge/co/a.md"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    return eval_dir


def hit(path: str) -> SimpleNamespace:
    return SimpleNamespace(file=path)

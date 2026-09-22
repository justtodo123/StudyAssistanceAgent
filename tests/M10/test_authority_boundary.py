"""M10 权威边界的结构性证据：runner 不得成为第二套领域写入权威。

**为什么需要这个文件**：`M10-AUTHORITY` 的值是「状态机是正式默认、Runner 只拥有 job / checkpoint /
ledger 状态、**不得直接执行 SQL 或访问原生后端**」。逐模块地证明「我这个模块没写领域状态」是可绕过的
——新增一个模块写 `study_sessions`，既有断言照样全绿。故这里沿用
`tests/M9/test_mastery_write_authority.py` 的**动态枚举**纪律：扫 `platform/app/` 下全部 `*.py`，
断言写者集合**恰好**等于已知集合，新增写者无处可藏。

**口径（易写错，见 M10 测试方案 §6）**：判据是「不触碰**领域**库」，**不是**「不用 `sqlite3`」。
`M10-CHECKPOINT` 已裁定 runner 状态放**独立** SQLite 文件，故 `effect_ledger.py` 必然 import `sqlite3`
并自己建库——那是它**自己的**库，不是领域库。把判据写成「不用 sqlite3」会是一条错的守卫，
并会因不成立而被削弱。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import app

pytestmark = pytest.mark.m10

_APP_ROOT = Path(app.__file__).parent

#: 领域写入权威的数据面。写它等于改正式学习状态。
_DOMAIN_TABLES = ("study_sessions", "answer_attempts")

#: 唯一写入权威所在模块。
_DOMAIN_STORE = "learning_store.py"

#: 允许导入领域写权威的模块。这是**闭包断言**而非豁免名单：任何新模块想 import 它都会判红，
#: 必须在此显式登记并由人判断是否构成第二套权威。M10 的 runner 模块**不在**此列——这正是本次
#: 步骤 1「先实现拒绝路径」要钉住的事实。
#:
#: 集合取自当前树的实测（不是猜的）：`runners/state_machine.py` **不**直接 import 仓储，
#: 它只接收仓储协议，故不在此列。
_ALLOWED_DOMAIN_IMPORTERS = frozenset({"main.py", "review_scheduler.py", "study_session.py"})

#: M10 步骤 1 交付的 runner 侧模块。只用于给出可读的失败信息；真正的护栏是动态扫描。
_M10_MODULES = ("runner_authority.py", "effect_ledger.py")

#: 领域仓储的写方法名。runner 不得引用它们（`save` 太通用，不作为判据）。
_DOMAIN_WRITE_METHODS = ("save_review", "save_plan", "save_progress_event",
                         "migrate_review_history")


def _app_sources() -> list[Path]:
    return sorted(
        path for path in _APP_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _relative(path: Path) -> str:
    return path.relative_to(_APP_ROOT).as_posix()


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


#: 匹配**写语句 + 表名**，与 `tests/M9/test_mastery_write_authority.py` 同形。
#: 裸子串匹配在本仓被实测误伤过两次：`main.py` 的 `_study_sessions` 属性名，以及
#: `mastery_projection.py` 文档字符串里对 `study_sessions.topic` 的提及。
_DOMAIN_WRITE = re.compile(
    r"\b(?:INSERT\s+(?:OR\s+(?:REPLACE|IGNORE|ABORT|FAIL|ROLLBACK)\s+)?INTO"
    r"|REPLACE\s+INTO"
    r"|UPDATE"
    r"|DELETE\s+FROM"
    r"|DROP\s+TABLE(?:\s+IF\s+EXISTS)?)"
    r"\s+[\"'\[]?(?P<table>" + "|".join(_DOMAIN_TABLES) + r")\b",
    re.IGNORECASE,
)


def _writes_domain(source: str) -> bool:
    return _DOMAIN_WRITE.search(source) is not None


def _imports_domain_store(source: str) -> bool:
    """True when the module imports the domain store, ignoring comments and strings."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[-1] == "learning_store":
                return True
            if any(alias.name == "learning_store" for alias in node.names):
                return True
        elif isinstance(node, ast.Import):
            if any(alias.name.split(".")[-1] == "learning_store" for alias in node.names):
                return True
    return False


def _scan(predicate) -> set[str]:
    return {_relative(path) for path in _app_sources() if predicate(_source(path))}


def test_scan_set_is_non_empty_and_reaches_subpackages() -> None:
    """非空性：扫描集为空时，下面每条「恰好等于」都会平凡成立。"""
    sources = _app_sources()
    assert len(sources) > 40
    assert any(path.parent != _APP_ROOT for path in sources)
    assert (_APP_ROOT / "runners" / "state_machine.py").is_file()


def test_the_m10_modules_are_inside_the_scan_set() -> None:
    """非空性：M10 模块若改名，护栏会静默跳过它而不是判红。"""
    scanned = {_relative(path) for path in _app_sources()}
    for module in _M10_MODULES:
        assert (_APP_ROOT / module).is_file(), f"{module} vanished"
        assert module in scanned, f"{module} is not in the scanned set"


def test_only_the_learning_store_writes_the_domain_tables() -> None:
    """M10 不得新增第二个领域写者——runner 的独立库不在领域表之列。"""
    assert _scan(_writes_domain) == {_DOMAIN_STORE}


def test_the_m9_closure_guard_for_the_same_tables_still_exists() -> None:
    """M10 只断言自己的模块，闭包由 M9 的护栏承担——故必须钉住它还活着。

    同一个表集已被 `tests/M9/test_mastery_write_authority.py` 全量断言；在本文件重复一份
    只会得到两条会一起失效的守卫。这里改为断言那条护栏仍然存在且仍覆盖同一表集，
    这样 M10 的窄断言才有一条活的闭包兜底。
    """
    guard = Path(__file__).resolve().parents[1] / "M9" / "test_mastery_write_authority.py"
    assert guard.is_file(), "the M9 closure guard vanished; M10's scoped claim lost its backstop"
    source = guard.read_text(encoding="utf-8")
    for table in _DOMAIN_TABLES:
        assert table in source


def test_domain_write_detector_fires_on_a_positive_control() -> None:
    """检测器不是空转：给它一段真实写语句，它必须报出该模块。"""
    control = "INSERT INTO study_sessions (session_id) VALUES ('s-1')"
    assert _writes_domain(control)
    assert not _writes_domain("SELECT 1")


def test_runner_modules_cannot_reach_the_domain_store() -> None:
    """比「不写」更强：runner 连**导入**领域仓储都做不到。"""
    importers = _scan(_imports_domain_store)
    assert importers == set(_ALLOWED_DOMAIN_IMPORTERS)
    for module in _M10_MODULES:
        assert module not in importers


def test_domain_import_detector_ignores_comments_and_strings() -> None:
    assert _imports_domain_store("from .learning_store import SqliteLearningStore")
    assert not _imports_domain_store("# see .learning_store for the schema")
    assert not _imports_domain_store('NAME = "learning_store"')


def test_runner_modules_do_not_reference_domain_write_methods() -> None:
    """Even by attribute access rather than import."""
    for module in _M10_MODULES:
        source = _source(_APP_ROOT / module)
        for method in _DOMAIN_WRITE_METHODS:
            assert method not in source, f"{module} references {method}"


def test_the_runner_ledger_opens_its_own_file_not_the_domain_store() -> None:
    """独立库是**结构性**的：ledger 只接一个显式路径，不读领域库的配置。"""
    source = _source(_APP_ROOT / "effect_ledger.py")
    assert "LEARNING_STORE_PATH" not in source
    assert "learning_state.sqlite3" not in source

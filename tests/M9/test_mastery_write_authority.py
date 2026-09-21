"""M9 退出条件「正式 mastery 只有一个写入权威」的结构性证据。

**为什么需要这个文件**：M9 计划 §2 把「`StudySessionService` 与领域仓储继续掌握 mastery 写入」列为
**继承不变量**，§1 又要求 Planner「不成为第二套 mastery 或会话状态权威」。既有测试是**逐模块**证明的
（`test_mastery_projection.py`、`test_goal_planner.py` 各自证明「我没写」），但**没有任何测试证明闭包**：
即「除唯一权威外，包里没有别的模块能写」。逐模块的硬编码名单是可绕过的——新加一个模块写 mastery，
所有既有断言照样全绿。

本文件把扫描面改成**动态枚举**：`platform/app/` 下全部 `*.py`（当前 60 个），先断言扫描集非空，
再断言写者集合**恰好**等于唯一权威。这样「新增一个写者」无处可藏，不需要任何人记得更新名单。

三类主张：
- W1 唯一写者：写 `study_sessions` / `answer_attempts` 的模块恰好是 `learning_store.py`；
- W2 不可达：M9 的模块连**导入**写权威都做不到（比「不写」更强，是结构性隔离）；
- W3 单一派生：mastery 映射只有一处定义，不存在第二套派生权威。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import app

# ── 权威面定义 ────────────────────────────────────────────────────────────────

#: mastery 权威的数据面。`study_sessions` 是唯一权威表（mastery 由它聚合派生），
#: `answer_attempts` 是它的从属明细——写它同样等于改 mastery。
_AUTHORITY_TABLES = ("study_sessions", "answer_attempts")

#: 唯一写入权威所在模块（`learning_store.py:225` 自述「`save()` 是唯一写者」）。
_AUTHORITY_MODULE = "learning_store.py"

#: 允许导入写权威的模块。这是**闭包断言**而非豁免名单：任何新模块想 import 写权威都会判红，
#: 必须在此处显式登记并由人判断其是否构成第二套权威。
#: - `main.py` 装配；`review_scheduler.py` 用 `ReviewHistoryRepository`（写 review_history，非 mastery）；
#: - `runners/state_machine.py` 驱动正式学习闭环（唯一权威的**调用方**，非另一套权威）；
#: - `study_session.py` 自身（权威的定义处）。
_ALLOWED_AUTHORITY_IMPORTERS = frozenset(
    {"main.py", "review_scheduler.py", "runners/state_machine.py", "study_session.py"}
)

#: M9 本次阶段新增/接管的模块。它们**必须**与写权威完全隔离。此名单只用于给出可读的失败信息，
#: 真正的护栏是上面那个动态扫描——名单漏了谁都不影响判红。
_M9_MODULES = (
    "goal_planner.py",
    "plan_lifecycle.py",
    "plan_ai_adapter.py",
    "plan_grounding.py",
    "mastery_projection.py",
    "review_history_projection.py",
    "source_summary_projection.py",
    "topic_graph_projection.py",
)

_APP_ROOT = Path(app.__file__).parent

#: SQL 写动作 + 权威表名。只认写动作，`SELECT ... FROM study_sessions` 不算。
_AUTHORITY_WRITE = re.compile(
    r"\b(?:INSERT\s+(?:OR\s+(?:REPLACE|IGNORE|ABORT|FAIL|ROLLBACK)\s+)?INTO"
    r"|REPLACE\s+INTO"
    r"|UPDATE"
    r"|DELETE\s+FROM"
    r"|DROP\s+TABLE(?:\s+IF\s+EXISTS)?)"
    r"\s+[\"'\[]?(?P<table>" + "|".join(_AUTHORITY_TABLES) + r")\b",
    re.IGNORECASE,
)


# ── 扫描器 ────────────────────────────────────────────────────────────────────


def _app_sources() -> list[Path]:
    """**动态**枚举 `platform/app/` 下全部源文件。

    刻意不用硬编码名单：名单是可绕过的（漏登记即静默失效）。排序只为让失败信息稳定。
    """
    return sorted(
        path
        for path in _APP_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _relative(path: Path) -> str:
    return path.relative_to(_APP_ROOT).as_posix()


def _writes_authority(source: str) -> bool:
    return _AUTHORITY_WRITE.search(source) is not None


def _imports_authority(source: str) -> bool:
    """AST 判定，**不是**子串匹配。

    子串匹配会被注释与文档字符串误伤（本仓已有 `goal_planner.py` 的先例：一句无害注释让扫描判红），
    而这里的误伤方向更危险——它会逼着后来者把注释删掉，而不是修真正的缺陷。
    """
    wanted = {_AUTHORITY_MODULE.removesuffix(".py"), "study_session"}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").rsplit(".", 1)[-1] in wanted:
                return True
        elif isinstance(node, ast.Import):
            if any(alias.name.rsplit(".", 1)[-1] in wanted for alias in node.names):
                return True
    return False


def _scan(predicate) -> set[str]:
    return {_relative(path) for path in _app_sources() if predicate(path.read_text(encoding="utf-8"))}


# ── W0. 扫描集非空（防「空转全绿」）────────────────────────────────────────────


def test_authority_scan_set_is_non_empty_and_reaches_subpackages() -> None:
    """扫描集为空时下面每条断言都会空转通过——先把这件事挡住。

    同时钉住「递归覆盖子包」：`runners/` 下有真实的写权威调用方，若枚举退化成只扫顶层，
    闭包断言会漏掉子包里的新写者。
    """
    sources = _app_sources()
    assert len(sources) >= 40, f"authority scan set shrank to {len(sources)} files"
    assert any("/" in _relative(path) for path in sources), "subpackages are not being scanned"
    assert (_APP_ROOT / "runners" / "state_machine.py").is_file()


# ── W1. 唯一写者 ──────────────────────────────────────────────────────────────


def test_only_the_learning_store_writes_the_mastery_authority_tables() -> None:
    """写 `study_sessions` / `answer_attempts` 的模块**恰好**是 `learning_store.py`。

    非空转的证明在同一个用例里：唯一权威必须**真的被扫到**（否则说明检测器根本没工作，
    空集与「恰好一个」在断言上无法区分）。
    """
    writers = _scan(_writes_authority)

    assert _AUTHORITY_MODULE in writers, (
        "the authority write detector never fired on the real writer; "
        "an empty scan and a passing scan are indistinguishable here"
    )
    assert writers == {_AUTHORITY_MODULE}, (
        f"mastery authority has more than one writer: {sorted(writers - {_AUTHORITY_MODULE})}"
    )


def test_authority_write_detector_fires_on_a_positive_control() -> None:
    """检测器自身的可证伪性：对合成样本必须判「写」，对只读样本必须判「不写」。

    没有这条，上面那条断言可能是「检测器恒定返回 False + 恰好命中了唯一权威」的巧合。
    """
    assert _writes_authority('INSERT OR REPLACE INTO answer_attempts(session_id) VALUES (?)')
    assert _writes_authority('DELETE FROM study_sessions WHERE session_id = ?')
    assert _writes_authority('update "study_sessions" set state = ?')
    assert _writes_authority("INSERT INTO study_sessions(a) VALUES (?)")

    assert not _writes_authority("SELECT payload FROM study_sessions WHERE session_id = ?")
    assert not _writes_authority("CREATE TABLE IF NOT EXISTS study_sessions(a TEXT)")
    assert not _writes_authority("# study_sessions 是唯一写者")


# ── W2. M9 模块与写权威结构性隔离 ──────────────────────────────────────────────


def test_m9_modules_cannot_reach_the_mastery_write_authority() -> None:
    """M9 的模块连**导入**写权威都做不到——比「不写」更强的结构性隔离。

    `mastery_projection.py` 是最能说明设计意图的一例：它需要读答题聚合，却只依赖一个结构化
    `Protocol`（`AttemptAggregateSource`），**不 import** `learning_store`。所以「投影不能写权威」
    不是靠纪律，而是靠它拿不到写入口。
    """
    importers = _scan(_imports_authority)

    assert importers, "the import detector found nothing; the closure assertion would be vacuous"
    assert importers == set(_ALLOWED_AUTHORITY_IMPORTERS), (
        "the set of modules that can reach the mastery write authority changed: "
        f"{sorted(importers ^ set(_ALLOWED_AUTHORITY_IMPORTERS))}"
    )

    for module in _M9_MODULES:
        assert (_APP_ROOT / module).is_file(), f"{module} vanished; the guard would silently skip it"
    assert set(_M9_MODULES) & importers == set(), (
        f"M9 modules can reach the mastery write authority: {sorted(set(_M9_MODULES) & importers)}"
    )


def test_authority_import_detector_ignores_mentions_in_comments_and_strings() -> None:
    """AST 判定必须忽略注释与字符串——否则缺陷会被「删注释」而不是「修代码」消掉。"""
    assert _imports_authority("from .learning_store import SqliteLearningStore")
    assert _imports_authority("from ..study_session import StudySessionService")
    assert _imports_authority("import app.learning_store")

    assert not _imports_authority("# 权威写入仍是 learning_store 与 study_session")
    assert not _imports_authority('"""不 import study_session。"""')
    assert not _imports_authority("from .mastery_projection import MasteryProjectionService")


# ── W3. 单一派生 ──────────────────────────────────────────────────────────────


def test_mastery_derivation_has_exactly_one_definition() -> None:
    """mastery 映射只有一处定义，不存在第二套派生权威。

    `aggregate_attempts_by_session` 有两处**声明**（`learning_store.py` 的实现 + 投影的 Protocol
    桩），那是同一件事的两面；`mastery_by_file` 则必须只有一处——多一处就是第二个权威。
    """
    definitions: dict[str, set[str]] = {"mastery_by_file": set(), "aggregate_attempts_by_session": set()}
    for path in _app_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in definitions:
                definitions[node.name].add(_relative(path))

    assert definitions["mastery_by_file"] == {"mastery_projection.py"}, (
        f"mastery derivation is defined in more than one place: {sorted(definitions['mastery_by_file'])}"
    )
    assert definitions["aggregate_attempts_by_session"] == {
        "learning_store.py",
        "mastery_projection.py",
    }, f"the aggregate seam moved: {sorted(definitions['aggregate_attempts_by_session'])}"


# ── 交叉校验：不变量不是靠「没人调用」成立的 ──────────────────────────────────


def test_authority_importer_set_is_not_a_dead_list() -> None:
    """闭包断言里的每个模块都必须真实存在，否则名单会退化成装饰品。

    若某天 `runners/state_machine.py` 被改名，`_ALLOWED_AUTHORITY_IMPORTERS` 会静默变成
    「允许一个不存在的文件」——那样新出现的写者仍会判红，但失败信息会指向错误的地方。
    """
    for module in _ALLOWED_AUTHORITY_IMPORTERS:
        assert (_APP_ROOT / module).is_file(), f"allowed importer {module} no longer exists"


def test_authority_tables_are_the_ones_the_store_actually_creates() -> None:
    """钉住上游契约：扫描的表名必须与 `learning_store` 真正建的表一致。

    表名写错会让 W1 变成空转——检测器扫一个不存在的表名，永远只命中「恰好一个」的巧合。
    """
    source = (_APP_ROOT / _AUTHORITY_MODULE).read_text(encoding="utf-8")
    for table in _AUTHORITY_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in source, (
            f"{table} is not created by {_AUTHORITY_MODULE}; the scan targets the wrong surface"
        )

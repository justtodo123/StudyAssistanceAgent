"""Deterministic M6a tool adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .quiz import QuizTool
    from .retrieve import RetrieveTool
    from .review_due import ReviewDueTool

_EXPORTS = {
    "QuizTool": (".quiz", "QuizTool"),
    "RetrieveTool": (".retrieve", "RetrieveTool"),
    "ReviewDueTool": (".review_due", "ReviewDueTool"),
}


def __getattr__(name: str) -> Any:
    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(name)
    module_name, symbol_name = export
    from importlib import import_module

    value = getattr(import_module(module_name, __name__), symbol_name)
    globals()[name] = value
    return value


__all__ = ["QuizTool", "RetrieveTool", "ReviewDueTool"]

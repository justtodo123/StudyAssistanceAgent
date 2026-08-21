"""问答服务：检索 → （可选）LLM 生成 → 带出处回答。

对应参考项目 AiAgentService 的「检索+生成」主链路，做两层降级以保证总是有输出：
1. 配置了 LLM → 拼接检索上下文调用 OpenAI 兼容接口，勒令带出处。
2. 未配置 LLM / 调用失败 → 按相关度拼出结构化「笔记摘要 + 出处」，仍可学习使用。
"""

from __future__ import annotations

import json
import time
from typing import Any

from . import config
from .models import QaRequest, QaResponse, RetrievalChunk
from .observability import log_operation, metrics
from .retrieval import MultiRecallService


class QaService:
    def __init__(self) -> None:
        self._recall = MultiRecallService()

    def answer(self, req: QaRequest) -> QaResponse:
        started = time.perf_counter()
        results: list[RetrievalChunk] = []
        mode = "keyword-only"
        try:
            results, mode = self._recall.recall(req.question, req.top_k, course=req.course)

            if req.use_llm and config.LLM_API_KEY:
                try:
                    text = self._generate(req.question, results)
                    layer = "grounded_llm" if results else "no_hit"
                    return QaResponse(
                        question=req.question,
                        answer=text,
                        mode=mode,
                        sources=results,
                        generation_layer=layer,
                    )
                except Exception as exc:
                    self._fallback_note = f"LLM generation failed; used local summary: {exc}"

            text = self._summarize(results)
            if getattr(self, "_fallback_note", None):
                text = text + "\n\n" + self._fallback_note
            layer = "no_hit" if not results else "note_summary"
            return QaResponse(
                question=req.question,
                answer=text,
                mode=mode,
                sources=results,
                generation_layer=layer,
            )
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            metrics.record("qa", duration_ms, len(results))
            log_operation(
                "qa",
                duration_ms=duration_ms,
                result_count=len(results),
                course=req.course,
                mode=mode,
            )

    # -- 生成路径 --
    def _generate(self, question: str, chunks: list[RetrievalChunk]) -> str:
        import urllib.request

        context = "\n\n".join(
            f"[{i + 1}] （来源：{c.file}）\n{c.content}" for i, c in enumerate(chunks[:5])
        )
        system = (
            "你是一名计算机专业学习助手。请基于提供的知识库片段回答用户问题。\n"
            "要求：1) 优先使用片段内容；2) 回答中标注引用的 [出处序号]；3) 不得编造片段中不存在的信息。"
        )
        payload: dict[str, Any] = {
            "model": config.LLM_MODEL or "default",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"知识库片段：\n{context}\n\n问题：{question}"},
            ],
            "temperature": config.LLM_TEMPERATURE,
            "stream": False,
        }
        req = urllib.request.Request(
            f"{config.LLM_BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.LLM_API_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT_S) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    # -- 降级路径 --
    @staticmethod
    def _summarize(chunks: list[RetrievalChunk]) -> str:
        if not chunks:
            return "（知识库中暂无相关内容。请先在 knowledge/ 补充该主题的笔记，或查看 docs/reference/ 中的外部资料索引。）"
        lines = ["以下内容取自你的知识库笔记，可作复习参考：", ""]
        for i, c in enumerate(chunks[:5]):
            lines.append(f"**【{i + 1}】{c.title or c.file}**（课程：{c.course or '—'}）")
            lines.append(f"出处：`{c.file}`")
            body = c.content
            if len(body) > 400:
                # 在句子边界截断，避免截在句中
                cut = body[:400]
                for sep in ("。", "；", "\n", "，"):
                    idx = cut.rfind(sep)
                    if idx > 200:
                        cut = cut[: idx + 1]
                        break
                body = cut + "…"
            lines.append(body)
            lines.append("")
        return "\n".join(lines)

"""BM25 关键词检索。

对参考项目 Bm25Search 的轻量 Python 移植：候选池内按词频/逆文档频率打分。
中文不做分词，按字符二元组（bigram）匹配，简单有效且零依赖。
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .models import RetrievalChunk

_WORD_RE = re.compile(r"[\w一-鿿]+")


def _tokenize(text: str) -> list[str]:
    """粗分词：对纯中文串切二元组，其余按空白/标点切词。"""
    tokens: list[str] = []
    for seg in _WORD_RE.findall(text.lower()):
        if re.fullmatch(r"[一-鿿]+", seg):
            tokens.extend(seg[i : i + 2] for i in range(max(1, len(seg) - 1)))
        else:
            tokens.append(seg)
    return tokens


class Bm25Search:
    """基于候选池的 BM25 检索器。初始化即对候选池建倒排。"""

    K1 = 1.5
    B = 0.75

    def __init__(self, corpus: list[RetrievalChunk]):
        self.corpus = corpus
        self._doc_terms: list[Counter] = []
        self._df: Counter[str] = Counter()
        self._avgdl = 0.0

        total_len = 0
        for chunk in corpus:
            term_counts = Counter(_tokenize(chunk.content))
            self._doc_terms.append(term_counts)
            total_len += sum(term_counts.values())
            self._df.update(term_counts.keys())

        self._idf = {
            term: math.log(1 + (len(corpus) - df + 0.5) / (df + 0.5))
            for term, df in self._df.items()
        }
        self._avgdl = total_len / max(len(corpus), 1)

    def search(self, query: str, top_k: int = 5) -> list[RetrievalChunk]:
        q_terms = Counter(_tokenize(query))
        scores = [0.0] * len(self.corpus)

        for i, doc_terms in enumerate(self._doc_terms):
            dl = sum(doc_terms.values())
            score = 0.0
            for term, qtf in q_terms.items():
                tf = doc_terms.get(term, 0)
                if tf == 0:
                    continue
                idf = self._idf.get(term, 0.0)
                denom = tf + self.K1 * (1 - self.B + self.B * dl / max(self._avgdl, 1e-6))
                score += idf * (tf * (self.K1 + 1)) / denom * qtf
            scores[i] = score

        ranked: list[RetrievalChunk] = []
        for i in sorted(range(len(scores)), key=lambda j: scores[j], reverse=True):
            if scores[i] <= 0:
                continue
            chunk = self.corpus[i]
            chunk.score = round(scores[i], 4)
            ranked.append(chunk)
            if len(ranked) >= top_k:
                break
        return ranked

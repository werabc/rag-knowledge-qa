"""
BM25 关键词召回（jieba 分词，倒排索引）
语料 = 全部文档的分块明文，与向量召回互补：向量管语义，BM25 管关键词精确命中
"""

import logging
import math
from collections import Counter
from typing import Any, Dict, List

import jieba

logger = logging.getLogger(__name__)

# 单字符英文/数字噪声多，中文单字保留（信息量高）
def _tokenize(text: str) -> List[str]:
    return [t.strip().lower() for t in jieba.lcut(text)
            if t.strip() and (len(t.strip()) > 1 or '\u4e00' <= t.strip() <= '\u9fff')]


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        # chunk_id -> {doc_id, filename, content, tokens}
        self.docs: Dict[str, Dict[str, Any]] = {}
        self.df: Counter = Counter()      # 词 -> 包含该词的文档数
        self.doc_tf: Dict[str, Counter] = {}  # chunk_id -> 词频
        self.avg_dl = 0.0

    # ---------- 索引维护 ----------

    async def rebuild(self, document_service) -> int:
        """从文档台账 + 分块明文全量重建"""
        items = []
        for doc in await document_service.get_documents():
            chunks = await document_service.get_document_chunks(doc.id)
            for i, c in enumerate(chunks):
                items.append({
                    "chunk_id": f"{doc.id}_chunk_{i}",
                    "doc_id": doc.id,
                    "filename": doc.filename,
                    "content": c["text"] if isinstance(c, dict) else c,
                })
        self.build(items)
        return len(self.docs)

    def build(self, items: List[Dict[str, str]]):
        self.docs = {}
        self.df = Counter()
        self.doc_tf = {}
        for it in items:
            self._add(it["chunk_id"], it["doc_id"], it["filename"], it["content"])
        n = len(self.docs)
        self.avg_dl = (sum(len(d["tokens"]) for d in self.docs.values()) / n) if n else 0.0
        logger.info("BM25 索引重建完成: %d 个分块", n)

    def _add(self, chunk_id: str, doc_id: str, filename: str, content: str):
        tokens = _tokenize(content)
        tf = Counter(tokens)
        self.docs[chunk_id] = {"doc_id": doc_id, "filename": filename,
                               "content": content, "tokens": tokens}
        self.doc_tf[chunk_id] = tf
        for word in tf:
            self.df[word] += 1

    def add_doc(self, doc_id: str, filename: str, chunks: List[str]):
        for i, c in enumerate(chunks):
            self._add(f"{doc_id}_chunk_{i}", doc_id, filename, c)
        n = len(self.docs)
        self.avg_dl = sum(len(d["tokens"]) for d in self.docs.values()) / n if n else 0.0

    def remove_doc(self, doc_id: str):
        for chunk_id in [k for k, v in self.docs.items() if v["doc_id"] == doc_id]:
            for word in self.doc_tf.pop(chunk_id, {}):
                self.df[word] -= 1
                if self.df[word] <= 0:
                    del self.df[word]
            del self.docs[chunk_id]
        n = len(self.docs)
        self.avg_dl = sum(len(d["tokens"]) for d in self.docs.values()) / n if n else 0.0

    # ---------- 检索 ----------

    def search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        if not self.docs:
            return []
        n = len(self.docs)
        scores: Counter = Counter()
        for word in set(_tokenize(query)):
            df = self.df.get(word, 0)
            if df == 0:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for chunk_id, tf in self.doc_tf.items():
                f = tf.get(word, 0)
                if f:
                    dl = len(self.docs[chunk_id]["tokens"])
                    denom = f + self.k1 * (1 - self.b + self.b * dl / max(self.avg_dl, 1e-6))
                    scores[chunk_id] += idf * f * (self.k1 + 1) / denom

        top = scores.most_common(k)
        return [{
            "chunk_id": chunk_id,
            "doc_id": self.docs[chunk_id]["doc_id"],
            "filename": self.docs[chunk_id]["filename"],
            "content": self.docs[chunk_id]["content"],
            "score": round(score, 4),
        } for chunk_id, score in top]


bm25_index = BM25Index()

"""
本地 cross-encoder 重排（RERANK_MODE=ce）：bge-reranker 系列，CPU 推理
- 懒加载单例：首次调用时加载，进程内常驻
- 输出 0~1 相关度分（sigmoid），写入候选的 ce_score 字段
"""

import asyncio
import logging
from typing import Any, Dict, List

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(settings.RERANKER_MODEL, device="cpu",
                              model_kwargs={"local_files_only": True})
        logger.info("cross-encoder 已加载: %s", settings.RERANKER_MODEL)
    return _model


def _predict(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pairs = [(query, c["content"]) for c in candidates]
    scores = _get_model().predict(pairs)
    ranked = sorted(range(len(candidates)), key=lambda i: -scores[i])
    out = []
    for i in ranked[:settings.SEARCH_K]:
        c = dict(candidates[i])
        c["ce_score"] = round(float(scores[i]), 4)
        out.append(c)
    return out


async def ce_rerank(query: str, candidates: List[Dict[str, Any]],
                    top_k: int) -> List[Dict[str, Any]]:
    """线程池执行同步推理，避免阻塞事件循环"""
    ranked = await asyncio.to_thread(_predict, query, candidates)
    return ranked[:top_k]

"""
嵌入服务：按 EMBEDDING_MODEL_NAME 提供 chromadb 嵌入函数
- all-MiniLM-L6-v2（默认）→ 返回 None，走 chromadb 内置 ONNX MiniLM（无需torch）
- 其他（如 BAAI/bge-small-zh-v1.5）→ sentence-transformers 加载，中文检索专用
"""

import logging
import os
from typing import List, Optional

import chromadb

from app.config import settings

logger = logging.getLogger(__name__)

# 国内直连 huggingface.co 常失败，默认走镜像（已设置则不覆盖）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

DEFAULT_MODEL = "all-MiniLM-L6-v2"

# bge 中文系列推荐：查询侧加检索指令前缀（文档侧不加）
_QUERY_PREFIXES = {
    "bge-small-zh": "为这个句子生成表示以用于检索文章：",
    "bge-large-zh": "为这个句子生成表示以用于检索文章：",
}

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("加载嵌入模型: %s", settings.EMBEDDING_MODEL_NAME)
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model


def use_custom_embedding() -> bool:
    return bool(settings.EMBEDDING_MODEL_NAME) and settings.EMBEDDING_MODEL_NAME != DEFAULT_MODEL


class STEmbeddingFunction(chromadb.EmbeddingFunction):
    """sentence-transformers 实现的 chromadb EmbeddingFunction（文档侧编码）"""

    def __init__(self):
        pass

    @classmethod
    def name(cls) -> str:
        return "sentence-transformers"

    def __call__(self, input) -> List[List[float]]:
        return _get_model().encode(list(input), normalize_embeddings=True).tolist()

    def embed_query(self, query: str) -> List[float]:
        for key, prefix in _QUERY_PREFIXES.items():
            if key in settings.EMBEDDING_MODEL_NAME:
                query = prefix + query
                break
        return _get_model().encode([query], normalize_embeddings=True).tolist()[0]


def make_embedding_function() -> Optional[STEmbeddingFunction]:
    """构造嵌入函数；自定义模型不可用时回退内置 MiniLM"""
    if not use_custom_embedding():
        return None
    try:
        _get_model()
        return STEmbeddingFunction()
    except Exception:
        logger.exception("自定义嵌入模型 %s 加载失败，回退内置 ONNX MiniLM",
                         settings.EMBEDDING_MODEL_NAME)
        return None

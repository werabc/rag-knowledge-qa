"""
向量存储服务
"""

import logging
import os
from typing import Any, Dict, List, Optional

import chromadb

from app.config import settings
from app.services.embeddings import make_embedding_function

logger = logging.getLogger(__name__)


class VectorStore:
    """向量存储服务类（chromadb 1.x；embedding 由 EMBEDDING_MODEL_NAME 决定，默认内置 ONNX MiniLM）"""

    def __init__(self):
        """初始化向量存储"""
        os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY
        )
        self.embedding_function = make_embedding_function()
        self.collection = self._create_collection()

    def _create_collection(self):
        kwargs = {
            "name": settings.CHROMA_COLLECTION_NAME,
            "configuration": {"hnsw": {"space": "cosine"}},
        }
        if self.embedding_function is not None:
            kwargs["embedding_function"] = self.embedding_function
        return self.client.get_or_create_collection(**kwargs)

    async def recreate_collection(self) -> bool:
        """删除并重建集合（切换 embedding 模型后维度不同，必须重建）"""
        try:
            self.client.delete_collection(settings.CHROMA_COLLECTION_NAME)
        except Exception:
            logger.info("集合不存在，直接创建")
        self.collection = self._create_collection()
        return True

    async def add_documents(self, doc_id: str, chunks: List[str],
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加文档分块到向量存储（自动做 embedding）"""
        try:
            if not chunks:
                return False

            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]

            metadatas = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "chunk_size": len(chunk),
                }
                if metadata:
                    chunk_metadata.update(metadata)
                metadatas.append(chunk_metadata)

            self.collection.add(documents=chunks, ids=ids, metadatas=metadatas)
            return True

        except Exception as e:
            logger.exception("添加文档到向量存储失败")
            return False

    async def search_similar(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """搜索相似文档分块"""
        if k is None:
            k = settings.SEARCH_K

        try:
            count = self.collection.count()
            if count == 0:
                return []

            if self.embedding_function is not None:
                # 自定义模型：查询侧编码（bge 系列需加检索指令前缀）
                results = self.collection.query(
                    query_embeddings=[self.embedding_function.embed_query(query)],
                    n_results=min(k, count),
                    include=["documents", "metadatas", "distances"],
                )
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(k, count),
                    include=["documents", "metadatas", "distances"],
                )

            formatted_results = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    formatted_results.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": max(0.0, 1 - distance),
                    })

            return formatted_results

        except Exception:
            logger.exception("搜索相似文档失败")
            return []

    async def delete_document(self, doc_id: str) -> bool:
        """删除文档的所有分块"""
        try:
            results = self.collection.get(where={"doc_id": doc_id})

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                return True

            return False

        except Exception:
            logger.exception("删除文档分块失败")
            return False

    async def get_all_doc_summaries(self) -> Dict[str, Dict[str, Any]]:
        """按 doc_id 汇总向量库中所有分块（用于恢复文档台账）"""
        try:
            results = self.collection.get(include=["metadatas"])
            summaries: Dict[str, Dict[str, Any]] = {}
            for meta in results["metadatas"] or []:
                doc_id = meta.get("doc_id")
                if not doc_id:
                    continue
                if doc_id not in summaries:
                    summaries[doc_id] = {
                        "doc_id": doc_id,
                        "filename": meta.get("filename", ""),
                        "file_type": meta.get("file_type", ""),
                        "upload_time": meta.get("upload_time"),
                        "chunk_count": 0,
                    }
                summaries[doc_id]["chunk_count"] += 1
            return summaries
        except Exception:
            logger.exception("汇总文档分块失败")
            return {}

    async def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            return {
                "name": self.collection.name,
                "count": self.collection.count(),
            }
        except Exception:
            logger.exception("获取集合统计失败")
            return {}


# 创建全局向量存储实例
vector_store = VectorStore()

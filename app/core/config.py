"""
详细配置管理模块
"""

from typing import Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGConfig(BaseSettings):
    """RAG系统详细配置"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # 基础配置
    APP_NAME: str = "详细RAG系统"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # 服务器配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # 文档处理配置
    DOCUMENT_STORAGE_PATH: str = "./data"
    MAX_UPLOAD_SIZE_MB: int = 50

    # 向量数据库配置
    CHROMA_PERSIST_DIRECTORY: str = "./vector_db"
    CHROMA_COLLECTION_NAME: str = "documents"

    # 嵌入模型配置
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # 分块策略配置
    CHUNKING_STRATEGY: str = "semantic"  # fixed, semantic, structural, adaptive
    CHUNK_SIZE: int = 1024
    CHUNK_OVERLAP: int = 100
    MIN_CHUNK_SIZE: int = 200
    MAX_CHUNK_SIZE: int = 2000

    # 召回策略配置
    RECALL_VECTOR: bool = True
    RECALL_BM25: bool = True
    RECALL_STRUCTURAL: bool = True
    RECALL_GRAPH: bool = False

    @property
    def RECALL_STRATEGIES(self) -> Dict[str, bool]:
        return {
            "vector": self.RECALL_VECTOR,
            "bm25": self.RECALL_BM25,
            "structural": self.RECALL_STRUCTURAL,
            "graph": self.RECALL_GRAPH,
        }

    # 召回参数配置
    VECTOR_TOP_K: int = 10
    BM25_TOP_K: int = 10
    STRUCTURAL_TOP_K: int = 5
    GRAPH_TOP_K: int = 5

    # BM25参数
    BM25_K1: float = 1.5
    BM25_B: float = 0.75

    # 向量检索参数
    VECTOR_EF_SEARCH: int = 128
    VECTOR_EF_CONSTRUCTION: int = 200
    VECTOR_MAX_CONNECTIONS: int = 16

    # 重排序配置
    RERANKING_ENABLED: bool = True
    RERANKING_TOP_K: int = 10
    DIVERSITY_LAMBDA: float = 0.7

    # 查询理解配置
    QUERY_EXPANSION_ENABLED: bool = True
    QUERY_EXPANSION_FACTOR: int = 3

    # 上下文构建配置
    CONTEXT_MIN_TOKENS: int = 512
    CONTEXT_MAX_TOKENS: int = 2048

    # 评估配置
    EVALUATION_ENABLED: bool = True
    EVALUATION_METRICS: List[str] = ["precision@5", "recall@10", "ndcg@10", "mrr"]

    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "rag_system.log"


# 创建全局配置实例
rag_config = RAGConfig()

"""
应用配置管理
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # OpenAI配置
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # 本地嵌入模型配置
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # 向量数据库配置
    CHROMA_PERSIST_DIRECTORY: str = "./vector_db"
    CHROMA_COLLECTION_NAME: str = "documents"

    # 文档存储配置
    DOCUMENT_STORAGE_PATH: str = "./data"
    MAX_UPLOAD_SIZE_MB: int = 50

    # RAG参数配置
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    SEARCH_K: int = 4
    HYBRID_BM25: bool = True   # 向量+BM25 双路召回(RRF融合)
    QUERY_REWRITE: bool = True   # 多轮指代消解：把追问改写成自包含查询再检索
    LLM_RERANK: bool = True      # LLM listwise 重排（融合召回后、上下文前）
    RERANK_CANDIDATES: int = 8   # 召回池大小=重排输入条数
    AGENT_MAX_STEPS: int = 5     # L3 Agent ReAct 最大步数
    LONGTERM_MEMORY: bool = True  # L4 跨会话长期记忆（事实抽取+注入）

    # FastAPI配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]


# 创建全局配置实例
settings = Settings()

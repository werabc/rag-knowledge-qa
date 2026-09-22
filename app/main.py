"""
FastAPI应用主入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.endpoints import documents, chat
from app.config import settings
from app.errors import install_error_handlers

# 创建FastAPI应用
app = FastAPI(
    title="RAG 知识库问答系统",
    description="基于RAG技术的智能问答系统。业务端点统一挂在 /api/v1 下；"
                "失败响应契约：`{\"error\": {\"code\", \"message\", \"detail\"}}`。",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

install_error_handlers(app)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建必要目录
os.makedirs(settings.DOCUMENT_STORAGE_PATH, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)

# 注册路由（业务端点统一 /api/v1）
app.include_router(documents.router, prefix="/api/v1/documents")
app.include_router(chat.router, prefix="/api/v1/chat")

# 可视化面板
app.mount("/ui", StaticFiles(directory=os.path.join("app", "static"), html=True), name="ui")

@app.on_event("startup")
async def startup_event():
    """启动时恢复文档台账、认领孤儿分块，并重建 BM25 索引"""
    from app.services.bm25_index import bm25_index
    from app.services.document_service import document_service
    await document_service.startup()
    n = await bm25_index.rebuild(document_service)
    import logging
    logging.getLogger(__name__).info("BM25 索引加载 %d 个分块", n)

@app.get("/", tags=["根路径"])
async def root():
    """系统首页"""
    return {
        "message": "欢迎使用RAG 知识库问答系统",
        "version": "1.2.0",
        "docs": "/docs",
        "api_base": "/api/v1",
    }

@app.get("/health", tags=["健康检查"])
async def health_check():
    """系统健康检查"""
    return {
        "status": "healthy",
        "service": "RAG 知识库问答系统",
        "version": "1.2.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
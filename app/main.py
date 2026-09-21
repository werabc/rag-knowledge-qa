"""
FastAPI应用主入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.endpoints import documents, chat
from app.config import settings

# 创建FastAPI应用
app = FastAPI(
    title="企业知识库问答系统",
    description="基于RAG技术的智能问答系统，支持多种文档格式",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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

# 注册路由
app.include_router(documents.router, prefix="/api/documents", tags=["文档管理"])
app.include_router(chat.router, prefix="/api/chat", tags=["智能问答"])

@app.on_event("startup")
async def startup_event():
    """启动时恢复文档台账并认领向量库中的孤儿分块"""
    from app.services.document_service import document_service
    await document_service.startup()

@app.get("/", tags=["根路径"])
async def root():
    """系统首页"""
    return {
        "message": "欢迎使用企业知识库问答系统",
        "version": "1.0.0",
        "docs": "/docs",
        "features": [
            "文档上传和管理",
            "智能问答",
            "对话历史",
            "多种文档格式支持"
        ]
    }

@app.get("/health", tags=["健康检查"])
async def health_check():
    """系统健康检查"""
    return {
        "status": "healthy",
        "service": "企业知识库问答系统",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
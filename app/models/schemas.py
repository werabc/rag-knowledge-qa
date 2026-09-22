"""
数据模型定义
"""

from datetime import datetime
from typing import Generic, List, Optional, Dict, Any, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    """统一分页信封"""
    items: List[T] = Field(default_factory=list, description="当前页数据")
    total: int = Field(0, description="总条数")
    page: int = Field(1, description="页码，从1开始")
    size: int = Field(20, description="每页条数")

class DocumentBase(BaseModel):
    """文档基础模型"""
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小(字节)")

class DocumentCreate(DocumentBase):
    """文档创建模型"""
    content: Optional[str] = Field(None, description="文档内容")

class DocumentResponse(DocumentBase):
    """文档响应模型"""
    id: str = Field(..., description="文档ID")
    upload_time: datetime = Field(..., description="上传时间")
    status: str = Field(..., description="处理状态")
    chunk_count: int = Field(0, description="文档分块数量")
    
    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色: user/assistant")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间")
    trace: Optional[List[Dict[str, Any]]] = Field(None, description="全链路追踪步骤")
    
    class Config:
        from_attributes = True

class ChatSession(BaseModel):
    """对话会话模型"""
    id: str = Field(..., description="会话ID")
    title: str = Field(..., description="会话标题")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    messages: List[ChatMessage] = Field(default_factory=list, description="消息列表")
    
    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    """查询请求模型"""
    question: str = Field(..., description="用户问题", min_length=1)
    session_id: Optional[str] = Field(None, description="会话ID")
    use_history: bool = Field(True, description="是否使用对话历史")
    
    class Config:
        from_attributes = True

class QueryResponse(BaseModel):
    """查询响应模型"""
    answer: str = Field(..., description="回答内容")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="参考来源")
    confidence: float = Field(..., description="置信度", ge=0, le=1)
    session_id: str = Field(..., description="会话ID")
    trace: Optional[List[Dict[str, Any]]] = Field(None, description="全链路追踪步骤")
    
    class Config:
        from_attributes = True

class DocumentStats(BaseModel):
    """文档统计模型"""
    total_documents: int = Field(0, description="总文档数")
    total_chunks: int = Field(0, description="总分块数")
    total_size: int = Field(0, description="总文件大小(字节)")
    file_types: Dict[str, int] = Field(default_factory=dict, description="文件类型统计")
    
    class Config:
        from_attributes = True

class ChunkListResponse(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    chunks: List[Dict[str, Any]]

class ReindexResult(BaseModel):
    total: int = Field(0, description="台账内文档总数")
    reindexed: int = Field(0, description="成功重嵌入数")
    failed: List[str] = Field(default_factory=list, description="失败的 doc_id")

class FactItem(BaseModel):
    id: str
    fact: str
    source: str = "extracted"
    created_at: str = ""

class MemoryList(BaseModel):
    count: int
    facts: List[FactItem]

class AddFactRequest(BaseModel):
    fact: str = Field(..., min_length=1, description="要记住的原子事实")

class ClearedResult(BaseModel):
    cleared_sessions: int

class RagStats(BaseModel):
    vector_store: Dict[str, Any]
    sessions: Dict[str, int]
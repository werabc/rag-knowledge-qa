"""
智能问答API
"""

from typing import List

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatMessage, ChatSession, QueryRequest, QueryResponse
from app.services.qa_service import qa_service
from app.services.vector_store import vector_store

router = APIRouter()


@router.post("/query", response_model=QueryResponse, summary="智能问答")
async def query_documents(request: QueryRequest):
    """基于文档知识库的智能问答"""
    try:
        return await qa_service.query(
            question=request.question,
            session_id=request.session_id,
            use_history=request.use_history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询处理失败：{str(e)}")


@router.get("/sessions", response_model=List[ChatSession], summary="获取会话列表")
async def get_sessions():
    """获取所有对话会话"""
    return await qa_service.get_all_sessions()


@router.get("/sessions/{session_id}", response_model=ChatSession, summary="获取会话详情")
async def get_session(session_id: str):
    """获取指定会话的详细信息"""
    session = await qa_service.get_session_history(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(session_id: str):
    """删除指定会话"""
    if await qa_service.delete_session(session_id):
        return {"message": "会话删除成功", "session_id": session_id}
    raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/sessions/{session_id}/history", response_model=List[ChatMessage],
            summary="获取对话历史")
async def get_chat_history(session_id: str):
    """获取指定会话的对话历史"""
    session = await qa_service.get_session_history(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session["messages"]


@router.get("/stats", summary="获取RAG系统统计")
async def get_rag_stats():
    """获取向量库与会话统计"""
    try:
        vector_stats = await vector_store.get_collection_stats()
        sessions = await qa_service.get_all_sessions()
        total_messages = sum(len(s["messages"]) for s in sessions)
        return {
            "vector_store": vector_stats,
            "sessions": {
                "total_sessions": len(sessions),
                "total_messages": total_messages,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败：{str(e)}")


@router.post("/clear-history", summary="清空对话历史")
async def clear_history(session_id: str = None):
    """清空指定会话；不传 session_id 则清空所有会话"""
    if session_id:
        if await qa_service.delete_session(session_id):
            return {"message": f"会话 {session_id} 已清空"}
        raise HTTPException(status_code=404, detail="会话不存在")
    n = await qa_service.clear_all_sessions()
    return {"message": f"已清空 {n} 个会话"}

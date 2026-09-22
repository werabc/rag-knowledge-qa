"""
智能问答API（/api/v1/chat）
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Query, Response
from fastapi.responses import StreamingResponse

from app.errors import ApiError
from app.models.schemas import (AddFactRequest, ChatMessage, ChatSession,
                                ClearedResult, FactItem, MemoryList, Page,
                                QueryRequest, QueryResponse, RagStats)
from app.services.agent_service import agent_service
from app.services.memory_service import memory_service
from app.services.qa_service import qa_service
from app.services.vector_store import vector_store

router = APIRouter()


@router.post("/query", response_model=QueryResponse, summary="智能问答",
             tags=["智能问答"])
async def query_documents(request: QueryRequest):
    """检索→重排→生成→引用核验 全链路；trace 逐步返回"""
    try:
        return await qa_service.query(
            question=request.question,
            session_id=request.session_id,
            use_history=request.use_history,
        )
    except Exception as e:
        raise ApiError(500, "query_failed", f"查询处理失败：{str(e)[:300]}")


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/stream", summary="智能问答（SSE 流式）", tags=["智能问答"])
async def stream_query(request: QueryRequest):
    """全链路事件流：step（trace 逐步）→ token（回答增量）→ citation（引用核验）→ done（完整响应）"""
    async def gen() -> AsyncGenerator[str, None]:
        try:
            async for ev in qa_service.query_stream(
                question=request.question,
                session_id=request.session_id,
                use_history=request.use_history,
            ):
                yield _sse(ev["event"], ev["data"])
        except Exception as e:
            yield _sse("error", {"code": "stream_failed",
                                 "message": str(e)[:300]})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@router.post("/agent", response_model=QueryResponse,
             summary="Agent 模式问答（多步工具调用）", tags=["智能问答"])
async def agent_query(request: QueryRequest):
    """L3 Agent：LLM 自主决定检索什么、检索几次（ReAct 循环），适合复合问题"""
    try:
        return await agent_service.run(
            question=request.question,
            session_id=request.session_id,
            use_history=request.use_history,
        )
    except Exception as e:
        raise ApiError(500, "agent_failed", f"Agent 处理失败：{str(e)[:300]}")


@router.get("/stats", response_model=RagStats, summary="RAG 系统统计",
            tags=["智能问答"])
async def get_rag_stats():
    try:
        vector_stats = await vector_store.get_collection_stats()
        sessions = await qa_service.get_all_sessions()
        total_messages = sum(len(s["messages"]) for s in sessions)
        return RagStats(vector_store=vector_stats,
                        sessions={"total_sessions": len(sessions),
                                  "total_messages": total_messages})
    except Exception as e:
        raise ApiError(500, "stats_failed", f"获取统计失败：{str(e)[:300]}")


# ---------- 长期记忆（L4） ----------

@router.get("/memories", response_model=MemoryList, summary="长期记忆列表",
            tags=["长期记忆"])
async def list_memories():
    facts = memory_service.list_facts()
    return MemoryList(count=len(facts), facts=facts)


@router.post("/memories", response_model=FactItem, status_code=201,
             summary="手动添加长期记忆", tags=["长期记忆"])
async def add_memory(request: AddFactRequest):
    item = memory_service.add_fact(request.fact, source="manual")
    if not item:
        raise ApiError(409, "fact_exists_or_empty", "事实为空或已存在")
    return item


@router.delete("/memories/{fact_id}", status_code=204, summary="删除一条长期记忆",
               tags=["长期记忆"])
async def delete_memory(fact_id: str):
    if not memory_service.delete_fact(fact_id):
        raise ApiError(404, "memory_not_found", f"记忆不存在: {fact_id}")
    return Response(status_code=204)


# ---------- 会话（短期记忆） ----------

@router.get("/sessions", response_model=Page[ChatSession], summary="会话列表（分页）",
            tags=["会话"])
async def get_sessions(page: int = Query(1, ge=1),
                       size: int = Query(20, ge=1, le=100)):
    sessions = await qa_service.get_all_sessions()
    start = (page - 1) * size
    return Page[ChatSession](items=sessions[start:start + size],
                             total=len(sessions), page=page, size=size)


@router.delete("/sessions", response_model=ClearedResult, summary="清空全部会话",
               tags=["会话"])
async def clear_sessions():
    return ClearedResult(cleared_sessions=await qa_service.clear_all_sessions())


@router.get("/sessions/{session_id}", response_model=ChatSession, summary="会话详情",
            tags=["会话"])
async def get_session(session_id: str):
    session = await qa_service.get_session_history(session_id)
    if not session:
        raise ApiError(404, "session_not_found", f"会话不存在: {session_id}")
    return session


@router.delete("/sessions/{session_id}", status_code=204, summary="删除会话",
               tags=["会话"])
async def delete_session(session_id: str):
    if not await qa_service.delete_session(session_id):
        raise ApiError(404, "session_not_found", f"会话不存在: {session_id}")
    return Response(status_code=204)


@router.get("/sessions/{session_id}/history", response_model=list[ChatMessage],
            summary="对话历史", tags=["会话"])
async def get_chat_history(session_id: str):
    session = await qa_service.get_session_history(session_id)
    if not session:
        raise ApiError(404, "session_not_found", f"会话不存在: {session_id}")
    return session["messages"]

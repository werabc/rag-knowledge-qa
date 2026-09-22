"""
文档管理API（/api/v1/documents）
"""

import os

from fastapi import APIRouter, File, Query, Response, UploadFile

from app.config import settings
from app.errors import ApiError
from app.models.schemas import (ChunkListResponse, DocumentResponse,
                                DocumentStats, Page, ReindexResult)
from app.services.document_service import document_service
from app.services.vector_store import vector_store

router = APIRouter()

_reindexing = False

_ALLOWED_TYPES = [".pdf", ".docx", ".txt"]


@router.post("/upload", response_model=DocumentResponse, summary="上传文档",
             tags=["文档管理"])
async def upload_document(file: UploadFile = File(...)):
    """上传 .txt/.pdf/.docx：提取文本 → 切块 → 向量库 + BM25 + 明文 + 台账"""
    safe_name = os.path.basename(file.filename or "document.txt")
    file_ext = os.path.splitext(safe_name)[1].lower()

    if file_ext not in _ALLOWED_TYPES:
        raise ApiError(400, "unsupported_file_type",
                       f"不支持的文件类型 {file_ext or '(无扩展名)'}",
                       {"allowed": _ALLOWED_TYPES})

    file_size = 0
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    temp_file_path = os.path.join(settings.DOCUMENT_STORAGE_PATH, f"temp_{safe_name}")

    try:
        with open(temp_file_path, "wb") as buffer:
            while True:
                piece = await file.read(1024 * 1024)
                if not piece:
                    break
                file_size += len(piece)
                if file_size > max_size:
                    raise ApiError(413, "file_too_large",
                                   f"文件大小超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")
                buffer.write(piece)

        return await document_service.upload_document(
            file_path=temp_file_path, filename=safe_name, file_size=file_size)

    except ApiError:
        raise
    except Exception as e:
        raise ApiError(500, "document_processing_failed",
                       f"文档处理失败：{str(e)[:300]}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.get("/", response_model=Page[DocumentResponse], summary="文档列表（分页）",
            tags=["文档管理"])
async def get_documents(page: int = Query(1, ge=1),
                        size: int = Query(20, ge=1, le=100)):
    docs = await document_service.get_documents()
    start = (page - 1) * size
    return Page[DocumentResponse](items=docs[start:start + size],
                                  total=len(docs), page=page, size=size)


@router.get("/stats/summary", response_model=DocumentStats, summary="文档统计",
            tags=["文档管理"])
async def get_document_stats():
    return await document_service.get_document_stats()


@router.post("/reindex", response_model=ReindexResult, summary="全量重建索引",
             tags=["文档管理"])
async def reindex_documents():
    """用当前 embedding 模型重建向量库+BM25；切换 EMBEDDING_MODEL_NAME 后必须调用"""
    global _reindexing
    if _reindexing:
        raise ApiError(409, "reindex_in_progress", "已有重建任务在执行中")
    _reindexing = True
    try:
        return ReindexResult(**await document_service.reindex_all())
    except ApiError:
        raise
    except Exception as e:
        raise ApiError(500, "reindex_failed", f"重建索引失败：{str(e)[:300]}")
    finally:
        _reindexing = False


@router.get("/{doc_id}", response_model=DocumentResponse, summary="文档详情",
            tags=["文档管理"])
async def get_document(doc_id: str):
    document = await document_service.get_document(doc_id)
    if not document:
        raise ApiError(404, "document_not_found", f"文档不存在: {doc_id}")
    return document


@router.delete("/{doc_id}", status_code=204, summary="删除文档",
               tags=["文档管理"])
async def delete_document(doc_id: str):
    """删除向量分块 + BM25 + 台账 + 分块明文；成功返回 204 无响应体"""
    if not await document_service.get_document(doc_id):
        raise ApiError(404, "document_not_found", f"文档不存在: {doc_id}")
    await vector_store.delete_document(doc_id)
    if not await document_service.delete_document(doc_id):
        raise ApiError(500, "document_delete_failed", "台账删除未生效")
    return Response(status_code=204)


@router.get("/{doc_id}/chunks", response_model=ChunkListResponse,
            summary="文档分块明文", tags=["文档管理"])
async def get_document_chunks(doc_id: str):
    document = await document_service.get_document(doc_id)
    if not document:
        raise ApiError(404, "document_not_found", f"文档不存在: {doc_id}")
    chunks = await document_service.get_document_chunks(doc_id)
    return ChunkListResponse(doc_id=doc_id, filename=document.filename,
                             chunk_count=len(chunks), chunks=chunks)

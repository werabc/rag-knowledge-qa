"""
文档管理API
"""

import os
import shutil
from datetime import datetime
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import DocumentResponse, DocumentStats
from app.services.document_service import document_service
from app.services.vector_store import vector_store

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse, summary="上传文档")
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档文件
    
    支持的文件格式：PDF、DOCX、TXT
    
    Args:
        file: 上传的文件
        
    Returns:
        DocumentResponse: 文档信息
    """
    # 清洗文件名，防止路径穿越
    safe_name = os.path.basename(file.filename or "document.txt")
    file_ext = os.path.splitext(safe_name)[1].lower()

    # 检查文件类型
    allowed_types = [".pdf", ".docx", ".txt"]

    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持的格式：{', '.join(allowed_types)}"
        )

    # 保存上传的文件（边写边限流）
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
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件大小超过限制。最大允许：{settings.MAX_UPLOAD_SIZE_MB}MB"
                    )
                buffer.write(piece)

        # 处理文档（提取内容、分块、写入向量库）
        document = await document_service.upload_document(
            file_path=temp_file_path,
            filename=safe_name,
            file_size=file_size
        )

        return document

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"文档处理失败：{str(e)}"
        )
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@router.get("/", response_model=List[DocumentResponse], summary="获取文档列表")
async def get_documents():
    """
    获取所有已上传的文档列表
    
    Returns:
        List[DocumentResponse]: 文档列表
    """
    return await document_service.get_documents()

@router.get("/{doc_id}", response_model=DocumentResponse, summary="获取文档详情")
async def get_document(doc_id: str):
    """
    获取指定文档的详细信息
    
    Args:
        doc_id: 文档ID
        
    Returns:
        DocumentResponse: 文档信息
    """
    document = await document_service.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document

@router.delete("/{doc_id}", summary="删除文档")
async def delete_document(doc_id: str):
    """
    删除指定文档
    
    Args:
        doc_id: 文档ID
        
    Returns:
        dict: 操作结果
    """
    # 检查文档是否存在
    document = await document_service.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 删除向量存储中的文档
    await vector_store.delete_document(doc_id)
    
    # 删除文档记录
    success = await document_service.delete_document(doc_id)
    
    if success:
        return {"message": "文档删除成功", "doc_id": doc_id}
    else:
        raise HTTPException(status_code=500, detail="文档删除失败")

@router.get("/stats/summary", response_model=DocumentStats, summary="获取文档统计")
async def get_document_stats():
    """
    获取文档统计信息
    
    Returns:
        DocumentStats: 统计信息
    """
    return await document_service.get_document_stats()

@router.get("/{doc_id}/chunks", summary="获取文档分块")
async def get_document_chunks(doc_id: str):
    """
    获取文档的分块内容
    
    Args:
        doc_id: 文档ID
        
    Returns:
        dict: 文档分块
    """
    # 检查文档是否存在
    document = await document_service.get_document(doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 获取分块内容
    chunks = await document_service.get_document_chunks(doc_id)
    
    return {
        "doc_id": doc_id,
        "filename": document.filename,
        "chunk_count": len(chunks),
        "chunks": chunks
    }
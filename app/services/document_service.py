"""
文档处理服务
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

import pymupdf
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.models.schemas import DocumentResponse, DocumentStats
from app.services.bm25_index import bm25_index
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

_ocr_engine = None


def _get_ocr():
    """RapidOCR 懒加载：只有遇到无文字层的 PDF 页才付出模型加载成本"""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine

class DocumentService:
    """文档处理服务类"""
    
    def __init__(self):
        """初始化文档服务"""
        self.documents_db: Dict[str, DocumentResponse] = {}
        self._store_file = os.path.join(settings.DOCUMENT_STORAGE_PATH, "documents.json")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True,
        )
        self._load_db()

    # ---------- 台账持久化 ----------

    def _load_db(self):
        if not os.path.exists(self._store_file):
            return
        try:
            with open(self._store_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.documents_db = {k: DocumentResponse(**v) for k, v in raw.items()}
        except Exception:
            logger.exception("加载文档台账失败，从空台账开始")

    def _save_db(self):
        try:
            os.makedirs(settings.DOCUMENT_STORAGE_PATH, exist_ok=True)
            tmp = self._store_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.model_dump(mode="json") for k, v in self.documents_db.items()},
                    f, ensure_ascii=False, indent=1,
                )
            os.replace(tmp, self._store_file)
        except Exception:
            logger.exception("保存文档台账失败")

    async def startup(self):
        """把向量库中无台账记录的孤儿分块认领回文档列表（断电/删库不同步时自愈）"""
        summaries = await vector_store.get_all_doc_summaries()
        recovered = False
        for doc_id, s in summaries.items():
            if doc_id in self.documents_db:
                continue
            try:
                upload_time = datetime.fromisoformat(s["upload_time"]) if s.get("upload_time") else datetime.now()
            except (TypeError, ValueError):
                upload_time = datetime.now()
            self.documents_db[doc_id] = DocumentResponse(
                id=doc_id,
                filename=s["filename"] or "(已恢复)",
                file_type=s["file_type"] or "",
                file_size=0,
                upload_time=upload_time,
                status="recovered",
                chunk_count=s["chunk_count"],
            )
            recovered = True
        if recovered:
            self._save_db()
    
    async def upload_document(self, file_path: str, filename: str, file_size: int) -> DocumentResponse:
        """
        上传并处理文档
        
        Args:
            file_path: 文件路径
            filename: 文件名
            file_size: 文件大小
            
        Returns:
            DocumentResponse: 文档信息
        """
        # 生成文档ID
        doc_id = str(uuid.uuid4())
        
        # 获取文件类型
        file_type = Path(filename).suffix.lower()
        
        # 逐页提取内容（含页码与是否OCR标记）
        pages = await self._extract_pages(file_path, file_type)

        # 分块处理：页内切块，跨页不合并，保证页码归属准确
        chunks: List[Dict[str, Any]] = []
        for p in pages:
            for t in (self.text_splitter.split_text(p["text"])
                      if p["text"].strip() else []):
                chunks.append({"text": t, "page_num": p["page_num"],
                               "ocr": p["ocr"]})

        # 创建文档记录
        document = DocumentResponse(
            id=doc_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            upload_time=datetime.now(),
            status="pending",
            chunk_count=len(chunks)
        )

        # 写入向量库（embedding 由 chromadb 完成）
        indexed = await vector_store.add_documents(
            doc_id, [c["text"] for c in chunks],
            metadata={
                "filename": filename,
                "file_type": file_type,
                "upload_time": document.upload_time.isoformat(),
            },
            per_chunk=chunks,
        )
        document.status = "processed" if indexed else "index_failed"
        if indexed:
            bm25_index.add_doc(doc_id, filename, [c["text"] for c in chunks])

        # 存储文档信息并落盘台账
        self.documents_db[doc_id] = document
        self._save_db()
        
        # 保存分块内容到文件，供查看
        chunks_dir = os.path.join(settings.DOCUMENT_STORAGE_PATH, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)

        chunks_file = os.path.join(chunks_dir, f"{doc_id}.json")
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=1)
        
        return document

    async def _extract_pages(self, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """统一按页返回 [{page_num, text, ocr}]；txt/docx 视为单页"""
        if file_type == ".pdf":
            return await self._extract_pdf(file_path)
        content = await self._extract_content(file_path, file_type)
        return [{"page_num": None, "text": content, "ocr": False}]
    
    async def _extract_content(self, file_path: str, file_type: str) -> str:
        """
        提取文档内容
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            str: 提取的文本内容
        """
        content = ""
        
        try:
            if file_type == ".pdf":
                content = await self._extract_pdf(file_path)
            elif file_type == ".docx":
                content = await self._extract_docx(file_path)
            elif file_type == ".txt":
                content = await self._extract_txt(file_path)
            else:
                # 尝试作为文本文件读取
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
        except Exception as e:
            print(f"文档内容提取失败: {e}")
            content = f"文档内容提取失败: {str(e)}"
        
        return content
    
    async def _extract_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """PyMuPDF 逐页提取；文字层稀薄且含图像的页判定为扫描页，渲染 200dpi 走 OCR"""
        pages: List[Dict[str, Any]] = []
        try:
            doc = pymupdf.open(file_path)
        except Exception as e:
            return [{"page_num": None, "text": f"PDF读取失败: {e}", "ocr": False}]
        with doc:
            for i, page in enumerate(doc, 1):
                text = page.get_text().strip()
                ocr = False
                if len(text) < 20 and page.get_images():
                    try:
                        pix = page.get_pixmap(dpi=200)
                        result, _ = _get_ocr()(pix.tobytes("png"))
                        text = "\n".join(line[1] for line in (result or []))
                        ocr = True
                    except Exception as e:
                        logger.exception("PDF 页 %s OCR 失败", i)
                        text = text or f"（第{i}页 OCR 失败: {e}）"
                pages.append({"page_num": i, "text": text, "ocr": ocr})
        return pages
    
    async def _extract_docx(self, file_path: str) -> str:
        """提取Word文档内容"""
        text = ""
        try:
            doc = DocxDocument(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            text = f"Word文档读取失败: {str(e)}"
        return text
    
    async def _extract_txt(self, file_path: str) -> str:
        """提取文本文件内容"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"文本文件读取失败: {str(e)}"
    
    async def get_documents(self) -> List[DocumentResponse]:
        """获取所有文档列表"""
        return list(self.documents_db.values())
    
    async def get_document(self, doc_id: str) -> Optional[DocumentResponse]:
        """获取指定文档信息"""
        return self.documents_db.get(doc_id)
    
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id in self.documents_db:
            del self.documents_db[doc_id]
            self._save_db()
            bm25_index.remove_doc(doc_id)
            # 删除分块文件
            chunks_file = os.path.join(settings.DOCUMENT_STORAGE_PATH, "chunks", f"{doc_id}.json")
            if os.path.exists(chunks_file):
                os.remove(chunks_file)
            return True
        return False
    
    async def get_document_stats(self) -> DocumentStats:
        """获取文档统计信息"""
        documents = list(self.documents_db.values())
        
        total_chunks = sum(doc.chunk_count for doc in documents)
        total_size = sum(doc.file_size for doc in documents)
        
        file_types = {}
        for doc in documents:
            file_type = doc.file_type
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        return DocumentStats(
            total_documents=len(documents),
            total_chunks=total_chunks,
            total_size=total_size,
            file_types=file_types
        )
    
    async def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """获取文档分块（新格式 [{text,page_num,ocr}]，兼容旧的纯字符串分块）"""
        chunks_file = os.path.join(settings.DOCUMENT_STORAGE_PATH, "chunks", f"{doc_id}.json")

        if not os.path.exists(chunks_file):
            return []

        try:
            with open(chunks_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return [{"text": c, "page_num": None, "ocr": False} if isinstance(c, str) else c
                    for c in raw]
        except Exception:
            logger.exception("读取文档分块失败")
            return []

    async def reindex_all(self) -> Dict[str, Any]:
        """用当前 embedding 模型重建整个向量库 + BM25（切换模型后维度不同必须执行）"""
        await vector_store.recreate_collection()
        bm25_index.build([])
        ok, failed = 0, []
        for doc in list(self.documents_db.values()):
            chunks = await self.get_document_chunks(doc.id)
            if not chunks:
                failed.append({"doc_id": doc.id, "filename": doc.filename,
                               "reason": "分块明文缺失"})
                continue
            indexed = await vector_store.add_documents(
                doc.id, [c["text"] for c in chunks],
                metadata={
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "upload_time": doc.upload_time.isoformat(),
                },
                per_chunk=chunks,
            )
            if indexed:
                bm25_index.add_doc(doc.id, doc.filename, [c["text"] for c in chunks])
                doc.status = "processed"
                ok += 1
            else:
                doc.status = "index_failed"
                failed.append({"doc_id": doc.id, "filename": doc.filename,
                               "reason": "向量写入失败"})
        self._save_db()
        return {"total": len(self.documents_db), "reindexed": ok, "failed": failed}

# 创建全局文档服务实例
document_service = DocumentService()
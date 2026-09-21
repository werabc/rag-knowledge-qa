"""
RAG核心服务 - 整合所有模块
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.config import rag_config
from app.services.chunking import *
from app.services.retrieval import *
from app.services.reranking import *
from app.services.query_understanding import *
from app.services.evaluation import *

class RAGService:
    """RAG核心服务类"""
    
    def __init__(self):
        """初始化RAG服务"""
        # 初始化各个模块
        self._init_chunkers()
        self._init_retrievers()
        self._init_rerankers()
        self._init_query_understanding()
        self._init_evaluation()
        
        # 会话存储
        self.sessions = {}
    
    def _init_chunkers(self):
        """初始化分块器"""
        self.chunkers = {
            "fixed": FixedSizeChunker(
                chunk_size=rag_config.CHUNK_SIZE,
                chunk_overlap=rag_config.CHUNK_OVERLAP
            ),
            "semantic": SemanticChunker(
                chunk_size=rag_config.CHUNK_SIZE,
                chunk_overlap=rag_config.CHUNK_OVERLAP,
                similarity_threshold=0.7
            ),
            "structural": StructureAwareChunker(
                chunk_size=rag_config.CHUNK_SIZE,
                chunk_overlap=rag_config.CHUNK_OVERLAP
            ),
            "adaptive": AdaptiveChunker(
                chunk_size=rag_config.CHUNK_SIZE,
                chunk_overlap=rag_config.CHUNK_OVERLAP,
                min_size=rag_config.MIN_CHUNK_SIZE,
                max_size=rag_config.MAX_CHUNK_SIZE
            )
        }
        
        # 默认分块器
        self.default_chunker = self.chunkers.get(
            rag_config.CHUNKING_STRATEGY, 
            self.chunkers["semantic"]
        )
    
    def _init_retrievers(self):
        """初始化召回器"""
        self.retrievers = {}
        
        # 向量召回器（稍后初始化，需要embedding_model和vector_db）
        self.vector_retriever = None
        
        # BM25召回器（稍后初始化，需要文档列表）
        self.bm25_retriever = None
        
        # 结构化召回器（稍后初始化，需要文档解析器）
        self.structural_retriever = None
    
    def _init_rerankers(self):
        """初始化重排序器"""
        self.rerankers = {
            "cross_encoder": CrossEncoderReranker(
                model_name=rag_config.CROSS_ENCODER_MODEL
            ),
            "diversity": DiversityReranker(
                lambda_param=rag_config.DIVERSITY_LAMBDA,
                diversity_metric="mmr"
            )
        }
    
    def _init_query_understanding(self):
        """初始化查询理解"""
        self.intent_classifier = IntentClassifier()
        self.entity_recognizer = EntityRecognizer()
        self.query_expander = QueryExpander(expansion_factor=rag_config.QUERY_EXPANSION_FACTOR)
    
    def _init_evaluation(self):
        """初始化评估模块"""
        self.evaluator = RetrievalEvaluator()
    
    async def process_query(self, query: str, session_id: Optional[str] = None,
                           use_history: bool = True) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            query: 用户查询
            session_id: 会话ID
            use_history: 是否使用对话历史
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        # 1. 查询理解
        query_analysis = await self._analyze_query(query)
        
        # 2. 查询扩展
        if rag_config.QUERY_EXPANSION_ENABLED:
            expanded_queries = await self.query_expander.expand_query(query)
        else:
            expanded_queries = [query]
        
        # 3. 多路召回
        retrieval_results = await self._multi_strategy_retrieval(
            expanded_queries, query_analysis
        )
        
        # 4. 重排序
        if rag_config.RERANKING_ENABLED:
            reranked_results = await self._rerank_results(query, retrieval_results)
        else:
            reranked_results = retrieval_results
        
        # 5. 上下文构建
        context = await self._build_context(query, reranked_results)
        
        # 6. 生成回答（模拟实现）
        answer = await self._generate_answer(query, context, query_analysis)
        
        # 7. 评估（如果启用）
        evaluation_metrics = {}
        if rag_config.EVALUATION_ENABLED:
            evaluation_metrics = await self._evaluate_results(
                query, reranked_results, answer
            )
        
        # 8. 保存到会话
        if session_id:
            await self._save_to_session(session_id, query, answer, reranked_results)
        
        return {
            "query": query,
            "answer": answer,
            "sources": reranked_results[:5],  # 返回前5个来源
            "query_analysis": query_analysis,
            "expanded_queries": expanded_queries,
            "context": context,
            "evaluation_metrics": evaluation_metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """分析查询"""
        # 意图识别
        intent_result = await self.intent_classifier.classify_intent(query)
        
        # 实体识别
        entities = await self.entity_recognizer.recognize_entities(query)
        
        return {
            "intent": intent_result,
            "entities": entities,
            "query_length": len(query),
            "language": self._detect_language(query)
        }
    
    def _detect_language(self, text: str) -> str:
        """检测语言"""
        # 简单实现：基于字符范围
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        total_chars = len(text)
        
        if total_chars == 0:
            return "unknown"
        
        if chinese_chars / total_chars > 0.3:
            return "zh"
        else:
            return "en"
    
    async def _multi_strategy_retrieval(self, queries: List[str], 
                                       query_analysis: Dict[str, Any]) -> List[Dict]:
        """多路召回"""
        all_results = []
        
        # 向量召回
        if rag_config.RECALL_STRATEGIES.get("vector", True) and self.vector_retriever:
            for query in queries:
                results = await self.vector_retriever.retrieve(query)
                all_results.extend([self._retrieval_result_to_dict(r) for r in results])
        
        # BM25召回
        if rag_config.RECALL_STRATEGIES.get("bm25", True) and self.bm25_retriever:
            results = await self.bm25_retriever.retrieve(queries[0])  # 使用原始查询
            all_results.extend([self._retrieval_result_to_dict(r) for r in results])
        
        # 结构化召回
        if rag_config.RECALL_STRATEGIES.get("structural", False) and self.structural_retriever:
            # 需要文档ID，这里简化处理
            pass
        
        # 去重
        unique_results = self._deduplicate_results(all_results)
        
        return unique_results
    
    def _retrieval_result_to_dict(self, result) -> Dict[str, Any]:
        """将检索结果转换为字典"""
        return {
            "content": result.content,
            "score": result.score,
            "metadata": result.metadata,
            "retrieval_method": result.retrieval_method,
            "doc_id": result.doc_id,
            "chunk_id": result.chunk_id
        }
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """去重"""
        seen_contents = set()
        unique_results = []
        
        for result in results:
            # 内容指纹（前200字符）
            content_fingerprint = result["content"][:200]
            
            if content_fingerprint not in seen_contents:
                seen_contents.add(content_fingerprint)
                unique_results.append(result)
        
        return unique_results
    
    async def _rerank_results(self, query: str, results: List[Dict]) -> List[Dict]:
        """重排序"""
        if not results:
            return []
        
        # 第一步：Cross-Encoder重排序
        cross_encoder_results = await self.rerankers["cross_encoder"].rerank(
            query, results, top_k=rag_config.RERANKING_TOP_K
        )
        
        # 第二步：多样性重排序
        diversity_results = await self.rerankers["diversity"].rerank(
            query, cross_encoder_results, top_k=rag_config.RERANKING_TOP_K
        )
        
        return diversity_results
    
    async def _build_context(self, query: str, results: List[Dict]) -> Dict[str, Any]:
        """构建上下文"""
        # 简单实现：拼接前几个结果作为上下文
        context_parts = []
        total_tokens = 0
        
        for result in results[:3]:  # 使用前3个结果
            content = result["content"]
            # 估算token数
            token_count = len(content) // 2  # 粗略估算
            
            if total_tokens + token_count > rag_config.CONTEXT_MAX_TOKENS:
                break
            
            context_parts.append(content)
            total_tokens += token_count
        
        return {
            "text": "\n\n".join(context_parts),
            "token_count": total_tokens,
            "source_count": len(context_parts),
            "strategy": "top_k_concatenation"
        }
    
    async def _generate_answer(self, query: str, context: Dict[str, Any],
                              query_analysis: Dict[str, Any]) -> str:
        """生成回答（模拟实现）"""
        # 这里应该集成真正的LLM
        # 目前返回模拟回答
        
        intent = query_analysis["intent"]["primary_intent"]
        
        if intent == "factual":
            return f"根据文档内容，关于'{query}'的事实性信息如下：\n\n{context['text'][:500]}..."
        elif intent == "explanatory":
            return f"让我为您解释'{query}'的相关概念：\n\n{context['text'][:500]}..."
        elif intent == "procedural":
            return f"关于'{query}'的操作步骤如下：\n\n{context['text'][:500]}..."
        else:
            return f"基于文档内容，关于'{query}'的信息：\n\n{context['text'][:500]}..."
    
    async def _evaluate_results(self, query: str, results: List[Dict],
                               answer: str) -> Dict[str, float]:
        """评估结果"""
        # 这里需要相关文档标签，暂时返回空评估
        return {
            "retrieval_quality": 0.0,
            "answer_relevance": 0.0,
            "context_utilization": 0.0
        }
    
    async def _save_to_session(self, session_id: str, query: str, answer: str,
                              results: List[Dict]):
        """保存到会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.now().isoformat(),
                "messages": []
            }
        
        self.sessions[session_id]["messages"].append({
            "role": "user",
            "content": query,
            "timestamp": datetime.now().isoformat()
        })
        
        self.sessions[session_id]["messages"].append({
            "role": "assistant",
            "content": answer,
            "sources": results[:3],
            "timestamp": datetime.now().isoformat()
        })
    
    async def get_session_history(self, session_id: str) -> Optional[Dict]:
        """获取会话历史"""
        return self.sessions.get(session_id)
    
    async def get_all_sessions(self) -> List[Dict]:
        """获取所有会话"""
        return list(self.sessions.values())
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    # 初始化方法
    def init_vector_retriever(self, embedding_model, vector_db):
        """初始化向量召回器"""
        self.vector_retriever = VectorRetriever(
            embedding_model=embedding_model,
            vector_db=vector_db,
            top_k=rag_config.VECTOR_TOP_K
        )
    
    def init_bm25_retriever(self, documents: List[str]):
        """初始化BM25召回器"""
        self.bm25_retriever = BM25Retriever(
            documents=documents,
            top_k=rag_config.BM25_TOP_K,
            k1=rag_config.BM25_K1,
            b=rag_config.BM25_B
        )
    
    def init_structural_retriever(self, document_parser):
        """初始化结构化召回器"""
        self.structural_retriever = StructuralRetriever(
            document_parser=document_parser,
            top_k=rag_config.STRUCTURAL_TOP_K
        )
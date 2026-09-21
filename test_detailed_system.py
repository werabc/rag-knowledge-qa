#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细RAG系统测试脚本
"""

import asyncio
import json
import sys
import io
from typing import List, Dict

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 导入各个模块
from app.services.chunking import *
from app.services.retrieval import *
from app.services.reranking import *
from app.services.query_understanding import *
from app.services.evaluation import *

async def test_chunking_strategies():
    """测试分块策略"""
    print("测试分块策略")
    print("=" * 50)
    
    test_text = """
    人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能才能完成的任务的系统。
    
    机器学习是人工智能的一个子领域，它使计算机系统能够从数据中学习，而无需显式编程。深度学习是机器学习的一个子集，它使用人工神经网络来模拟人脑的工作方式。
    
    自然语言处理（NLP）是人工智能的另一个重要分支，它使计算机能够理解、解释和生成人类语言。计算机视觉则专注于让计算机从图像和视频中获取高层次的理解。
    
    近年来，随着大数据和计算能力的提升，人工智能技术取得了显著进展。Transformer架构的出现标志着自然语言处理领域的重大突破，GPT和BERT等预训练语言模型展示了强大的语言理解能力。
    
    然而，人工智能的发展也带来了一些挑战，包括数据隐私、算法偏见、可解释性等问题。我们需要在推动技术进步的同时，确保人工智能的发展符合伦理和法律规范。
    """
    
    # 测试固定大小分块
    print("\n1. 固定大小分块:")
    fixed_chunker = FixedSizeChunker(chunk_size=200, chunk_overlap=20)
    fixed_chunks = await fixed_chunker.chunk(test_text)
    print(f"   分块数量: {len(fixed_chunks)}")
    for i, chunk in enumerate(fixed_chunks[:3]):
        print(f"   分块{i+1}: {chunk.text[:50]}... (长度: {len(chunk.text)})")
    
    # 测试语义分块
    print("\n2. 语义分块:")
    semantic_chunker = SemanticChunker(chunk_size=200, chunk_overlap=20)
    semantic_chunks = await semantic_chunker.chunk(test_text)
    print(f"   分块数量: {len(semantic_chunks)}")
    for i, chunk in enumerate(semantic_chunks[:3]):
        print(f"   分块{i+1}: {chunk.text[:50]}... (长度: {len(chunk.text)})")
    
    # 测试结构感知分块
    print("\n3. 结构感知分块:")
    structural_chunker = StructureAwareChunker(chunk_size=200, chunk_overlap=20)
    structural_chunks = await structural_chunker.chunk(test_text)
    print(f"   分块数量: {len(structural_chunks)}")
    for i, chunk in enumerate(structural_chunks[:3]):
        print(f"   分块{i+1}: {chunk.text[:50]}... (长度: {len(chunk.text)})")
    
    # 测试自适应分块
    print("\n4. 自适应分块:")
    adaptive_chunker = AdaptiveChunker(chunk_size=200, chunk_overlap=20)
    adaptive_chunks = await adaptive_chunker.chunk(test_text)
    print(f"   分块数量: {len(adaptive_chunks)}")
    for i, chunk in enumerate(adaptive_chunks[:3]):
        print(f"   分块{i+1}: {chunk.text[:50]}... (长度: {len(chunk.text)})")
    
    print("\n✅ 分块策略测试完成")

async def test_retrieval_strategies():
    """测试召回策略"""
    print("\n测试召回策略")
    print("=" * 50)
    
    # 模拟文档集合
    documents = [
        "人工智能是计算机科学的一个分支，致力于创建智能系统。",
        "机器学习使计算机能够从数据中学习，无需显式编程。",
        "深度学习使用人工神经网络模拟人脑工作方式。",
        "自然语言处理使计算机能够理解人类语言。",
        "计算机视觉专注于让计算机从图像中获取理解。",
        "Transformer架构标志着NLP领域的重大突破。",
        "GPT和BERT展示了强大的语言理解能力。",
        "人工智能的发展带来了数据隐私等挑战。"
    ]
    
    # 测试BM25召回
    print("\n1. BM25召回:")
    bm25_retriever = BM25Retriever(documents, top_k=3)
    query = "什么是机器学习？"
    bm25_results = await bm25_retriever.retrieve(query)
    print(f"   查询: {query}")
    print(f"   召回数量: {len(bm25_results)}")
    for i, result in enumerate(bm25_results):
        print(f"   结果{i+1}: {result.content[:50]}... (分数: {result.score:.3f})")
    
    print("\n✅ 召回策略测试完成")

async def test_reranking_strategies():
    """测试重排序策略"""
    print("\n测试重排序策略")
    print("=" * 50)
    
    # 模拟候选结果
    candidates = [
        {"content": "人工智能是计算机科学的一个分支", "score": 0.8, "metadata": {"doc_id": "1"}},
        {"content": "机器学习使计算机能够从数据中学习", "score": 0.7, "metadata": {"doc_id": "2"}},
        {"content": "深度学习使用人工神经网络", "score": 0.6, "metadata": {"doc_id": "3"}},
        {"content": "自然语言处理使计算机理解语言", "score": 0.5, "metadata": {"doc_id": "4"}},
        {"content": "计算机视觉专注于图像理解", "score": 0.4, "metadata": {"doc_id": "5"}}
    ]
    
    # 测试Cross-Encoder重排序
    print("\n1. Cross-Encoder重排序:")
    cross_encoder_reranker = CrossEncoderReranker()
    query = "什么是人工智能？"
    
    try:
        cross_encoder_results = await cross_encoder_reranker.rerank(query, candidates, top_k=3)
        print(f"   查询: {query}")
        print(f"   重排序结果数量: {len(cross_encoder_results)}")
        for i, result in enumerate(cross_encoder_results):
            print(f"   结果{i+1}: {result['content'][:30]}... (重排序分数: {result.get('rerank_score', 'N/A')})")
    except Exception as e:
        print(f"   Cross-Encoder重排序失败: {e}")
    
    # 测试多样性重排序
    print("\n2. 多样性重排序 (MMR):")
    diversity_reranker = DiversityReranker(lambda_param=0.7, diversity_metric="mmr")
    
    try:
        diversity_results = await diversity_reranker.rerank(query, candidates, top_k=3)
        print(f"   查询: {query}")
        print(f"   重排序结果数量: {len(diversity_results)}")
        for i, result in enumerate(diversity_results):
            print(f"   结果{i+1}: {result['content'][:30]}... (多样性分数: {result.get('diversity_score', 'N/A')})")
    except Exception as e:
        print(f"   多样性重排序失败: {e}")
    
    print("\n✅ 重排序策略测试完成")

async def test_query_understanding():
    """测试查询理解"""
    print("\n测试查询理解")
    print("=" * 50)
    
    test_queries = [
        "什么是机器学习？",
        "如何使用Python进行数据分析？",
        "比较TensorFlow和PyTorch的区别",
        "人工智能的发展历史",
        "深度学习模型的训练步骤"
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        
        # 意图识别
        intent_classifier = IntentClassifier()
        intent_result = await intent_classifier.classify_intent(query)
        print(f"  意图: {intent_result['primary_intent']} (置信度: {intent_result['confidence']:.2f})")
        
        # 实体识别
        entity_recognizer = EntityRecognizer()
        entities = await entity_recognizer.recognize_entities(query)
        if entities:
            print(f"  实体: {[e['text'] for e in entities[:3]]}")
        
        # 查询扩展
        query_expander = QueryExpander(expansion_factor=2)
        expanded_queries = await query_expander.expand_query(query)
        print(f"  扩展查询: {len(expanded_queries)} 个")
        for i, exp_query in enumerate(expanded_queries[:2]):
            print(f"    {i+1}. {exp_query}")
    
    print("\n✅ 查询理解测试完成")

async def test_evaluation():
    """测试评估模块"""
    print("\n测试评估模块")
    print("=" * 50)
    
    # 模拟检索结果和相关文档
    retrieved_docs = [
        {"doc_id": "1", "content": "人工智能是计算机科学的一个分支"},
        {"doc_id": "2", "content": "机器学习使计算机能够从数据中学习"},
        {"doc_id": "3", "content": "深度学习使用人工神经网络"},
        {"doc_id": "4", "content": "自然语言处理使计算机理解语言"},
        {"doc_id": "5", "content": "计算机视觉专注于图像理解"}
    ]
    
    relevant_docs = ["1", "2", "3"]  # 相关文档ID
    
    # 评估
    evaluator = RetrievalEvaluator()
    metrics = evaluator.evaluate(retrieved_docs, relevant_docs, k=5)
    
    print("评估结果:")
    for metric_name, value in metrics.items():
        print(f"  {metric_name}: {value:.3f}")
    
    print("\n✅ 评估模块测试完成")

async def main():
    """主测试函数"""
    print("详细RAG系统测试")
    print("=" * 50)
    
    # 运行所有测试
    await test_chunking_strategies()
    await test_retrieval_strategies()
    await test_reranking_strategies()
    await test_query_understanding()
    await test_evaluation()
    
    print("\n" + "=" * 50)
    print("所有测试完成！")

if __name__ == "__main__":
    asyncio.run(main())
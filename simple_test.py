#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试脚本
"""

import sys
import io
import asyncio

# 设置标准输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("开始简单测试...")

async def run_tests():
    try:
        # 测试导入
        print("1. 测试导入模块...")
        from app.services.chunking import FixedSizeChunker, SemanticChunker
        from app.services.retrieval import BM25Retriever
        from app.services.query_understanding import IntentClassifier, EntityRecognizer
        from app.services.evaluation import RetrievalEvaluator
        print("   导入成功")
        
        # 测试分块
        print("2. 测试分块功能...")
        test_text = "这是一个测试文本。用于验证分块功能是否正常工作。"
        
        fixed_chunker = FixedSizeChunker(chunk_size=20, chunk_overlap=5)
        chunks = await fixed_chunker.chunk(test_text)
        print(f"   固定分块: {len(chunks)} 个分块")
        
        # 测试召回
        print("3. 测试召回功能...")
        documents = ["这是第一个文档", "这是第二个文档", "这是第三个文档"]
        bm25_retriever = BM25Retriever(documents, top_k=2)
        print("   BM25召回器初始化成功")
        
        # 测试查询理解
        print("4. 测试查询理解...")
        intent_classifier = IntentClassifier()
        entity_recognizer = EntityRecognizer()
        print("   查询理解模块初始化成功")
        
        # 测试评估
        print("5. 测试评估模块...")
        evaluator = RetrievalEvaluator()
        print("   评估模块初始化成功")
        
        print("\n✅ 所有简单测试通过！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_tests())
#!/usr/bin/env python3
"""
系统测试脚本
"""

import requests
import json
import os
from pathlib import Path

# 配置
BASE_URL = "http://127.0.0.1:8000"
TEST_DATA_DIR = "test_data"

def test_health_check():
    """测试健康检查"""
    print("🔍 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ 健康检查通过")
            print(f"   状态: {response.json()['status']}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_document_upload():
    """测试文档上传"""
    print("\n📄 测试文档上传...")
    
    # 创建测试目录
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    
    # 创建测试文件
    test_file = os.path.join(TEST_DATA_DIR, "test_document.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("这是一个测试文档。\n")
        f.write("RAG系统可以处理多种文档格式。\n")
        f.write("包括PDF、Word和TXT文件。\n")
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": ("test_document.txt", f, "text/plain")}
            response = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
        
        if response.status_code == 200:
            print("✅ 文档上传成功")
            doc_data = response.json()
            print(f"   文档ID: {doc_data['id']}")
            print(f"   文件名: {doc_data['filename']}")
            print(f"   分块数: {doc_data['chunk_count']}")
            return doc_data['id']
        else:
            print(f"❌ 文档上传失败: {response.status_code}")
            print(f"   错误: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 上传异常: {e}")
        return None

def test_document_list():
    """测试文档列表"""
    print("\n📋 测试文档列表...")
    try:
        response = requests.get(f"{BASE_URL}/api/documents/")
        if response.status_code == 200:
            documents = response.json()
            print(f"✅ 获取文档列表成功，共 {len(documents)} 个文档")
            for doc in documents:
                print(f"   - {doc['filename']} ({doc['file_type']})")
            return True
        else:
            print(f"❌ 获取文档列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def test_query():
    """测试智能问答"""
    print("\n🤖 测试智能问答...")
    try:
        query_data = {
            "question": "这个文档的主要内容是什么？",
            "use_history": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/chat/query",
            json=query_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 智能问答成功")
            print(f"   问题: {query_data['question']}")
            print(f"   回答: {result['answer'][:100]}...")
            print(f"   置信度: {result['confidence']}")
            print(f"   参考来源: {len(result['sources'])} 个")
            return True
        else:
            print(f"❌ 智能问答失败: {response.status_code}")
            print(f"   错误: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 问答异常: {e}")
        return False

def test_sessions():
    """测试会话管理"""
    print("\n💬 测试会话管理...")
    try:
        response = requests.get(f"{BASE_URL}/api/chat/sessions")
        if response.status_code == 200:
            sessions = response.json()
            print(f"✅ 获取会话列表成功，共 {len(sessions)} 个会话")
            for session in sessions:
                print(f"   - {session['title']} (ID: {session['id'][:8]}...)")
            return True
        else:
            print(f"❌ 获取会话列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 会话查询异常: {e}")
        return False

def test_stats():
    """测试统计信息"""
    print("\n📊 测试统计信息...")
    try:
        response = requests.get(f"{BASE_URL}/api/documents/stats/summary")
        if response.status_code == 200:
            stats = response.json()
            print("✅ 获取统计信息成功")
            print(f"   总文档数: {stats['total_documents']}")
            print(f"   总分块数: {stats['total_chunks']}")
            print(f"   总文件大小: {stats['total_size']} 字节")
            print(f"   文件类型: {stats['file_types']}")
            return True
        else:
            print(f"❌ 获取统计信息失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 统计查询异常: {e}")
        return False

def cleanup_test_data():
    """清理测试数据"""
    print("\n🧹 清理测试数据...")
    try:
        # 删除测试文件
        if os.path.exists(TEST_DATA_DIR):
            import shutil
            shutil.rmtree(TEST_DATA_DIR)
            print("✅ 测试数据已清理")
    except Exception as e:
        print(f"⚠️  清理失败: {e}")

def main():
    """主测试函数"""
    print("🚀 开始系统测试...")
    print("=" * 50)
    
    # 运行测试
    tests = [
        test_health_check,
        test_document_upload,
        test_document_list,
        test_query,
        test_sessions,
        test_stats
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append(False)
    
    # 清理
    cleanup_test_data()
    
    # 总结
    print("\n" + "=" * 50)
    print("📈 测试总结")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统运行正常。")
    else:
        print(f"\n⚠️  有 {total-passed} 个测试失败，请检查系统。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
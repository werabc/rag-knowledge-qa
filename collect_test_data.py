#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据收集脚本
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# 设置标准输出编码
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class TestDataCollector:
    """测试数据收集器"""
    
    def __init__(self, base_dir: str = "./test_data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.raw_dir.mkdir(exist_ok=True)
        self.processed_dir.mkdir(exist_ok=True)
        
        # 数据源配置
        self.data_sources = self._init_data_sources()
    
    def _init_data_sources(self) -> Dict[str, Any]:
        """初始化数据源配置"""
        return {
            "technical_docs": {
                "name": "技术文档",
                "description": "编程、API、算法文档",
                "formats": ["md", "txt", "pdf"],
                "sample_count": 20,
                "domains": ["programming", "api", "algorithm"]
            },
            "enterprise_knowledge": {
                "name": "企业知识库",
                "description": "产品手册、操作指南、政策文档",
                "formats": ["pdf", "docx", "txt"],
                "sample_count": 15,
                "domains": ["product", "policy", "guide"]
            },
            "academic_papers": {
                "name": "学术论文",
                "description": "研究论文、技术报告",
                "formats": ["pdf", "txt"],
                "sample_count": 10,
                "domains": ["research", "technical", "review"]
            },
            "general_knowledge": {
                "name": "通用知识",
                "description": "百科、问答、教程",
                "formats": ["json", "txt", "md"],
                "sample_count": 25,
                "domains": ["wiki", "qa", "tutorial"]
            }
        }
    
    async def collect_all_data(self):
        """收集所有数据"""
        print("开始收集测试数据...")
        print("=" * 50)
        
        all_data = {}
        
        for source_type, config in self.data_sources.items():
            print(f"\n收集 {config['name']} 数据...")
            try:
                data = await self._collect_source_data(source_type, config)
                all_data[source_type] = data
                print(f"✅ {config['name']} 收集完成: {len(data)} 条记录")
            except Exception as e:
                print(f"❌ {config['name']} 收集失败: {e}")
                all_data[source_type] = []
        
        # 保存收集的数据
        await self._save_collected_data(all_data)
        
        # 生成数据统计
        self._generate_data_statistics(all_data)
        
        print("\n" + "=" * 50)
        print("数据收集完成！")
        
        return all_data
    
    async def _collect_source_data(self, source_type: str, config: Dict) -> List[Dict]:
        """收集单个数据源的数据"""
        # 这里模拟数据收集，实际应该从真实数据源获取
        collected_data = []
        
        # 生成模拟数据
        for i in range(config["sample_count"]):
            document = await self._generate_sample_document(source_type, config, i)
            collected_data.append(document)
        
        return collected_data
    
    async def _generate_sample_document(self, source_type: str, config: Dict, index: int) -> Dict:
        """生成示例文档"""
        # 根据不同类型生成不同的模拟文档
        if source_type == "technical_docs":
            return await self._generate_technical_doc(config, index)
        elif source_type == "enterprise_knowledge":
            return await self._generate_enterprise_doc(config, index)
        elif source_type == "academic_papers":
            return await self._generate_academic_doc(config, index)
        elif source_type == "general_knowledge":
            return await self._generate_general_knowledge(config, index)
        else:
            return await self._generate_generic_doc(config, index)
    
    async def _generate_technical_doc(self, config: Dict, index: int) -> Dict:
        """生成技术文档"""
        # 技术文档模板
        templates = [
            {
                "title": f"Python编程指南 - 第{index+1}章",
                "content": f"""
# Python编程指南 - 第{index+1}章

## 概述
本章介绍Python编程的基础知识和高级特性。

## 主要内容
1. 变量和数据类型
2. 控制结构
3. 函数和模块
4. 面向对象编程

## 代码示例
```python
# 示例代码
def example_function():
    return "Hello, World!"
```

## 注意事项
- 遵循PEP8编码规范
- 使用类型提示提高代码可读性
- 编写单元测试确保代码质量
""",
                "metadata": {
                    "category": "programming",
                    "difficulty": "intermediate",
                    "language": "python"
                }
            },
            {
                "title": f"RESTful API设计最佳实践 - 第{index+1}部分",
                "content": f"""
# RESTful API设计最佳实践

## API设计原则
1. 使用标准HTTP方法
2. 资源命名规范
3. 状态码使用
4. 错误处理

## 接口设计示例
```
GET /api/v1/users/{id}
POST /api/v1/users
PUT /api/v1/users/{id}
DELETE /api/v1/users/{id}
```

## 认证和授权
- JWT Token认证
- OAuth2.0授权
- API密钥管理

## 性能优化
- 缓存策略
- 分页处理
- 限流机制
""",
                "metadata": {
                    "category": "api",
                    "difficulty": "advanced",
                    "format": "rest"
                }
            }
        ]
        
        template = templates[index % len(templates)]
        
        return {
            "id": f"tech_doc_{index}",
            "type": "technical",
            "title": template["title"],
            "content": template["content"],
            "metadata": template["metadata"],
            "source": "generated",
            "format": "markdown"
        }
    
    async def _generate_enterprise_doc(self, config: Dict, index: int) -> Dict:
        """生成企业文档"""
        templates = [
            {
                "title": f"产品使用手册 - {['用户管理', '数据报表', '系统设置'][index%3]}",
                "content": f"""
# 产品使用手册

## 功能概述
本手册介绍{['用户管理', '数据报表', '系统设置'][index%3]}功能的使用方法。

## 操作步骤
1. 登录系统
2. 导航到相关页面
3. 按照提示操作
4. 保存设置

## 注意事项
- 请确保权限充足
- 操作前建议备份数据
- 遇到问题请联系管理员

## 常见问题
Q: 如何重置密码？
A: 在个人设置页面点击"重置密码"按钮。

Q: 如何导出数据？
A: 在数据报表页面选择"导出"功能。
""",
                "metadata": {
                    "category": "product_manual",
                    "department": "技术部",
                    "version": "1.0"
                }
            }
        ]
        
        template = templates[index % len(templates)]
        
        return {
            "id": f"enterprise_doc_{index}",
            "type": "enterprise",
            "title": template["title"],
            "content": template["content"],
            "metadata": template["metadata"],
            "source": "generated",
            "format": "markdown"
        }
    
    async def _generate_academic_doc(self, config: Dict, index: int) -> Dict:
        """生成学术文档"""
        templates = [
            {
                "title": f"基于深度学习的自然语言处理研究 - 第{index+1}部分",
                "content": f"""
# 基于深度学习的自然语言处理研究

## 摘要
本文研究了深度学习在自然语言处理领域的应用。

## 1. 引言
自然语言处理是人工智能的重要分支...

## 2. 相关工作
### 2.1 传统方法
### 2.2 深度学习方法

## 3. 方法论
### 3.1 模型架构
### 3.2 训练策略

## 4. 实验结果
### 4.1 数据集
### 4.2 评估指标
### 4.3 结果分析

## 5. 结论
本研究证明了深度学习在NLP任务中的有效性。

## 参考文献
[1] Smith et al. (2023)
[2] Johnson et al. (2022)
""",
                "metadata": {
                    "category": "research",
                    "field": "nlp",
                    "year": 2024,
                    "authors": ["张三", "李四"]
                }
            }
        ]
        
        template = templates[index % len(templates)]
        
        return {
            "id": f"academic_doc_{index}",
            "type": "academic",
            "title": template["title"],
            "content": template["content"],
            "metadata": template["metadata"],
            "source": "generated",
            "format": "markdown"
        }
    
    async def _generate_general_knowledge(self, config: Dict, index: int) -> Dict:
        """生成通用知识文档"""
        templates = [
            {
                "title": f"人工智能基础知识 - {['机器学习', '深度学习', '自然语言处理'][index%3]}",
                "content": f"""
# 人工智能基础知识

## {['机器学习', '深度学习', '自然语言处理'][index%3]}简介

### 基本概念
{['机器学习', '深度学习', '自然语言处理'][index%3]}是人工智能的重要分支。

### 主要方法
1. 监督学习
2. 无监督学习
3. 强化学习

### 应用场景
- 图像识别
- 语音识别
- 自然语言处理
- 推荐系统

### 学习资源
- 在线课程
- 开源项目
- 技术博客
- 学术论文

## 实践建议
1. 从基础开始学习
2. 多做项目实践
3. 参与开源社区
4. 持续学习更新
""",
                "metadata": {
                    "category": "ai_basics",
                    "level": "beginner",
                    "topics": ["ai", "machine_learning", "deep_learning"]
                }
            }
        ]
        
        template = templates[index % len(templates)]
        
        return {
            "id": f"knowledge_doc_{index}",
            "type": "knowledge",
            "title": template["title"],
            "content": template["content"],
            "metadata": template["metadata"],
            "source": "generated",
            "format": "markdown"
        }
    
    async def _generate_generic_doc(self, config: Dict, index: int) -> Dict:
        """生成通用文档"""
        return {
            "id": f"generic_doc_{index}",
            "type": "generic",
            "title": f"通用文档 {index+1}",
            "content": f"这是第{index+1}个通用文档的内容。",
            "metadata": {"category": "general"},
            "source": "generated",
            "format": "text"
        }
    
    async def _save_collected_data(self, all_data: Dict[str, List[Dict]]):
        """保存收集的数据"""
        # 保存原始数据
        raw_file = self.raw_dir / "collected_data.json"
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"原始数据保存到: {raw_file}")
        
        # 按类型保存
        for source_type, data in all_data.items():
            type_file = self.raw_dir / f"{source_type}.json"
            with open(type_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 生成预处理后的数据
        processed_data = await self._preprocess_data(all_data)
        
        processed_file = self.processed_dir / "processed_data.json"
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        
        print(f"预处理数据保存到: {processed_file}")
    
    async def _preprocess_data(self, all_data: Dict[str, List[Dict]]) -> List[Dict]:
        """预处理数据"""
        processed_documents = []
        
        for source_type, documents in all_data.items():
            for doc in documents:
                processed_doc = await self._preprocess_document(doc)
                processed_documents.append(processed_doc)
        
        return processed_documents
    
    async def _preprocess_document(self, document: Dict) -> Dict:
        """预处理单个文档"""
        # 文本清洗
        cleaned_content = self._clean_text(document["content"])
        
        # 提取元数据
        metadata = self._extract_metadata(document)
        
        # 计算质量分数
        quality_score = self._calculate_quality_score(document)
        
        return {
            "id": document["id"],
            "type": document["type"],
            "title": document["title"],
            "content": cleaned_content,
            "original_content": document["content"],
            "metadata": metadata,
            "quality_score": quality_score,
            "source": document["source"],
            "format": document["format"]
        }
    
    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        import re
        
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符（保留中文和基本标点）
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、；：""''（）\[\]{}，\.\!\?\,\;\:\'\"\(\)\[\]\{\}]+', '', text)
        
        return text.strip()
    
    def _extract_metadata(self, document: Dict) -> Dict:
        """提取元数据"""
        metadata = document.get("metadata", {})
        
        # 添加通用元数据
        metadata.update({
            "content_length": len(document["content"]),
            "word_count": len(document["content"].split()),
            "has_code": "```" in document["content"],
            "has_list": any(line.strip().startswith(('1.', '2.', '-', '*')) 
                          for line in document["content"].split('\n'))
        })
        
        return metadata
    
    def _calculate_quality_score(self, document: Dict) -> float:
        """计算质量分数"""
        score = 0.0
        
        # 基于内容长度
        content_length = len(document["content"])
        if content_length > 100:
            score += 0.3
        if content_length > 500:
            score += 0.2
        
        # 基于结构
        if "```" in document["content"]:  # 包含代码
            score += 0.1
        if any(line.strip().startswith('#') for line in document["content"].split('\n')):  # 包含标题
            score += 0.1
        
        # 基于元数据
        metadata = document.get("metadata", {})
        if metadata:
            score += 0.1
        
        return min(score, 1.0)
    
    def _generate_data_statistics(self, all_data: Dict[str, List[Dict]]):
        """生成数据统计"""
        print("\n数据统计:")
        print("-" * 30)
        
        total_documents = 0
        total_content_length = 0
        
        for source_type, documents in all_data.items():
            doc_count = len(documents)
            total_documents += doc_count
            
            # 计算平均内容长度
            avg_length = 0
            if documents:
                avg_length = sum(len(doc["content"]) for doc in documents) / len(documents)
                total_content_length += sum(len(doc["content"]) for doc in documents)
            
            print(f"{source_type}: {doc_count} 个文档, 平均长度: {avg_length:.0f} 字符")
        
        print("-" * 30)
        print(f"总计: {total_documents} 个文档")
        print(f"总内容长度: {total_content_length:,} 字符")
        
        # 保存统计信息
        statistics = {
            "total_documents": total_documents,
            "total_content_length": total_content_length,
            "source_statistics": {
                source_type: {
                    "document_count": len(documents),
                    "avg_content_length": sum(len(doc["content"]) for doc in documents) / len(documents) if documents else 0
                }
                for source_type, documents in all_data.items()
            }
        }
        
        stats_file = self.processed_dir / "data_statistics.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2)
        
        print(f"统计信息保存到: {stats_file}")

async def main():
    """主函数"""
    print("RAG系统测试数据收集工具")
    print("=" * 50)
    
    collector = TestDataCollector()
    data = await collector.collect_all_data()
    
    print("\n数据收集完成！")
    print("下一步：")
    print("1. 检查 test_data/raw/ 目录中的原始数据")
    print("2. 检查 test_data/processed/ 目录中的预处理数据")
    print("3. 使用这些数据测试RAG系统")

if __name__ == "__main__":
    asyncio.run(main())
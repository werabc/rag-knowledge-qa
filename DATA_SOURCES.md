# RAG系统测试数据源收集方案

## 🎯 数据源选择原则

### 1. **数据统一性要求**
- **格式统一**: 优先选择结构化或半结构化数据
- **内容完整**: 数据质量高，内容完整
- **规模适中**: 适合测试和验证
- **多样性**: 覆盖不同领域和场景

### 2. **数据类型覆盖**
- **技术文档**: 编程、API、算法文档
- **企业知识**: 产品手册、操作指南、政策文档
- **学术论文**: 研究论文、技术报告
- **通用知识**: 百科、问答、教程

---

## 📚 推荐数据源

### 1. **技术文档类数据源**

#### 1.1 GitHub技术文档数据集
```yaml
数据源名称: GitHub AI Project Docs
来源: HuggingFace
链接: https://huggingface.co/datasets/meowterspace42/github-ai-project-docs
格式: Markdown, JSON
规模: 中等
特点:
  - 包含AI项目文档
  - 结构清晰
  - 适合技术问答测试
```

#### 1.2 技术写作数据集
```yaml
数据源名称: Technical Writing SFT 100k
来源: HuggingFace
链接: https://huggingface.co/datasets/stindardlogic/technical-writing-sft-100k
格式: JSON
规模: 10万条
特点:
  - 技术写作数据
  - 包含代码示例
  - 适合代码相关问答
```

#### 1.3 CoDocBench数据集
```yaml
数据源名称: CoDocBench
来源: Zenodo
链接: https://zenodo.org/records/14251623
格式: 多种格式
规模: 中等
特点:
  - 代码-文档对齐数据
  - 软件维护相关
  - 适合代码理解测试
```

### 2. **企业知识库类数据源**

#### 2.1 企业知识问答数据集
```yaml
数据源名称: Enterprise Knowledge QA Dataset
来源: HuggingFace
链接: https://huggingface.co/datasets/ozguragrali/enterprise-knowledge-qa-dataset-gemini-flash-for-t5-large
格式: JSON
规模: 中等
特点:
  - 企业知识问答
  - 多领域覆盖
  - 适合企业场景测试
```

#### 2.2 RAG多语料库数据集
```yaml
数据源名称: RAG-Multi-Corpus
来源: GitHub
链接: https://github.com/udayallu/RAG-Multi-Corpus
格式: 多种文档格式
规模: 多文档类型
特点:
  - 多格式文档
  - 企业级数据
  - 适合多格式处理测试
```

### 3. **中文文档类数据源**

#### 3.1 中文多文档问答数据集
```yaml
数据源名称: multi-doc-qa-zh-translated
来源: HuggingFace
链接: https://huggingface.co/datasets/yuyijiong/multi-doc-qa-zh-translated
格式: JSON
规模: 中等
特点:
  - 中文文档问答
  - 多文档场景
  - 适合中文处理测试
```

#### 3.2 十万个为什么中文版
```yaml
数据源名称: I Wonder Why Chinese
来源: HuggingFace
链接: https://huggingface.co/datasets/Mxode/I_Wonder_Why-Chinese
格式: JSON
规模: 中等
特点:
  - 中文问答数据
  - 知识性强
  - 适合知识问答测试
```

### 4. **RAG评测数据源**

#### 4.1 RAG评测基准数据集
```yaml
数据源名称: RAGAS Golden Dataset
来源: HuggingFace
链接: https://huggingface.co/datasets/dwb2023/ragas-golden-dataset-documents
格式: JSON
规模: 评测基准
特点:
  - RAG评测标准数据
  - 包含质量标注
  - 适合系统评测
```

#### 4.2 OmniEval金融RAG评测
```yaml
数据源名称: OmniEval
来源: GitHub
链接: https://github.com/RUC-NLPIR/OmniEval
格式: 多种格式
规模: 金融领域
特点:
  - 金融领域RAG评测
  - 多维度评估
  - 适合垂直领域测试
```

---

## 🎯 统一数据处理方案

### 1. **数据标准化处理**

#### 1.1 文档格式标准化
```python
class DataStandardizer:
    """数据标准化处理器"""
    
    standardization_rules = {
        "text_format": {
            "encoding": "UTF-8",
            "line_ending": "LF",
            "whitespace": "标准化"
        },
        "structure_format": {
            "headings": "Markdown格式",
            "lists": "标准列表格式",
            "tables": "Markdown表格"
        },
        "metadata_format": {
            "title": "文档标题",
            "source": "数据来源",
            "category": "文档分类",
            "timestamp": "时间戳"
        }
    }
```

#### 1.2 数据清洗流程
```python
class DataCleaner:
    """数据清洗处理器"""
    
    cleaning_pipeline = [
        "remove_html_tags",      # 移除HTML标签
        "normalize_unicode",     # 标准化Unicode
        "fix_encoding",          # 修复编码问题
        "remove_special_chars",  # 移除特殊字符
        "normalize_whitespace",  # 标准化空白字符
        "remove_duplicates",     # 移除重复内容
        "validate_content"       # 验证内容完整性
    ]
```

### 2. **数据质量检查**

#### 2.1 质量检查指标
```python
class QualityChecker:
    """数据质量检查器"""
    
    quality_metrics = {
        "completeness": {
            "min_word_count": 100,      # 最少字数
            "max_word_count": 10000,    # 最多字数
            "required_sections": ["title", "content"]  # 必需章节
        },
        "consistency": {
            "format_consistency": 0.9,  # 格式一致性
            "structure_consistency": 0.8  # 结构一致性
        },
        "accuracy": {
            "encoding_accuracy": 0.99,  # 编码准确性
            "content_accuracy": 0.95    # 内容准确性
        }
    }
```

#### 2.2 质量评估流程
```python
class QualityAssessor:
    """质量评估器"""
    
    assessment_steps = [
        "automated_check",     # 自动化检查
        "statistical_analysis", # 统计分析
        "sample_verification",  # 抽样验证
        "quality_scoring",      # 质量评分
        "report_generation"     # 报告生成
    ]
```

---

## 📋 数据收集脚本

### 1. **自动下载脚本**
```python
#!/usr/bin/env python3
"""
数据源自动下载脚本
"""

import os
import requests
import zipfile
import json
from pathlib import Path

class DataSourceDownloader:
    """数据源下载器"""
    
    def __init__(self, base_dir="./data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # 数据源配置
        self.data_sources = {
            "github_ai_docs": {
                "url": "https://huggingface.co/datasets/meowterspace42/github-ai-project-docs",
                "format": "json",
                "size": "medium"
            },
            "enterprise_knowledge": {
                "url": "https://huggingface.co/datasets/ozguragrali/enterprise-knowledge-qa-dataset",
                "format": "json",
                "size": "medium"
            },
            "chinese_qa": {
                "url": "https://huggingface.co/datasets/yuyijiong/multi-doc-qa-zh-translated",
                "format": "json",
                "size": "medium"
            }
        }
    
    def download_all(self):
        """下载所有数据源"""
        for source_name, config in self.data_sources.items():
            print(f"下载数据源: {source_name}")
            try:
                self.download_source(source_name, config)
                print(f"✅ {source_name} 下载完成")
            except Exception as e:
                print(f"❌ {source_name} 下载失败: {e}")
    
    def download_source(self, source_name, config):
        """下载单个数据源"""
        # 这里实现具体的下载逻辑
        pass
```

### 2. **数据预处理脚本**
```python
#!/usr/bin/env python3
"""
数据预处理脚本
"""

import json
import re
from typing import List, Dict

class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(self):
        self.cleaning_rules = {
            "remove_html": re.compile(r'<[^>]+>'),
            "normalize_space": re.compile(r'\s+'),
            "remove_special": re.compile(r'[^\w\s\u4e00-\u9fff]'),
        }
    
    def preprocess_document(self, document: Dict) -> Dict:
        """预处理单个文档"""
        preprocessed = {
            "id": document.get("id", ""),
            "title": self.clean_text(document.get("title", "")),
            "content": self.clean_text(document.get("content", "")),
            "metadata": self.extract_metadata(document),
            "quality_score": self.assess_quality(document)
        }
        
        return preprocessed
    
    def clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""
        
        # 移除HTML标签
        text = self.cleaning_rules["remove_html"].sub('', text)
        
        # 标准化空白字符
        text = self.cleaning_rules["normalize_space"].sub(' ', text)
        
        # 移除特殊字符
        text = self.cleaning_rules["remove_special"].sub('', text)
        
        return text.strip()
```

---

## 🎯 测试数据集构建

### 1. **分层测试数据集**
```python
class TestDatasetBuilder:
    """测试数据集构建器"""
    
    def build_test_datasets(self):
        """构建分层测试数据集"""
        datasets = {
            "basic_test": {
                "description": "基础功能测试",
                "size": "small",
                "documents": 10,
                "queries": 20,
                "format": "json"
            },
            "performance_test": {
                "description": "性能测试",
                "size": "medium",
                "documents": 100,
                "queries": 200,
                "format": "json"
            },
            "comprehensive_test": {
                "description": "综合测试",
                "size": "large",
                "documents": 1000,
                "queries": 2000,
                "format": "json"
            }
        }
        
        return datasets
```

### 2. **多领域测试数据**
```python
class MultiDomainTestData:
    """多领域测试数据"""
    
    domain_config = {
        "technology": {
            "description": "技术文档领域",
            "document_types": ["api_doc", "tutorial", "code_example"],
            "query_types": ["how_to", "explanation", "troubleshooting"]
        },
        "business": {
            "description": "商业文档领域",
            "document_types": ["report", "policy", "manual"],
            "query_types": ["factual", "procedural", "comparative"]
        },
        "academic": {
            "description": "学术文档领域",
            "document_types": ["paper", "thesis", "review"],
            "query_types": ["theoretical", "methodological", "critical"]
        }
    }
```

---

## 📊 数据使用建议

### 1. **测试阶段数据使用**
```
阶段1：功能验证 → 使用小型数据集（10-50文档）
阶段2：性能测试 → 使用中型数据集（100-500文档）
阶段3：综合测试 → 使用大型数据集（1000+文档）
```

### 2. **数据质量要求**
- **完整性**: 文档内容完整，无缺失
- **准确性**: 内容准确，无错误
- **一致性**: 格式统一，结构清晰
- **多样性**: 覆盖不同场景和类型

### 3. **数据处理建议**
- **预处理**: 统一格式，清洗数据
- **质量检查**: 验证数据质量
- **分层测试**: 不同规模测试
- **持续更新**: 定期更新数据

---

## 🚀 快速开始

### 1. **下载数据**
```bash
# 创建数据目录
mkdir -p data/raw data/processed

# 下载示例数据源
python download_data.py
```

### 2. **预处理数据**
```bash
# 预处理数据
python preprocess_data.py

# 验证数据质量
python validate_data.py
```

### 3. **运行测试**
```bash
# 使用预处理数据进行测试
python test_with_data.py
```

---

## 📝 总结

### 数据源特点：
1. **统一性**: 所有数据源都提供标准化格式
2. **多样性**: 覆盖技术、企业、学术等多个领域
3. **质量保证**: 数据质量高，适合测试
4. **易于获取**: 大部分数据源公开可用

### 使用建议：
1. **从小规模开始**: 先用小数据集验证功能
2. **逐步扩展**: 根据需要扩展数据规模
3. **质量优先**: 确保数据质量再追求规模
4. **持续优化**: 根据测试结果优化数据处理

**这些数据源将为您的RAG系统测试提供坚实的数据基础！** 📊✨
# 真实RAG测试数据源列表

## 🎯 数据源分类

### 1. **HuggingFace数据集**

#### 1.1 中文数据集
```yaml
数据集名称: multi-doc-qa-zh-translated
链接: https://huggingface.co/datasets/yuyijiong/multi-doc-qa-zh-translated
格式: JSON
规模: 中等
特点: 中文多文档问答数据
下载方式: HuggingFace Hub
```

```yaml
数据集名称: I_Wonder_Why-Chinese
链接: https://huggingface.co/datasets/Mxode/I_Wonder_Why-Chinese
格式: JSON
规模: 中等
特点: 中文问答数据
下载方式: HuggingFace Hub
```

#### 1.2 英文数据集
```yaml
数据集名称: enterprise-knowledge-qa-dataset
链接: https://huggingface.co/datasets/ozguragrali/enterprise-knowledge-qa-dataset-gemini-flash-for-t5-large
格式: JSON
规模: 中等
特点: 企业知识问答数据
下载方式: HuggingFace Hub
```

```yaml
数据集名称: ragas-golden-dataset-documents
链接: https://huggingface.co/datasets/dwb2023/ragas-golden-dataset-documents
格式: JSON
规模: 评测基准
特点: RAG评测标准数据
下载方式: HuggingFace Hub
```

### 2. **GitHub数据集**

#### 2.1 技术文档数据集
```yaml
数据集名称: RAG-Multi-Corpus
链接: https://github.com/udayallu/RAG-Multi-Corpus
格式: 多种格式
规模: 多文档类型
特点: 多格式企业文档
下载方式: Git clone
```

```yaml
数据集名称: OmniEval
链接: https://github.com/RUC-NLPIR/OmniEval
格式: 多种格式
规模: 金融领域
特点: 金融RAG评测数据
下载方式: Git clone
```

### 3. **学术数据集**

#### 3.1 代码文档数据集
```yaml
数据集名称: CoDocBench
链接: https://zenodo.org/records/14251623
格式: 多种格式
规模: 中等
特点: 代码-文档对齐数据
下载方式: Zenodo下载
```

### 4. **其他数据源**

#### 4.1 技术写作数据集
```yaml
数据集名称: technical-writing-sft-100k
链接: https://huggingface.co/datasets/stindardlogic/technical-writing-sft-100k
格式: JSON
规模: 10万条
特点: 技术写作数据
下载方式: HuggingFace Hub
```

---

## 📋 数据下载脚本

### 1. **HuggingFace数据集下载**
```python
#!/usr/bin/env python3
"""
HuggingFace数据集下载脚本
"""

from datasets import load_dataset
import json
from pathlib import Path

class HuggingFaceDataDownloader:
    """HuggingFace数据集下载器"""
    
    def __init__(self, save_dir: str = "./data/huggingface"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def download_dataset(self, dataset_name: str, subset: str = None):
        """下载数据集"""
        print(f"下载数据集: {dataset_name}")
        
        try:
            # 加载数据集
            if subset:
                dataset = load_dataset(dataset_name, subset)
            else:
                dataset = load_dataset(dataset_name)
            
            # 保存数据集
            save_path = self.save_dir / dataset_name.replace("/", "_")
            save_path.mkdir(exist_ok=True)
            
            # 保存为JSON格式
            for split_name, split_data in dataset.items():
                split_file = save_path / f"{split_name}.json"
                
                # 转换为列表格式
                data_list = [item for item in split_data]
                
                with open(split_file, 'w', encoding='utf-8') as f:
                    json.dump(data_list, f, ensure_ascii=False, indent=2)
                
                print(f"  保存 {split_name}: {len(data_list)} 条记录")
            
            print(f"✅ 数据集 {dataset_name} 下载完成")
            return True
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            return False
    
    def download_all_datasets(self):
        """下载所有推荐数据集"""
        datasets_to_download = [
            ("yuyijiong/multi-doc-qa-zh-translated", None),
            ("Mxode/I_Wonder_Why-Chinese", None),
            ("ozguragrali/enterprise-knowledge-qa-dataset-gemini-flash-for-t5-large", None),
            ("dwb2023/ragas-golden-dataset-documents", None),
            ("stindardlogic/technical-writing-sft-100k", None),
        ]
        
        for dataset_name, subset in datasets_to_download:
            self.download_dataset(dataset_name, subset)
```

### 2. **GitHub数据集下载**
```python
#!/usr/bin/env python3
"""
GitHub数据集下载脚本
"""

import subprocess
import shutil
from pathlib import Path

class GitHubDataDownloader:
    """GitHub数据集下载器"""
    
    def __init__(self, save_dir: str = "./data/github"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def clone_repository(self, repo_url: str, repo_name: str):
        """克隆GitHub仓库"""
        print(f"克隆仓库: {repo_name}")
        
        try:
            repo_path = self.save_dir / repo_name
            
            if repo_path.exists():
                print(f"  仓库已存在，跳过克隆")
                return True
            
            # 克隆仓库
            subprocess.run([
                "git", "clone", repo_url, str(repo_path)
            ], check=True, capture_output=True)
            
            print(f"✅ 仓库 {repo_name} 克隆完成")
            return True
            
        except Exception as e:
            print(f"❌ 克隆失败: {e}")
            return False
    
    def download_all_repositories(self):
        """下载所有推荐仓库"""
        repositories = [
            ("https://github.com/udayallu/RAG-Multi-Corpus.git", "RAG-Multi-Corpus"),
            ("https://github.com/RUC-NLPIR/OmniEval.git", "OmniEval"),
        ]
        
        for repo_url, repo_name in repositories:
            self.clone_repository(repo_url, repo_name)
```

---

## 🎯 数据统一处理方案

### 1. **数据格式标准化**

#### 1.1 统一数据格式
```python
class DataFormatStandardizer:
    """数据格式标准化器"""
    
    def standardize_document(self, document: dict) -> dict:
        """标准化文档格式"""
        standardized = {
            "id": self._generate_id(document),
            "title": self._extract_title(document),
            "content": self._extract_content(document),
            "metadata": self._extract_metadata(document),
            "source": self._extract_source(document),
            "format": self._detect_format(document),
            "timestamp": self._get_timestamp()
        }
        
        return standardized
    
    def _generate_id(self, document: dict) -> str:
        """生成文档ID"""
        import hashlib
        import time
        
        # 基于内容生成唯一ID
        content = str(document.get("content", ""))
        hash_obj = hashlib.md5(content.encode())
        
        return f"doc_{hash_obj.hexdigest()[:8]}_{int(time.time())}"
    
    def _extract_title(self, document: dict) -> str:
        """提取标题"""
        # 尝试多种字段名
        title_fields = ["title", "name", "heading", "subject"]
        
        for field in title_fields:
            if field in document and document[field]:
                return str(document[field])
        
        # 从内容中提取标题
        content = str(document.get("content", ""))
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                return line[:100]  # 取前100个字符作为标题
        
        return "无标题文档"
```

#### 1.2 内容清洗标准化
```python
class ContentCleanerStandardizer:
    """内容清洗标准化器"""
    
    def clean_content(self, content: str) -> str:
        """清洗内容"""
        import re
        
        if not content:
            return ""
        
        # 1. 移除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 2. 标准化空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 3. 移除特殊字符（保留中文和基本标点）
        content = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、；：""''（）\[\]{}，\.\!\?\,\;\:\'\"\(\)\[\]\{\}]+', '', content)
        
        # 4. 标准化标点符号
        content = content.replace('，', ',').replace('。', '.').replace('！', '!').replace('？', '?')
        
        return content.strip()
```

---

## 📊 数据质量检查

### 1. **质量检查脚本**
```python
#!/usr/bin/env python3
"""
数据质量检查脚本
"""

import json
from pathlib import Path
from typing import List, Dict

class DataQualityChecker:
    """数据质量检查器"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
    
    def check_data_quality(self, data_file: str) -> Dict:
        """检查数据质量"""
        data = self._load_data(data_file)
        
        quality_report = {
            "total_documents": len(data),
            "quality_metrics": self._calculate_quality_metrics(data),
            "issues": self._identify_issues(data),
            "recommendations": self._generate_recommendations(data)
        }
        
        return quality_report
    
    def _load_data(self, data_file: str) -> List[Dict]:
        """加载数据"""
        file_path = self.data_dir / data_file
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _calculate_quality_metrics(self, data: List[Dict]) -> Dict:
        """计算质量指标"""
        metrics = {
            "completeness": self._check_completeness(data),
            "consistency": self._check_consistency(data),
            "accuracy": self._check_accuracy(data),
            "diversity": self._check_diversity(data)
        }
        
        return metrics
    
    def _check_completeness(self, data: List[Dict]) -> float:
        """检查完整性"""
        complete_docs = 0
        
        for doc in data:
            if (doc.get("title") and 
                doc.get("content") and 
                len(doc.get("content", "")) > 100):
                complete_docs += 1
        
        return complete_docs / len(data) if data else 0
    
    def _check_consistency(self, data: List[Dict]) -> float:
        """检查一致性"""
        consistent_docs = 0
        
        for doc in data:
            # 检查格式一致性
            if (doc.get("id") and 
                doc.get("title") and 
                doc.get("content") and 
                doc.get("metadata")):
                consistent_docs += 1
        
        return consistent_docs / len(data) if data else 0
    
    def _check_accuracy(self, data: List[Dict]) -> float:
        """检查准确性"""
        accurate_docs = 0
        
        for doc in data:
            # 检查内容准确性
            content = doc.get("content", "")
            
            # 简单检查：内容不为空且长度合理
            if content and 100 < len(content) < 10000:
                accurate_docs += 1
        
        return accurate_docs / len(data) if data else 0
    
    def _check_diversity(self, data: List[Dict]) -> float:
        """检查多样性"""
        types = set()
        categories = set()
        
        for doc in data:
            types.add(doc.get("type", "unknown"))
            categories.add(doc.get("metadata", {}).get("category", "unknown"))
        
        # 多样性分数 = 不同类型数量 / 总文档数量（归一化）
        type_diversity = len(types) / 10  # 假设最多10种类型
        category_diversity = len(categories) / 20  # 假设最多20种类别
        
        return (type_diversity + category_diversity) / 2
    
    def _identify_issues(self, data: List[Dict]) -> List[Dict]:
        """识别问题"""
        issues = []
        
        for i, doc in enumerate(data):
            # 检查缺失字段
            missing_fields = []
            for field in ["id", "title", "content"]:
                if not doc.get(field):
                    missing_fields.append(field)
            
            if missing_fields:
                issues.append({
                    "document_index": i,
                    "issue_type": "missing_fields",
                    "details": missing_fields
                })
            
            # 检查内容质量问题
            content = doc.get("content", "")
            if len(content) < 50:
                issues.append({
                    "document_index": i,
                    "issue_type": "short_content",
                    "details": f"内容长度: {len(content)}"
                })
        
        return issues
    
    def _generate_recommendations(self, data: List[Dict]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于质量指标生成建议
        completeness = self._check_completeness(data)
        if completeness < 0.8:
            recommendations.append("建议增加文档内容的完整性")
        
        consistency = self._check_consistency(data)
        if consistency < 0.9:
            recommendations.append("建议统一文档格式和结构")
        
        diversity = self._check_diversity(data)
        if diversity < 0.5:
            recommendations.append("建议增加文档类型的多样性")
        
        return recommendations
```

---

## 🚀 快速开始指南

### 1. **下载推荐数据集**
```bash
# 安装HuggingFace库
pip install datasets

# 运行下载脚本
python download_huggingface_data.py

# 下载GitHub仓库
python download_github_data.py
```

### 2. **处理和标准化数据**
```bash
# 标准化数据格式
python standardize_data.py

# 清洗数据内容
python clean_data.py

# 检查数据质量
python check_data_quality.py
```

### 3. **使用数据进行测试**
```bash
# 使用处理后的数据测试RAG系统
python test_rag_with_data.py
```

---

## 📋 推荐测试数据集组合

### 1. **基础测试组合**
```yaml
组合名称: 基础功能测试
数据源:
  - multi-doc-qa-zh-translated (中文问答)
  - enterprise-knowledge-qa-dataset (企业知识)
规模: 100-200文档
用途: 验证基本功能
```

### 2. **性能测试组合**
```yaml
组合名称: 性能压力测试
数据源:
  - technical-writing-sft-100k (技术文档)
  - RAG-Multi-Corpus (多格式文档)
规模: 500-1000文档
用途: 测试系统性能
```

### 3. **综合测试组合**
```yaml
组合名称: 综合功能测试
数据源:
  - 所有推荐数据集
  - 自定义测试数据
规模: 1000+文档
用途: 全面功能测试
```

---

## 🎯 数据使用建议

### 1. **测试阶段建议**
- **开发阶段**: 使用小型数据集（50-100文档）
- **测试阶段**: 使用中型数据集（200-500文档）
- **生产验证**: 使用大型数据集（1000+文档）

### 2. **数据质量要求**
- **完整性**: 文档内容完整，无缺失
- **准确性**: 内容准确，无错误
- **一致性**: 格式统一，结构清晰
- **多样性**: 覆盖不同领域和类型

### 3. **数据处理流程**
1. **下载数据**: 从推荐数据源下载
2. **格式标准化**: 统一数据格式
3. **内容清洗**: 清洗和预处理内容
4. **质量检查**: 验证数据质量
5. **分层测试**: 不同规模测试

---

## 📝 总结

### 推荐数据源特点：
1. **多样性**: 覆盖中文、英文、技术、企业等多个领域
2. **质量保证**: 数据质量高，适合测试
3. **易于获取**: 大部分数据源公开可用
4. **格式统一**: 提供标准化格式

### 数据处理建议：
1. **从简单开始**: 先用小数据集验证功能
2. **逐步扩展**: 根据需要扩展数据规模
3. **质量优先**: 确保数据质量再追求规模
4. **持续优化**: 根据测试结果优化数据处理

**这些数据源将为您的RAG系统测试提供全面的数据支持！** 📊✨
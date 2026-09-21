# 详细RAG系统实现

## 🎯 系统概述

这是一个完整实现的RAG（检索增强生成）系统，包含了详细的召回策略、分块策略、重排序机制和评估框架。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户查询                              │
├─────────────────────────────────────────────────────────┤
│                 查询理解层                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │  意图识别   │ │  实体识别   │ │  查询扩展   │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
├─────────────────────────────────────────────────────────┤
│                 多路召回层                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │  向量召回   │ │  BM25召回   │ │  结构化召回  │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
├─────────────────────────────────────────────────────────┤
│                 重排序层                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │Cross-Encoder│ │  多样性重排  │ │  查询扩展   │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
├─────────────────────────────────────────────────────────┤
│                 上下文构建层                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │  质量感知   │ │  层级上下文  │ │  动态窗口   │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
├─────────────────────────────────────────────────────────┤
│                 生成与评估层                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │  LLM生成   │ │  评估框架   │ │  A/B测试    │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
└─────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
D:\rag\
├── app/
│   ├── core/
│   │   └── config.py                 # 详细配置管理
│   ├── services/
│   │   ├── chunking/                 # 分块策略模块
│   │   │   ├── base.py              # 分块基类
│   │   │   ├── fixed_size.py        # 固定大小分块
│   │   │   ├── semantic.py          # 语义分块
│   │   │   ├── structural.py        # 结构感知分块
│   │   │   └── adaptive.py          # 自适应分块
│   │   ├── retrieval/                # 召回策略模块
│   │   │   ├── base.py              # 召回基类
│   │   │   ├── vector_retriever.py  # 向量召回
│   │   │   ├── bm25_retriever.py    # BM25召回
│   │   │   └── structural_retriever.py # 结构化召回
│   │   ├── reranking/                # 重排序模块
│   │   │   ├── base.py              # 重排序基类
│   │   │   ├── cross_encoder.py     # Cross-Encoder重排序
│   │   │   └── diversity.py         # 多样性重排序
│   │   ├── query_understanding/      # 查询理解模块
│   │   │   ├── intent_classifier.py # 意图识别
│   │   │   ├── entity_recognizer.py # 实体识别
│   │   │   └── query_expander.py    # 查询扩展
│   │   ├── evaluation/               # 评估模块
│   │   │   └── retrieval_evaluator.py # 检索质量评估
│   │   └── rag_service.py           # RAG核心服务
│   └── main.py                      # FastAPI应用入口
├── requirements_detailed.txt        # 详细依赖包
├── test_detailed_system.py          # 系统测试脚本
├── .env.detailed                    # 详细配置文件
└── README_DETAILED.md               # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements_detailed.txt
```

### 2. 配置系统

```bash
# 复制配置文件
copy .env.detailed .env

# 编辑配置文件，根据需要调整参数
```

### 3. 运行测试

```bash
# 运行详细系统测试
python test_detailed_system.py
```

### 4. 启动服务

```bash
# 启动FastAPI服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🧩 模块详解

### 1. 分块策略模块

#### 固定大小分块 (`FixedSizeChunker`)
- **原理**: 按固定字符数分割，支持重叠
- **参数**: `chunk_size`, `chunk_overlap`, `separators`
- **适用场景**: 结构简单的文档

#### 语义分块 (`SemanticChunker`)
- **原理**: 基于句子语义相似度分割
- **参数**: `similarity_threshold`, `min_sentences`
- **优势**: 保持语义完整性

#### 结构感知分块 (`StructureAwareChunker`)
- **原理**: 保持文档结构层次
- **参数**: `preserve_structure`
- **优势**: 适合技术文档、学术论文

#### 自适应分块 (`AdaptiveChunker`)
- **原理**: 根据内容重要性动态调整分块大小
- **参数**: `min_size`, `max_size`
- **优势**: 重要部分更精细，普通部分更粗略

### 2. 召回策略模块

#### 向量召回 (`VectorRetriever`)
- **原理**: 基于语义相似度的稠密向量检索
- **参数**: `similarity_threshold`, `search_params`
- **优势**: 理解语义相似性

#### BM25召回 (`BM25Retriever`)
- **原理**: 基于词频和文档频率的稀疏检索
- **参数**: `k1`, `b` (BM25参数)
- **优势**: 精确匹配效果好

#### 结构化召回 (`StructuralRetriever`)
- **原理**: 基于文档结构的检索
- **参数**: `document_parser`
- **优势**: 支持标题、章节检索

### 3. 重排序模块

#### Cross-Encoder重排序 (`CrossEncoderReranker`)
- **原理**: 使用BERT等模型计算查询-文档相关性
- **参数**: `model_name`, `batch_size`
- **优势**: 精度高，适合重排序

#### 多样性重排序 (`DiversityReranker`)
- **原理**: 平衡相关性和多样性
- **参数**: `lambda_param`, `diversity_metric`
- **算法**: MMR (最大边际相关性), DPP (行列式点过程)

### 4. 查询理解模块

#### 意图识别 (`IntentClassifier`)
- **支持意图**: 事实性、解释性、操作性、比较性、探索性
- **方法**: 基于规则匹配和权重计算

#### 实体识别 (`EntityRecognizer`)
- **支持实体**: 人物、组织、地点、时间、数字、技术、概念
- **方法**: 正则表达式匹配

#### 查询扩展 (`QueryExpander`)
- **扩展策略**: 同义词扩展、上下位词扩展、LLM重写
- **参数**: `expansion_factor`

### 5. 评估模块

#### 检索质量评估 (`RetrievalEvaluator`)
- **评估指标**: Precision@k, Recall@k, NDCG@k, MRR, MAP, Hit Rate
- **批量评估**: 支持批量查询评估

## 📊 配置参数详解

### 分块参数
```python
CHUNKING_STRATEGY = "semantic"  # 分块策略
CHUNK_SIZE = 1024              # 分块大小
CHUNK_OVERLAP = 100            # 分块重叠
MIN_CHUNK_SIZE = 200           # 最小分块大小
MAX_CHUNK_SIZE = 2000          # 最大分块大小
```

### 召回参数
```python
RECALL_STRATEGIES = {
    "vector": True,      # 启用向量召回
    "bm25": True,        # 启用BM25召回
    "structural": True,  # 启用结构化召回
    "graph": False       # 禁用图谱召回
}

VECTOR_TOP_K = 10       # 向量召回数量
BM25_TOP_K = 10         # BM25召回数量
BM25_K1 = 1.5           # BM25参数k1
BM25_B = 0.75           # BM25参数b
```

### 重排序参数
```python
RERANKING_ENABLED = True        # 启用重排序
RERANKING_TOP_K = 10            # 重排序后返回数量
DIVERSITY_LAMBDA = 0.7          # MMR参数
```

### 查询理解参数
```python
QUERY_EXPANSION_ENABLED = True   # 启用查询扩展
QUERY_EXPANSION_FACTOR = 3       # 扩展因子
```

## 🧪 测试说明

### 运行完整测试
```bash
python test_detailed_system.py
```

### 测试内容
1. **分块策略测试**: 测试四种分块策略的效果
2. **召回策略测试**: 测试BM25召回的准确性
3. **重排序策略测试**: 测试Cross-Encoder和多样性重排序
4. **查询理解测试**: 测试意图识别、实体识别、查询扩展
5. **评估模块测试**: 测试各种评估指标的计算

## 🔧 扩展指南

### 添加新的分块策略
```python
class NewChunker(BaseChunker):
    async def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        # 实现新的分块逻辑
        pass
```

### 添加新的召回策略
```python
class NewRetriever(BaseRetriever):
    async def retrieve(self, query: str, **kwargs) -> List[RetrievalResult]:
        # 实现新的召回逻辑
        pass
```

### 添加新的重排序策略
```python
class NewReranker(BaseReranker):
    async def rerank(self, query: str, candidates: List[Dict], 
                    top_k: int = None, **kwargs) -> List[Dict]:
        # 实现新的重排序逻辑
        pass
```

## 📈 性能优化建议

### 1. 分块优化
- 使用语义分块提高召回质量
- 根据文档类型选择合适的分块策略
- 调整分块大小和重叠参数

### 2. 召回优化
- 组合多种召回策略提高召回率
- 调整向量检索参数平衡精度和速度
- 使用预过滤减少不必要的计算

### 3. 重排序优化
- 使用轻量级Cross-Encoder模型
- 缓存嵌入向量减少重复计算
- 并行处理多个查询

### 4. 系统优化
- 使用异步处理提高并发性能
- 实现缓存机制减少重复计算
- 监控系统性能并持续优化

## 🎯 最佳实践

### 1. 分块策略选择
- **简单文档**: 使用固定大小分块
- **技术文档**: 使用结构感知分块
- **长文档**: 使用语义分块或自适应分块

### 2. 召回策略组合
- **通用场景**: 向量召回 + BM25召回
- **精确匹配**: BM25召回为主
- **语义理解**: 向量召回为主

### 3. 重排序策略
- **高精度要求**: 使用Cross-Encoder重排序
- **多样性要求**: 使用MMR多样性重排序
- **平衡场景**: 级联重排序

### 4. 评估策略
- **离线评估**: 使用标注数据集评估
- **在线评估**: A/B测试和用户反馈
- **持续监控**: 监控关键指标变化

## 🔗 相关资源

- [LangChain文档](https://python.langchain.com/)
- [Sentence Transformers文档](https://www.sbert.net/)
- [ChromaDB文档](https://docs.trychroma.com/)
- [BM25算法详解](https://en.wikipedia.org/wiki/Okapi_BM25)
- [MMR算法详解](https://en.wikipedia.org/wiki/Maximal_marginal_relevance)

## 📝 更新日志

### v2.0.0 (当前版本)
- ✅ 实现四种分块策略
- ✅ 实现三种召回策略
- ✅ 实现两种重排序策略
- ✅ 实现查询理解模块
- ✅ 实现评估框架
- ✅ 完整的配置管理系统
- ✅ 详细的测试脚本

### 计划功能
- 🔄 集成真正的LLM生成
- 🔄 实现知识图谱召回
- 🔄 添加A/B测试框架
- 🔄 实现性能监控
- 🔄 添加更多评估指标

---

**注意**: 这是一个详细实现的RAG系统，包含了生产环境所需的各种功能。根据实际需求，可以进一步优化和扩展各个模块。
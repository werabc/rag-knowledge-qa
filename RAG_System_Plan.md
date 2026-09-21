# 企业知识库问答系统 - RAG Agent 规划方案

## 🎯 项目概述

基于Python + FastAPI的企业知识库问答系统，支持PDF、Word、TXT等文档的智能问答。

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户界面 (Web/CLI)                     │
├─────────────────────────────────────────────────────────┤
│                   API层 (FastAPI)                        │
├─────────────────────────────────────────────────────────┤
│              RAG处理层 (LangChain/LlamaIndex)            │
├─────────────────────────────────────────────────────────┤
│                 向量数据库 (Chroma/Milvus)               │
├─────────────────────────────────────────────────────────┤
│                 文档处理 (PyPDF2, python-docx)           │
├─────────────────────────────────────────────────────────┤
│                 嵌入模型 (OpenAI/本地模型)               │
└─────────────────────────────────────────────────────────┘
```

## 📦 核心组件选择

### 1. RAG框架
- **LangChain**: 生态丰富，组件多，适合快速开发
- **LlamaIndex**: 专注于数据连接和索引，性能优化好
- **推荐**: 使用 **LangChain** 作为主要框架，因为它的文档和社区支持更好

### 2. 向量数据库
- **Chroma**: 轻量级，易于集成，适合本地开发
- **Milvus**: 分布式，高性能，适合生产环境
- **推荐**: 开发阶段使用 **Chroma**，生产环境可迁移到 **Milvus**

### 3. 嵌入模型
- **OpenAI Embeddings**: 效果好，需要API密钥
- **本地模型**: 如 `sentence-transformers`，无需网络，隐私性好
- **推荐**: 先用 **OpenAI** 快速验证，后考虑本地模型

### 4. 文档处理
- **PyPDF2**: 处理PDF文件
- **python-docx**: 处理Word文档
- **Unstructured**: 支持多种文档格式

## 🚀 项目结构

```
D:\rag\
├── 📁 app/
│   ├── __init__.py
│   ├── main.py              # FastAPI应用入口
│   ├── config.py            # 配置管理
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── services/            # 业务服务
│   │   ├── __init__.py
│   │   ├── document_service.py    # 文档处理服务
│   │   ├── rag_service.py         # RAG核心服务
│   │   └── vector_store.py        # 向量存储服务
│   ├── api/                 # API路由
│   │   ├── __init__.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── documents.py       # 文档管理API
│   │       └── chat.py            # 问答API
│   └── utils/               # 工具函数
│       ├── __init__.py
│       └── document_loader.py     # 文档加载器
├── 📁 data/                 # 文档存储目录
├── 📁 vector_db/            # 向量数据库存储
├── 📁 tests/                # 测试文件
├── 📁 docs/                 # 项目文档
├── 📄 requirements.txt      # 依赖包列表
├── 📄 .env.example          # 环境变量示例
├── 📄 README.md             # 项目说明
├── 📄 setup.py              # 项目安装配置
└── 📄 run.py                # 启动脚本
```

## 📋 依赖包清单

### 核心依赖
```txt
# Web框架
fastapi==0.104.1
uvicorn[standard]==0.24.0

# RAG框架
langchain==0.0.340
langchain-community==0.0.6
langchain-core==0.0.6

# 向量数据库
chromadb==0.4.18
# milvus==2.3.4  # 生产环境可选

# 文档处理
pypdf2==3.0.1
python-docx==1.1.0
unstructured==0.11.0

# 嵌入模型
sentence-transformers==2.2.2
# openai==1.6.1  # OpenAI API

# 工具库
python-dotenv==1.0.0
pydantic==2.5.2
python-multipart==0.0.6

# 开发工具
pytest==7.4.3
black==23.11.0
flake8==6.1.0
```

### 可选依赖（根据需求）
```txt
# 如果使用OpenAI API
openai==1.6.1
tiktoken==0.5.2

# 如果需要更多文档格式支持
pdf2image==1.16.3
pytesseract==0.3.10

# 如果需要数据库存储元数据
sqlalchemy==2.0.23
alembic==1.13.0
```

## 🔧 环境配置

### 1. 创建环境变量文件
```bash
# .env 文件内容
OPENAI_API_KEY=your_openai_api_key_here
CHROMA_PERSIST_DIRECTORY=./vector_db
DOCUMENT_STORAGE_PATH=./data
EMBEDDING_MODEL=text-embedding-ada-002
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### 2. 安装步骤
```bash
# 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填入你的配置

# 4. 启动服务
python run.py
```

## 🚀 快速开始

### 第一阶段：基础框架搭建（1-2天）
1. 创建项目结构
2. 实现FastAPI基础框架
3. 配置文档上传API
4. 实现基础文档处理

### 第二阶段：RAG核心功能（2-3天）
1. 集成LangChain框架
2. 实现文档分块和嵌入
3. 集成Chroma向量数据库
4. 实现基础问答功能

### 第三阶段：功能完善（1-2天）
1. 添加对话历史管理
2. 实现文档管理功能（删除、更新）
3. 添加API文档和测试
4. 优化性能和用户体验

## 📊 API设计

### 文档管理API
```
POST /api/documents/upload          # 上传文档
GET  /api/documents                 # 获取文档列表
GET  /api/documents/{id}            # 获取文档详情
DELETE /api/documents/{id}          # 删除文档
```

### 问答API
```
POST /api/chat/query                # 问答查询
GET  /api/chat/history              # 获取对话历史
POST /api/chat/session              # 创建对话会话
```

## 🎯 下一步行动

1. **确认选择**: 你选择的技术栈和组件是否合适？
2. **开始实施**: 我将为你创建项目文件和代码框架
3. **配置环境**: 设置开发环境和依赖包
4. **开发测试**: 逐步实现各个功能模块

## 💡 建议

- **开发顺序**: 先实现基础功能，再添加高级特性
- **测试策略**: 每个模块开发完成后立即测试
- **文档记录**: 保持代码和文档同步更新
- **性能监控**: 添加日志和监控，便于问题排查

## 🔗 参考资源

- [LangChain官方文档](https://python.langchain.com/)
- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [ChromaDB文档](https://docs.trychroma.com/)
- [RAG最佳实践](https://research.trychroma.com/rag-best-practices)

---

**准备开始了吗？** 我可以立即为你创建项目文件和代码框架！
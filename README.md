# 企业知识库问答系统 - RAG Agent

基于Python + FastAPI的RAG（检索增强生成）智能问答系统，支持多种文档格式的智能问答。

## 🚀 功能特性

- **多格式文档支持**: PDF、Word、TXT等文档格式
- **智能问答**: 基于文档内容的智能问答
- **对话历史**: 支持多轮对话和历史记录
- **文档管理**: 上传、删除、查看文档信息
- **向量检索**: 使用ChromaDB进行高效的相似度检索
- **本地部署**: 支持本地开发和部署

## 📁 项目结构

```
D:\rag\
├── app/                          # 应用主目录
│   ├── __init__.py              # 应用初始化
│   ├── main.py                  # FastAPI应用入口
│   ├── config.py                # 配置管理
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic模型定义
│   ├── services/                # 业务服务
│   │   ├── __init__.py
│   │   ├── document_service.py  # 文档处理服务
│   │   ├── rag_service.py       # RAG核心服务
│   │   └── vector_store.py      # 向量存储服务
│   ├── api/                     # API路由
│   │   ├── __init__.py
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── documents.py     # 文档管理API
│   │       └── chat.py          # 问答API
│   └── utils/                   # 工具函数
│       ├── __init__.py
│       └── document_loader.py   # 文档加载器
├── data/                        # 文档存储目录
├── vector_db/                   # 向量数据库存储
├── tests/                       # 测试文件
├── docs/                        # 项目文档
├── requirements.txt             # 依赖包列表
├── .env.example                 # 环境变量示例
├── README.md                    # 项目说明
├── run.py                       # 启动脚本
└── RAG_System_Plan.md           # 系统规划文档
```

## 🛠️ 技术栈

- **Web框架**: FastAPI
- **RAG框架**: LangChain
- **向量数据库**: ChromaDB
- **嵌入模型**: sentence-transformers (本地模型)
- **文档处理**: PyPDF2, python-docx
- **数据验证**: Pydantic

## 📋 前置要求

- Python 3.8+
- pip (Python包管理器)
- 足够的磁盘空间用于存储文档和向量数据库

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境 (推荐)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖包
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
copy .env.example .env

# 编辑 .env 文件，配置以下变量：
# - OPENAI_API_KEY (如果使用OpenAI API)
# - CHROMA_PERSIST_DIRECTORY (向量数据库存储路径)
# - DOCUMENT_STORAGE_PATH (文档存储路径)
```

### 3. 启动服务

```bash
# 启动FastAPI服务
python run.py
```

### 4. 访问系统

- **API文档**: http://127.0.0.1:8000/docs
- **系统首页**: http://127.0.0.1:8000
- **健康检查**: http://127.0.0.1:8000/health

## 📚 API接口

### 文档管理

- `POST /api/documents/upload` - 上传文档
- `GET /api/documents` - 获取文档列表
- `GET /api/documents/{doc_id}` - 获取文档详情
- `DELETE /api/documents/{doc_id}` - 删除文档
- `GET /api/documents/stats/summary` - 获取文档统计

### 智能问答

- `POST /api/chat/query` - 智能问答
- `GET /api/chat/sessions` - 获取会话列表
- `GET /api/chat/sessions/{session_id}` - 获取会话详情
- `DELETE /api/chat/sessions/{session_id}` - 删除会话
- `GET /api/chat/sessions/{session_id}/history` - 获取对话历史

## 🎯 使用示例

### 1. 上传文档

```bash
curl -X POST "http://127.0.0.1:8000/api/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_document.pdf"
```

### 2. 智能问答

```bash
curl -X POST "http://127.0.0.1:8000/api/chat/query" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "这个文档的主要内容是什么？",
    "use_history": true
  }'
```

## ⚙️ 配置说明

### 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPENAI_API_KEY` | - | OpenAI API密钥 |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | 本地嵌入模型名称 |
| `CHROMA_PERSIST_DIRECTORY` | `./vector_db` | 向量数据库存储路径 |
| `DOCUMENT_STORAGE_PATH` | `./data` | 文档存储路径 |
| `CHUNK_SIZE` | `1000` | 文档分块大小 |
| `CHUNK_OVERLAP` | `200` | 分块重叠大小 |
| `SEARCH_K` | `4` | 返回相似文档数量 |

### RAG参数调优

- **CHUNK_SIZE**: 文档分块大小，建议1000-2000
- **CHUNK_OVERLAP**: 分块重叠，建议100-300
- **SEARCH_K**: 返回的相似文档数量，建议3-6

## 🔧 开发指南

### 添加新的文档格式支持

1. 在 `app/services/document_service.py` 中添加新的提取方法
2. 在 `app/utils/document_loader.py` 中添加对应的加载器
3. 更新API的文件类型验证

### 集成新的LLM

1. 在 `app/services/rag_service.py` 中修改 `_generate_answer` 方法
2. 配置相应的API密钥和模型参数

### 数据库迁移

当前使用ChromaDB作为向量数据库，如需迁移到其他数据库：

1. 修改 `app/services/vector_store.py` 中的实现
2. 更新配置文件中的数据库连接参数

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_document_service.py

# 生成测试报告
pytest --cov=app tests/
```

## 📝 注意事项

1. **文件大小限制**: 默认最大50MB，可在 `.env` 中调整
2. **支持格式**: 目前支持PDF、DOCX、TXT格式
3. **存储空间**: 确保有足够的磁盘空间存储文档和向量数据库
4. **性能**: 大量文档时建议使用更好的硬件或分布式部署

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目使用MIT许可证 - 详见LICENSE文件

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 创建GitHub Issue
- 发送邮件至项目维护者

## 🔗 相关资源

- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [LangChain文档](https://python.langchain.com/)
- [ChromaDB文档](https://docs.trychroma.com/)
- [RAG最佳实践](https://research.trychroma.com/rag-best-practices)
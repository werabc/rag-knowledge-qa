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
│   ├── main.py                  # FastAPI应用入口
│   ├── config.py                # 配置管理 (pydantic-settings)
│   ├── models/schemas.py        # Pydantic模型定义
│   ├── services/                # 业务服务
│   │   ├── document_service.py  # 文档提取与分块，写入向量库
│   │   ├── qa_service.py        # 问答核心：检索→上下文→生成→会话记忆
│   │   └── vector_store.py      # ChromaDB向量存储 (内置ONNX MiniLM embedding)
│   └── api/endpoints/
│       ├── documents.py         # 文档管理API
│       └── chat.py              # 问答API
├── data/                        # 文档分块与会话持久化 (sessions.json)
├── vector_db/                   # ChromaDB持久化目录
├── test_data/                   # 测试文档
├── requirements.txt             # 依赖包列表
├── .env.example                 # 环境变量示例
├── test_system.py               # 端到端测试脚本 (需先启动服务)
├── run.py                       # 启动脚本
└── RAG_System_Plan.md           # 系统规划文档
```

## 🛠️ 技术栈

- **Web框架**: FastAPI
- **向量数据库**: ChromaDB 1.x (PersistentClient, cosine空间)
- **嵌入模型**: chromadb内置 ONNX all-MiniLM-L6-v2（无需torch；中文效果弱，待换bge-small-zh）
- **LLM生成**: OpenAI兼容接口（已接美团LongCat），未配置key时自动回退抽取式回答
- **文档分块**: langchain-text-splitters
- **文档处理**: PyPDF2, python-docx
- **数据验证**: Pydantic v2 + pydantic-settings

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
- **可视化面板**: http://127.0.0.1:8000/ui （知识库管理 / 对话记忆 / 全链路trace调试）
- **系统首页**: http://127.0.0.1:8000
- **健康检查**: http://127.0.0.1:8000/health

## 📚 API接口

### 文档管理

- `POST /api/documents/upload` - 上传文档
- `GET /api/documents` - 获取文档列表
- `GET /api/documents/{doc_id}` - 获取文档详情
- `DELETE /api/documents/{doc_id}` - 删除文档
- `GET /api/documents/{doc_id}/chunks` - 查看文档分块明文
- `GET /api/documents/stats/summary` - 获取文档统计

### 智能问答

- `POST /api/v1/chat/query` - 智能问答
- `GET /api/v1/chat/sessions` - 获取会话列表
- `GET /api/v1/chat/sessions/{session_id}` - 获取会话详情
- `DELETE /api/v1/chat/sessions/{session_id}` - 删除会话
- `GET /api/v1/chat/sessions/{session_id}/history` - 获取对话历史

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
curl -X POST "http://127.0.0.1:8000/api/v1/chat/query" \
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
| `OPENAI_API_KEY` | 空 | LLM密钥；为空时回答走抽取式回退 |
| `OPENAI_API_BASE` | `https://api.openai.com/v1` | OpenAI兼容接口地址，如LongCat：`https://api.longcat.chat/openai/v1` |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名，如 `LongCat-2.0` |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | 嵌入模型（当前由chromadb内置ONNX实现） |
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

1. 在 `app/services/document_service.py` 中添加新的 `_extract_*` 方法
2. 更新 `app/api/endpoints/documents.py` 的 `allowed_types`

### 集成新的LLM

1. 在 `.env` 中配置 `OPENAI_API_KEY` / `OPENAI_API_BASE` / `LLM_MODEL`
2. 生成逻辑位于 `app/services/qa_service.py` 的 `query_stream`（流式生成器，`query` 为其薄壳）

### 数据库迁移

当前使用ChromaDB作为向量数据库，如需迁移到其他数据库：

1. 修改 `app/services/vector_store.py` 中的实现
2. 更新配置文件中的数据库连接参数

## 🧪 测试

```bash
# 先启动服务: python run.py
python test_system.py   # 端到端测试：上传→查询→会话
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
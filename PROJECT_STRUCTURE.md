# 项目结构说明

## 📁 目录结构

```
D:\rag\
├── 📁 app/                          # 应用主目录
│   ├── 📄 __init__.py              # 应用初始化文件
│   ├── 📄 main.py                  # FastAPI应用入口
│   ├── 📄 config.py                # 配置管理
│   ├── 📁 models/                  # 数据模型模块
│   │   ├── 📄 __init__.py
│   │   └── 📄 schemas.py          # Pydantic模型定义
│   ├── 📁 services/                # 业务服务模块
│   │   ├── 📄 __init__.py
│   │   ├── 📄 document_service.py  # 文档处理服务
│   │   ├── 📄 rag_service.py       # RAG核心服务
│   │   └── 📄 vector_store.py      # 向量存储服务
│   ├── 📁 api/                     # API路由模块
│   │   ├── 📄 __init__.py
│   │   └── 📁 endpoints/
│   │       ├── 📄 __init__.py
│   │       ├── 📄 documents.py     # 文档管理API
│   │       └── 📄 chat.py          # 问答API
│   └── 📁 utils/                   # 工具函数模块
│       ├── 📄 __init__.py
│       └── 📄 document_loader.py   # 文档加载器
├── 📁 data/                        # 文档存储目录
├── 📁 vector_db/                   # 向量数据库存储
├── 📁 tests/                       # 测试文件
├── 📁 docs/                        # 项目文档
├── 📄 requirements.txt             # 依赖包列表
├── 📄 .env.example                 # 环境变量示例
├── 📄 README.md                    # 项目说明
├── 📄 QUICKSTART.md                # 快速开始指南
├── 📄 PROJECT_STRUCTURE.md         # 项目结构说明
├── 📄 RAG_System_Plan.md           # 系统规划文档
├── 📄 run.py                       # 启动脚本
├── 📄 setup.py                     # 项目安装配置
└── 📄 test_system.py               # 系统测试脚本
```

## 🎯 核心文件说明

### 1. 应用入口

#### `app/main.py`
- **功能**: FastAPI应用的主入口
- **职责**: 
  - 创建FastAPI应用实例
  - 配置CORS中间件
  - 注册API路由
  - 提供系统首页和健康检查接口

#### `run.py`
- **功能**: 应用启动脚本
- **职责**:
  - 加载环境变量
  - 配置服务器参数
  - 启动uvicorn服务器

### 2. 配置管理

#### `app/config.py`
- **功能**: 应用配置管理
- **职责**:
  - 读取环境变量
  - 提供配置类 `Settings`
  - 管理所有配置参数

### 3. 数据模型

#### `app/models/schemas.py`
- **功能**: Pydantic数据模型定义
- **包含模型**:
  - `DocumentBase`: 文档基础模型
  - `DocumentCreate`: 文档创建模型
  - `DocumentResponse`: 文档响应模型
  - `ChatMessage`: 聊天消息模型
  - `ChatSession`: 对话会话模型
  - `QueryRequest`: 查询请求模型
  - `QueryResponse`: 查询响应模型

### 4. 业务服务

#### `app/services/document_service.py`
- **功能**: 文档处理服务
- **职责**:
  - 上传和处理文档
  - 提取文档内容（PDF、DOCX、TXT）
  - 文档分块处理
  - 文档信息管理

#### `app/services/vector_store.py`
- **功能**: 向量存储服务
- **职责**:
  - 管理ChromaDB向量数据库
  - 添加文档向量
  - 搜索相似文档
  - 删除文档向量

#### `app/services/rag_service.py`
- **功能**: RAG核心服务
- **职责**:
  - 处理用户查询
  - 生成智能回答
  - 管理对话会话
  - 计算回答置信度

### 5. API路由

#### `app/api/endpoints/documents.py`
- **功能**: 文档管理API
- **接口**:
  - `POST /upload`: 上传文档
  - `GET /`: 获取文档列表
  - `GET /{doc_id}`: 获取文档详情
  - `DELETE /{doc_id}`: 删除文档
  - `GET /stats/summary`: 获取文档统计

#### `app/api/endpoints/chat.py`
- **功能**: 智能问答API
- **接口**:
  - `POST /query`: 智能问答
  - `GET /sessions`: 获取会话列表
  - `GET /sessions/{session_id}`: 获取会话详情
  - `DELETE /sessions/{session_id}`: 删除会话
  - `GET /sessions/{session_id}/history`: 获取对话历史

### 6. 工具函数

#### `app/utils/document_loader.py`
- **功能**: 文档加载器工具
- **职责**:
  - 加载不同格式的文档
  - 文档分块处理
  - 获取文档基本信息

## 🔄 数据流

### 1. 文档上传流程

```
用户上传文档 → API接收 → 文档服务处理 → 向量存储 → 返回结果
```

### 2. 智能问答流程

```
用户提问 → API接收 → RAG服务 → 向量检索 → 生成回答 → 返回结果
```

## 📊 配置文件

### `.env.example`
- **功能**: 环境变量配置示例
- **包含配置**:
  - OpenAI API配置
  - 本地模型配置
  - 向量数据库配置
  - 文档存储配置
  - RAG参数配置
  - FastAPI配置
  - 安全配置

### `requirements.txt`
- **功能**: Python依赖包列表
- **主要依赖**:
  - Web框架: FastAPI
  - RAG框架: LangChain
  - 向量数据库: ChromaDB
  - 文档处理: PyPDF2, python-docx
  - 嵌入模型: sentence-transformers

## 🧪 测试文件

### `test_system.py`
- **功能**: 系统测试脚本
- **测试内容**:
  - 健康检查
  - 文档上传
  - 文档列表
  - 智能问答
  - 会话管理
  - 统计信息

## 📚 文档文件

### `README.md`
- **功能**: 项目主文档
- **内容**: 项目介绍、功能特性、技术栈、安装指南、API文档

### `QUICKSTART.md`
- **功能**: 快速开始指南
- **内容**: 5分钟快速启动、使用示例、常见问题解决

### `RAG_System_Plan.md`
- **功能**: 系统规划文档
- **内容**: 技术架构、组件选择、项目结构、开发计划

## 🎯 设计原则

### 1. 模块化设计
- 每个功能模块独立封装
- 清晰的职责划分
- 易于维护和扩展

### 2. 配置管理
- 环境变量配置
- 支持多环境部署
- 敏感信息分离

### 3. 错误处理
- 完善的异常处理
- 用户友好的错误信息
- 日志记录

### 4. API设计
- RESTful API设计
- 完整的API文档
- 参数验证

## 🚀 扩展指南

### 添加新的文档格式
1. 在 `document_service.py` 中添加提取方法
2. 在 `document_loader.py` 中添加加载器
3. 更新API的文件类型验证

### 集成新的LLM
1. 在 `rag_service.py` 中修改生成逻辑
2. 配置相应的API参数
3. 更新配置文件

### 添加新的API接口
1. 在 `api/endpoints/` 中创建新的路由文件
2. 在 `main.py` 中注册路由
3. 更新API文档

## 📈 性能优化

### 1. 异步处理
- 使用async/await异步编程
- 提高并发处理能力

### 2. 缓存机制
- 文档内容缓存
- 向量检索缓存

### 3. 数据库优化
- 向量数据库索引优化
- 查询性能优化

## 🔒 安全考虑

### 1. 文件上传安全
- 文件类型验证
- 文件大小限制
- 恶意文件检测

### 2. API安全
- 输入参数验证
- SQL注入防护
- XSS防护

### 3. 数据安全
- 敏感信息加密
- 访问权限控制
- 数据备份

---

这个项目结构遵循了**关注点分离**原则，每个模块都有明确的职责，便于开发、测试和维护。
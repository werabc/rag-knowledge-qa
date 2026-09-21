# 快速开始指南

## 🚀 5分钟快速启动

### 步骤1: 安装Python环境

确保你已安装Python 3.8或更高版本：

```bash
python --version
```

### 步骤2: 创建项目目录并进入

```bash
cd D:\rag
```

### 步骤3: 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
# source venv/bin/activate
```

### 步骤4: 安装依赖包

```bash
pip install -r requirements.txt
```

### 步骤5: 配置环境变量

```bash
# 复制环境变量示例文件
copy .env.example .env
```

编辑 `.env` 文件，至少配置以下内容：

```env
# 如果使用OpenAI API，配置API密钥
OPENAI_API_KEY=your_openai_api_key_here

# 如果使用本地模型，可以保持默认
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2

# 文件存储路径（可以使用默认值）
CHROMA_PERSIST_DIRECTORY=./vector_db
DOCUMENT_STORAGE_PATH=./data
```

### 步骤6: 启动系统

```bash
python run.py
```

### 步骤7: 访问系统

- **API文档**: 在浏览器中打开 http://127.0.0.1:8000/docs
- **系统首页**: http://127.0.0.1:8000
- **健康检查**: http://127.0.0.1:8000/health

## 📝 使用示例

### 1. 上传文档

在API文档页面（http://127.0.0.1:8000/docs）：

1. 点击 **POST /api/documents/upload**
2. 点击 **Try it out**
3. 选择要上传的文件（支持PDF、DOCX、TXT格式）
4. 点击 **Execute**

### 2. 智能问答

1. 点击 **POST /api/chat/query**
2. 点击 **Try it out**
3. 在请求体中输入：

```json
{
  "question": "这个文档的主要内容是什么？",
  "use_history": true
}
```

4. 点击 **Execute**

### 3. 查看文档列表

1. 点击 **GET /api/documents/**
2. 点击 **Try it out**
3. 点击 **Execute**

### 4. 查看会话历史

1. 点击 **GET /api/chat/sessions**
2. 点击 **Try it out**
3. 点击 **Execute**

## 🔧 常见问题解决

### 问题1: 依赖安装失败

```bash
# 尝试使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题2: 端口被占用

修改 `.env` 文件中的端口配置：

```env
APP_PORT=8001
```

### 问题3: 文件上传失败

检查文件大小限制：

```env
MAX_UPLOAD_SIZE_MB=100  # 增加到100MB
```

### 问题4: 向量数据库错误

删除向量数据库目录并重新启动：

```bash
rmdir /s /q vector_db
python run.py
```

## 📊 系统监控

### 健康检查

```bash
curl http://127.0.0.1:8000/health
```

### 文档统计

```bash
curl http://127.0.0.1:8000/api/documents/stats/summary
```

### RAG统计

```bash
curl http://127.0.0.1:8000/api/chat/stats
```

## 🎯 下一步

1. **上传更多文档**: 测试不同格式的文档
2. **调整参数**: 根据实际需求调整RAG参数
3. **集成前端**: 开发Web界面或集成到现有系统
4. **生产部署**: 配置生产环境和安全设置

## 📚 更多资源

- 详细文档: [README.md](README.md)
- 系统规划: [RAG_System_Plan.md](RAG_System_Plan.md)
- API文档: http://127.0.0.1:8000/docs

## 🆘 获取帮助

如果遇到问题：

1. 查看系统日志
2. 检查API文档
3. 查看GitHub Issues
4. 联系开发团队

---

**恭喜！** 你已经成功启动了企业知识库问答系统。现在可以开始上传文档并测试智能问答功能了！
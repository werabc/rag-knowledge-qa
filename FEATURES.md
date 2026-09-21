# 功能文档 — 企业知识库问答系统（RAG）

> 版本：v1.0 · 更新日期：2026-09-21 · 对应提交：`f7c89ba`

## 1. 系统概览

本地部署的检索增强问答系统：上传文档 → 切块 → 向量化入库 → 混合检索（向量 + BM25，RRF 融合）→ 拼接上下文 → LLM 生成（OpenAI 兼容接口，未配置时抽取式回退）→ 多轮会话记忆。全程带链路 trace，可在 `/ui` 面板可视化。

## 2. 架构

```
                        ┌──────────────────────────────────────────┐
 上传 .txt/.pdf/.docx   │                FastAPI (app/main.py)     │
 ─────────────────────► │  /api/documents/*   /api/chat/*   /ui    │
                        └──────┬───────────────────┬───────────────┘
                               │                   │
                     DocumentService            QAService
                     ├ 文本提取(PyPDF2/docx)      ├ 向量召回 ──► VectorStore ──► ChromaDB(512维,cosine)
                     ├ 切块(1000/200)             ├ BM25召回 ──► BM25Index(内存, jieba分词)
                     ├ 写向量库 + BM25增量        ├ RRF融合(k=60, 取top SEARCH_K)
                     └ 台账 documents.json        ├ 上下文拼接 [资料N]
                       分块明文 chunks/*.json     ├ LLM生成(LongCat) / 抽取式回退
                                                 └ 会话记忆 sessions.json
                               │
                        Embeddings（EMBEDDING_MODEL_NAME 决定）
                        ├ 默认 MiniLM → chromadb 内置 ONNX（无需 torch）
                        └ bge-small-zh-v1.5 → sentence-transformers，查询侧加指令前缀
```

## 3. 模块清单

| 模块 | 文件 | 职责 |
|---|---|---|
| 配置 | `app/config.py` | pydantic-settings，读 `.env`，大小写敏感 |
| 数据模型 | `app/models/schemas.py` | Pydantic 请求/响应模型（含 `trace` 字段） |
| 文档服务 | `app/services/document_service.py` | 提取/切块/入库/删除/台账持久化/孤儿恢复/全量重建 reindex_all |
| 向量存储 | `app/services/vector_store.py` | chromadb 1.x PersistentClient，cosine HNSW，自定义 EF 接入，recreate_collection |
| 嵌入服务 | `app/services/embeddings.py` | 按配置加载 sentence-transformers；bge 查询前缀；失败回退内置 MiniLM |
| BM25 | `app/services/bm25_index.py` | jieba 分词倒排 + Lucene idf 公式 BM25；启动时从台账+分块明文重建 |
| 问答服务 | `app/services/qa_service.py` | 检索→融合→上下文→生成→记忆 主流程 + trace 采集 |
| 文档 API | `app/api/endpoints/documents.py` | 上传（流式限流+文件名清洗）、列表、详情、删除、分块查看、reindex、统计 |
| 问答 API | `app/api/endpoints/chat.py` | 查询、会话增删查、历史、统计、清空 |
| 可视化面板 | `app/static/index.html` | 三页签：知识库 / 对话记忆 / 问答调试（全链路 trace） |

## 4. API 参考

### 文档管理 `/api/documents`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/upload` | multipart 上传 `.txt/.pdf/.docx`，超 `MAX_UPLOAD_SIZE_MB` 返回 413 |
| GET | `/` | 文档台账列表 |
| GET | `/{doc_id}` | 单个文档详情 |
| GET | `/{doc_id}/chunks` | 该文档全部分块明文 |
| DELETE | `/{doc_id}` | 删向量分块 + BM25 + 台账 + 分块明文 |
| POST | `/reindex` | **用当前 embedding 模型全量重建向量库+BM25**（切换模型后必调，见 §7） |
| GET | `/stats/summary` | 文档数/分块数/总大小/类型分布 |

### 智能问答 `/api/chat`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/query` | 入参 `{question, session_id?, use_history=true}`；返回 `{answer, sources[], confidence, session_id, trace[]}` |
| GET | `/sessions` | 全部会话 |
| GET | `/sessions/{id}` | 会话详情（含消息与 trace） |
| GET | `/sessions/{id}/history` | 仅消息列表 |
| DELETE | `/sessions/{id}` | 删除会话 |
| POST | `/clear-history?session_id=` | 清空指定会话；不带参数清空全部 |
| GET | `/stats` | 向量库分块数 + 会话/消息数 |

### 其他

`GET /health` 健康检查 · `GET /ui` 可视化面板 · `GET /docs` OpenAPI

## 5. 存储布局

```
D:\rag\
├── data\
│   ├── documents.json        # 文档台账（上传即落盘；启动时与向量库对账）
│   ├── chunks\{doc_id}.json  # 分块明文（查看分块、reindex 的数据源）
│   └── sessions.json         # 会话记忆（含每条回答的 trace）
├── vector_db\                # ChromaDB PersistentClient（512 维 cosine）
├── models\bge-small-zh-v1.5\ # 本地嵌入权重（gitignore，95MB）
└── app\                      # 代码
```

向量分块 id 规则：`{doc_id}_chunk_{i}`；metadata 含 `doc_id/chunk_index/filename/file_type/upload_time`。

## 6. 配置项（.env）

| 变量 | 当前值 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | （LongCat key，勿入库） | 为空则走抽取式回答 |
| `OPENAI_API_BASE` | `https://api.longcat.chat/openai/v1` | OpenAI 兼容端点 |
| `LLM_MODEL` | `LongCat-2.0` | 生成模型 |
| `EMBEDDING_MODEL_NAME` | `models/bge-small-zh-v1.5` | 本地路径=加载 sentence-transformers；`all-MiniLM-L6-v2`=chroma 内置 ONNX |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 1000 / 200 | 切块参数 |
| `SEARCH_K` | 4 | 融合后进入上下文的分块数 |
| `HYBRID_BM25` / `BM25_TOP_K` | True / 4 | 双路召回开关与 BM25 路条数 |
| `CHROMA_PERSIST_DIRECTORY` / `CHROMA_COLLECTION_NAME` | `./vector_db` / `documents` | 向量库位置 |
| `DOCUMENT_STORAGE_PATH` / `MAX_UPLOAD_SIZE_MB` | `./data` / 50 | 文档存储 |

## 7. 关键机制

### 混合检索（RRF）
向量路与 BM25 路各出候选，按分块 id 去重，`rrf = Σ 1/(60+排名)`，降序取 top `SEARCH_K`。向量管语义近似（同义改写也能命中），BM25 管关键词精确命中（型号、人名、编号）。`confidence` 取向量路最高相似度。

### 中文嵌入
bge 系列查询侧自动加前缀「为这个句子生成表示以用于检索文章：」（文档侧不加），中文短问句相似度显著优于 MiniLM（实测正确文档向量分 0.65~0.77，MiniLM 时代约 0.18~0.54 且排序不稳）。

### 切换 embedding 模型（三步）
1. `.env` 改 `EMBEDDING_MODEL_NAME`（模型名或本地目录）；
2. 重启服务（不同模型维度不同，旧库不兼容）；
3. `POST /api/documents/reindex` —— 从 `data/chunks/` 明文全量重嵌入，无需重新上传。

### 会话记忆
`session_id` 缺省时服务端自动生成并在响应回传，客户端带上即续聊。最近 `HISTORY_ROUNDS=6` 条消息进 prompt。每轮问答（含 trace）即时落盘 `sessions.json`。

### 断电自愈
启动时对比向量库与台账：向量库里有、台账里没有的 doc_id 以 `status="recovered"` 认领回列表。

### 生成回退
LLM 调用失败（网络/配额）自动回退抽取式回答（直接罗列 top 分块），不中断服务；trace 的 generation 步骤会记录 `mode=extractive_fallback` 与错误信息。

## 8. Trace 字段（问答响应 `trace[]`，5 步）

| step | 耗时 | detail 关键字段 |
|---|---|---|
| `retrieval` | ✓ | `query`、`channels.vector[] / channels.bm25[]`（各路命中）、`merged[]`（rank/filename/rrf/vec_score/bm25_score/preview） |
| `context` | ✓ | `chars`、`source_count`、`strategy=top_k_concatenation` |
| `generation` | ✓ | `mode=llm`、`model`、`base_url`、`history_messages_used`、`prompt_chars`、`prompt_preview`(前500字)；失败时 `mode=extractive_fallback`+`error` |
| `memory` | ✓ | 会话写入情况 |
| `total` | ✓ | 端到端总耗时 |

trace 同时存进会话消息，`/ui` 问答调试页签逐层展开渲染。

## 9. 已知边界

- **BM25 全内存**：启动时从台账+分块明文重建，语料规模适合万级分块以内；检索为线性扫描词频表，数据量大需换倒排跳过。
- **reindex 是破坏性重建**：先删集合再重灌，期间检索结果不完整；分块明文丢失的文档无法恢复（原始文件上传后即删，只保留明文）。
- **单进程文件存储**：sessions/documents 为 JSON 整文件读写，无并发锁，不适合多 worker 横向扩展。
- **PDF 能力有限**：PyPDF2 纯文本提取，无 OCR、不保留表格结构。
- **无鉴权/多租户**：面板与 API 均裸奔，仅适合本机或内网使用。
- **API key 安全**：`.env` 已 gitignore，但 key 曾出现在聊天记录中，建议轮换。

## 10. 快速上手

```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# .env 填 OPENAI_API_KEY（可选，不填走抽取式）
python run.py
# 浏览器打开 http://127.0.0.1:8000/ui
```

换中文嵌入模型需先下载 `models/bge-small-zh-v1.5`（见 §7），并安装 `sentence-transformers` + torch。

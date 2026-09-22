# 功能文档 — 企业知识库问答系统（RAG）

> 版本：v1.1 · 更新日期：2026-09-22 · 对应提交：`5710b70`

## 1. 系统概览

本地部署的检索增强问答系统：上传文档 → 切块 → 向量化入库 → 查询改写（多轮指代消解）→ 混合检索（向量 + BM25，RRF 融合）→ LLM 重排 → 拼接上下文 → LLM 生成（OpenAI 兼容接口，未配置时抽取式回退）→ 多轮会话记忆 + 跨会话长期记忆。另提供 **Agent 模式**（ReAct 循环，LLM 自主决定检索次数与工具）。检索质量有 golden set 评估基线（hit@k/MRR）。全程带链路 trace，可在 `/ui` 面板可视化。

Agent 能力按 L1-L5 分级规范建设，见 `docs/AGENT_SPEC.md`；当前 L1-L5 全部落地。

## 2. 架构

```
                        ┌──────────────────────────────────────────┐
 上传 .txt/.pdf/.docx   │                FastAPI (app/main.py)     │
 ─────────────────────► │  /api/v1/documents/*  /api/v1/chat/*  /ui │
                        └──────┬───────────────────┬───────────────┘
                               │                   │
                     DocumentService            QAService / AgentService
                     ├ 文本提取(PyPDF2/docx)      ├ 查询改写(指代消解, LLM)
                     ├ 切块(1000/200)             ├ 向量召回 ──► VectorStore ──► ChromaDB(512维,cosine)
                     ├ 写向量库 + BM25增量        ├ BM25召回 ──► BM25Index(内存, jieba分词)
                     └ 台账 documents.json        ├ RRF融合(k=60, 召回池8) → LLM重排 → top4
                       分块明文 chunks/*.json     ├ 上下文拼接 [资料N] + 长期记忆注入system prompt
                                                 ├ LLM生成(LongCat) / 抽取式回退
                        Agent模式(L3)：同一LLM在 ├ 会话记忆 sessions.json
                        ReAct循环(≤5步)里自主调  └ 长期记忆 MemoryService(L4)
                        kb_search/kb_stats/         ├ 答后异步抽取事实 → longterm.json
                        session_history 工具        └ 按词重叠召回

                        评估(L5)：eval/golden_set.json 11条金标
                        scripts/evaluate_retrieval.py → hit@1/hit@4/MRR
                        双通道报告(仅RRF vs RRF+重排) → eval/report.json
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
| 问答服务 | `app/services/qa_service.py` | 查询改写→检索→融合→LLM重排→上下文→生成→记忆 主流程 + trace 采集；`hybrid_search` 供 Agent 复用 |
| Agent 服务 | `app/services/agent_service.py` | L3：ReAct 循环（JSON-in-text 协议），LLM 自主调用 kb_search/kb_stats/session_history，步数上限+强制收口+解析兜底 |
| 长期记忆 | `app/services/memory_service.py` | L4：答后异步 LLM 抽取原子事实、去重落盘 longterm.json，按词重叠召回注入 prompt |
| 检索评估 | `scripts/evaluate_retrieval.py` | L5：跑 golden set，输出 RRF 与 RRF+重排双通道 hit@1/hit@4/MRR |
| 文档 API | `app/api/endpoints/documents.py` | 上传（流式限流+文件名清洗）、列表、详情、删除、分块查看、reindex、统计 |
| 问答 API | `app/api/endpoints/chat.py` | 查询、Agent 查询、会话增删查、历史、统计、清空、长期记忆增删查 |
| 可视化面板 | `app/static/index.html` | 三页签：知识库 / 对话记忆（含长期记忆卡片）/ 问答调试（全链路 trace、Agent 逐 turn、Agent 模式开关） |

## 4. API 参考（v1.2 起统一 `/api/v1` 前缀）

**错误契约**：所有失败响应为 `{"error": {"code", "message", "detail"}}`，状态码语义化（400 参数错 / 404 不存在 / 409 冲突 / 413 超限 / 500 内部错）。删除成功返回 **204 无响应体**。列表端点统一分页信封 `{items, total, page, size}`。契约回归：`python -X utf8 scripts/api_contract_test.py`（21 项矩阵）。

### 文档管理 `/api/v1/documents`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/upload` | multipart 上传 `.txt/.pdf/.docx`；400 unsupported_file_type / 413 file_too_large |
| GET | `/` | 文档台账列表（分页 `?page=&size=`，size≤100） |
| GET | `/{doc_id}` | 单个文档详情；404 document_not_found |
| GET | `/{doc_id}/chunks` | 该文档全部分块明文 |
| DELETE | `/{doc_id}` | 删向量分块 + BM25 + 台账 + 分块明文；成功 204 |
| POST | `/reindex` | **用当前 embedding 模型全量重建向量库+BM25**（切换模型后必调，见 §7）；并发再入 409 |
| GET | `/stats/summary` | 文档数/分块数/总大小/类型分布 |

### 智能问答 `/api/v1/chat`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/query` | 入参 `{question, session_id?, use_history=true}`；返回 `{answer, sources[]（含 cited 标记）, confidence, session_id, trace[]}` |
| POST | `/agent` | **Agent 模式（L3）**：同 `/query` 入参出参，但走 ReAct 循环，LLM 自主决定检索次数与工具；trace 含 `agent` 步骤（逐 turn 思考/工具/观察） |
| GET | `/memories` | 长期记忆事实列表（L4）`{count, facts[]}` |
| POST | `/memories` | 手动添加事实，body `{fact}`；成功 201，重复/空 409 |
| DELETE | `/memories/{fact_id}` | 删除单条事实；成功 204，不存在 404 |
| GET | `/sessions` | 会话列表（分页） |
| DELETE | `/sessions` | 清空全部会话，返回 `{cleared_sessions}` |
| GET | `/sessions/{id}` | 会话详情（含消息与 trace）；404 session_not_found |
| GET | `/sessions/{id}/history` | 仅消息列表 |
| DELETE | `/sessions/{id}` | 删除会话；成功 204 |
| GET | `/stats` | 向量库分块数 + 会话/消息数 |

### 其他

`GET /health` 健康检查 · `GET /ui` 可视化面板 · `GET /docs` OpenAPI

## 5. 存储布局

```
D:\rag\
├── data\
│   ├── documents.json        # 文档台账（上传即落盘；启动时与向量库对账）
│   ├── chunks\{doc_id}.json  # 分块明文（查看分块、reindex 的数据源）
│   ├── sessions.json         # 会话记忆（含每条回答的 trace）
│   └── longterm.json         # 长期记忆事实（L4，去重后 ≤200 条）
├── vector_db\                # ChromaDB PersistentClient（512 维 cosine）
├── eval\                     # golden_set.json 金标集 + report.json 最近一次评估报告
├── scripts\evaluate_retrieval.py  # L5 评估脚本
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
| `HYBRID_BM25` | True | 双路召回开关 |
| `CITATION_VERIFY` | True | 生成后引用核验（防幻觉）开关 |
| `QUERY_REWRITE` / `LLM_RERANK` | True / True | 指代消解改写、LLM 重排开关 |
| `RERANK_CANDIDATES` | 8 | 召回池大小（重排输入条数） |
| `AGENT_MAX_STEPS` | 5 | L3 Agent ReAct 循环最大轮数，超限强制收口 |
| `LONGTERM_MEMORY` | True | L4 长期记忆开关（抽取+召回注入） |
| `CHROMA_PERSIST_DIRECTORY` / `CHROMA_COLLECTION_NAME` | `./vector_db` / `documents` | 向量库位置 |
| `DOCUMENT_STORAGE_PATH` / `MAX_UPLOAD_SIZE_MB` | `./data` / 50 | 文档存储 |

## 7. 关键机制

### 查询改写（指代消解）
带会话历史的追问先经 LLM 改写成自包含查询再检索（「那它的上线时间呢？」→「朱雀系统的上线时间和并发规格是什么？」）。首轮/关历史/未配 LLM 时跳过；改写失败用原问题。

### LLM 重排（listwise）
RRF 融合取召回池 8 条，连同问题交给 LLM 按相关度重排，取 top4 进上下文。对召回池只输出部分编号（如 `[1]`）做容错：已列出的置顶、其余按 RRF 原序补齐；完全解析失败则沿用 RRF 顺序。实测能把向量+BM25 都排错的英文文档从第 2 顶到第 1。

### 混合检索（RRF）
向量路与 BM25 路各出候选，按分块 id 去重，`rrf = Σ 1/(60+排名)`，降序取 top `SEARCH_K`。向量管语义近似（同义改写也能命中），BM25 管关键词精确命中（型号、人名、编号）。`confidence` 取向量路最高相似度。

### 中文嵌入
bge 系列查询侧自动加前缀「为这个句子生成表示以用于检索文章：」（文档侧不加），中文短问句相似度显著优于 MiniLM（实测正确文档向量分 0.65~0.77，MiniLM 时代约 0.18~0.54 且排序不稳）。

### Agent 模式：ReAct 工具循环（L3）
`POST /api/chat/agent`：LLM 在循环里自主决定「查什么、查几次、何时收口」。协议为 JSON-in-text（模型无关，不依赖 function-calling API）：每轮模型输出 `{"thought":…,"tool":…,"args":…}` 调工具，或 `{"thought":…,"final":…}` 收敛。工具三个：`kb_search`（复用 hybrid_search 双路召回+RRF）、`kb_stats`（库规模）、`session_history`（本会话历史）。防线：≤`AGENT_MAX_STEPS` 轮、达上限 for-else 强制收口、JSON 解析失败按 protocol_fallback 处理；各轮检回的分块去重汇总为 sources，与普通模式共用同一条记忆落盘管线。实测复合对比问题会自动规划 2 次不同角度的 kb_search。

### 长期记忆（L4）
每轮回答后 `asyncio.create_task` 异步让 LLM 从对话中抽取原子事实（如用户身份、项目名），归一化去重后写 `data/longterm.json`（上限 200 条 FIFO）。新问题按 jieba 分词与事实计算词重叠分（`overlap/√|fact_tokens|`）召回 top 事实，以「【长期记忆】」段注入 system prompt。因此 `use_history=false` 的全新会话仍能认出用户身份（实测通过）。可查看/手动添加/删除（`/api/chat/memories` + 面板卡片）。

### 检索评估（L5）
`eval/golden_set.json`：11 条「问题 → 应命中文档」金标（跨 4 个文档，含中英文、关键词式与语义式问法）。`python -X utf8 scripts/evaluate_retrieval.py` 对每条跑一次 `/api/chat/query`，从 trace 取 RRF 融合序、从 sources 取重排后序，双通道各算 hit@1 / hit@4 / MRR 写入 `eval/report.json`。当前基线：**两通道均 1.0（11/11 rank1）**——语料小，指标主要防回退（改参数/换模型后重跑对照）。

### 切换 embedding 模型（三步）
1. `.env` 改 `EMBEDDING_MODEL_NAME`（模型名或本地目录）；
2. 重启服务（不同模型维度不同，旧库不兼容）；
3. `POST /api/documents/reindex` —— 从 `data/chunks/` 明文全量重嵌入，无需重新上传。

### 引用核验（防幻觉，零额外 LLM 往返）
生成后、写记忆前，用规则校验答案里的 `[资料N]`/`【资料N】` 引用：编号超出来源数 → 从答案中**剔除**（模型引用了不存在的资料即幻觉信号）；通篇无引用 → 末尾**补默认来源行**。trace 的 `citation` 步骤记录 发现/采信/剔除 的编号集合，响应 `sources[].cited` 标记哪条真被答案引用，面板同步渲染。mode：`ok / stripped_invalid / appended_default / no_sources / disabled`。

### 会话记忆
`session_id` 缺省时服务端自动生成并在响应回传，客户端带上即续聊。最近 `HISTORY_ROUNDS=6` 条消息进 prompt。每轮问答（含 trace）即时落盘 `sessions.json`。

### 断电自愈
启动时对比向量库与台账：向量库里有、台账里没有的 doc_id 以 `status="recovered"` 认领回列表。

### 生成回退
LLM 调用失败（网络/配额）自动回退抽取式回答（直接罗列 top 分块），不中断服务；trace 的 generation 步骤会记录 `mode=extractive_fallback` 与错误信息。

## 8. Trace 字段（问答响应 `trace[]`，8 步）

| step | 耗时 | detail 关键字段 |
|---|---|---|
| `query_rewrite` | ✓ | `mode=skipped/no_change/llm/fallback`、`original`、`rewritten` |
| `retrieval` | ✓ | `query`（改写后）、`k`（召回池）、`channels.vector[] / channels.bm25[]`（各路命中）、`merged[]`（rank/filename/rrf/vec_score/bm25_score/preview） |
| `rerank` | ✓ | `mode=llm/disabled/skipped/fallback`、`before[]`（RRF 原序）、`after[]`（重排后 top4） |
| `context` | ✓ | `chars`、`source_count`、`strategy=top_k_concatenation` |
| `generation` | ✓ | `mode=llm`、`model`、`base_url`、`history_messages_used`、`prompt_chars`、`prompt_preview`(前500字)；失败时 `mode=extractive_fallback`+`error` |
| `citation` | ✓ | `mode=ok/stripped_invalid/appended_default/no_sources/disabled`（可组合）、`source_count`、`found[]/cited[]/stripped[]` 引用编号 |
| `memory` | ✓ | 会话写入情况 |
| `total` | ✓ | 端到端总耗时 |

trace 同时存进会话消息，`/ui` 问答调试页签逐层展开渲染。Agent 模式（`/api/chat/agent`）trace 不同：核心是一条 `agent` 步骤，`detail.turns[]` 逐轮记录 `{turn, ms, mode(tool/final/forced_final/protocol_fallback), thought, tool, args, observation}`。

## 9. 已知边界

- **LLM 重排/改写各多一次 LLM 往返**：LongCat 实测单次 3~11s，重排是端到端最大耗时项；对延迟敏感可 `LLM_RERANK=False`（RRF 兜底质量已可用）。Agent 模式耗时 = 轮数 × LLM 往返，通常比 `/query` 慢数倍，适合复杂多跳问题而非常规问答。
- **评估基线在 tiny 语料上**：11 条金标、4 个文档，两通道指标全 1.0，区分度有限；价值在于改动后防回退对照，语料扩大后需补充困难样本。
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

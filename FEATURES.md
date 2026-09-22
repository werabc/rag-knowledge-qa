# 功能文档 — RAG 知识库问答系统

> 版本：v1.3 · 更新日期：2026-09-22 · 对应提交：P1 本地重排 `3033f51` / P2 结构分块（本次）

## 1. 系统概览

本地部署的检索增强问答系统：上传文档（含无文本层的中文扫描件，自动 OCR）→ 结构优先切块（标题/空行分节段，PDF 带页码元数据）→ 向量化入库 → 查询改写（多轮指代消解）→ 混合检索（向量 + BM25，RRF 融合）→ 重排（默认本地 cross-encoder）→ 拼接上下文 → LLM 生成（OpenAI 兼容接口，支持 **SSE 流式**，未配置时抽取式回退）→ 引用核验防幻觉 → 多轮会话记忆 + 跨会话长期记忆。另提供 **Agent 模式**（ReAct 循环，LLM 自主决定检索次数与工具）。检索质量有 29 条六类金标（含对抗/多跳/扫描件OCR/不可回答拒答）+ `--strict` 回归门禁。全程带链路 trace，可在 `/ui` 面板可视化。

Agent 能力按 L1-L5 分级规范建设，见 `docs/AGENT_SPEC.md`；当前 L1-L5 全部落地。

## 2. 架构

```
                        ┌──────────────────────────────────────────┐
 上传 .txt/.pdf/.docx   │                FastAPI (app/main.py)     │
 ─────────────────────► │  /api/v1/documents/*  /api/v1/chat/*  /ui │
                        └──────┬───────────────────┬───────────────┘
                               │                   │
                     DocumentService            QAService / AgentService
                     ├ 文本提取(PyMuPDF逐页/docx)  ├ 查询改写(指代消解, LLM)
                     │ 扫描页→rapidocr中文OCR     │
                     ├ 切块(structure/300)         ├ 向量召回 ──► VectorStore ──► ChromaDB(512维,cosine)
                     ├ 写向量库 + BM25增量        ├ BM25召回 ──► BM25Index(内存, jieba分词)
                     └ 台账 documents.json        ├ RRF融合(k=60, 召回池8) → 重排(ce本地) → top4
                       分块明文 chunks/*.json     ├ 上下文拼接 [资料N] + 长期记忆注入system prompt
                       {text,page_num,ocr,section}├ LLM生成(LongCat) / 抽取式回退
                        Agent模式(L3)：同一LLM在 ├ 会话记忆 sessions.json
                        ReAct循环(≤5步)里自主调  └ 长期记忆 MemoryService(L4)
                        kb_search/kb_stats/         ├ 答后异步抽取事实 → longterm.json
                        session_history 工具        └ 按词重叠召回

                        评估(L5)：eval/golden_set.json 29条六类金标(含扫描件OCR)
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
| 文档服务 | `app/services/document_service.py` | 提取（PyMuPDF 逐页+扫描页 rapidocr 中文 OCR/docx/txt）/结构优先切块（CHUNK_MODE）/入库/删除/台账持久化/孤儿恢复/全量重建 reindex_all |
| 向量存储 | `app/services/vector_store.py` | chromadb 1.x PersistentClient，cosine HNSW，自定义 EF 接入，recreate_collection |
| 嵌入服务 | `app/services/embeddings.py` | 按配置加载 sentence-transformers；bge 查询前缀；失败回退内置 MiniLM |
| BM25 | `app/services/bm25_index.py` | jieba 分词倒排 + Lucene idf 公式 BM25；启动时从台账+分块明文重建 |
| 问答服务 | `app/services/qa_service.py` | 查询改写→检索→融合→重排(ce/llm/off)→上下文→生成→记忆 主流程 + trace 采集；`hybrid_search` 供 Agent 复用 |
| 重排服务 | `app/services/reranker.py` | 本地 cross-encoder（bge-reranker，CPU，懒加载单例，to_thread），`ce_rerank` 打分排序 |
| Agent 服务 | `app/services/agent_service.py` | L3：ReAct 循环（JSON-in-text 协议），LLM 自主调用 kb_search/kb_stats/session_history，步数上限+强制收口+解析兜底 |
| 长期记忆 | `app/services/memory_service.py` | L4：答后异步 LLM 抽取原子事实、去重落盘 longterm.json，按词重叠召回注入 prompt |
| 检索评估 | `scripts/evaluate_retrieval.py` | L5：跑 golden set，输出 RRF 与 RRF+重排双通道 hit@1/hit@4/MRR |
| 文档 API | `app/api/endpoints/documents.py` | 上传（流式限流+文件名清洗）、列表、详情、删除、分块查看、reindex、统计 |
| 问答 API | `app/api/endpoints/chat.py` | 查询、Agent 查询、会话增删查、历史、统计、清空、长期记忆增删查 |
| 可视化面板 | `app/static/index.html` | 三页签：知识库（分块带 页码/OCR 徽标） / 对话记忆（含长期记忆卡片）/ 问答调试（全链路 trace、来源带 页码/OCR/被引用 徽标、流式打字机、Agent 逐 turn） |

## 4. API 参考（v1.2 起统一 `/api/v1` 前缀）

**错误契约**：所有失败响应为 `{"error": {"code", "message", "detail"}}`，状态码语义化（400 参数错 / 404 不存在 / 409 冲突 / 413 超限 / 500 内部错）。删除成功返回 **204 无响应体**。列表端点统一分页信封 `{items, total, page, size}`。契约回归：`python -X utf8 scripts/api_contract_test.py`（26 项矩阵）。

### 文档管理 `/api/v1/documents`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/upload` | multipart 上传 `.txt/.pdf/.docx`；PDF 逐页提取，无文本层的扫描页自动 OCR（页码+ocr 标记入元数据）；400 unsupported_file_type / 413 file_too_large |
| GET | `/` | 文档台账列表（分页 `?page=&size=`，size≤100） |
| GET | `/{doc_id}` | 单个文档详情；404 document_not_found |
| GET | `/{doc_id}/chunks` | 该文档全部分块明文，JSON 数组，每块 `{text, page_num, ocr, section}`（非 PDF 页码为 null；旧格式纯字符串自动升级） |
| DELETE | `/{doc_id}` | 删向量分块 + BM25 + 台账 + 分块明文；成功 204 |
| POST | `/reindex` | **用当前 embedding 模型全量重建向量库+BM25**（切换模型后必调，见 §7）；并发再入 409 |
| GET | `/stats/summary` | 文档数/分块数/总大小/类型分布 |

### 智能问答 `/api/v1/chat`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/query` | 入参 `{question, session_id?, use_history=true}`；返回 `{answer, sources[]（含 cited 标记）, confidence, session_id, trace[]}` |
| POST | `/stream` | **SSE 流式问答（G2）**：同 `/query` 入参，响应 `text/event-stream`，事件 `step / token / citation / done / error`（协议见 §8）；`/query` 即消费同一生成器取 `done` |
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

向量分块 id 规则：`{doc_id}_chunk_{i}`；metadata 含 `doc_id/chunk_index/filename/file_type/upload_time`，PDF 分块额外带 `page_num/ocr`（扫描件回答可标注「第N页（扫描件OCR）」），所有分块带 `section`（结构节号，small-to-big 预留：检索小块、生成时可回查父节全文）。

## 6. 配置项（.env）

| 变量 | 当前值 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | （LongCat key，勿入库） | 为空则走抽取式回答 |
| `OPENAI_API_BASE` | `https://api.longcat.chat/openai/v1` | OpenAI 兼容端点 |
| `LLM_MODEL` | `LongCat-2.0` | 生成模型 |
| `EMBEDDING_MODEL_NAME` | `models/bge-small-zh-v1.5` | 本地路径=加载 sentence-transformers；`all-MiniLM-L6-v2`=chroma 内置 ONNX |
| `CHUNK_MODE` | `structure` | 切块策略：structure=标题/空行结构优先 / fixed=固定字符数（改策略需删文档重传生效） |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 1000 / 200 | 目标块大小与 fixed 模式重叠；structure 模式金标实测 300 最优 |
| `SEARCH_K` | 4 | 融合后进入上下文的分块数 |
| `HYBRID_BM25` | True | 双路召回开关 |
| `CITATION_VERIFY` | True | 生成后引用核验（防幻觉）开关 |
| `QUERY_REWRITE` | True | 指代消解改写开关 |
| `RERANK_MODE` | `ce` | 重排通道：`ce`=本地 cross-encoder / `llm`=LLM listwise / `off`=不重排 |
| `RERANKER_MODEL` | `models/bge-reranker-base` | ce 通道的本地权重目录（需自行下载，见 README） |
| `RERANK_CANDIDATES` | 8 | 召回池大小（重排输入条数） |
| `AGENT_MAX_STEPS` | 5 | L3 Agent ReAct 循环最大轮数，超限强制收口 |
| `LONGTERM_MEMORY` | True | L4 长期记忆开关（抽取+召回注入） |
| `CHROMA_PERSIST_DIRECTORY` / `CHROMA_COLLECTION_NAME` | `./vector_db` / `documents` | 向量库位置 |
| `DOCUMENT_STORAGE_PATH` / `MAX_UPLOAD_SIZE_MB` | `./data` / 50 | 文档存储 |

## 7. 关键机制

### 查询改写（指代消解）
带会话历史的追问先经 LLM 改写成自包含查询再检索（「那它的上线时间呢？」→「朱雀系统的上线时间和并发规格是什么？」）。首轮/关历史/未配 LLM 时跳过；改写失败用原问题。

### 重排（`RERANK_MODE` 三通道）
RRF 融合取召回池 8 条后进入重排，截取 top4 进上下文。默认 `ce`：本地 cross-encoder（`bge-reranker-base`，sentence-transformers CPU 推理，懒加载单例，`asyncio.to_thread` 避免阻塞事件循环），对每对 (问题, 候选) 打相关度分排序，模型加载失败自动回退 RRF 顺序（trace 标 `ce_fallback`）。`llm`：LLM listwise 重排作对照——对召回池只输出部分编号做容错（已列出的置顶、其余按 RRF 原序补齐），解析失败沿用 RRF 顺序。`off`：直接按 RRF 截断。ce 通道实测：单次打分 ~1.7s（对比 LLM 往返 3~11s），把向量+BM25 都排错的文档从第 4 顶到第 1。

### 结构优先切块（`CHUNK_MODE=structure`）
`split_structure`：markdown 标题行分节 → 节内空行分段 → 段按序合并到 `CHUNK_SIZE`（永不跨节合并）；单段超限交给固定 splitter 兜底。每块带 `section` 节号（small-to-big 预留）。P2 实验（`scripts/experiment_chunking.py`，进程内隔离库、不走 LLM，5 配置×26 题，数据在 `eval/chunk_experiment.json`）：kb_sample 这类"单文档单大块"把多条无关事实挤进同一向量，同义问法位次被稀释——structure@300 把它切成 3 块后，重排通道 hit@1 0.923→0.962、MRR 0.955→0.974、**paraphrase 类 hit@1 0.8→1.0**（「值班升级找谁」2→1），其余类别全部持平；@200/@500 时纯 RRF 通道 MRR 反而低于基线（0.892/0.897 < 0.905），故选 300。改块大小只需 `.env` 调 `CHUNK_SIZE` + `scripts/reload_corpus.py` 重灌 + 重跑门禁。

### 混合检索（RRF）
向量路与 BM25 路各出候选，按分块 id 去重，`rrf = Σ 1/(60+排名)`，降序取 top `SEARCH_K`。向量管语义近似（同义改写也能命中），BM25 管关键词精确命中（型号、人名、编号）。`confidence` 取向量路最高相似度。

### 中文嵌入
bge 系列查询侧自动加前缀「为这个句子生成表示以用于检索文章：」（文档侧不加），中文短问句相似度显著优于 MiniLM（实测正确文档向量分 0.65~0.77，MiniLM 时代约 0.18~0.54 且排序不稳）。

### Agent 模式：ReAct 工具循环（L3）
`POST /api/v1/chat/agent`：LLM 在循环里自主决定「查什么、查几次、何时收口」。协议为 JSON-in-text（模型无关，不依赖 function-calling API）：每轮模型输出 `{"thought":…,"tool":…,"args":…}` 调工具，或 `{"thought":…,"final":…}` 收敛。工具三个：`kb_search`（复用 hybrid_search 双路召回+RRF）、`kb_stats`（库规模）、`session_history`（本会话历史）。防线：≤`AGENT_MAX_STEPS` 轮、达上限 for-else 强制收口、JSON 解析失败按 protocol_fallback 处理；各轮检回的分块去重汇总为 sources，与普通模式共用同一条记忆落盘管线。实测复合对比问题会自动规划 2 次不同角度的 kb_search。

### 长期记忆（L4）
每轮回答后 `asyncio.create_task` 异步让 LLM 从对话中抽取原子事实（如用户身份、项目名），归一化去重后写 `data/longterm.json`（上限 200 条 FIFO）。新问题按 jieba 分词与事实计算词重叠分（`overlap/√|fact_tokens|`）召回 top 事实，以「【长期记忆】」段注入 system prompt。因此 `use_history=false` 的全新会话仍能认出用户身份（实测通过）。可查看/手动添加/删除（`/api/v1/chat/memories` + 面板卡片）。

### 检索评估（L5/G3）
`eval/golden_set.json`：**29 条**金标，六类——`direct` 直查(11) / `paraphrase` 同义改写(5) / `adversarial` 对抗：跨文档近似句抢位(4) / `multihop` 多跳：expect 为文档列表任一命中(3) / `ocr` 扫描件 OCR 命中：期望检索到 scan_xuanhe.pdf(3) / `unanswerable` 不可回答：期望拒答(3)。`python -X utf8 scripts/evaluate_retrieval.py` 逐条跑 `/api/v1/chat/query`，双通道（RRF 序 / 重排后序）算 hit@1 / hit@4 / MRR，不可回答题用拒答词典正则匹配答案判 `refusal_accuracy`，分类别指标 + 逐题明细写入 `eval/report.json`。

**回归门禁**：`--update-baseline` 把核心指标固化为 `eval/baseline.json`；`--strict` 逐叶子对比基线，任一指标低于即 **exit 1 拦截**。实测：`RERANK_MODE=off` 重启后 strict 点名 `with_rerank.hit@1`、`adversarial` 等三项拦截；恢复配置后 strict 通过。当前基线（P2 后）：重排通道 hit@1 0.962 / hit@4 1.0 / MRR 0.974、仅 RRF hit@1 0.846 / MRR 0.905、拒答 1.0；paraphrase 类经结构分块已达 1.0，adversarial 0.75 为 ce 通道跨语言抢位边界（见 §9）。

### PDF 逐页提取 + 扫描件 OCR（G4）
PyMuPDF 逐页 `get_text` 并按页切块（跨页不混块，页码进元数据）。页文本层 <20 字符且含图片 → 判为扫描页：`page.get_pixmap(dpi=200)` 转 PNG 交 rapidocr（onnxruntime，懒加载单例）识别中文。每块明文以 `{text, page_num, ocr}` 落 `chunks/*.json` 并写进 chroma metadata；上下文资料头标注「文件名，第N页（扫描件OCR）」，面板来源徽标与 `/chunks` 端点同步展示。实测零文本层两页扫描 PDF（`scripts/make_scan_pdf.py` 生成）：上传 28s（含 OCR 模型冷加载），问答「年度维保费+负责人」正确答出 90 万元/陈立，两条来源均带 页码+OCR+被引用 徽标。

### 切换 embedding 模型（三步）
1. `.env` 改 `EMBEDDING_MODEL_NAME`（模型名或本地目录）；
2. 重启服务（不同模型维度不同，旧库不兼容）；
3. `POST /api/v1/documents/reindex` —— 从 `data/chunks/` 明文全量重嵌入，无需重新上传。

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
| `generation` | ✓ | `mode=llm_stream`、`model`、`base_url`、`history_messages_used`、`prompt_chars`、`prompt_preview`(前500字)；流式失败回退 `extractive_fallback`+`error`，未配 key 时 `extractive` |
| `citation` | ✓ | `mode=ok/stripped_invalid/appended_default/no_sources/disabled`（可组合）、`source_count`、`found[]/cited[]/stripped[]` 引用编号 |
| `memory` | ✓ | 会话写入情况 |
| `total` | ✓ | 端到端总耗时 |

trace 同时存进会话消息，`/ui` 问答调试页签逐层展开渲染。Agent 模式（`/api/v1/chat/agent`）trace 不同：核心是一条 `agent` 步骤，`detail.turns[]` 逐轮记录 `{turn, ms, mode(tool/final/forced_final/protocol_fallback), thought, tool, args, observation}`。

### SSE 流式协议（`POST /api/v1/chat/stream`）

每帧 `event: <名>\ndata: <JSON>\n\n`，事件时序：

| 事件 | data | 说明 |
|---|---|---|
| `step` | 单条 trace 步骤对象 | 每完成一步实时推送（query_rewrite→retrieval→rerank→context→generation→citation→memory），面板据此逐步点亮 |
| `token` | `{t: "增量文本"}` | LLM 生成段逐 token 推送；抽取式回退时整段一条 |
| `citation` | `{detail, answer}` | 引用核验后的最终答案与明细（流式答案被规则改写时客户端据此纠正） |
| `done` | 与 `/query` 响应同构的完整对象 | 收尾；会话记忆此时已落盘 |
| `error` | `{code, message}` | 生成器异常兜底（正常流程不出现） |

面板勾选「流式输出（SSE）」即走此端点：token 打字机追加 + trace 实时点亮，done 后切标准渲染。契约测试断言事件序列（step 开头、token≥1、citation 恰好 1、done 收尾）。

## 9. 已知边界

- **`RERANK_MODE=llm` 时重排多一次 LLM 往返**：LongCat 实测单次 3~11s，是端到端最大耗时项；默认 `ce` 通道本地打分 ~1.7s，无此问题（首次查询另含 ~26s 模型冷加载）。`QUERY_REWRITE` 的改写也是一次 LLM 往返。Agent 模式耗时 = 轮数 × LLM 往返，通常比 `/query` 慢数倍，适合复杂多跳问题而非常规问答。
- **ce 通道不吃跨文档/跨语言推理**：cross-encoder 逐对 (问题,片段) 打分，看不到片段间关系。实测「旗舰产品单节点能扛多少并发？」（期望 kb_sample 英文片段，decoy 是中文"单节点并发"近似句）：中文 decoy 表面词面分 0.34，英文目标片段仅 0.009 排第 3——LLM listwise 通道曾靠跨文档推断「旗舰产品=QuantumLeap」排第 1。该题最终答案仍正确（目标片段进了上下文且被引用），仅位次回退；为此 `adversarial.hit@1` 基线 1.0→0.75（整体 hit@4 1.0、MRR 0.955 均超旧基线），属换通道的刻意取舍。
- **评估仍在 tiny 语料上**：29 条六类金标（含对抗/多跳/扫描件OCR/不可回答）已比 v1.0 的 11 条有区分度（paraphrase 类 hit@1 仅 0.6），但 5 文档池子仍小；拒答判定基于词典正则，LLM 措辞变化可能造成同配置下 ±1 题抖动。
- **BM25 全内存**：启动时从台账+分块明文重建，语料规模适合万级分块以内；检索为线性扫描词频表，数据量大需换倒排跳过。
- **reindex 是破坏性重建**：先删集合再重灌，期间检索结果不完整；分块明文丢失的文档无法恢复（原始文件上传后即删，只保留明文）。
- **单进程文件存储**：sessions/documents 为 JSON 整文件读写，无并发锁，不适合多 worker 横向扩展。
- **OCR 边界**：扫描页判定是启发式（文本层<20字符且含图片），排版复杂/手写/表格截图识别质量有限；rapidocr 首次调用有模型加载冷启动（整文件 28s 里占大头），逐页位图按 200dpi，过大页面内存敏感。表格结构仍不保留。
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

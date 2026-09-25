# 开发计划 v1.4（2026-09-25 定）

> 进度：P1-P4 ✅（数字见各节实测行）。本版新增：全仓库逐文件代码审查（2026-09-25）发现的 16 项问题，按风险排成 Q1-Q4 四个修复阶段；原 P5 顺延为 Q5。

## 代码审查发现（全部带 file:line 证据，复核过当前代码）

按"真会出事 → latent 坑 → 卫生问题"排序：

| # | 问题 | 位置 | 后果 |
|---|------|------|------|
| F1 | 删除文档的编排放在 endpoint：先删向量、再删台账，非原子 | documents.py:113-115，document_service.py:301-312 | 台账删除失败时向量已没了：文档留在台账却永远检索不到，启动孤儿认领救不回来 |
| F2 | 上传临时文件名 `temp_{safe_name}`，同名并发互相覆盖 | documents.py:37-49 | 两人同时传同名文件（深测时 4 并发实测过）内容串台；413 中断时 finally 删掉对方正在写的文件 |
| F3 | 嵌入模型加载失败静默回退内置 MiniLM | embeddings.py:65-75 | 配置说 bge（512 维）实际集合是 MiniLM（384 维），只有一条日志；之后 reindex 或维度错乱报错，运维无感知 |
| F4 | BM25 独路命中的条目 metadata 只有 doc_id/filename | qa_service.py:256-259 | 生成侧来源标签丢"第X页/OCR"（qa_service.py:120-126,208-209），UI 页码列为空；深测已证实 BM25 独路命中常见 |
| F5 | 会话内存无上限 + 每查询全量重写 sessions.json | qa_service.py:31-55,181 | trace 整体嵌进每条 assistant 消息后全文件落盘，会话一多写放大严重、内存只进不出 |
| F6 | `ce_rerank` 的 top_k 参数是死的：`_predict` 内部已按 `settings.SEARCH_K` 截断 | reranker.py:33,44 | 现在唯一调用方恰好传 SEARCH_K 所以没炸；哪天有人传大 top_k 会静默拿不够数 |
| F7 | confidence 只取 rerank 前的向量分最大值 | qa_service.py:196 | 位次以 ce_score 为准了，置信度却还看向量分——重排把误召回顶上来时 confidence 虚高/虚低都对不上 |
| F8 | 长期记忆抽取 fire-and-forget：create_task 不留引用、无并发上限 | memory_service.py:88-94 | asyncio 官方明示无强引用的 task 可能被 GC 掉；高并发时每查询一个 LLM 往返无节流 |
| F9 | `.md` 走通用 else 分支：utf-8 + errors=ignore | document_service.py:241-244 | gb18030 编码的 md 静默丢字；`.txt` 反而有 `_extract_txt` 编码探测（285 行） |
| F10 | `_extract_content` 的 .pdf 分支返回 List 却标注 -> str | document_service.py:221,235-236 | 当前调用链走 `_extract_pages` 到不了这里，纯死代码且误导维护者 |
| F11 | 启动事件用已废弃的 `@app.on_event`；静态目录相对路径 `"app/static"` | main.py:44-46 | 非 FastAPI 推荐（无 shutdown 钩子）；从其他 cwd 起进程直接 mount 失败 |
| F12 | 版本号三处手写：main.py 两处 "1.2.0" + 描述，FEATURES 已到 v1.3 | main.py:19,62,72 | 已开始漂移，无单一事实源 |
| F13 | 上传全程同步：OCR+embedding 都在请求里 | documents.py:51-52 | 深测 1.4MB 语料单本上传占住 worker 几十秒；50MB 上限下单请求可挂起数分钟 |
| F14 | index_failed 的文档照常写台账+明文，无人提示要 reindex | document_service.py:196-210 | 台账在、UI 状态黄牌，但检索必 miss；reindex 能救却没入口提示 |
| F15 | agent 协议违约时把模型原文（可能是半截 JSON）直接当答案写入会话记忆 | agent_service.py:68-73 | 下轮历史注入时污染上下文 |
| F16 | BM25 search 对全部 doc_tf 线性扫 | bm25_index.py:85-100 | 3618 块无感，10⁵ 块每查询秒级；FEATURES §9 已登记但无量化退化点 |

卫生项（不单列阶段）：`app/core`、`app/services/{chunking,evaluation,query_understanding,reranking,retrieval}` 只剩 `__pycache__` 空壳（源码早已删，未入库），本地清目录即可；`deep_test/fetch_wiki.py` 死路脚本本次已删（未跟踪）。

## P1 本地 cross-encoder 重排 ✅（`3033f51`）

- 方案：`bge-reranker-base` CPU 推理为新通道，`RERANK_MODE = ce | llm | off`，默认 ce。
- 实测：热路径端到端 5.8s（原 30~50s）；重排 hit@1 0.923→0.962、hit@4 1.0。

## P2 分块策略实验 ✅（`48562ac`）

- 实测：structure@300 下 paraphrase hit@1 0.6→1.0，重排 hit@1 0.923→0.962（eval/chunk_experiment.json）。

## P3 多轮对话评测 ✅（`dac2746`）

- 实测：改写开 multi_turn hit@1/MRR = 1.0/1.0；改写关 0.5/0.688（hit@4 仍 1.0）。金标 39 题，基线 0.971/1.0/0.98。

## P4 生成质量量化 ✅（`6948a92`）

- 实测：13 题 22 条句级论断 22/22 有据，规则层漏检 0。边界：tiny 语料、评审与生成同源模型。

## Q1 检索链路一致性（F4+F6+F7，半天）

- 方案：
  - `_rrf_merge` BM25 独路条目回查分块明文补齐 `page_num/ocr/chunk_index`（document_service 已有 `{doc_id}_chunk_{i}` 索引结构，bm25_index.py 的 docs 里可直接带出来）；
  - `reranker._predict` 删除内部 `SEARCH_K` 截断，截断职责交 `ce_rerank(top_k)`；
  - confidence 改用重排后首位分数（ce 模式取 `ce_score`，off/llm 模式维持向量分）。
- 验收：`--strict` 全绿且基线不降；挑一道 BM25 独路题（金标 paraphrase 值班题）trace 里 sources 出现页码；`RERANK_MODE=off` 与 `ce` 各跑一次 confidence 对比表贴进提交说明。
- 涉及：qa_service.py、reranker.py、bm25_index.py。
- 风险：动检索链路，必须 strict；置信度语义变了，UI"置信"徽章含义要同步 FEATURES 一句话。

## Q2 生命周期健壮性（F1+F2+F3+F5，1 天）

- 方案：
  - 删除编排下沉 `document_service.delete_document`：先摘台账、再向量/BM25/明文，任一步失败返回结构化错误并保住可重试状态（endpoint 只调用）；
  - 临时文件 `temp_{uuid4}_{safe_name}`，写失败即删自己的；
  - 嵌入加载失败不再静默：`make_embedding_function` 返回 None 时向上传递"降级"标记，startup 日志 ERROR + `/health` 增加 `embedding_degraded: true` 字段（不阻断启动，但让监控看得见）；
  - 会话加 `MAX_SESSIONS=200` LRU（超出丢最久未活跃，先落盘再淘汰）、`MAX_MESSAGES_PER_SESSION=100` 截尾；trace 只保留最近 20 会话的，旧会话剥离 trace 字段。
- 验收：并发 4 路上传同名 5KB 文件互不干扰（脚本跑通+台账 4 条）；删文档中途模拟台账写失败后重试可收敛（手动注入一次）；压 250 个会话后 sessions.json 大小与单查询写入字节数前后对比表；strict 全绿。
- 涉及：documents.py、document_service.py、embeddings.py、main.py（health）、qa_service.py。
- 风险：LRU 淘汰会让老会话在 UI 消失——验收时写明是预期行为，金标 turns 用例用新 sid 不受扰。

## Q3 API 与工程卫生（F9+F10+F11+F12+F14+F15，半天）

- 方案：`.md` 与 `.txt` 共用 `_extract_txt`（编码探测）；删 `_extract_content` pdf 死分支并收紧签名；`on_event` 改 lifespan、静态目录用 `Path(__file__)` 绝对路径；版本号单源（`app/__init__.py` `__version__`，main/UI footer 读取）；上传返回 `index_failed` 时 detail 带 "调用 /reindex 可修复"；agent `protocol_fallback` 时回答前加标记 `[未走协议]`，历史注入时跳过该轮（trace mode 字段已有，注入处过滤）；本地清 `__pycache__` 空壳目录。
- 验收：gb18030 编码的 .md 上传后 chunk 明文无 U+FFFD/丢字（造一个测试文件）；从 `C:\` 下任意 cwd 起服务 `/ui` 可访问；`/docs` 与首页与 FEATURES 版本一致；strict 全绿。
- 涉及：document_service.py、main.py、agent_service.py、config 不动。
- 风险：低，纯局部。

## Q4 吞吐与杂项（F8+F13+F16，可并入 Q5 一起做）

- 方案：`spawn_extraction` 用模块级 set 持引用 + `done_callback` 释放，并加 `asyncio.Semaphore(2)` 节流，满则跳过本轮抽取（丢弃计数写日志）；上传文档大小软提示：`.env.example`/README 标注"50MB ≈ 单请求 N 分钟"，不做异步任务队列（明确不做项）；BM25 倒排索引（词→chunk posting list）**仅在 Q5 压测显示 10⁵ 块检索退化后再做**，不提前优化。
- 验收：连续 20 查询后无未完成任务堆积（日志计数）；压测脚本能复现退化点或证明无退化。
- 涉及：memory_service.py、README/.env.example、（条件触发）bm25_index.py。

## Q5 规模与 CI（原 P5，1~2 天，量力）

- 合成语料压测：生成 500/1000 文档（含长尾），量上传吞吐、检索 P95、BM25 内存曲线、sessions.json 尺寸，结论进 FEATURES 已知边界（Q4 的 BM25 触发判据从这里来）。
- CI（GitHub Actions）：`api_contract_test.py` + 无 key 抽取式冒烟（`OPENAI_API_KEY` 置空即走 extractive 回退）+ 带本地模型环境下起服务跑检索评估 `--strict`（权重下载放缓存步骤，下载不到就跳过并在报告注明）；不跑依赖 LongCat 的生成类评估。
- 结构化访问日志：每查询一行 JSON（耗时分解/命中通道/confidence），先写文件，面板二期。

## 明确不做

鉴权/多租户/多 worker；Agent 流式；版面级表格解析；自动调参/自训练；上传异步任务队列；会话存储数据库化（JSON+LRU 够用）；在压测前给 BM25 上倒排索引。

## 执行约定（沿用）

每阶段独立提交；验收看真实产出（答案原文、位次表、耗时数字），不看状态码；动检索链路必跑 `--strict`；增删语料必同步金标并 `--update-baseline` 写理由。评估/服务期间不随手改 `app/**/*.py`（uvicorn reload 会打断在途请求）。

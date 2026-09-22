# RAG 知识库问答系统

本地部署的中文知识库问答服务。完整链路：文档上传 → 逐页提取/分块（扫描页自动 OCR）→ Chroma 向量召回 + jieba BM25 双路 → RRF 融合 → 重排（默认本地 cross-encoder）→ 生成 → 引用核验 → 会话/长期记忆。全链路 trace 可视化。

功能细节、存储布局、trace 字段见 [FEATURES.md](FEATURES.md)；能力分级与工程化基线见 [docs/AGENT_SPEC.md](docs/AGENT_SPEC.md)。

## 快速开始

```bash
pip install -r requirements.txt        # Windows 可加 -i https://pypi.tuna.tsinghua.edu.cn/simple
copy .env.example .env                 # 填 OPENAI_API_KEY / OPENAI_API_BASE / LLM_MODEL（任意 OpenAI 兼容接口）
python run.py
```

- 面板：http://127.0.0.1:8000/ui （知识库管理 / 对话记忆 / 问答 trace 调试）
- API 文档：http://127.0.0.1:8000/docs
- 不配 LLM key 也能跑：回答自动降级为抽取式（不依赖外部服务）
- 嵌入模型默认加载本地目录 `models/bge-small-zh-v1.5`（需自行下载权重；.gitignore 已排除）。换嵌入模型后必须 `POST /api/v1/documents/reindex` 全量重建向量库
- 重排模型默认加载 `models/bge-reranker-base`（同样不入库，缺失时自动回退 RRF 顺序）。权重可从 HF 镜像获取，如 `https://hf-mirror.com/BAAI/bge-reranker-base/resolve/main/model.safetensors` 等文件放入该目录；`RERANK_MODE=llm|off` 可不装
- 演示语料在 `test_data/`（含 4 个 txt）；扫描件演示用 `python scripts/make_scan_pdf.py` 生成
- 切块默认 `CHUNK_MODE=structure`（标题/空行结构优先），金标语料实测 `CHUNK_SIZE=300` 最优；改切块策略后需 `python scripts/reload_corpus.py` 重灌语料（reindex 不重切块）

## 主要端点（/api/v1）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/documents/upload` | 上传 PDF/DOCX/TXT/MD，返回 doc_id 与分块数 |
| GET | `/documents` | 文档列表（分页：page/size） |
| GET | `/documents/{id}/chunks` | 分块明文（含 page_num/ocr 元数据） |
| POST | `/documents/reindex` | 换嵌入模型后重建向量库 + BM25 |
| POST | `/chat/query` | 问答（非流式），返回答案/来源/完整 trace |
| POST | `/chat/stream` | 问答（SSE：step → token → citation → done） |
| POST | `/chat/agent` | ReAct Agent，LLM 自主决定检索次数与收口 |
| GET/DELETE | `/chat/memories` | 跨会话长期记忆（答后自动抽取，可查可删） |

错误统一为 `{"error": {"code", "message", "detail"}}`，状态码 400/404/409/413/502 语义化。

## 验证与回归

```bash
python scripts/api_contract_test.py               # 26 项端点×状态码契约矩阵
python -X utf8 scripts/evaluate_retrieval.py      # 29 条六类金标：hit@k / MRR / 拒答正确率
python -X utf8 scripts/evaluate_retrieval.py --strict            # 回归门禁：任一核心指标低于 eval/baseline.json 则退出码非零
python -X utf8 scripts/evaluate_retrieval.py --update-baseline   # 有意变更语料/配置后固化基线
```

改动检索/重排/嵌入链路后必须跑 `--strict`。增删知识库文档必须同步 `eval/golden_set.json` 并刷新基线。

## 目录结构

```
app/
  api/endpoints/     documents.py / chat.py（/api/v1 路由）
  services/          qa_service（主流水线+trace）· agent_service（ReAct）· document_service
                     （提取/分块/OCR）· vector_store（Chroma）· bm25_index · embeddings · reranker · memory_service
  static/            /ui 面板（单文件）
  config.py errors.py main.py models/schemas.py
scripts/             api_contract_test · evaluate_retrieval · compare_rerank ·
                     experiment_chunking · reload_corpus · make_scan_pdf
deep_test/           真实语料深测（run_deep_test + 28 题；corpus/results 不入库）
eval/                golden_set.json · baseline.json · report.json
test_data/           演示语料（txt）
docs/                AGENT_SPEC.md（能力分级 L1-L5 + 工程化基座）
data/ vector_db/ models/ .env   运行时产物与密钥，均不入库
```

## 边界

- 单进程、无鉴权、无多租户：定位本地学习/演示，不打算做
- Agent 模式不流式；SSE 仅覆盖固定流水线
- OCR 表格页按行拼接，不做版面还原

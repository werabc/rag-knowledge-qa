# 综合开发目标 v1.2（2026-09-22 定）

> 执行约定（沿用已验证的工作方式）：每个阶段独立提交、真实产出验证（curl 实测 + /ui 截图，不看状态码看内容）、文档同步；顺序即依赖顺序，REST 规范先行，后面功能都长在规范 API 上。

## G1 REST API 规范化（地基）

现状问题：路径无版本、错误直接抛 HTTPException(detail=中文串)、列表不分页、响应模型一半是裸 Dict。

1. 版本前缀 `/api/v1/*`，面板与文档全部切过去（不留 /api 旧别名，内部代码一次改净）。
2. 统一错误契约：`{"error": {"code": "doc_not_found", "message": "...", "detail": {...}}}`；状态码语义化——400 参数错 / 404 不存在 / 413 超限 / 409 冲突（重复 reindex）/ 502 上游 LLM 挂。
3. 分页：`GET /api/v1/documents?page=1&size=20`、`GET /api/v1/chat/sessions?page=&size=`，返回 `{items, total, page, size}`。
4. 所有端点补齐 Pydantic response_model + OpenAPI summary/tags/example，`/docs` 可直接当调试台用。
5. 语义修正：DELETE 成功返回 204；资源不存在时删除返回 404。

**验收**：`scripts/api_contract_test.py` 跑端点×状态码矩阵全绿；`/docs` 截图；面板回归无错。

## G2 SSE 流式输出（体验）

1. `POST /api/v1/chat/stream`：SSE 事件流——`event: step`（trace 逐步推送，检索完成即可见）→ `event: token`（LLM `stream=True` 逐 token 透传）→ `event: citation`（核验结果，流结束后补发）→ `event: done`（完整响应 JSON 含 session_id）。抽取式回退模式逐块推送。
2. 会话落盘与长期记忆抽取在 done 后照常触发（流式不绕开质量闭环）。
3. 面板：打字机渲染回答，trace 步骤实时点亮；Agent 模式暂不流式（边界写明）。

**验收**：curl -N 收到完整事件序列；面板打字机截图（中途+完成两张）。

## G3 评估深化：困难样本 + 回归门禁

1. golden set 11 → 25+ 条，新增四类困难样本：同义改写问法、跨分块多跳（答案需 2 个 chunk）、对抗诱饵（两个文档都有相似词但只一个能回答）、**不可回答题**（期望行为=拒答）。
2. 指标扩展：除 hit@1/hit@4/MRR 外，加 `answerable_refusal`（不可回答题的拒答正确率，检查答案含"未找到/不知道"类标记）。
3. 回归门禁：`--strict` 模式，任一指标低于 `eval/baseline.json` 记录值 → 退出码非零；每次改动检索/重排/嵌入后必跑。

**验收**：新 report.json + baseline.json 落库；故意关掉 rerank 跑一次 strict 应失败（证明门禁真的拦得住）。

## G4 PDF/OCR 增强（数据入口）

1. PyMuPDF(fitz) 替换 PyPDF2：保留页码，metadata 加 `page_num`，来源展示为 `filename p.12`。
2. 扫描件路径：页面无文本层 → `rapidocr-onnxruntime`（CPU、无 torch、中文好）OCR 出文本再切块；OCR 分块 metadata 标 `ocr=true`。
3. 表格页降级策略：OCR/文本混排按行拼接，不强求结构（边界写明）。

**验收**：造一份中文扫描 PDF（图片转 PDF）实测上传→问答，trace 里可见 ocr 分块；截图。

## G5 收口

- FEATURES.md → v1.2（新端点、SSE 事件表、OCR 链路、评估门禁）；AGENT_SPEC.md 补「工程化分级」小节对照 G1-G4。
- 打标签 v1.2.0；云端推送（前置：用户装好 gh CLI 并 auth login）。

## 明确不做（防过度工程）

- 多 worker/鉴权/多租户（本地学习项目，写进已知边界即可）
- Agent 模式流式、WebSocket 双向流
- 版面还原级 PDF 表格解析（结构表格 → Markdown 是另一篇论文）

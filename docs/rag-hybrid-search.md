# RAG 混合检索与入库边界

## 当前实现

- 默认 `RAG_BACKEND=lexical`，无需数据库即可运行演示。
- 设置 `RAG_BACKEND=pgvector` 后，检索限定在当前课程，并组合全文词项排名与
  pgvector 余弦相似度。
- `TokenHashEmbedder` 是可复现的离线词项哈希向量，只用于打通工程链路和测试，
  不宣称具备语义理解能力。后续经模型、费用和数据合规评审后可替换为正式向量模型。
- 回答证据只来自 `status: reviewed` 且 `rag.eligible: true` 的来源。课程知识点草稿
  在教师审核前不会进入正式索引。

## 本地启用顺序

1. 启动 `infra/compose.yaml` 中的 PostgreSQL。
2. 配置本地 `.env` 的 `DATABASE_URL`，不要提交密码。
3. 执行 `alembic upgrade head` 建表并启用 pgvector。
4. 执行 `python scripts/sync_knowledge_index.py` 同步审核通过的来源。
5. 将 `RAG_BACKEND` 改为 `pgvector` 后启动 API。

同步操作是事务性的：更新当前审核快照，并删除三门课程中已经不在审核快照内的旧片段。
课程隔离在 SQL 查询条件中强制执行，不能跨课程返回证据。

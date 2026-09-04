# RAG 检索评测

评测对象是“证据检索”，不调用大模型，因此结果可重复且不产生模型费用。数据集包含
75 条问题，C 语言、Python、数据结构各 25 条；每门课程分别包含 15 条可回答问题、
5 条知识库外问题和 5 条刻意放错课程的问题。

## 指标定义

- `recall_at_k`：前 K 条是否包含人工标注的预期来源。
- `mean_reciprocal_rank`：预期来源排名的倒数均值。
- `unanswerable_rejection_rate`：知识库外问题没有返回证据的比例。
- `cross_course_rejection_rate`：放错课程的问题没有返回证据的比例。
- `course_isolation_rate`：返回证据全部属于请求课程的比例。

## 当前实测基线

| 后端 | Recall@5 | MRR | 库外拒答 | 跨课程拒答 | 课程隔离 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 内存词法检索 | 100% | 100% | 100% | 100% | 100% |
| pgvector 混合检索 | 100% | 100% | 100% | 100% | 100% |

最新原始结果保存在 `docs/audits/rag-eval-lexical-v4.json` 和
`docs/audits/rag-eval-pgvector-v4.json`。历史版本保留用于说明改进过程，不能用旧报告
替代当前代码的回归结果。

2026-08-26 的 v4 修复消除了中文单字噪声，增加复合问题分句检索，并对明确点名其他
课程的请求执行透明课程域门禁。pgvector 的全文检索改为已转义词项的 OR 查询，避免
多个词项被错误地按全部同时出现处理。两种后端均通过全部 75 条固定用例；该结果只证明
当前测试集上的检索质量，新增课程资料或修改分词规则后仍必须重新回归。

运行方式：

```powershell
python scripts/evaluate_rag.py --backend lexical
python scripts/evaluate_rag.py --backend pgvector
```

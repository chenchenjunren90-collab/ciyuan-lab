# RAG 检索评测 v1

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
| 内存词法检索 | 100% | 100% | 93.33% | 73.33% | 100% |
| pgvector 混合检索 | 95.56% | 95.56% | 93.33% | 80% | 100% |

原始结果保存在 `docs/audits/rag-eval-*-v1.json`，包括全部失败用例编号。当前基线证明
了课程隔离有效，但拒答仍有提升空间；不能把检索到相似片段直接等同于“问题可回答”。
后续应在生成前增加课程意图判定和证据覆盖率阈值，并以本数据集持续回归。

2026-08-26 内容 v3 技术复核后，RAG 来源片段由 13 个增加到 14 个。重新执行同一 75 问
评测后，词法与 pgvector 五项指标均与上表一致，说明新增“算法设计与验证”来源没有造成
检索回归。结果分别保存在 `docs/audits/rag-eval-lexical-v3.json` 和
`docs/audits/rag-eval-pgvector-v3.json`。

运行方式：

```powershell
python scripts/evaluate_rag.py --backend lexical
python scripts/evaluate_rag.py --backend pgvector
```

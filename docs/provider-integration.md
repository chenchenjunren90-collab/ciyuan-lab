# 讯飞 MaaS 模型与检索服务接入

更新日期：2026-09-05。当前路线是 MaaS 托管推理、学科知识库、检索增强、三个逻辑智能体及确定性代码验证。

## 统一推理

学情规划、C语言/Python/数据结构课程辅导、质量监督与受控项目编排，共用
`model_adapters/` 内的讯飞适配器和并发限制。默认模型服务标识为
`xopdeepseekv4flash0731`，必须与实际服务卡一致。

```text
XFYUN_MAAS_BASE_URL=https://maas-api.cn-huabei-1.xf-yun.com/v2
XFYUN_MAAS_MODEL=xopdeepseekv4flash0731
XFYUN_MAAS_TIMEOUT_SECONDS=45
XFYUN_MAAS_MAX_RETRIES=2
```

请求使用 `POST /chat/completions` 和 Bearer 鉴权。模型输出必须通过结构、引用和质量门禁。
适配器为注入的 HTTP 客户端也设置明确超时，瞬态错误有限重试；错误日志不含凭据或学生原文。
课程辅导接口失败时使用证据摘录或明确拒答，不把网络故障说成模型已生成正确答案。

协议依据：[讯飞推理服务 HTTP 文档](https://www.xfyun.cn/doc/spark/%E6%8E%A8%E7%90%86%E6%9C%8D%E5%8A%A1-http.html)。

## MaaS 文档重排

已实现 `model_adapters/xfyun_maas_reranker.py` 与 `rag/reranking.py`。
只有显式配置后才调用官方 `POST /rerank`：

```text
XFYUN_MAAS_RERANKER_ENABLED=false
XFYUN_MAAS_RERANKER_MODEL=
XFYUN_MAAS_RERANKER_API_KEY=
XFYUN_MAAS_RERANKER_CANDIDATE_LIMIT=12
XFYUN_MAAS_RERANKER_TIMEOUT_SECONDS=8
XFYUN_MAAS_RERANKER_MAX_RETRIES=1
```

MODEL 填实际重排服务卡的 modelId，不能使用聊天模型ID或文档示例ID代替。
专用 API Key 留空时复用通用 MaaS Key，前提是该 Key 具有对应服务授权。
真实凭据仅由部署者保管，不能写进此文档、测试、截图或 Git。

处理顺序：当前课程召回最多一组有限候选 → MaaS 返回候选索引与相关度 →
本地验证索引范围、唯一性和分数 → 按相关度重新排序 → 辅导模型与质量监督。
默认候选上限12条，配置最高20条；实际数量受召回结果限制，当前词法后端最多返回10条。超长片段不会被偷偷截断后送出。
重排只改变候选次序，不更换来源、正文、片段ID或原检索分数。
供应商只返回子集时保留未评分候选；服务失败时保留原召回顺序，并在执行记录中标记降级。

协议依据：[讯飞 Embedding 与 Rerank HTTP 文档](https://www.xfyun.cn/doc/spark/Embedding%26Rerank%E6%9C%8D%E5%8A%A1_HTTP%E5%8D%8F%E8%AE%AE.html)。
本轮验证使用 MockTransport 和受控测试输入；尚未验证账户服务授权、实际费用、线上延迟和质量增益。
接入代码不等于该能力已在运行实例开启。

## 数据库与语义索引边界

PostgreSQL/pgvector 用于本地知识持久化和课程隔离；Redis 及学习数据库承担系统自己的状态。
这些存储没有迁往 MaaS。当前向量列是384维，使用本地 TokenHash，不是远程语义 Embedding。

若接入 MaaS Embedding，应先核对真实模型维度与版本，使用独立索引/迁移方案和全量重建，
同时记录 provider、model、dimensions、知识版本及内容哈希；不能截断向量或混用旧索引。
在事务外完成批量向量化，再短事务写入；查询语义向量与文档向量必须来自同一模型。
重排能改善已有候选排序，不能补回召回阶段完全漏掉的资料。

## 验收与平台证据

配置验证可运行 `scripts/check_provider_readiness.py`；真实调用应另行明确启用 live 检查。
代码单元测试不替代账户配置与线上验收。

至少保存三个典型教学任务的完整证据：请求情境、知识来源、片段ID、响应、确定性验证结果、
MaaS 服务标识、耗时、失败/降级情况和教师核验意见。密钥必须遮蔽。
比较“原检索”和“增加 MaaS 重排”的同题结果，报告召回、排序、引用支持、响应时延与成本；
不能只凭模型调用成功或来源级 Recall 声称教学准确率达标。

MaaS 与星辰 Agent 是不同平台。当前三个逻辑智能体由本项目后端编排，
不能描述为已经部署到星辰 Agent。若以后将规划/监督流程发布为平台工作流，
应通过官方应用接口接入，保留本地白名单、Schema、确定性判题和引用门禁，
再记录工作流发布版本、ServiceID及调用证据。

## 财经场景

当前版本使用已登记的公开来源字段结构和固定合成数据，不调用驼灵。
模型只能在已审核模板内组织情境与任务拆分，不能获得学生身份或完整学习日志；
来源ID须在课程包中登记。详见 `docs/finance-scenario-catalog.md`。

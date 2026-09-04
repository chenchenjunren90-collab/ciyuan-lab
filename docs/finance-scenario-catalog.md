# 公开来源驱动的合成财经场景目录

## 定位

财经场景只进入计算机课程学习后的综合项目。公开来源用于证明字段结构和问题类型具有
现实依据；项目实际使用的主体、编号、日期和数值全部由本地固定规则合成，不复制个人
记录，也不把练习输出解释为真实金融、营销、信用或合规结论。

本地课程包是当前单一事实来源，便于代码审查、版本控制和RAG引用。场景模板稳定后再
导入PostgreSQL；当前不为“看起来用了数据库”而提前复制一份容易漂移的数据。

## 已登记来源与教学改编

| 场景 | 公开依据 | 权利与隐私处理 | 计算机教学重点 |
| --- | --- | --- | --- |
| 信用还款记录质量审计 | [UCI Default of Credit Card Clients](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) | CC BY 4.0；只参考字段结构，记录重新合成 | 文件解析、字段校验、异常处理、测试 |
| 银行营销活动统计 | [UCI Bank Marketing](https://archive.ics.uci.edu/dataset/222/bank+marketing) | CC BY 4.0；虚构客户编号和活动记录 | 字典分组、复合键去重、聚合与偏差说明 |
| 金融投诉分类统计 | [CFPB数据使用说明](https://www.consumerfinance.gov/complaint/data-use/) | 只参考结构化类别；不使用叙述、企业名、邮编或身份字段 | 类别映射、日期校验、隐私字段门禁 |
| 合成交易网络路径分析 | [IBM AMLSim](https://github.com/IBM/AMLSim) | Apache-2.0；自行生成小型教学图 | 邻接表、BFS/DFS、限定深度路径、复杂度 |

CFPB在2026年8月宣布停止继续公开未验证的投诉叙述，因此本项目从设计上不依赖叙述
字段，只保留虚构的产品类别、问题类别、日期、状态和按期回复等结构化字段。

## 本地文件

- Python公开来源：`course_packs/python/sources/SRC-PY-OPEN-*.yaml` 与
  `SRC-PY-OFFICIAL-CFPB-COMPLAINT.yaml`；
- Python合成边界：`SRC-PY-SYNTHETIC-FINANCE-CATALOG.yaml`；
- Python项目模板：信用质量审计、银行营销统计、金融投诉统计；
- 数据结构来源与模板：`SRC-DS-OPEN-AMLSIM.yaml`、
  `SRC-DS-SYNTHETIC-TRANSACTION-GRAPH.yaml` 与交易网络项目；
- 受控生成逻辑：`apps/api/app/modules/scenarios/generation.py`。

## 模型生成边界

`ScenarioProjectGenerator`只向模型发送非身份化的学习要求、已审核项目模板和来源ID。
模型可以调整标题、场景说明、任务拆分、约束和交付物，但不能：

1. 修改课程模板确定的计算机知识目标；
2. 使用模板之外的来源ID；
3. 加入真实姓名、证件号、手机号、地址或银行卡号；
4. 输出参考答案或完整代码；
5. 生成真实信用、营销、投资、经营或合规结论。

模型响应必须通过严格JSON Schema和来源白名单检查。格式错误、伪造引用、出现敏感字段
或模型不可用时，系统返回课程包中的固定合成项目，保证本地Demo仍可运行。

## 当前边界与下一步

当前已经完成来源登记、课程项目模板、讯飞MaaS适配器、模型输入/输出门禁、学生端生成
API、固定种子数据与前端入口。未配置模型凭据或模型输出不合规时，系统自动回退到经过
审核的固定项目，仍能完整演示。下一步是使用项目专用环境变量完成一次真实MaaS联调，
补充三种能力水平的端到端案例，并在正式发布前由课程教师复核教学内容与项目难度。

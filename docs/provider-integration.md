# 模型服务接入与验收

## 通用模型：讯飞星辰 MaaS 托管 DeepSeek-V4-Flash-0731

当前默认接入讯飞星辰MaaS的OpenAI兼容接口：
`https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions`，服务卡片模型ID为
`xopdeepseekv4flash0731`。鉴权使用 `Authorization: Bearer <APIKey>`。依据为讯飞官方
[推理服务HTTP协议](https://www.xfyun.cn/doc/spark/%E6%8E%A8%E7%90%86%E6%9C%8D%E5%8A%A1-http.html)。
该模型作为通用推理路由，用于学情规划候选、质量监督语义复核和受控项目编排。默认请求不发送 `lora_id`。

## Python 垂类辅导模型：MaaS SFT/LoRA（已训练，待优化后启用）

Python 课堂教师、助教和同伴角色可以单独路由到 MaaS 的经审核 LoRA 模型，而 C语言、数据结构和通用智能体继续使用 DeepSeek。锁定评测集位于 `training/python_tutor/v1/eval/`；实际训练候选与审核脚本位于 `training/python_tutor/v2/`。V2 的 1120 条记录已由 `AI-AUDIT-V2` 做可复现来源、格式和边界审计。Qwen3-14B 的 SFT/LoRA 任务已完成并发布为服务；`training/python_tutor/evaluation/` 中保留了评测报告。该标记不等同于教师人工签字。

训练通过后，只在未跟踪的 `.env` 写入以下非秘密标识：

```env
XFYUN_MAAS_PYTHON_TUTOR_ENABLED=false
XFYUN_MAAS_PYTHON_TUTOR_API_KEY=Python服务专用APIKey（如与通用服务不同）
XFYUN_MAAS_PYTHON_TUTOR_MODEL=模型服务卡片的modelId
XFYUN_MAAS_PYTHON_TUTOR_LORA_ID=微调任务的resourceId
```

三个变量必须同时满足“启用 + 两个标识完整”；适配器才会在 Python 课程辅导请求中发送 `lora_id`。若 LoRA 服务与通用模型的授权 Key 不同，则把服务 Key 单独写入 `XFYUN_MAAS_PYTHON_TUTOR_API_KEY`，避免覆盖通用 DeepSeek 路由。当前锁定评测中，通用 DeepSeek 自动通过 8/12，LoRA 自动通过 4/12；虽然 LoRA 的 JSON、引用和安全边界均通过，但概念解释与角色贴合度仍低于基线，因此 `XFYUN_MAAS_PYTHON_TUTOR_ENABLED` 必须保持 `false`，待补充定向样本并复训后再启用。未启用或训练服务不可用时，系统保留 DeepSeek 通用模型与确定性证据降级路径。训练请求、费用、模型卡截图和基线对比必须进入竞赛证据包。

第二轮定向训练文件位于 `training/python_tutor/v3/approved/`，共 1400 条。V3 对齐真实
五角色提示，新增课堂总结与安全拒答，并强化一条回答覆盖两项证据。建议使用 2 epoch、
`5e-6` 学习率，避免重复 V2 的低 loss 过拟合。V3 只有在锁定评测至少 9/12、严格高于
DeepSeek 且人工边界复核通过后才能启用。

模型接入前，使用 `scripts/evaluate_python_tutor_models.py --live` 分别评测当前 DeepSeek 基线和
微调路由，两个结果文件必须保留；该工具要求显式传入 `--live` 和结果 `--output`，默认不调用
外部接口。自动指标仅覆盖 JSON、引用与关键教学点，完整代码泄露、角色口吻及课程边界由课程审核人
按锁定题集的 `manual_checks` 复核。MaaS 服务卡的实际 `modelId` 与训练产物的 `resourceId` 必须以
训练完成页为准，不得自行猜测或复用演示值。

模型仅负责学习规划候选和基于证据组织语言：课程事实来自 RAG，代码正确性来自确定性
测试，质量监督会拒绝伪造引用。Python LoRA 训练教学行为与结构化输出，不替代来源核验、代码测试或画像规则。接口返回的推理过程字段不进入平台响应。

## 财经场景

当前版本不调用驼灵。财经综合项目使用已登记公开来源的字段结构和项目组固定合成数据。
模型只在已审核模板内调整场景说明与任务拆分，不获得学生身份、源代码或完整学习记录；
返回的来源ID必须在课程包中登记，否则自动降级为固定项目。具体见
`docs/finance-scenario-catalog.md`。

## 自检

```powershell
python scripts/check_provider_readiness.py
```

默认只检查配置，不发起外部请求、不消耗额度。确认授权和额度后才运行：

```powershell
python scripts/check_provider_readiness.py --live
```

密钥只写入未跟踪的 `.env`，不得出现在代码、截图、日志、Issue 或 Pull Request 中。

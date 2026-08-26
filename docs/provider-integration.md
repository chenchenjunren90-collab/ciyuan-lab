# 模型服务接入与验收

## 当前模型：讯飞星辰MaaS托管 DeepSeek-V4-Flash-0731

当前默认接入讯飞星辰MaaS的OpenAI兼容接口：
`https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions`，服务卡片模型ID为
`xopdeepseekv4flash0731`。鉴权使用 `Authorization: Bearer <APIKey>`。依据为讯飞官方
[推理服务HTTP协议](https://www.xfyun.cn/doc/spark/%E6%8E%A8%E7%90%86%E6%9C%8D%E5%8A%A1-http.html)。
项目不做模型微调，因此不发送 `lora_id`。

模型仅负责学习规划候选和基于证据组织语言：课程事实来自 RAG，代码正确性来自确定性
测试，质量监督会拒绝伪造引用。接口返回的推理过程字段不进入平台响应。

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

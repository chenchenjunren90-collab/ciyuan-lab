# 模型服务接入与验收

## 科大讯飞星火

当前默认接入 X2-Flash 的 OpenAI 兼容接口：
`https://spark-api-open.xf-yun.com/agent/v1/chat/completions`，模型名为 `spark-x`。
鉴权优先读取控制台 HTTP 协议 `APIPassword`；也兼容将 WebSocket 协议的
`APIKey:APISecret` 组合为 Bearer Token。依据为讯飞官方
[Spark-X2-Flash HTTP 协议文档](https://www.xfyun.cn/doc/spark/X2-Flash.html)。

模型仅负责学习规划候选和基于证据组织语言：课程事实来自 RAG，代码正确性来自确定性
测试，质量监督会拒绝伪造引用。接口返回的推理过程字段不进入平台响应。

## 驼灵

驼灵只用于 `post_course_finance_practice` 类型的课后综合项目，调用请求不包含学生身份、
源代码和完整学习记录。返回的来源 ID 必须已经在项目课程包中登记，否则不会展示。
接口关闭、超时或返回异常时，系统使用固定合成场景继续同一计算机任务。

校方最终接口文档未确认前，`TUOLING_BASE_URL`、鉴权和字段映射仍属于待联调项，不能宣称
完成真实调用。收到文档后只需调整 `model_adapters/tuoling.py` 的边界映射。

## 自检

```powershell
python scripts/check_provider_readiness.py
```

默认只检查配置，不发起外部请求、不消耗额度。确认授权和额度后才运行：

```powershell
python scripts/check_provider_readiness.py --live
```

密钥只写入未跟踪的 `.env`，不得出现在代码、截图、日志、Issue 或 Pull Request 中。

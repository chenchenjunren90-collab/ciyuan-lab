# Python 垂类辅导模型训练包 v1

本目录为“词元研究所”Python 课程辅导模型的 MaaS SFT/LoRA 训练准备材料。它只训练教学行为：循序讲解、分层提示、Debug 引导、角色边界、课程范围约束与结构化输出；课程事实、引用、代码判题和学生画像仍分别由 RAG、规则与业务服务负责。

## 状态与边界

- 目录下的 `candidates/` 是从项目组 Python 课程包机械生成的**待人工审核候选集**，禁止直接上传或声称为已完成的训练数据。
- `eval/golden.jsonl` 是锁定评测集，不得合并入候选训练集，也不得上传至 MaaS 的训练集。
- 候选集不读取练习的 `evaluation.tests`、隐藏测试、学生记录、环境变量或外部密钥。
- 课程包目前仍是 MVP `draft` 内容；每条候选必须经过可追溯审核后才能进入训练集。优先由具备 Python
  教学能力的审核人复核；项目负责人也可授权执行可复现的 AI 审计，但必须如实保留 `AI-AUDIT-V1` 标记，
  不得表述为教师人工签字。

## 生成与校验

在仓库根目录运行：

```powershell
python scripts/build_python_tutor_sft_candidates.py
python scripts/validate_python_tutor_dataset.py
```

生成结果：

- `candidates/sharegpt-python-tutor-v1.jsonl`：纯 ShareGPT 训练候选，供审核后复制为提交文件；
- `candidates/review-manifest.jsonl`：逐条来源、类别、哈希和审核状态；
- `candidates/review-queue.csv`：供课程教师或助教审核的可编辑队列；
- `candidates/summary.json`：候选数量及类别统计。

审核人把 `review_status` 改为 `approved`，填写非身份化的 `reviewer_code` 和必要备注后，运行：

```powershell
python scripts/export_reviewed_python_tutor_dataset.py
```

该命令默认要求至少 200 条审核通过的数据，才导出 `approved/sharegpt-python-tutor-v1-approved.jsonl`。评测集始终单独保留。

项目负责人授权的 AI 审计会先逐条复现数据来源，再检查 JSON、引用、角色、长度、代码泄露与敏感标记。
默认只验证，不改审核状态；确认后才使用 `--apply`，并输出 `candidates/ai-audit-report.json`：

```powershell
python scripts/audit_python_tutor_sft_candidates.py
python scripts/audit_python_tutor_sft_candidates.py --apply
```

## MaaS 提交配置（待人工确认）

1. 进入 MaaS 的“数据集”，创建**文本对话数据 / SFT-RL / ShareGPT**数据集；
2. 上传经审核后的 JSONL 文件，不上传 `golden.jsonl` 或审核清单；
3. 首轮选择当前平台可精调的 **Qwen3-14B**；训练类型为 SFT，方法为 LoRA。它用于验证本项目的
   中文教学角色、结构化 JSON 与课程边界等行为，而非替代通用推理模型；
4. 首轮保守使用平台默认的 15% 内部测试集、3 个 epoch、学习率 `1e-5`、最大序列长度 2048、bf16、LoRA Rank 8、Alpha 16、Dropout 0.1；
5. 记录训练任务截图、基础模型、数据版本、参数、费用、生成模型 ID 与 `lora_id/resourceId`；
6. 在接入课堂前，使用 `eval/golden.jsonl` 对比基础模型、DeepSeek 通用模型与微调模型。

选择理由是：本轮候选数据量为 280 条，目标是受证据约束的教学表达与工具调用格式，先以 14B 规模
验证“微调是否带来可测增益”比直接选择更大基座更容易控制数据质量、费用与回滚风险。若页面显示的
首轮费用超出项目可接受范围，则暂停提交，不自动降级；由项目负责人确认后再改用当前平台可精调的
Qwen3-4B 作为成本受限的对照方案。Spark X2 当前只作为推理模型展示，不作为本轮零代码精调基座。

训练提交会开启自动付费；只有项目负责人确认上述基座、页面显示的预估费用和审核记录后才能点击提交。

## 锁定评测与接入门槛

`eval/golden.jsonl` 包含 12 条不进入训练集的锁定题目，覆盖概念讲解、误区纠正、分层提示、
Debug、同伴讨论、课程范围拒答、测试边界和安全拒答。每一轮模型比较均使用同一份文件，
并同时检查：严格 JSON、有效引用、关键教学点和人工教学质量复核。

默认只校验评测集文件，不调用 MaaS：

```powershell
python scripts/evaluate_python_tutor_models.py
```

在训练后，且已确认推理额度时，分别运行“当前 DeepSeek 通用模型”和“新 LoRA 路由”的评测。
必须把两个结果保存到不同的文件中：

```powershell
python scripts/evaluate_python_tutor_models.py --live `
  --output training/python_tutor/v1/eval/results/deepseek-baseline.json

python scripts/evaluate_python_tutor_models.py --live `
  --model <MaaS模型服务卡modelId> `
  --lora-id <已完成训练的resourceId> `
  --output training/python_tutor/v1/eval/results/python-tutor-lora-v1.json
```

报告中的 `automatic_pass_rate` 只代表结构、引用和关键点的可自动检查，不替代人工判断。
每条结果仍要按照 `manual_checks` 复核：是否泄露完整解法、是否符合对应角色口吻、是否在课程范围内。
只有微调模型不低于 DeepSeek 基线、无测试边界泄露，并经课程审核人确认后，才能把它的两个
标识填入本地 `.env` 并开启 Python 课堂路由。

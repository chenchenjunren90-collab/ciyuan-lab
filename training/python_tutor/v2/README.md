# Python 垂类辅导模型训练包 v2

V2 是用于 MaaS 首轮训练的扩展数据集。V1 的 280 条候选在 MaaS 页面被提示“数据集内容较小，存在训练失败风险”，因此 V1 仅保留为生成与审计原型，不再作为本轮上传数据。

## 数据与边界

- 已导出的训练文件：`approved/sharegpt-python-tutor-v2-approved.jsonl`；共 **1120** 条、约 **1.49 MiB**。
- 七个类别各 160 条：教师讲解、助教误区纠正、助教分层提示、同伴讨论、同伴 Debug、课程范围拒答、测评边界拒答。
- 数据只从 `course_packs/python/` 的公开概念、公开题面与公开提示机械生成；不读取 `evaluation.tests`、学生数据、环境变量或密钥。
- `candidates/ai-audit-report.json` 记录了 `AI-AUDIT-V2`：每条可从课程包复现，并通过 JSON、引用、角色、字数、代码围栏和敏感标记检查。该记录不是教师人工签字。
- `eval/golden.jsonl` 仍属于 V1 的锁定评测集；不得上传为训练数据。

## 复现与导出

```powershell
python scripts/build_python_tutor_sft_v2_candidates.py
python scripts/validate_python_tutor_dataset.py `
  --dataset training/python_tutor/v2/candidates/sharegpt-python-tutor-v2.jsonl `
  --manifest training/python_tutor/v2/candidates/review-manifest.jsonl
python scripts/audit_python_tutor_sft_candidates.py `
  --candidate-root training/python_tutor/v2/candidates `
  --source-version v2 --apply
python scripts/export_reviewed_python_tutor_dataset.py `
  --dataset training/python_tutor/v2/candidates/sharegpt-python-tutor-v2.jsonl `
  --manifest training/python_tutor/v2/candidates/review-manifest.jsonl `
  --review-queue training/python_tutor/v2/candidates/review-queue.csv `
  --output-root training/python_tutor/v2/approved `
  --minimum-records 1000
```

## MaaS 上传设置

创建新数据集时选择：**文本对话数据 / 训练集 / SFT-RL / Sharegpt**，上传
`approved/sharegpt-python-tutor-v2-approved.jsonl`。训练页选择 **Qwen3-14B / SFT / LoRA**，
先保留平台默认的学习率 `1e-5`、3 epoch、序列长度 2048、bf16、Rank 8、Alpha 16、Dropout 0.1。

如果平台不再显示“小数据集”风险，记录预估费用但不要提交；需先由项目负责人确认自动付费。训练完成后，使用 V1 的锁定评测集同时对比 DeepSeek 基线与 LoRA 路由，达标后才接入 Python 课堂。
